import { describe, expect, it } from 'vitest'

import {
  excludedAfterBarNote,
  gapConfidenceChip,
  gapEmptyCopy,
  gapKicker,
  risingEmptyCopy,
  sectionReceiptToEvidence,
  sectionReceipts,
  whyNowParts,
  type GapSection,
  type RisingSection,
} from './briefSections'

describe('rising — LO QUE SUBE honest states', () => {
  it('says the lane did not answer, never "nothing is rising"', () => {
    const section: RisingSection = { status: 'unavailable', reason: 'movement_unavailable', items: [] }
    expect(risingEmptyCopy(section)).toBe(
      'The movement lane did not answer for this window, so today\'s acceleration is unmeasured — '
      + 'not a claim that nothing is rising.',
    )
  })

  it('says nothing cleared the bar when that is the measurement', () => {
    expect(risingEmptyCopy({ status: 'empty', reason: 'no_story_cleared_the_bar', items: [] })).toBe(
      'No story cleared the acceleration bar in this window.',
    )
  })

  it('falls back to naming an unmapped reason code rather than staying silent', () => {
    expect(risingEmptyCopy({ status: 'unavailable', reason: 'ghost_lane', items: [] })).toBe(
      'Not measured for this window (ghost_lane).',
    )
    expect(risingEmptyCopy({ status: 'empty', items: [] })).toBe(
      'No story cleared the acceleration bar in this window.',
    )
  })

  it('renders nothing when items were served', () => {
    expect(risingEmptyCopy({ status: 'ok', items: [{ thread_id: 'dynamic-topic-1', label: 'x' }] }))
      .toBeNull()
  })

  it('keeps the partial state visible under the served item', () => {
    const partial: RisingSection = {
      status: 'partial',
      reason: 'fewer_than_two_cleared_the_bar',
      items: [{ thread_id: 'dynamic-topic-1', label: 'x' }],
    }
    expect(risingEmptyCopy(partial)).toBeNull()
    expect(gapKicker).toBeTypeOf('string')
  })
})

describe('excluded_after_bar — cleared the bar, could not be printed', () => {
  it('is silent only when nothing was excluded', () => {
    expect(excludedAfterBarNote(undefined)).toBeNull()
    expect(excludedAfterBarNote({})).toBeNull()
    expect(excludedAfterBarNote({ junk: 0 })).toBeNull()
  })

  it('names every reason with its count', () => {
    expect(excludedAfterBarNote({ label_court_too_broad: 2, unlabelled: 1 })).toBe(
      '3 stories cleared the bar but could not be printed: '
      + '2 whose label the court ruled too broad, 1 with no label yet.',
    )
  })

  it('agrees in the singular', () => {
    expect(excludedAfterBarNote({ roundup: 1 })).toBe(
      '1 story cleared the bar but could not be printed: 1 service roundup.',
    )
  })

  it('prints an unmapped reason code verbatim rather than hiding it', () => {
    expect(excludedAfterBarNote({ some_new_reason: 4 })).toBe(
      '4 stories cleared the bar but could not be printed: 4 some new reason.',
    )
  })
})

describe('gap — EL VACÍO honest states', () => {
  const witness: GapSection = {
    status: 'ok',
    reason: null,
    confidence: 'provisional',
    confidence_note: 'the joint rate was inferred, not measured',
    day: '2026-08-12',
    day_complete: false,
    country: { code: 'TL', name: 'Timor-Leste' },
    measured: {
      volume: 28,
      baseline: 2.5,
      baseline_days: 6,
      multiplier: 11.2,
      self_voice_ratio: 0,
      self_voice_status: 'measured',
      known_origin_n: 53,
      domestic_n: 0,
      unattributed_n: 7,
    },
    prose: 'Timor-Leste ran 11.2× its own daily baseline…',
    caveat: 'Much of that is one piece under many mastheads: 53 of the 56 outlets…',
    receipts: [],
  }

  it('distinguishes "nothing cleared" from "we could not look"', () => {
    expect(gapEmptyCopy({ status: 'empty', reason: 'no_country_cleared_the_bar' })).toBe(
      'No country cleared the divergence bar today — no blindspot is claimed.',
    )
    expect(gapEmptyCopy({ status: 'unavailable', reason: 'anomaly_lane_unavailable' })).toBe(
      'The anomaly lane did not answer, so today\'s blindspot is unmeasured — not a claim that '
      + 'there is none.',
    )
    expect(gapEmptyCopy({ status: 'unavailable', reason: 'voice_lane_unavailable' })).toBe(
      'The voice lane did not answer. A volume spike alone is not a blindspot, so nothing is '
      + 'served rather than a finding we cannot support.',
    )
  })

  it('renders nothing when a finding exists', () => {
    expect(gapEmptyCopy(witness)).toBeNull()
  })

  it('carries the provisional confidence with the served note as its tip', () => {
    expect(gapConfidenceChip(witness)).toEqual({
      label: 'PROVISIONAL BAR',
      tip: 'the joint rate was inferred, not measured',
    })
  })

  it('falls back to a generic tip when the payload omits the note', () => {
    expect(gapConfidenceChip({ ...witness, confidence_note: null })?.tip)
      .toContain('provisional')
  })

  it('gives no chip when the bar does not declare a confidence', () => {
    expect(gapConfidenceChip({ ...witness, confidence: undefined })).toBeNull()
  })
})

describe('section receipts', () => {
  it('maps the served receipt shape onto the Brief receipt contract', () => {
    expect(sectionReceiptToEvidence({
      signal_id: 17776884,
      headline: 'All-women East Timorese delegation welcomed to Canberra',
      source: 'gleninnesexaminer.com.au',
      url: 'https://example.com/9329365',
      lang: 'en',
      origin_country: 'AU',
      timestamp: '2026-08-12T14:45:00+00:00',
    })).toEqual({
      id: 17776884,
      headline: 'All-women East Timorese delegation welcomed to Canberra',
      source: 'gleninnesexaminer.com.au',
      url: 'https://example.com/9329365',
      source_lang: 'en',
      source_origin_country: 'AU',
      timestamp: '2026-08-12T14:45:00+00:00',
    })
  })

  it('drops a receipt with no headline (nothing to show) and keeps the rest', () => {
    expect(sectionReceipts([
      { signal_id: 1, headline: '  ' },
      { signal_id: 2, headline: 'Real headline' },
    ])).toEqual([expect.objectContaining({ id: 2, headline: 'Real headline' })])
    expect(sectionReceipts(undefined)).toEqual([])
  })

  it('keeps an id-less receipt (the sealed lane serves some) so it can still translate', () => {
    expect(sectionReceipts([{ headline: 'No id here' }])).toEqual([
      expect.objectContaining({ id: undefined, headline: 'No id here' }),
    ])
  })
})

// X4 (2026-08-13) — blind college C5. "surprise 2.6σ over its own baseline,
// velocity +0.59 (log-volume per 6 h)" was a named witness. The backend now
// serves the plain reading and the statistics separately so the Brief can set
// them differently; this splitter also has to survive a seal frozen BEFORE X4.
describe('whyNowParts — the plain lead and the numbers behind it', () => {
  it('keeps the two halves the backend served', () => {
    const parts = whyNowParts({
      thread_id: 'dynamic-topic-9',
      label: 'x',
      why_now_plain: 'Rising much faster than its own normal pace, and still speeding up',
      why_now_measured: 'surprise 2.6σ over its own baseline, velocity +0.59 (log-volume per 6 h) on 116 signals in the movement window',
      why_now: 'joined — ignored when both halves exist',
    })
    expect(parts.plain).toBe('Rising much faster than its own normal pace, and still speeding up')
    expect(parts.measured).toContain('2.6σ')
    // The number is NOT dropped: this is translation, not simplification.
    expect(parts.measured).toContain('116 signals')
  })

  it('prints a pre-X4 seal verbatim rather than guessing where a clause was', () => {
    const parts = whyNowParts({
      thread_id: 'dynamic-topic-9',
      label: 'x',
      why_now: 'surprise 2.6σ over its own baseline, velocity +0.59 (log-volume per 6 h) on 116 signals in the movement window',
    })
    expect(parts.plain).toBeNull()
    expect(parts.measured).toContain('2.6σ')
  })

  it('has nothing to say when the item carries no why-now at all', () => {
    expect(whyNowParts({ thread_id: 'dynamic-topic-9', label: 'x' }))
      .toEqual({ plain: null, measured: null })
    expect(whyNowParts(null)).toEqual({ plain: null, measured: null })
  })
})
