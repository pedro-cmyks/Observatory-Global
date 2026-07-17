// Verdict-chip flywheel (Inés's big idea). The dossier already surfaces
// self-critiques — "metadata only", "matched the taxonomy, not evidence",
// "isolated", "single-sourced". Each is dead text today. This turns EACH into an
// ACTIONABLE chip: a critique KIND resolves to an ACTION the analyst can take,
// and every resolution is logged with full provenance (verdictLog) — which IS the
// #204 gold the labeler is starved for (the analyst telling us the label/receipt
// is wrong, and which receipts they were looking at).
import type { WorkbenchPin } from './workbench'

/** The four self-critique classes the dossier can raise. */
export type VerdictCritiqueKind =
  | 'label-unreliable'   // the served label doesn't hold against its receipts
  | 'unrelated-receipt'  // a pinned item connects to nothing / didn't clear the gate
  | 'single-sourced'     // the claim rests on one outlet — needs corroboration
  | 'stale-snapshot'     // metadata-only / frozen-and-drifted — no live receipts

/** The action each critique offers. */
export type VerdictActionKind =
  | 'split-relabel'
  | 'drop-receipt'
  | 'needs-corroboration'
  | 'request-snapshot'

export interface VerdictAction {
  kind: VerdictActionKind
  /** Button copy. */
  label: string
  /** data-tip: what resolving actually does. */
  tip: string
  /** true = the action mutates/removes pinned state (drop-receipt). Drives the
   *  toast+undo path and a confirm-friendly styling. */
  destructive: boolean
}

const ACTIONS: Record<VerdictCritiqueKind, VerdictAction> = {
  'label-unreliable': {
    kind: 'split-relabel',
    label: 'Split / relabel',
    tip: 'Flag this label as not matching its receipts — logged as gold so the labeler learns the boundary. The frozen receipts are kept.',
    destructive: false,
  },
  'unrelated-receipt': {
    kind: 'drop-receipt',
    label: 'Drop receipt',
    tip: 'Remove this receipt from the investigation — it connects to nothing pinned. The removal is logged with provenance.',
    destructive: true,
  },
  'single-sourced': {
    kind: 'needs-corroboration',
    label: 'Needs corroboration',
    tip: 'Flag this claim as resting on a single outlet — logged so corroboration is owed before it publishes.',
    destructive: false,
  },
  'stale-snapshot': {
    kind: 'request-snapshot',
    label: 'Request snapshot',
    tip: 'This pin froze metadata only (no receipts) — log a request to re-capture live evidence for it.',
    destructive: false,
  },
}

/** The tested core: a critique kind → the action the chip offers. */
export function resolveVerdictAction(kind: VerdictCritiqueKind): VerdictAction {
  return ACTIONS[kind]
}

/** Best-effort classifier: map a free-form critique sentence (a dossier gap line,
 *  a label-review reason, a node-state phrase) to a critique kind. Returns null
 *  when nothing matches (the sentence is not an actionable self-critique). Order
 *  matters — the most specific classes are tested first. */
export function classifyCritique(reason: string): VerdictCritiqueKind | null {
  const r = reason.toLowerCase()
  if (/single[- ]?source|single outlet|one outlet|one source|uncorroborat|not corroborat/.test(r)) {
    return 'single-sourced'
  }
  if (/label[- ]?(failed|partial)|under review|low[- ]?confidence|did not match|not match its receipts|only partially match|taxonomy|not found evidence|keyword[- ]?only/.test(r)) {
    return 'label-unreliable'
  }
  if (/metadata only|no frozen evidence|without frozen evidence|no snapshot|stale|drifted|frozen at pin time/.test(r)) {
    return 'stale-snapshot'
  }
  if (/unrelated|isolated|connect to nothing|similar[- ]?only|coverage[- ]?context|below[- ]?gate|did not clear the (quality )?gate|not verified coverage|candidate material/.test(r)) {
    return 'unrelated-receipt'
  }
  return null
}

// ── pin evidence predicates (pure) ──────────────────────────────────────────

/** Distinct, case-folded, non-empty sources across a pin's frozen evidence. */
export function pinEvidenceSources(pin: Pick<WorkbenchPin, 'snapshot'>): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const e of pin.snapshot?.evidence ?? []) {
    const s = (e.source ?? '').trim().toLowerCase()
    if (!s || seen.has(s)) continue
    seen.add(s)
    out.push(s)
  }
  return out
}

/** True when the pin has frozen evidence but it all rests on ONE outlet — the
 *  claim is single-sourced. No evidence at all is metadata-only, not this. */
export function isSingleSourced(pin: Pick<WorkbenchPin, 'snapshot'>): boolean {
  const ev = pin.snapshot?.evidence ?? []
  if (ev.length === 0) return false
  return pinEvidenceSources(pin).length <= 1
}

/** True when the pin froze metadata only — no evidence rows to stand on. */
export function isMetadataOnly(pin: Pick<WorkbenchPin, 'snapshot'>): boolean {
  return (pin.snapshot?.evidence ?? []).length === 0
}

// ── derivation ──────────────────────────────────────────────────────────────

export type ConnectionNodeState =
  | 'grounded' | 'text-linked' | 'context-only' | 'similar-only' | 'isolated'

/** Minimal shape from the connection measurement: a pin's topic id + its verdict
 *  state. Isolated / similar-only nodes are the "unrelated" self-critique. */
export interface NodeStateRef { id: string; state: ConnectionNodeState }

export interface VerdictChipDescriptor {
  /** Stable id per (kind, targetKind, targetId) — idempotent across renders. */
  id: string
  kind: VerdictCritiqueKind
  targetId: string
  targetKind: 'pin' | 'citation' | 'node'
  /** The human critique sentence the chip stands next to. */
  critique: string
  /** Receipt provenance the analyst is looking at (urls, else headlines) — the
   *  #204 gold captured on resolution. */
  provenance: string[]
}

function chipId(kind: VerdictCritiqueKind, targetKind: string, targetId: string): string {
  return `verdict:${kind}:${targetKind}:${targetId}`
}

/** Receipt provenance for a pin: prefer urls, fall back to headlines. */
function pinProvenance(pin: WorkbenchPin): string[] {
  return (pin.snapshot?.evidence ?? []).map(e => e.url || e.headline).filter(Boolean)
}

/** Pure: turn the frozen pins + the measured connection node states into the set
 *  of actionable chips the dossier renders. A pin can raise more than one chip
 *  (e.g. single-sourced AND label-unreliable) — each is independently resolvable. */
export function deriveVerdictChips(
  pins: WorkbenchPin[],
  nodeStates: NodeStateRef[] = [],
): VerdictChipDescriptor[] {
  const stateById = new Map(nodeStates.map(n => [n.id, n.state]))
  const chips: VerdictChipDescriptor[] = []
  for (const p of pins) {
    const prov = pinProvenance(p)
    if (isMetadataOnly(p)) {
      chips.push({
        id: chipId('stale-snapshot', 'pin', p.anchorId),
        kind: 'stale-snapshot', targetId: p.anchorId, targetKind: 'pin',
        critique: `“${p.label}” froze metadata only — no receipts to stand on.`,
        provenance: prov,
      })
      continue // a metadata-only pin can't also be single-sourced or unrelated
    }
    if (isSingleSourced(p)) {
      chips.push({
        id: chipId('single-sourced', 'pin', p.anchorId),
        kind: 'single-sourced', targetId: p.anchorId, targetKind: 'pin',
        critique: `“${p.label}” rests on a single outlet — corroboration owed.`,
        provenance: prov,
      })
    }
    if (p.matchBasis === 'topic_description') {
      chips.push({
        id: chipId('label-unreliable', 'pin', p.anchorId),
        kind: 'label-unreliable', targetId: p.anchorId, targetKind: 'pin',
        critique: `“${p.label}” matched the taxonomy description, not found evidence.`,
        provenance: prov,
      })
    }
    const st = stateById.get(p.anchorId)
    if (st === 'isolated' || st === 'similar-only') {
      chips.push({
        id: chipId('unrelated-receipt', 'pin', p.anchorId),
        kind: 'unrelated-receipt', targetId: p.anchorId, targetKind: 'pin',
        critique: st === 'isolated'
          ? `“${p.label}” connects to nothing else pinned.`
          : `“${p.label}” is only semantically similar — no shared actor or coverage.`,
        provenance: prov,
      })
    }
  }
  return chips
}
