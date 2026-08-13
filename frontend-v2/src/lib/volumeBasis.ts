// Volume-basis contract (fix round 2026-08-12, cold-user probe pair c).
//
// The country panel printed two numbers about "how loud is this country right
// now" and neither stated what it was:
//
//   ▲ 12× above 7-day baseline   ← /api/v2/anomalies. A RATIO. Current window
//                                  is a hard-coded 24h; the baseline SQL spans
//                                  8 days, so the printed "7-day" was false.
//   (z: 71.2)                    ← /api/indicators/country/{cc}. A Z-SCORE.
//                                  Current window is the panel's own
//                                  timeWindow; baseline is 7 days of raw
//                                  signals_v2.
//
// Two endpoints, two windows, two statistics — read as two answers to one
// question. This module holds the pure decision: given what each endpoint
// served, what strings do we render. Council doctrine: a labeled divergence
// invites reconciliation, a mislabel forecloses it.
//
// Nothing here invents a value. Missing metadata yields wording the number can
// stand behind ("recent baseline"), never a fabricated day count.

import { timesPhrase, zPhrase } from './statPhrases'

export interface AnomalyMultiplierInput {
  multiplier?: number | null
  /** Days the baseline SQL spans, as served. Absent → we do not name a length. */
  baselineDays?: number | null
  /** Days that actually carried data inside that span. */
  daysObserved?: number | null
}

export interface AnomalyMultiplierResult {
  /** Badge text without the ▲ glyph, or null when there is no number. */
  text: string | null
  /**
   * The same ratio in plain words, for printing BESIDE `text` (X4).
   *
   * W5 renamed this badge's "12σ" to "12×", which made it correct without
   * making it readable — "12× VS 8-DAY BASELINE" is a verbatim witness from
   * the blind college's C5. Null wherever `timesPhrase` refuses, so the badge
   * never gains words the number cannot back.
   */
  plain: string | null
  /** data-tip explaining the basis and distinguishing it from the z-score. */
  tip: string
}

export interface VolumeZInput {
  zScore?: number | null
  /** Printed window the z-score's CURRENT half was measured over, e.g. '24h'. */
  windowLabel?: string | null
  baselineDays?: number | null
  daysObserved?: number | null
  /** Backend flag: the baseline is too sparse for a meaningful sigma. */
  thinBaseline?: boolean | null
}

export interface VolumeZResult {
  /** Chip text, or null when there is no z-score to show. */
  text: string | null
  /**
   * The z-score's direction and coarse size in plain words (X4), for printing
   * beside `text`. Null on a thin baseline: the number is already withheld
   * there as false precision, and a sentence must not smuggle it back.
   */
  plain: string | null
  /** True when we printed a real number; false when we degraded to a direction. */
  precise: boolean
  tip: string
}

function isNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v)
}

/**
 * A ratio below 10 rounded to an integer erases the signal it is reporting:
 * 1.4× would print as "1×", i.e. "nothing is happening". Keep one decimal
 * under 10, whole numbers above where the decimal is noise.
 */
function formatMultiplier(n: number): string {
  return n >= 10 ? String(Math.round(n)) : n.toFixed(1)
}

export function anomalyMultiplierBasis(input: AnomalyMultiplierInput): AnomalyMultiplierResult {
  const { multiplier, baselineDays, daysObserved } = input
  const hasDays = isNumber(baselineDays) && baselineDays > 0
  const basisPhrase = hasDays ? `${baselineDays}-day baseline` : 'recent baseline'

  // The observed-days clause is the honest caveat: an 8-day window with 3 days
  // of data is a different claim from a full one.
  const observedClause =
    isNumber(daysObserved) && daysObserved > 0 && hasDays && daysObserved < (baselineDays as number)
      ? ` Only ${daysObserved} of ${baselineDays} days carried data, so the average rests on a short history.`
      : ''

  const tip =
    `Multiplier = this country's signal count in a fixed 24h window divided by its average day over the ${basisPhrase}. ` +
    `It is a ratio, not a z-score.${observedClause} ` +
    `The z-score under Trust Indicators is a different statistic measured over a different window — the two are not expected to match.`

  if (!isNumber(multiplier)) return { text: null, plain: null, tip }
  // The companion is a word rendering of THE NUMBER THE BADGE PRINTS, not of
  // the raw value: `formatMultiplier` already rounds 12.4 to "12×", so phrasing
  // the raw value would put "12×" and "about 12.4 times" on one line and hand
  // the reader a precision the badge deliberately withheld. Feeding the shown
  // value through makes badge and sentence agree by construction.
  const shown = Number(formatMultiplier(multiplier))
  return {
    text: `${formatMultiplier(multiplier)}× vs ${basisPhrase}`,
    plain: timesPhrase(shown),
    tip,
  }
}

export function volumeZBasis(input: VolumeZInput): VolumeZResult {
  const { zScore, windowLabel, baselineDays, daysObserved, thinBaseline } = input
  const hasDays = isNumber(baselineDays) && baselineDays > 0
  const windowPhrase = windowLabel ? `the last ${windowLabel}` : 'the current window'
  const basisPhrase = hasDays ? `a ${baselineDays}-day baseline` : 'a multi-day baseline'
  const observedDays = isNumber(daysObserved) && daysObserved > 0 ? daysObserved : null

  const contrast =
    ' This is not the same measure as the × multiplier badge above: that one is a ratio on a fixed 24h window, this one counts standard deviations on this panel\'s window.'

  if (!isNumber(zScore)) {
    return {
      text: null,
      plain: null,
      precise: false,
      tip: `No z-score was measured for ${windowPhrase} against ${basisPhrase}.${contrast}`,
    }
  }

  if (thinBaseline) {
    // A sigma computed from a couple of low-volume days is arithmetic, not
    // evidence. Print the direction we can defend and say why the number is
    // withheld — degrade honestly rather than invent precision.
    const direction = zScore >= 2 ? 'high' : zScore <= -2 ? 'low' : 'n/a'
    const daysClause = observedDays
      ? `only ${observedDays} day${observedDays === 1 ? '' : 's'} of baseline data`
      : 'too few baseline days'
    return {
      text: `z: ${direction} (thin baseline)`,
      // No companion here: the number was withheld as false precision, so a
      // sentence stating a magnitude would reintroduce exactly what we refused.
      plain: null,
      precise: false,
      tip:
        `The baseline had ${daysClause} at low volume, so its standard deviation is not meaningful and a precise z-score would be false precision. ` +
        `We show the direction only.${contrast}`,
    }
  }

  const observedClause =
    observedDays && hasDays && observedDays < (baselineDays as number)
      ? ` ${observedDays} of ${baselineDays} days carried data.`
      : ''

  return {
    text: `z: ${zScore.toFixed(1)}`,
    plain: zPhrase(zScore),
    precise: true,
    tip:
      `Standard deviations above this country's normal volume: ${windowPhrase} compared against ${basisPhrase}.${observedClause}` +
      contrast,
  }
}
