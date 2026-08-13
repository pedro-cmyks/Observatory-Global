/**
 * Under-the-Radar receipt basis (W5, re-judge §4g / §5 "precision theatre").
 *
 * The judge's sharpest trust finding: under "Currency and debt stress" the gap
 * box listed an evergreen history.com explainer — "How Did the Gold Standard
 * Contribute to the Great Depression?" — stamped **score 0.99**. Two decimals
 * of apparent confidence on an obviously wrong match. In their words: "Three-
 * decimal confidence attached to obviously wrong matches is worse than no
 * number."
 *
 * They are right, and the number was never what it looked like. `gate_score`
 * is the scope gate's raw model output, and this tier's own measured slice
 * precision is 29-43% (docs/research/gap-pool/2026-07-16-gap-pool-relevance.md).
 * A 0.99 here does not mean 99% anything. Printing it beside a headline
 * borrows a calibration the engine has not earned.
 *
 * So: the visible chip states the BASIS on which the row was matched — the
 * assignment method the engine actually recorded (`lexicon` = a keyword hit,
 * `embedding` = a vector neighbour) — and never a digit. The raw score stays
 * reachable in the tooltip, explicitly labelled uncalibrated, so nothing is
 * hidden from someone who goes looking.
 *
 * Fixing the calibration underneath is the engine program's job, not this
 * surface's. This only stops the surface overstating it.
 */

import type { GapReceipt } from './coverageGaps'

/** Shared explanation of what this whole tier is worth. */
export const GAP_RECEIPT_TIER_TIP =
  'Extended tier: recovered by the ~75%-precision model from this gap\'s raw pool. '
  + 'Measured precision on gap slices is 29-43% — read these as leads to check, never as verified evidence.'

export interface ReceiptBasis {
  /** What the reader sees. Never contains a digit. */
  chip: string
  /** What hovering reveals — including the raw score, named as uncalibrated. */
  tip: string
}

function basisPhrase(method: GapReceipt['method']): string {
  switch (method) {
    case 'lexicon':
      // A keyword in the category's lexicon appeared in the headline. That is
      // all it means — and it is exactly how "radio blackout" pulled a video
      // game story into "Telecom or internet shutdown".
      return 'lexical match'
    case 'embedding':
      return 'semantic match'
    default:
      // The engine did not record how this row was assigned. Name the tier
      // rather than guessing a basis we cannot back.
      return 'extended-model match'
  }
}

export function receiptBasis(r: GapReceipt): ReceiptBasis {
  const chip = `${basisPhrase(r.method)} · unverified`

  const how = r.method === 'lexicon'
    ? 'Matched because a keyword from this category appeared in the headline — a word, not a judgement about the story. '
    : r.method === 'embedding'
      ? 'Matched because its embedding sits near this category — a similarity, not a judgement about the story. '
      : ''

  const score = typeof r.gate_score === 'number' && Number.isFinite(r.gate_score)
    // Deliberately spelled out, not rendered as a bare figure: the words carry
    // the caveat wherever the number travels.
    ? `Raw gate output ${r.gate_score.toFixed(2)} — UNCALIBRATED, not a probability and not a confidence. `
    : ''

  return { chip, tip: `${how}${score}${GAP_RECEIPT_TIER_TIP}` }
}
