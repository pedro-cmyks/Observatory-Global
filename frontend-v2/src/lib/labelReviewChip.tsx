// "LABEL UNDER REVIEW" chip — ONE chip, every surface (council Phase 1, Move 1).
//
// The front page was leading with labels the receipts don't support ("17-Year-Old
// British Teen Fall", avg_confidence 0.214, receipts are Greek traffic news). Two
// independent signals demote a label's trust:
//   1. Label Court verdict (`label_status`): a nightly entailment check of the
//      label against its own top-N receipts — 'failed' / 'partial' / 'entailed'.
//      NULL until the court has run on the thread.
//   2. Assignment confidence (`avg_confidence`): when the court has NOT run, a
//      below-floor confidence is the fallback trust signal.
//
// This chip is PURELY ADDITIVE labeling: it never hides a thread and never
// changes ranking. It sits next to the served label and, on a court failure,
// advises the receipt-derived neutral label WITHOUT silently replacing what the
// engine served. Rendered wherever a thread label shows — NarrativeThreads rows,
// Brief lead + watchlist, ThemeDetail header, the low-confidence tray.
import React from 'react'
import { LEAD_CONFIDENCE_FLOOR } from './leadConfidence'
import './labelReviewChip.css'

// Default confidence floor below which an UNCHECKED label (court not yet run)
// is treated as under review. Unified with lane A's lead-confidence gate so the
// chip and the lead/tray split move on ONE number. Surfaces may still override
// via the `floor` param.
export const LABEL_REVIEW_FLOOR = LEAD_CONFIDENCE_FLOOR

export type LabelReviewReason = 'label-failed' | 'label-partial' | 'low-confidence'

export interface LabelReviewInput {
  /** Label Court verdict: 'failed' | 'partial' | 'entailed' | null (unchecked). */
  labelStatus?: string | null
  /** Mean assignment confidence for the thread (0..1), or null when unmeasured. */
  avgConfidence?: number | null
  /** Whether avgConfidence is a real measurement. Defaults to "measured when a
   * finite number is present". */
  confidenceMeasured?: boolean
  /** Trust floor for the UNCHECKED-label fallback path. */
  floor: number
}

/**
 * The single source of truth for WHY a label is under review — TDD'd.
 * Precedence: the court's verdict wins; only when the court has NOT reached a
 * verdict does the confidence floor decide. An 'entailed' verdict suppresses the
 * chip outright (the label was validated against its receipts).
 */
export function labelReviewReason(input: LabelReviewInput): LabelReviewReason | null {
  const status = input.labelStatus
  if (status === 'failed') return 'label-failed'
  if (status === 'partial') return 'label-partial'
  if (status === 'entailed') return null

  // Unchecked (null / undefined / anything else): fall back to the floor.
  const conf =
    typeof input.avgConfidence === 'number' && Number.isFinite(input.avgConfidence)
      ? input.avgConfidence
      : null
  const measured = conf !== null && input.confidenceMeasured !== false
  if (measured && (conf as number) < input.floor) return 'low-confidence'
  return null
}

/** Plain-language explanation of the review reason, for the chip's data-tip. */
export function labelReviewTip(reason: LabelReviewReason, labelProposed?: string | null): string {
  const advisory =
    labelProposed && labelProposed.trim()
      ? ` The receipts suggest: ${labelProposed.trim()}`
      : ''
  switch (reason) {
    case 'label-failed':
      return `This label did not match its receipts.${advisory}`
    case 'label-partial':
      return `This label only partially matches its receipts.${advisory}`
    case 'low-confidence':
      return `Low assignment confidence — this label may not match its receipts yet.${advisory}`
  }
}

export interface LabelReviewChipProps {
  labelStatus?: string | null
  avgConfidence?: number | null
  confidenceMeasured?: boolean
  /** Receipt-derived neutral label offered on a court failure (advisory only). */
  labelProposed?: string | null
  /** Trust floor; defaults to LABEL_REVIEW_FLOOR. Pass lane A's lead floor to
   * unify the two. */
  floor?: number
  /** Extra class for surface-specific spacing. */
  className?: string
  /**
   * Force the review reason, bypassing internal derivation. For callers that
   * have ALREADY decided ineligibility via a band-aware gate (the Brief
   * "Unassembled signals" tray, whose membership == leadBlockReason != null) —
   * guarantees the chip renders that decision even when the row carries only a
   * coarse confidence band and no measured avg_confidence. Pass `null` to hide.
   */
  reason?: LabelReviewReason | null
}

/**
 * Renders the "LABEL UNDER REVIEW" chip, or nothing when the label is trusted.
 * Additive only — the caller keeps rendering the served label unchanged.
 */
export function LabelReviewChip(props: LabelReviewChipProps): React.ReactElement | null {
  const floor = props.floor ?? LABEL_REVIEW_FLOOR
  // An explicit `reason` (even null) overrides derivation — the caller already
  // gated the row. Otherwise derive from the court verdict + confidence floor.
  const reason =
    props.reason !== undefined
      ? props.reason
      : labelReviewReason({
          labelStatus: props.labelStatus,
          avgConfidence: props.avgConfidence,
          confidenceMeasured: props.confidenceMeasured,
          floor,
        })
  if (!reason) return null
  const tip = labelReviewTip(reason, props.labelProposed)
  return (
    <span
      className={`label-review-chip${props.className ? ` ${props.className}` : ''}`}
      data-reason={reason}
      data-tip={tip}
    >
      LABEL UNDER REVIEW
    </span>
  )
}
