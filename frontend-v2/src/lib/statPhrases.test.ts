import { describe, it, expect } from 'vitest'
import {
  MENTIONED_IT,
  PASSED_VERIFICATION,
  surprisePhrase,
  velocityPhrase,
  risingPlain,
  timesPhrase,
  baselinePhrase,
  selfVoicePhrase,
  zPhrase,
  verifiedCountPhrase,
  tradingWindowPhrase,
  heatComponentPhrase,
} from './statPhrases'

/**
 * X4 (2026-08-13) — the blind college's C5: four of eight personas, the whole
 * non-analyst range, could not parse the grading system. Verbatim from the
 * retired teacher: "I taught school for forty years and cannot parse that."
 *
 * The rule these pin: the number STAYS (the analyst and the news-junkie value
 * it) and gains a plain companion. So every phrase here must be readable with
 * NO statistical vocabulary at all — no sigma, no log, no velocity, no z, no
 * baseline, no gate — while never claiming more than the number does.
 *
 * Backend lockstep: `app/services/stat_phrases.py` asserts the same strings for
 * the two phrases that are served as PROSE (rising why-now, gap prose), so a
 * one-sided edit fails a suite.
 */

/** No phrase this module produces may contain analyst vocabulary. */
const JARGON = [
  'σ', 'sigma', 'z-score', 'z:', 'log-volume', 'log volume', 'velocity',
  'surprise', 'baseline', 'gate', 'kalman', 'std', 'deviation', 'multiplier',
]

function expectPlain(phrase: string | null) {
  expect(phrase).not.toBeNull()
  const lower = (phrase as string).toLowerCase()
  for (const word of JARGON) {
    expect(lower).not.toContain(word)
  }
}

describe('surprisePhrase — the sigma, in words', () => {
  it('translates the witness value (2.6σ) without the sigma', () => {
    const phrase = surprisePhrase(2.6)
    expectPlain(phrase)
    expect(phrase).toBe('rising much faster than its own normal pace')
  })

  it('escalates above the bar and stays modest below it', () => {
    expect(surprisePhrase(6)).toBe('far beyond anything this story normally does')
    expect(surprisePhrase(2.0)).toBe('rising faster than its own normal pace')
    expect(surprisePhrase(0.4)).toBe('close to its own normal pace')
  })

  it('refuses to phrase what was not measured', () => {
    expect(surprisePhrase(null)).toBeNull()
    expect(surprisePhrase(undefined)).toBeNull()
    expect(surprisePhrase(Number.NaN)).toBeNull()
  })

  it('never invents a direction for a negative reading', () => {
    // A surprise is a magnitude; below the bar we say so, we do not say "falling".
    expect(surprisePhrase(-3)).toBe('close to its own normal pace')
  })
})

describe('velocityPhrase — the slope, in words', () => {
  it('translates the witness value (+0.59) without the units', () => {
    const phrase = velocityPhrase(0.59)
    expectPlain(phrase)
    expect(phrase).toBe('still speeding up')
  })

  it('names a cooling story as cooling, never as rising', () => {
    expect(velocityPhrase(-0.4)).toBe('already slowing down')
  })

  it('holds steady at exactly zero and refuses an unmeasured slope', () => {
    expect(velocityPhrase(0)).toBe('holding steady')
    expect(velocityPhrase(null)).toBeNull()
  })
})

describe('risingPlain — the why-now sentence the reader leads with', () => {
  it('joins both readings into one plain clause', () => {
    const phrase = risingPlain(2.6, 0.59)
    expectPlain(phrase)
    expect(phrase).toBe('Rising much faster than its own normal pace, and still speeding up')
  })

  it('degrades to whichever half was measured', () => {
    expect(risingPlain(2.6, null)).toBe('Rising much faster than its own normal pace')
    expect(risingPlain(null, 0.59)).toBe('Still speeding up')
    expect(risingPlain(null, null)).toBeNull()
  })
})

describe('timesPhrase — the × multiplier, in words', () => {
  it('translates the witness badge (12×) exactly as the plan wrote it', () => {
    const phrase = timesPhrase(12)
    expectPlain(phrase)
    expect(phrase).toBe('twelve times its usual coverage')
  })

  it('spells small whole counts and keeps a decimal when the rounding would lie', () => {
    expect(timesPhrase(2)).toBe('twice its usual coverage')
    expect(timesPhrase(3.05)).toBe('three times its usual coverage')
    expect(timesPhrase(3.6)).toBe('about 3.6 times its usual coverage')
    expect(timesPhrase(41)).toBe('41 times its usual coverage')
  })

  it('takes the subject it is compared against, so a day reads as a day', () => {
    // The gap section's own witness value, rounded only because 11.2 is inside
    // the quarter that rounding cannot misstate.
    expect(timesPhrase(11.2, { of: 'its usual day' }))
      .toBe('eleven times its usual day')
    expect(timesPhrase(11.6, { of: 'its usual day' }))
      .toBe('about 11.6 times its usual day')
  })

  it('never turns a non-surge into one', () => {
    expect(timesPhrase(1)).toBe('about its usual coverage')
    expect(timesPhrase(0)).toBeNull()
    expect(timesPhrase(null)).toBeNull()
  })
})

describe('baselinePhrase — what "baseline 28/day · 7 days" means', () => {
  it('says the usual level in plain words, keeping the number', () => {
    const phrase = baselinePhrase(28, 7)
    expectPlain(phrase)
    expect(phrase).toBe('usually about 28 a day, judged over 7 days')
  })

  it('omits the span it does not have rather than inventing one', () => {
    expect(baselinePhrase(28, null)).toBe('usually about 28 a day')
    expect(baselinePhrase(null, 7)).toBeNull()
  })

  it('never disagrees with the number printed beside it', () => {
    // Browser-verified 2026-08-13: rounding put "2.5/DAY" and "usually about 3
    // a day" on the same pill. A companion restates its number; it never
    // offers a second opinion about it.
    expect(baselinePhrase(2.5, 6)).toBe('usually about 2.5 a day, judged over 6 days')
  })
})

describe('selfVoicePhrase — the ownership share, in words', () => {
  it('reads a share as a share of the reports Atlas read', () => {
    const phrase = selfVoicePhrase(0.08)
    expectPlain(phrase)
    expect(phrase).toBe('about 8 in every 100 came from outlets based there')
  })

  it('states a zero as a zero without claiming silence', () => {
    const phrase = selfVoicePhrase(0)
    expectPlain(phrase)
    expect(phrase).toBe('none of them came from outlets based there')
    expect(phrase).not.toContain('silent')
  })

  it('refuses to round a tiny share up to a visible one', () => {
    expect(selfVoicePhrase(0.002)).toBe('fewer than 1 in every 100 came from outlets based there')
  })

  it('refuses an unmeasured share', () => {
    expect(selfVoicePhrase(null)).toBeNull()
  })
})

describe('zPhrase — the standard deviations, in words', () => {
  it('translates the witness chip (z: 71.2) into a direction with a size', () => {
    const phrase = zPhrase(71.2)
    expectPlain(phrase)
    expect(phrase).toBe('far above its usual level')
  })

  it('bands both directions and the middle', () => {
    expect(zPhrase(3.4)).toBe('well above its usual level')
    expect(zPhrase(2.1)).toBe('above its usual level')
    expect(zPhrase(0.3)).toBe('around its usual level')
    expect(zPhrase(-2.4)).toBe('below its usual level')
    expect(zPhrase(-6)).toBe('far below its usual level')
    expect(zPhrase(null)).toBeNull()
  })
})

describe('verifiedCountPhrase — "Raw assigned / Gate-verified", in words', () => {
  it('reads the funnel as two plain facts', () => {
    const phrase = verifiedCountPhrase(172, 0)
    expectPlain(phrase)
    expect(phrase).toBe('172 mentioned it · none passed verification yet')
  })

  it('keeps the verified count when there is one', () => {
    expect(verifiedCountPhrase(1200, 43)).toBe('1,200 mentioned it · 43 passed verification')
  })

  it('is singular where singular is correct', () => {
    expect(verifiedCountPhrase(1, 1)).toBe('1 mentioned it · 1 passed verification')
  })

  it('refuses to phrase a funnel it does not have', () => {
    expect(verifiedCountPhrase(null, 0)).toBeNull()
  })

  it('exports the two step labels so the breadcrumb cannot drift from the sentence', () => {
    expect(MENTIONED_IT).toBe('mentioned it')
    expect(PASSED_VERIFICATION).toBe('passed verification')
  })
})

describe('tradingWindowPhrase — "21 sessions", in words', () => {
  it('says trading days, which is what a session is', () => {
    const phrase = tradingWindowPhrase(21)
    expectPlain(phrase)
    expect(phrase).toBe('21 trading days')
  })

  it('is singular at one and absent at none', () => {
    expect(tradingWindowPhrase(1)).toBe('1 trading day')
    expect(tradingWindowPhrase(0)).toBeNull()
    expect(tradingWindowPhrase(null)).toBeNull()
  })
})

describe('heatComponentPhrase — "Malta 67 SURPRISE", in words', () => {
  it('translates every component the Brief can print', () => {
    for (const key of ['velocity', 'surprise', 'diversity', 'voice', 'polyphony']) {
      expectPlain(heatComponentPhrase(key))
    }
    expect(heatComponentPhrase('surprise')).toBe('an unusual mix of stories for it')
    expect(heatComponentPhrase('velocity')).toBe('coverage climbing fast')
  })

  it('describes the two sentinel-bearing components without asserting a direction', () => {
    // local_voice_ratio and polyphony_norm both collapse to a literal 0.5 below
    // their attribution floors (migration 017). "strong local press" there would
    // be X1's error again — so these say what is measured, not what it means.
    expect(heatComponentPhrase('voice')).toBe('share of local outlets')
    expect(heatComponentPhrase('voice')).not.toMatch(/strong|more|less|own press/)
    expect(heatComponentPhrase('polyphony')).toBe('outlets framing it differently')
  })

  it('says nothing for a component it does not know', () => {
    // A new heat column must not be silently mistranslated — the card falls
    // back to the raw name, which is at least true.
    expect(heatComponentPhrase('geo_confidence_mean')).toBeNull()
    expect(heatComponentPhrase(null)).toBeNull()
  })
})
