// Verdict log — the resolution ledger for the verdict-chip flywheel.
//
// Every time an analyst resolves a dossier self-critique (drops an unrelated
// receipt, flags a single-sourced claim, relabels an unreliable thread), the
// decision lands here with full provenance. This log IS the #204 gold the
// labeler is starved for: a human saying THIS label/receipt is wrong, WHICH one,
// and WHY — grounded in the receipts they were looking at.
//
// Storage is localStorage (`atlas.verdictlog.v1`) — per-browser, evictable; the
// durable copy is exportVerdictLog() (same discipline as the workbench store).
import { track } from './telemetry'

export interface VerdictLogEntry {
  id: string
  investigationId: string
  /** The dossier target the critique attached to (pin anchorId / citation id). */
  dossierTargetId: string
  targetKind: string
  /** The critique kind (e.g. 'single-sourced'). */
  critique: string
  /** The action taken (e.g. 'needs-corroboration'). */
  action: string
  /** Receipt provenance the analyst was looking at (urls, else headlines). */
  citations: string[]
  resolvedAt: string
}

export type VerdictLogInput = Omit<VerdictLogEntry, 'id' | 'resolvedAt'>

const STORE_KEY = 'atlas.verdictlog.v1'

interface StoreShape { entries: VerdictLogEntry[] }

function read(): StoreShape {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    if (!raw) return { entries: [] }
    const parsed = JSON.parse(raw) as StoreShape
    if (!Array.isArray(parsed.entries)) return { entries: [] }
    return parsed
  } catch {
    return { entries: [] }
  }
}

function write(store: StoreShape): void {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(store))
  } catch { /* quota/eviction: export is the durability mechanism */ }
}

/** Record one resolution + fire the gold telemetry. Returns the stamped entry. */
export function logVerdict(input: VerdictLogInput): VerdictLogEntry {
  const entry: VerdictLogEntry = {
    ...input,
    id: `vl-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    resolvedAt: new Date().toISOString(),
  }
  const store = read()
  store.entries.push(entry)
  write(store)
  // The #204 gold signal: {kind, target, provenance}.
  track('verdict_resolved', {
    kind: entry.critique,
    action: entry.action,
    target: entry.dossierTargetId,
    target_kind: entry.targetKind,
    provenance: entry.citations,
    investigation_id: entry.investigationId,
  })
  return entry
}

export function listVerdictLog(investigationId?: string): VerdictLogEntry[] {
  const all = read().entries
  return investigationId ? all.filter(e => e.investigationId === investigationId) : all
}

/** True when this target already has a logged resolution for the given action —
 *  drives the chip's resolved state (so it doesn't re-offer a done decision). */
export function isTargetResolved(
  investigationId: string, dossierTargetId: string, action: string,
): boolean {
  return read().entries.some(e =>
    e.investigationId === investigationId &&
    e.dossierTargetId === dossierTargetId &&
    e.action === action)
}

/** Remove an entry (the toast+undo path — undo a resolution). */
export function undoVerdict(id: string): void {
  const store = read()
  store.entries = store.entries.filter(e => e.id !== id)
  write(store)
}

/** Portable gold export (the durable copy). */
export function exportVerdictLog(investigationId?: string): string {
  return JSON.stringify(
    {
      format: 'atlas-verdict-log-v1',
      exportedAt: new Date().toISOString(),
      entries: listVerdictLog(investigationId),
    },
    null,
    2,
  )
}
