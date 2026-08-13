/**
 * Plain-language companions for the measured stats.
 *
 * X4, 2026-08-13 — C5 of the blind college
 * (`docs/research/ux-council/2026-08-13-colegio-ciego.md`): four of eight
 * personas, the entire non-analyst range, could not parse the grading system.
 * The witnesses were "surprise 2.6σ over its own baseline", "velocity +0.59
 * (log-volume per 6 h)", "12× vs 8-day baseline", "Raw assigned / Gate-verified"
 * and "the sealed edition carried no stories". The retired teacher: *"I taught
 * school for forty years and cannot parse that."*
 *
 * The structural finding is the reason this module exists rather than a copy
 * pass: when the reader cannot parse the grading system, the honesty is taken
 * ON FAITH. Jargon does not merely obscure the receipts — it disables the trust
 * mechanism the receipts are there to provide. An unreadable honesty claim is,
 * to that reader, indistinguishable from an assertion.
 *
 * THE RULE, and its two halves:
 *
 * 1. THE NUMBER STAYS. The analyst and the news-junkie personas named the
 *    numbers as the product's differentiator; deleting them would trade one
 *    audience for another. This is translation, not simplification.
 * 2. THE PHRASE NEVER OUT-CLAIMS THE NUMBER. Every band here is a restatement
 *    of what was measured — never a cause, never a forecast, never a
 *    comparison to anything the statistic did not compare against. A surprise
 *    is a magnitude against a story's OWN history, so its phrase says "its own
 *    normal pace" and nothing about the world.
 *
 * Phrases are built here, in one place, so a number served by the backend and a
 * number rendered by a panel get the SAME words. The two that are served as
 * prose (the rising why-now and the gap sentence) have a backend mirror in
 * `app/services/stat_phrases.py`, test-pinned on both sides.
 *
 * These deliberately do NOT restate the ingest base — that is X1's job
 * (`ingestBasis.ts`), and every surface calling this one already carries it.
 */

function isNum(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v)
}

/** Small whole counts read better as words — newspaper style, not code style. */
const COUNT_WORDS = [
  '', '', 'two', 'three', 'four', 'five', 'six',
  'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
]

// ── the acceleration pair (LO QUE SUBE / What Is Rising) ────────────────────

/**
 * `surprise` in words. It is a magnitude in standard deviations against the
 * story's OWN Kalman baseline, so every band compares the story to itself.
 *
 * The bar for the section is 2.5, so the middle band is the one readers meet.
 * Below the bar we still answer plainly instead of returning nothing: this
 * function is also used where no bar has been applied.
 */
export function surprisePhrase(sigma: number | null | undefined): string | null {
  if (!isNum(sigma)) return null
  if (sigma >= 4) return 'far beyond anything this story normally does'
  if (sigma >= 2.5) return 'rising much faster than its own normal pace'
  if (sigma >= 1.5) return 'rising faster than its own normal pace'
  // A surprise is a MAGNITUDE. A small or negative reading means "nothing
  // unusual", never "falling" — direction is `velocity`'s to report.
  return 'close to its own normal pace'
}

/**
 * `velocity` in words — the smoothed slope. The unit (change in log-volume per
 * 6 h step) is meaningless to a lay reader and misleading if guessed at, so the
 * phrase carries only the sign, which is the part that is plainly true.
 */
export function velocityPhrase(velocity: number | null | undefined): string | null {
  if (!isNum(velocity)) return null
  if (velocity > 0) return 'still speeding up'
  if (velocity < 0) return 'already slowing down'
  return 'holding steady'
}

/**
 * The plain clause the why-now LEADS with, before the numbers.
 *
 * Sentence-cased because it opens the sentence. Either half may be missing —
 * a payload from an older seal, or a lane that answered on only one field —
 * and the clause degrades to whichever was measured rather than inventing the
 * other or dropping both.
 */
export function risingPlain(
  surprise: number | null | undefined,
  velocity: number | null | undefined,
): string | null {
  const rising = surprisePhrase(surprise)
  const slope = velocityPhrase(velocity)
  if (rising && slope) {
    return `Rising ${rising.replace(/^rising /, '')}, and ${slope}`
      .replace(/^Rising far beyond/, 'Far beyond')
      .replace(/^Rising close to/, 'Close to')
  }
  if (rising) {
    return rising.charAt(0).toUpperCase() + rising.slice(1)
  }
  if (slope) {
    return slope.charAt(0).toUpperCase() + slope.slice(1)
  }
  return null
}

// ── the × multiplier (EL VACÍO, country anomalies, the dock) ────────────────

export interface TimesOptions {
  /** What the multiplier is measured against, e.g. 'its usual day'. */
  of?: string
}

/**
 * A ratio in words. "12×" becomes "twelve times its usual coverage".
 *
 * Rounding is allowed only when it does not change the claim: a value within
 * 0.25 of a whole number prints as that whole number, anything else keeps its
 * decimal behind an explicit "about". 1.4× must never read as "once" — that
 * would turn a measured surge into "nothing is happening", the exact failure
 * `volumeBasis.formatMultiplier` already guards on the numeric side.
 */
export function timesPhrase(
  multiplier: number | null | undefined,
  opts: TimesOptions = {},
): string | null {
  if (!isNum(multiplier) || multiplier <= 0) return null
  const of = opts.of ?? 'its usual coverage'
  const rounded = Math.round(multiplier)
  const clean = Math.abs(multiplier - rounded) < 0.25

  if (clean && rounded <= 1) return `about ${of}`
  if (clean && rounded === 2) return `twice ${of}`
  if (clean && rounded <= 12) return `${COUNT_WORDS[rounded]} times ${of}`
  if (clean) return `${rounded} times ${of}`
  return `about ${multiplier.toFixed(1)} times ${of}`
}

/**
 * "baseline 28/day · 7 days" in words. The span is omitted when unknown.
 *
 * The level is printed AS SERVED, never rounded. Browser-verified 2026-08-13:
 * rounding put "2.5/DAY" and "usually about 3 a day" on one pill — two numbers
 * for one quantity, the same disagreement `anomalyMultiplierBasis` guards
 * against from the other direction. A companion must restate the number beside
 * it, never a second opinion about it.
 */
export function baselinePhrase(
  baseline: number | null | undefined,
  days: number | null | undefined,
): string | null {
  if (!isNum(baseline)) return null
  const level = `usually about ${baseline.toLocaleString()} a day`
  if (!isNum(days) || days <= 0) return level
  return `${level}, judged over ${Math.round(days)} day${Math.round(days) === 1 ? '' : 's'}`
}

/**
 * The self-voice ratio in words — outlet OWNERSHIP, as "N in every 100".
 *
 * Percentages are exactly the notation the panel stumbled on, and a share below
 * 1% must not round to "0 in every 100", which reads as the zero case. The zero
 * case itself states the count and nothing more: whether the country's press
 * stayed silent is not knowable from this corpus (X1), so the phrase reports
 * the outlets read and stops.
 */
export function selfVoicePhrase(ratio: number | null | undefined): string | null {
  if (!isNum(ratio) || ratio < 0) return null
  const tail = 'came from outlets based there'
  if (ratio === 0) return `none of them ${tail}`
  const per100 = ratio * 100
  if (per100 < 1) return `fewer than 1 in every 100 ${tail}`
  return `about ${Math.round(per100)} in every 100 ${tail}`
}

// ── the z-score (Trust Indicators) ──────────────────────────────────────────

/**
 * Standard deviations in words. Direction plus a coarse size — the two things
 * a z-score plainly means. No band claims a cause, and the middle band says
 * "around its usual level" rather than "normal", which would read as a verdict.
 */
export function zPhrase(z: number | null | undefined): string | null {
  if (!isNum(z)) return null
  if (z >= 6) return 'far above its usual level'
  if (z >= 3) return 'well above its usual level'
  if (z >= 2) return 'above its usual level'
  if (z > -2) return 'around its usual level'
  if (z > -6) return 'below its usual level'
  return 'far below its usual level'
}

// ── the verification funnel (Under the Radar, the evidence route) ───────────

/** The plain reading of the funnel's two steps — one string, two consumers. */
export const MENTIONED_IT = 'mentioned it'
export const PASSED_VERIFICATION = 'passed verification'

/**
 * "172 raw signals / 0 verified" in words.
 *
 * The zero case says "none passed verification YET" because that is what the
 * gate state means: unverified is not rejected, and the card's own status line
 * has always distinguished the two. Dropping the "yet" would quietly convert a
 * pending judgement into a negative one.
 */
export function verifiedCountPhrase(
  raw: number | null | undefined,
  verified: number | null | undefined,
): string | null {
  if (!isNum(raw) || raw < 0) return null
  const seen = `${Math.round(raw).toLocaleString()} ${MENTIONED_IT}`
  if (!isNum(verified) || verified < 0) return seen
  const passed = verified === 0
    ? `none ${PASSED_VERIFICATION} yet`
    : `${Math.round(verified).toLocaleString()} ${PASSED_VERIFICATION}`
  return `${seen} · ${passed}`
}

// ── the heat composite (HEATING UP) ────────────────────────────────────────

/**
 * The dominant heat component, in words. Browser-verified 2026-08-13: the
 * Brief's HEATING UP strip printed the raw metric name — "Malta 67 SURPRISE" —
 * i.e. an internal column name on the front page.
 *
 * Each phrase is a restatement of what migration 017 actually computes, and
 * NONE is stronger than the bare word it replaces:
 *   velocity   z_velocity_norm      — volume against this country's own baseline
 *   surprise   surprise_kl_norm     — KL of its topic mix against its own baseline
 *   diversity  source_diversity_norm— Shannon entropy over outlets
 *   voice      local_voice_ratio    — domestic share of attributable outlets
 *   polyphony  polyphony_norm       — entropy over frames
 *
 * `voice` and `polyphony` deliberately describe WHAT IS MEASURED rather than
 * asserting a direction, because both collapse to a literal 0.5 sentinel below
 * their attribution floors (known_origin_n < 50, framed_n < 25) — the same
 * sentinel EL VACÍO refuses to read as a fact. Saying "strong local press"
 * there would be the X1 error all over again.
 */
const HEAT_COMPONENT_PHRASES: Record<string, string> = {
  velocity: 'coverage climbing fast',
  surprise: 'an unusual mix of stories for it',
  diversity: 'spread across many outlets',
  voice: 'share of local outlets',
  polyphony: 'outlets framing it differently',
}

export function heatComponentPhrase(component: string | null | undefined): string | null {
  const key = (component ?? '').trim().toLowerCase()
  return HEAT_COMPONENT_PHRASES[key] ?? null
}

// ── markets ────────────────────────────────────────────────────────────────

/**
 * "21 sessions" in words. A session IS a trading day; the trade jargon buys the
 * reader nothing and cost the panel a parse.
 */
export function tradingWindowPhrase(sessions: number | null | undefined): string | null {
  if (!isNum(sessions) || sessions <= 0) return null
  const n = Math.round(sessions)
  return `${n} trading day${n === 1 ? '' : 's'}`
}
