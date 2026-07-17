// Confidence-gated front-page lead selection for the L1 Brief.
//
// Council Phase 1, Move 1 ("stop the front page lying"). The motivating live
// case: prod briefing top_threads[0] = "17-Year-Old British Teen Fall" with
// avg_confidence 0.214 — the label matches nothing in its receipts (Greek
// traffic-accident news). Real stories score 0.9+. A thread may only LEAD the
// front page (or render as an assembled desk card, label-as-fact) when we
// actually trust its label.
//
// Two gates, in strict precedence:
//   1. Label Court (engine, #204/#224): label_status === "failed" ALWAYS blocks
//      — the label was checked against its own top-N receipts and did not
//      entail. This wins even above the confidence floor. label_status is NULL
//      until the nightly court runs; a null status never blocks on its own.
//   2. Confidence floor: the measured assignment confidence (avg_confidence,
//      0..1) must be >= FLOOR. When avg_confidence is absent we derive a
//      representative value from the served `confidence` band; an entirely
//      unscored thread cannot clear the floor.
//
// This is the ONE source of truth for lead/desk eligibility — the page renders
// eligible threads as assembled stories and drops the rest to the honest
// "Unassembled signals" tray (nothing vanishes; council no-silent-filtering).

export const LEAD_CONFIDENCE_FLOOR = 0.7

export type LabelStatus = 'entailed' | 'partial' | 'failed' | null

export interface LeadGateThread {
  avg_confidence?: number | null
  // Coarse served band (thread_intelligence.confidence_band): the fallback
  // when a numeric avg_confidence is not carried on the row.
  confidence?: string | null
  label_status?: LabelStatus
}

export type LeadBlockReason = 'low-confidence' | 'label-failed' | null

// Representative numeric value for a served confidence band, used only when a
// numeric avg_confidence is missing. Mirrors thread_intelligence.confidence_band:
//   high   -> assignment_confidence >= 0.75 (+ strong evidence)  -> above floor
//   medium -> assignment_confidence >= 0.6                       -> below floor
//   thin   -> weak                                                -> below floor
//   degraded -> confidence < 0.5 or single-source                 -> below floor
// Unknown bands resolve to null (treated as unscored -> below floor).
const BAND_SCORE: Record<string, number> = {
  high: 0.85,
  strong: 0.85,
  medium: 0.65,
  moderate: 0.65,
  thin: 0.5,
  limited: 0.45,
  low: 0.35,
  degraded: 0.3,
}

/**
 * Resolve a thread's confidence to a number in [0,1], or null when it is
 * genuinely unscored. Prefers the measured avg_confidence; falls back to the
 * served band label.
 */
export function resolveLeadConfidence(t: LeadGateThread): number | null {
  const n = t.avg_confidence
  if (typeof n === 'number' && Number.isFinite(n)) {
    return Math.max(0, Math.min(1, n))
  }
  const band = t.confidence?.trim().toLowerCase()
  if (band && band in BAND_SCORE) return BAND_SCORE[band]
  return null
}

/**
 * Why a thread cannot lead / cannot be presented as an assembled story.
 * Precedence: a failed Label Court verdict blocks unconditionally; otherwise a
 * below-floor (or unscored) confidence blocks. Returns null when eligible.
 */
export function leadBlockReason(t: LeadGateThread): LeadBlockReason {
  if (t.label_status === 'failed') return 'label-failed'
  const c = resolveLeadConfidence(t)
  if (c == null || c < LEAD_CONFIDENCE_FLOOR) return 'low-confidence'
  return null
}

/** A thread may lead / render label-as-fact only when it has no block reason. */
export function isLeadEligible(t: LeadGateThread): boolean {
  return leadBlockReason(t) === null
}

export interface LeadSelection<T extends LeadGateThread> {
  /** Top-ranked ELIGIBLE thread, or null when none clears the gate. */
  lead: T | null
  /** The eligible pool, in the caller's rank order (lead is eligible[0]). */
  eligible: T[]
  /** true when threads exist but NONE cleared the gate — the caller renders the
   * honest empty-lead state instead of leading with a label it doesn't trust. */
  leadUnavailable: boolean
}

/**
 * Select the front-page lead from a RANK-ORDERED list of live threads: the
 * top-ranked thread that clears the eligibility gate (confidence floor AND not
 * Label-Court-failed). Reads label_status/avg_confidence off each row every
 * call, so a payload that newly serves the top thread as court-failed
 * automatically demotes it and the next eligible thread wins.
 *
 * The ONE source of truth for lead selection — the Brief (global AND country
 * editions) calls this so both paths gate identically.
 */
export function selectLiveLead<T extends LeadGateThread>(threads: T[]): LeadSelection<T> {
  const eligible = threads.filter(isLeadEligible)
  const lead = eligible[0] ?? null
  return { lead, eligible, leadUnavailable: lead === null && threads.length > 0 }
}
