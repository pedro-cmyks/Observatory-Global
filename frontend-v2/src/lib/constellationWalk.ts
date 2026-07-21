// The walked constellation (contract constellation-walk-v0).
//
// Spec: docs/superpowers/specs/2026-07-21-multi-hop-transitive-chains.md. From the
// analyst's pins, the backend walks the whitened topic graph outward and returns
// KIN by honest distance: a HERMANO (a direct measured edge) or a PRIMO Nº (reached
// only by traversing intermediaries — "no direct line, only this trail"). This lib
// fetches that walk and derives, PURELY (unit-testable), the RADIAL layout + the
// honesty grammar (spec §1.5):
//   - node size RECEDES with distance-from-ground (pin biggest → far primo faintest)
//   - line style: SOLID = hermano · DASHED = primo (more gaps / fainter further out)
//   - line THICKNESS = accumulated weight (honesty + brake, one number)
//   - RADIAL layout, pin at center, kin outward by degree — a left-to-right chain is
//     FORBIDDEN (a sequential row imports the causation the walk exists to kill;
//     form beats a degree label). v1 is UNDIRECTED — no causal arrow anywhere.
import type { Investigation } from './workbench'
import { connectionTopicIds } from './dossierConnections'

export type WalkKinship = 'hermano' | 'primo'

export interface WalkVia {
  parent_id: string | null
  parent_label: string | null
  /** v1 receipt basis: the walk graph is whitened-semantic. */
  basis: string
  /** RAW whitened cosine of this hop — the honest measured receipt. */
  weight: number
  /** the hop passed OUT of a flagged vague-blob connector (grab-bag topic). */
  through_blob: boolean
}

export interface WalkKin {
  id: string
  label: string
  category: string | null
  /** hop-count of the MAX-PRODUCT path from its seed (spec B1). */
  degree: number
  kinship: WalkKinship
  /** product of the hop weights — the trail thickness (spec §1.5). */
  acc_weight: number
  via: WalkVia
  /** this node is itself a flagged vague-blob connector. */
  is_blob: boolean
  /** same-event fragments folded into this representative (spec §2.6). */
  folded_count: number
  folded_labels: string[]
  /** a typed energy/oil destination match (spec §2.7), or null. */
  destination: string | null
}

export interface WalkSeed {
  id: string
  label: string
  category: string | null
}

export interface WalkMeta {
  reason: string | null
  topic_universe?: number
  rel_floor?: number
  hop_cap?: number
  k_neighbors?: number
  blob_connectors?: number
  dedup_tau?: number
  reached_before_dedup?: number
  hermanos?: number
  primos?: number
  max_degree?: number
  semantic_space?: string
  walk?: string
}

export interface WalkData {
  contract: string
  seeds: WalkSeed[]
  kin: WalkKin[]
  unresolved: string[]
  meta: WalkMeta
}

/** POST the pins to the walk endpoint. `relFloor` is the "¿hasta dónde caminar?"
 *  slider (spec §2.3); HOP_CAP is fixed server-side. Degrades to null (absence). */
export async function fetchWalk(
  inv: Investigation, relFloor = 0.35,
): Promise<WalkData | null> {
  const topicIds = connectionTopicIds(inv)
  if (topicIds.length < 1) return null
  try {
    const res = await fetch('/api/v2/dossier/walk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic_ids: topicIds, rel_floor: relFloor }),
    })
    if (!res.ok) return null
    const d = await res.json() as WalkData
    if (!Array.isArray(d.kin) || !Array.isArray(d.seeds)) return null
    return d
  } catch {
    return null // absence — the frozen report always stands alone
  }
}

// ── Degree filter (the analyst walks it, the app never pushes the whole chain) ──
/** Kin whose degree is within the currently-revealed depth. "¿Ver primos?" raises
 *  `maxDegree` one step at a time (spec §4). */
export function visibleKin(kin: WalkKin[], maxDegree: number): WalkKin[] {
  return kin.filter(k => k.degree <= maxDegree)
}

/** The next degree the analyst could reveal, or null when the walk is exhausted. */
export function nextDegree(kin: WalkKin[], maxDegree: number): number | null {
  const deeper = kin.filter(k => k.degree > maxDegree).map(k => k.degree)
  return deeper.length ? Math.min(...deeper) : null
}

// ── Honesty grammar ───────────────────────────────────────────────────────────
export type WalkColorRole = 'hermano' | 'primo' | 'blob' | 'destination'

/** Line/stroke role for a hop (spec §1.5). A trail through a blob connector is
 *  flagged (warning tint); a typed destination is highlighted; otherwise the
 *  kinship carries it (solid hermano / dashed primo). Color = the "why". */
export function hopColorRole(k: WalkKin): WalkColorRole {
  if (k.destination) return 'destination'
  if (k.via.through_blob || k.is_blob) return 'blob'
  return k.kinship
}

export const WALK_COLORS: Record<WalkColorRole, string> = {
  hermano: '#34d399',      // measured-direct green
  primo: '#7dd3fc',        // walked-cousin cyan
  blob: '#f59e0b',         // trail through a grab-bag topic — verify
  destination: '#c084fc',  // a typed energy/oil arrival
}

/** Stroke dash for a hop: SOLID for a hermano (direct), DASHED for a primo with
 *  progressively larger gaps the further the cousin (spec §1.5). undefined = solid. */
export function hopDash(k: WalkKin): string | undefined {
  if (k.kinship === 'hermano') return undefined
  // 2º "3 3", 3º "2 5" — more gap, fainter, the further out
  const gap = 2 + Math.max(0, k.degree - 2) * 2
  return `3 ${gap}`
}

/** Line thickness = accumulated weight (spec §1.5: honesty + brake, one number).
 *  Scaled into a legible px band; a strong near hermano is thick, a far primo thin. */
export function hopWidth(k: WalkKin, min = 0.5, max = 3.0): number {
  const w = Math.max(0, Math.min(1, k.acc_weight))
  return Math.round((min + (max - min) * w) * 100) / 100
}

/** Node radius RECEDES with degree — the pin (degree 0) is biggest, a far primo
 *  smallest/faintest (spec §1.5). */
export function nodeRadius(degree: number, base = 7): number {
  return Math.max(2.5, base - degree * 1.4)
}

/** Node opacity fades with distance-from-ground (spec §1.5). */
export function nodeOpacity(degree: number): number {
  return Math.max(0.4, 1 - degree * 0.18)
}

/** The always-visible honesty label: "hermano" (direct) or "primo Nº" (walked).
 *  The degree label carries the "indirect, N hops, no direct touch" by construction. */
export function degreeLabel(k: WalkKin): string {
  if (k.kinship === 'hermano') return 'hermano'
  return `primo ${k.degree}º`
}

/** The per-hop receipt line (glass-box, spec §1.3): why + how strong + honest
 *  caveats. Never asserts a causal chain — states the measured hop. */
export function receiptLine(k: WalkKin): string {
  const parts: string[] = []
  const pct = Math.round(k.via.weight * 100)
  if (k.via.parent_label) {
    parts.push(`via ${k.via.parent_label} — semantic ${pct}%`)
  } else {
    parts.push(`semantic ${pct}%`)
  }
  if (k.via.through_blob) parts.push('through a grab-bag topic (verify)')
  if (k.folded_count > 0) parts.push(`+${k.folded_count} same-event fragment${k.folded_count === 1 ? '' : 's'}`)
  if (k.destination) parts.push(`typed destination: ${k.destination}`)
  return parts.join(' · ')
}

// ── Pure radial layout ─────────────────────────────────────────────────────────
export interface WalkPlacedNode {
  id: string
  label: string
  degree: number         // 0 = seed/pin
  kinship: WalkKinship | 'seed'
  px: number
  py: number
  angle: number
  kin?: WalkKin          // absent for seeds
}

function hashAngle(id: string): number {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0
  return (Math.abs(h) % 360) * (Math.PI / 180)
}

/** RADIAL layout: seeds at/near the center, kin on concentric rings by DEGREE, each
 *  kin fanned around its parent's angle so a trail reads OUTWARD (never a left-to-
 *  right chain — spec §1.5). Pure + deterministic. Nodes whose parent is a folded
 *  (non-represented) node fall back to a stable hash angle. */
export function layoutWalkRadial(
  seeds: WalkSeed[], kin: WalkKin[], width: number, height: number, pad = 26,
): WalkPlacedNode[] {
  const W = Math.max(1, width), H = Math.max(1, height)
  const cx = W / 2, cy = H / 2
  const maxDeg = Math.max(1, ...kin.map(k => k.degree))
  const usableR = Math.max(1, Math.min(W, H) / 2 - pad)
  const step = usableR / maxDeg
  const angle = new Map<string, number>()
  const out: WalkPlacedNode[] = []

  // Seeds: single at center; multiple on a tiny central ring so each has an angle.
  const seedR = seeds.length > 1 ? step * 0.35 : 0
  seeds.forEach((s, i) => {
    const a = seeds.length === 1 ? -Math.PI / 2 : (i / seeds.length) * Math.PI * 2 - Math.PI / 2
    angle.set(s.id, a)
    out.push({
      id: s.id, label: s.label, degree: 0, kinship: 'seed', angle: a,
      px: cx + Math.cos(a) * seedR, py: cy + Math.sin(a) * seedR,
    })
  })

  // Group kin by parent so siblings fan within a wedge around the parent's angle.
  const byParent = new Map<string, WalkKin[]>()
  for (const k of kin) {
    const p = k.via.parent_id ?? '~root'
    byParent.set(p, [...(byParent.get(p) ?? []), k])
  }

  // Assign angles degree-by-degree (parents placed before children).
  for (let d = 1; d <= maxDeg; d++) {
    const atDeg = kin.filter(k => k.degree === d)
    for (const k of atDeg) {
      const parentId = k.via.parent_id
      const siblings = byParent.get(parentId ?? '~root') ?? [k]
      const base = (parentId !== null && angle.has(parentId))
        ? angle.get(parentId)!
        : hashAngle(k.id)             // folded/unknown parent → stable fallback
      const n = siblings.length
      const idxInSibs = Math.max(0, siblings.indexOf(k))
      // wedge widens with sibling count but never wraps; deeper rings fan tighter
      const spread = Math.min(Math.PI * 1.4, n * 0.5) / Math.max(1, d)
      const a = n === 1 ? base : base + (idxInSibs / (n - 1) - 0.5) * spread
      angle.set(k.id, a)
      const r = d * step
      out.push({
        id: k.id, label: k.label, degree: d, kinship: k.kinship, angle: a,
        px: cx + Math.cos(a) * r, py: cy + Math.sin(a) * r, kin: k,
      })
    }
  }
  return out
}
