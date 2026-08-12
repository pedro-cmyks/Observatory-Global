// Brief row source-count honesty (cold-user probe 2026-08-12, "the one internal
// contradiction I'd call a bug, not a degradation").
//
// The probe read: "Russian Air Defense Shoots Down Ukrainian Drones — 116
// SIGNALS · 0 sources" with no receipts at all. 116 signals from zero sources
// is not a possible state, and the Brief asserted it as a measurement.
//
// It is not a possible state because the two numbers come from DIFFERENT
// lineages (backend/app/services/thread_intelligence.py:assemble_dynamic_thread):
//   • signal_count  = `recent_n_signals`, a persisted per-snapshot count.
//   • source_count  = `len(sources)`, derived from the RESOLVED receipt sample
//                     (`sample_signal_ids` → live `signals_v2` rows).
// When the receipt sample resolves to nothing (7-day hot retention deleted the
// rows the snapshot's sample ids point at), the count survives and the source
// lane returns zero. Zero there means "the receipt lane could not answer",
// never "this story was published by no one".
//
// So: a zero here is a DEGRADED STATE, not a measurement. It renders as one.
// The backend keeps its own half of the fix (prefer live ids when slicing the
// sample); this module guarantees the page can never assert the impossible
// state again, whichever lane goes quiet.

export type UnmeasuredSourceReason =
  /** No receipt resolved for this row at all — the sample lane came back empty. */
  | 'no_receipts_carried'
  /** Receipts exist, but none of them carries an outlet name to count. */
  | 'receipts_carry_no_outlet'

export type SourceCountBasis =
  | { kind: 'measured'; count: number }
  | { kind: 'unmeasured'; reason: UnmeasuredSourceReason; emptyField: string }

export interface SourceCountRow {
  thread_id?: string
  signal_count?: number
  source_count?: number | null
  evidence_samples?: readonly unknown[] | null
}

/** The degraded chip's words. States that we did not measure — never a number,
 *  never a claim about how many outlets exist. */
export const UNMEASURED_SOURCES_LABEL = 'sources not measured'

/**
 * Decide what the row may honestly print for "sources".
 *
 * - absent `source_count`      → null (render nothing, unchanged behaviour)
 * - positive count             → measured
 * - zero / negative / NaN      → unmeasured, with the upstream field that came
 *                                back empty named for the log
 */
export function resolveSourceCount(row: SourceCountRow): SourceCountBasis | null {
  const raw = row.source_count
  if (raw == null) return null
  if (typeof raw === 'number' && Number.isFinite(raw) && raw > 0) {
    return { kind: 'measured', count: raw }
  }
  const receipts = row.evidence_samples ?? []
  if (receipts.length === 0) {
    return { kind: 'unmeasured', reason: 'no_receipts_carried', emptyField: 'evidence_samples' }
  }
  return { kind: 'unmeasured', reason: 'receipts_carry_no_outlet', emptyField: 'source_name' }
}

/** Plain-language explanation for the data-tip. Never asserts an outlet count. */
export function sourceCountTip(basis: SourceCountBasis): string {
  if (basis.kind === 'measured') {
    return `${basis.count.toLocaleString('en-US')} distinct outlets in this row's resolved receipt sample — the readable subset, not every outlet that published.`
  }
  if (basis.reason === 'no_receipts_carried') {
    return 'The receipt sample for this story came back empty this window, so its outlets were not counted. The signal count comes from a different lineage and survives — read the story to see its sources.'
  }
  return 'Receipts resolved for this story but none carried an outlet name, so the outlet count could not be measured. Not a claim that no outlet published it.'
}

/** The dev-console line: which row, and which upstream field was empty. */
export function formatSourceCountWarning(threadId: string, basis: SourceCountBasis): string {
  if (basis.kind === 'measured') return ''
  return `[brief] source count unmeasured for ${threadId}: ${basis.reason} (upstream field empty: ${basis.emptyField}); signal count served from a separate lineage`
}

const warned = new Set<string>()

/** Test seam — resets the once-per-thread warning memo. */
export function __resetSourceCountWarnings(): void {
  warned.clear()
}

/**
 * Warn ONCE per thread per session. The Brief re-renders often; a per-render
 * warn would bury the signal it exists to raise.
 */
export function logUnmeasuredSourceCount(threadId: string, basis: SourceCountBasis): void {
  if (basis.kind === 'measured') return
  if (warned.has(threadId)) return
  warned.add(threadId)
  console.warn(formatSourceCountWarning(threadId, basis))
}
