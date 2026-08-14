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

/**
 * WHICH receipt sample the backend counted the outlets over. Both are samples
 * of what Atlas ingests; neither is ever every outlet that published.
 *
 * - `receipt_sample`     the receipts this row renders. Capped at 24 by the
 *                        list SQL, so it SATURATES for busy stories (the live
 *                        front page served 23, 22, 18, 21, 23, 23 across its
 *                        top rows — pinned at the cap, so every big story
 *                        looked the same size).
 * - `snapshot_receipts`  the frozen `sample_receipts` of the story's latest
 *                        clustering pass (migration 097), which is wider
 *                        exactly where that cap binds: 12 of 40 front-page
 *                        rows, e.g. 132 outlets over 148 frozen receipts while
 *                        the page shows 24. The page therefore shows FEWER
 *                        receipts than the number was counted over, and the
 *                        copy has to say so.
 */
export type SourceCountPopulation = 'receipt_sample' | 'snapshot_receipts'

export type SourceCountBasis =
  | {
      kind: 'measured'
      count: number
      /** Absent on hand-built callers; treated as `receipt_sample`. */
      population?: SourceCountPopulation
      /** Receipts the count was measured over, when the row declares it. */
      sampleSize?: number
    }
  | { kind: 'unmeasured'; reason: UnmeasuredSourceReason; emptyField: string }

export interface SourceCountRow {
  thread_id?: string
  signal_count?: number
  source_count?: number | null
  /** Backend `source_count_basis`. An unknown value is not trusted. */
  source_count_basis?: SourceCountPopulation | null
  /** Backend `source_sample_size` — the population, not what is rendered. */
  source_sample_size?: number | null
  evidence_samples?: readonly unknown[] | null
}

const KNOWN_POPULATIONS: readonly SourceCountPopulation[] = [
  'receipt_sample',
  'snapshot_receipts',
]

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
    // An unrecognised basis is NOT trusted: falling back to the served
    // receipts can only understate the population, while trusting an unknown
    // string could let a future/typo'd lane borrow the widest wording.
    const declared = row.source_count_basis
    const population: SourceCountPopulation =
      declared != null && KNOWN_POPULATIONS.includes(declared) ? declared : 'receipt_sample'
    const rendered = (row.evidence_samples ?? []).length
    const declaredSize = row.source_sample_size
    const sampleSize =
      population === 'snapshot_receipts'
        && typeof declaredSize === 'number' && Number.isFinite(declaredSize) && declaredSize > 0
        ? declaredSize
        : rendered
    return { kind: 'measured', count: raw, population, sampleSize }
  }
  const receipts = row.evidence_samples ?? []
  if (receipts.length === 0) {
    return { kind: 'unmeasured', reason: 'no_receipts_carried', emptyField: 'evidence_samples' }
  }
  return { kind: 'unmeasured', reason: 'receipts_carry_no_outlet', emptyField: 'source_name' }
}

/** Plain-language explanation for the data-tip. Never asserts an outlet count. */
export function sourceCountTip(
  basis: SourceCountBasis,
  opts?: { receiptsShown?: number },
): string {
  if (basis.kind === 'measured') {
    const n = basis.count.toLocaleString('en-US')
    if (basis.population === 'snapshot_receipts') {
      const over = basis.sampleSize
        ? ` across the ${basis.sampleSize.toLocaleString('en-US')} receipts frozen with this story's latest clustering pass`
        : " in this story's latest clustering pass"
      const shown = opts?.receiptsShown
      // Only claim a hidden remainder when there provably is one — a row that
      // renders everything it counted must not imply it is holding some back.
      const rest = shown != null && basis.sampleSize != null && shown < basis.sampleSize
        ? ` This page shows the ${shown.toLocaleString('en-US')} most recent of them.`
        : ''
      return `${n} distinct outlets${over} — a sample of the coverage Atlas ingests, not every outlet that published.${rest}`
    }
    return `${n} distinct outlets in this row's resolved receipt sample — the readable subset, not every outlet that published.`
  }
  if (basis.reason === 'no_receipts_carried') {
    return 'The receipt sample for this story came back empty this window, so its outlets were not counted. The signal count comes from a different lineage and survives — read the story to see its sources.'
  }
  return 'Receipts resolved for this story but none carried an outlet name, so the outlet count could not be measured. Not a claim that no outlet published it.'
}

/**
 * The same honesty, compressed to a clause for sentences that already run long
 * (the threads rail's row hint). A widened count names its population inline —
 * the rail has no tip of its own to carry that qualifier.
 */
export function sourceCountClause(basis: SourceCountBasis): string {
  if (basis.kind !== 'measured') return UNMEASURED_SOURCES_LABEL
  const n = `${basis.count.toLocaleString('en-US')} sources`
  return basis.population === 'snapshot_receipts'
    ? `${n} in its latest clustering pass`
    : n
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
