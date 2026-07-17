import { describe, it, expect } from 'vitest'
import { reconcileSentimentProse, joinSegments } from './reconcileSentimentProse'

// Fix round 2026-07-17 item 3: the measured chip alone was not enough — stale
// generated prose still printed "-0.1" three lines under the measured -0.53
// strip. Numeric sentiment claims in the prose are now RECONCILED: when a
// claimed figure disagrees with the measured value beyond tolerance, the stale
// figure is replaced inline with the measured one (the correction is marked so
// the renderer can attach a "corrected against the measured strip" tip).
// One metric never renders as two different numbers on one page.

describe('reconcileSentimentProse', () => {
  it('replaces a stale sentiment figure with the measured value (the -0.1 vs -0.53 repro)', () => {
    const segs = reconcileSentimentProse(
      'Coverage broadened while average sentiment held at -0.1 across the window.',
      -0.53,
    )
    const corrected = segs.filter(s => s.corrected)
    expect(corrected).toHaveLength(1)
    expect(corrected[0].text).toBe('-0.53')
    expect(corrected[0].corrected?.original).toBe('-0.1')
    expect(joinSegments(segs)).toBe(
      'Coverage broadened while average sentiment held at -0.53 across the window.',
    )
  })

  it('leaves prose alone when the claimed figure agrees within tolerance (0.05)', () => {
    const prose = 'Average sentiment sits at -0.51 for the window.'
    const segs = reconcileSentimentProse(prose, -0.53)
    expect(segs).toHaveLength(1)
    expect(segs[0].corrected).toBeUndefined()
    expect(segs[0].text).toBe(prose)
  })

  it('only touches numbers CLAIMED as sentiment/tone/mood — other figures pass through', () => {
    const prose = 'Volume rose 42% across 12 countries while tone slid to -0.2.'
    const segs = reconcileSentimentProse(prose, -0.6)
    expect(joinSegments(segs)).toBe('Volume rose 42% across 12 countries while tone slid to -0.60.')
    const corrected = segs.filter(s => s.corrected)
    expect(corrected).toHaveLength(1)
    expect(corrected[0].corrected?.original).toBe('-0.2')
  })

  it('handles the unicode minus sign', () => {
    const segs = reconcileSentimentProse('Sentiment averaged −0.1 today.', -0.53)
    expect(segs.filter(s => s.corrected)).toHaveLength(1)
    expect(joinSegments(segs)).toBe('Sentiment averaged -0.53 today.')
  })

  it('corrects EVERY stale claim, not just the first', () => {
    const segs = reconcileSentimentProse(
      'Sentiment fell to -0.1 early, and mood closed near -0.15.',
      -0.53,
    )
    expect(segs.filter(s => s.corrected)).toHaveLength(2)
    expect(joinSegments(segs)).toBe('Sentiment fell to -0.53 early, and mood closed near -0.53.')
  })

  it('ignores numbers with no sentiment keyword nearby', () => {
    const prose = 'Three quakes above magnitude 5.9 struck within 24 hours.'
    const segs = reconcileSentimentProse(prose, -0.53)
    expect(segs).toHaveLength(1)
    expect(segs[0].corrected).toBeUndefined()
  })

  it('degrades to pass-through when the measured value is not finite', () => {
    const prose = 'Sentiment held at -0.1.'
    expect(reconcileSentimentProse(prose, Number.NaN)).toEqual([{ text: prose }])
  })

  // ROUND 2 item 1 — the over-correction regression. Only GLOBAL claims may be
  // reconciled against the global measurement; a figure sitting next to a
  // country name is a PER-COUNTRY figure and must pass through untouched.
  describe('per-country figures are never corrected (round-2 regression)', () => {
    const fiveCountryProse =
      'Sentiment split by country: the United States sits at -0.09, ' +
      'China sentiment rose to +0.08, United Kingdom tone is +0.02, ' +
      'India mood fell to -0.05, and Italy tone rests at -0.1. ' +
      'Overall average sentiment for the window is -0.1.'

    it('leaves all 5 per-country figures intact, corrects only the global one', () => {
      const segs = reconcileSentimentProse(fiveCountryProse, -0.52)
      const corrected = segs.filter(s => s.corrected)
      expect(corrected).toHaveLength(1)
      expect(corrected[0].text).toBe('-0.52')
      expect(corrected[0].corrected?.original).toBe('-0.1')
      const joined = joinSegments(segs)
      // Every per-country figure survives verbatim…
      expect(joined).toContain('United States sits at -0.09')
      expect(joined).toContain('China sentiment rose to +0.08')
      expect(joined).toContain('United Kingdom tone is +0.02')
      expect(joined).toContain('India mood fell to -0.05')
      expect(joined).toContain('Italy tone rests at -0.1.')
      // …and only the global claim is rewritten.
      expect(joined).toContain('Overall average sentiment for the window is -0.52.')
    })

    it('never rewrites two polarities into the same number (the repro symptom)', () => {
      const prose =
        'China shows more positive sentiment at +0.08 while the United States ' +
        'and India lean negative in tone at -0.09 and -0.05 each.'
      const segs = reconcileSentimentProse(prose, -0.52)
      expect(segs.filter(s => s.corrected)).toHaveLength(0)
      expect(joinSegments(segs)).toBe(prose)
    })

    it('a country-adjacent figure stays untouched even with global wording elsewhere in the window', () => {
      const prose = 'Across the window, tone in France slid to -0.2 on Tuesday.'
      const segs = reconcileSentimentProse(prose, -0.52)
      expect(segs.filter(s => s.corrected)).toHaveLength(0)
    })

    it('a global figure still corrects when a country name sits farther away than the global wording', () => {
      const prose = 'After the France protests, overall sentiment for the window fell to -0.1 sharply.'
      const segs = reconcileSentimentProse(prose, -0.52)
      const corrected = segs.filter(s => s.corrected)
      expect(corrected).toHaveLength(1)
      expect(joinSegments(segs)).toBe(
        'After the France protests, overall sentiment for the window fell to -0.52 sharply.',
      )
    })

    it('detects bare uppercase ISO codes as country mentions (US/CN class)', () => {
      const prose = 'Sentiment ran at -0.09 in US and +0.08 in CN over the day.'
      const segs = reconcileSentimentProse(prose, -0.52)
      expect(segs.filter(s => s.corrected)).toHaveLength(0)
      expect(joinSegments(segs)).toBe(prose)
    })
  })
})
