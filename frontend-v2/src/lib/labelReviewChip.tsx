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

// 'awaiting-verification' (lane A lead-eligibility v2) is deliberately NOT
// derived from labelStatus/avgConfidence alone — deriving it from plain NULL
// would chip every unstamped row on every surface (most rows are simply
// "the incremental court hasn't reached this one yet", not a real signal).
// It is derived in exactly one narrow case now (2026-07-29, GB4 fix 1 —
// docs/research/label-court/2026-07-29-gb4-blind-check.md): `courtWithheld`,
// an explicit "the court DID try this row and could not ground a verdict"
// signal (label_court.py's quote-gate withhold, umbrella lane). That is a
// stronger, more specific claim than ordinary unchecked-ness, and umbrella
// rows sit at avg_confidence 0.95+ — far above the low-confidence floor — so
// the ordinary fallback path can structurally never fire for them; without
// this, a withheld umbrella renders with NO chip at all, indistinguishable
// from a trusted label (the exact dt-8070/dt-8084 finding). It ALSO stays
// available for callers that gate via leadBlockReason (the Brief tray) and
// pass the `reason` override directly, same as before.
// RESIDUAL (documented, not silently assumed away): as of this fix, no
// backend payload actually SETS `courtWithheld` yet — thread_intelligence.py
// does not select label_checked_at/label_court_model at all, so there is no
// served signal to distinguish "withheld" from "never reached" today. This
// change makes the derivation READY to consume that signal once a serializer
// change wires it through; until then this path is dead code by construction
// (courtWithheld defaults to undefined/false for every existing caller, so
// behavior is unchanged).
export type LabelReviewReason =
  | 'label-failed'
  | 'label-partial'
  | 'low-confidence'
  | 'awaiting-verification'

export interface LabelReviewInput {
  /** Label Court verdict: 'failed' | 'partial' | 'entailed' | null (unchecked). */
  labelStatus?: string | null
  /** Mean assignment confidence for the thread (0..1), or null when unmeasured. */
  avgConfidence?: number | null
  /** Whether avgConfidence is a real measurement. Defaults to "measured when a
   * finite number is present". */
  confidenceMeasured?: boolean
  /**
   * The court attempted this row and explicitly withheld its verdict (a
   * quote-gate / absence-check / rule-4 failure — label_court.py, umbrella
   * lane) rather than never having reached it. NOT yet populated by any
   * served payload (see the RESIDUAL note above) — future-proofing only.
   */
  courtWithheld?: boolean
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

  // Unchecked (null / undefined / anything else). A row the court explicitly
  // WITHHELD (2026-07-29 GB4 fix 1) is a stronger, more specific claim than
  // ordinary unchecked-ness — surface it ahead of the confidence-floor guess,
  // and independently of the floor (an umbrella's avg_confidence sits at
  // 0.95+, so the floor path alone can never fire for it; see the type's
  // doc comment for the residual on wiring this signal through serving).
  if (input.courtWithheld === true) return 'awaiting-verification'

  // Otherwise fall back to the floor.
  const conf =
    typeof input.avgConfidence === 'number' && Number.isFinite(input.avgConfidence)
      ? input.avgConfidence
      : null
  const measured = conf !== null && input.confidenceMeasured !== false
  if (measured && (conf as number) < input.floor) return 'low-confidence'
  return null
}

/** The court's build_neutral_label emits an INTERNAL placeholder
 * "<geo>: <subject> — from N receipts" for freshly-failed topics before the
 * DeepSeek relabel regenerates a real headline. That token-triple is not a
 * human-facing suggestion — it must never surface (#261: "do not surface
 * anywhere"). Only a real relabel (no "— from N receipts" tail) is presentable
 * advisory. (#261 gap, 2026-07-21.) */
export function isPresentableProposedLabel(labelProposed?: string | null): boolean {
  const t = labelProposed?.trim()
  if (!t) return false
  return !/—\s*from\s+\d+\s+receipts?\s*$/i.test(t)
}

/** Plain-language explanation of the review reason, for the chip's data-tip. */
export function labelReviewTip(reason: LabelReviewReason, labelProposed?: string | null): string {
  const advisory =
    isPresentableProposedLabel(labelProposed)
      ? ` The receipts suggest: ${labelProposed!.trim()}`
      : ''
  switch (reason) {
    case 'label-failed':
      return `This label did not match its receipts.${advisory}`
    case 'label-partial':
      return `This label only partially matches its receipts.${advisory}`
    case 'low-confidence':
      return `Low assignment confidence — this label may not match its receipts yet.${advisory}`
    case 'awaiting-verification':
      return `Not yet verified — this label is queued for its receipt check.${advisory}`
  }
}

export interface LabelReviewChipProps {
  labelStatus?: string | null
  avgConfidence?: number | null
  confidenceMeasured?: boolean
  /**
   * The court attempted this row and explicitly withheld its verdict rather
   * than never reaching it (2026-07-29 GB4 fix 1). See LabelReviewInput's
   * doc comment — not yet populated by any served payload.
   */
  courtWithheld?: boolean
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
  /**
   * N15 (council R2): presentation density. 'chip' (default) = the full
   * "LABEL UNDER REVIEW" pill; 'dot' = a compact marker for dense surfaces
   * (universe hover card, search result rows, CountryBrief thread chips,
   * dossier pin labels). Same derivation, same tip, same reason — ONE
   * component, two densities.
   */
  variant?: 'chip' | 'dot'
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
          courtWithheld: props.courtWithheld,
          floor,
        })
  if (!reason) return null
  const tip = labelReviewTip(reason, props.labelProposed)
  if (props.variant === 'dot') {
    // Compact marker for dense surfaces — no visible copy, so the meaning
    // rides on the tip + accessible name. Same class family = same colors.
    return (
      <span
        className={`label-review-chip label-review-chip--dot${props.className ? ` ${props.className}` : ''}`}
        data-reason={reason}
        data-tip={tip}
        aria-label="Label under review"
        role="img"
      />
    )
  }
  return (
    <span
      className={`label-review-chip${props.className ? ` ${props.className}` : ''}`}
      data-reason={reason}
      data-tip={tip}
    >
      {reason === 'awaiting-verification' ? 'AWAITING VERIFICATION' : 'LABEL UNDER REVIEW'}
    </span>
  )
}
