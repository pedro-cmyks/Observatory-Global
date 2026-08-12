// Prose-vs-tables validator (council Phase 3, Lane B — Marcos: generated prose
// lies more than tables). These tests exercise the pure logic: the
// confirmation-without-corroboration downgrade (the load-bearing case), an
// unbacked numeric figure, a properly-backed claim passing untouched, and the
// context helpers.
import { describe, expect, it } from 'vitest'
import {
  validateProse,
  corroborationBackedFrom,
  joinValidatedText,
  hasUnbacked,
  type MeasuredContext,
} from './proseValidator'
import type { CorroborationData } from './dossierCorroboration'

const NO_CORROBORATION: MeasuredContext = { figures: [], corroborationBacked: false }

describe('confirmation words without a corroboration verdict', () => {
  it('downgrades "confirmed" to "reported (uncorroborated)" when nothing backs it', () => {
    const segs = validateProse('Israel confirmed the strike on the depot.', NO_CORROBORATION)
    const conf = segs.find(s => s.kind === 'unbacked-confirmation')
    expect(conf).toBeTruthy()
    expect(conf!.original).toBe('confirmed')
    expect(conf!.text).toBe('reported (uncorroborated)')
    expect(conf!.note).toMatch(/corroborat/i)
    // The rendered plain text carries the softened word, not "confirmed".
    expect(joinValidatedText(segs)).toBe('Israel reported (uncorroborated) the strike on the depot.')
  })

  it('downgrades verified / corroborated / established the same way', () => {
    for (const word of ['verified', 'corroborated', 'established']) {
      const segs = validateProse(`The toll was ${word} by two outlets.`, NO_CORROBORATION)
      const conf = segs.find(s => s.kind === 'unbacked-confirmation')
      expect(conf, word).toBeTruthy()
      expect(conf!.original).toBe(word)
      expect(conf!.text).toBe('reported (uncorroborated)')
    }
  })

  it('preserves leading-capital when the confirmation word opens a sentence', () => {
    const segs = validateProse('Confirmed by AFP, the depot burned.', NO_CORROBORATION)
    const conf = segs.find(s => s.kind === 'unbacked-confirmation')
    expect(conf!.text).toBe('Reported (uncorroborated)')
  })

  it('leaves confirmation words untouched when a corroboration verdict backs them', () => {
    const ctx: MeasuredContext = { figures: [], corroborationBacked: true }
    const segs = validateProse('Israel confirmed the strike on the depot.', ctx)
    expect(segs.some(s => s.kind === 'unbacked-confirmation')).toBe(false)
    expect(joinValidatedText(segs)).toBe('Israel confirmed the strike on the depot.')
  })
})

describe('numeric figure claims vs the measured set', () => {
  it('flags a thousands-separated figure that no measured value backs', () => {
    const segs = validateProse('At least 4,930 people were killed.', { figures: [4734], corroborationBacked: false })
    const fig = segs.find(s => s.kind === 'unbacked-figure')
    expect(fig).toBeTruthy()
    expect(fig!.original).toBe('4,930')
    // Unbacked figures are flagged, not rewritten — the text is preserved.
    expect(fig!.text).toBe('4,930')
    expect(joinValidatedText(segs)).toBe('At least 4,930 people were killed.')
  })

  it('passes a figure that a measured value backs (exact)', () => {
    const segs = validateProse('At least 4,734 people were killed.', { figures: [4734], corroborationBacked: false })
    expect(segs.some(s => s.kind === 'unbacked-figure')).toBe(false)
  })

  it('passes a measured figure within rounding tolerance of a large count', () => {
    // 4,730 measured vs 4,734 in prose — within relative tolerance.
    const segs = validateProse('About 4,734 dead.', { figures: [4730], corroborationBacked: false })
    expect(segs.some(s => s.kind === 'unbacked-figure')).toBe(false)
  })

  it('flags a sentiment figure the measured set does not carry', () => {
    const segs = validateProse('Global sentiment sat at -0.42.', { figures: [-0.53], corroborationBacked: false })
    expect(segs.find(s => s.kind === 'unbacked-figure')?.original).toBe('-0.42')
  })

  it('backs a sentiment figure within tolerance', () => {
    const segs = validateProse('Global sentiment sat at -0.53.', { figures: [-0.53], corroborationBacked: false })
    expect(segs.some(s => s.kind === 'unbacked-figure')).toBe(false)
  })

  it('flags a %-count the measured set does not carry', () => {
    const segs = validateProse('Roughly 61% of coverage was foreign.', { figures: [42], corroborationBacked: false })
    expect(segs.find(s => s.kind === 'unbacked-figure')?.original).toBe('61')
  })

  it('does not treat a citation marker [4] as a figure claim', () => {
    const segs = validateProse('The depot burned [4] overnight.', NO_CORROBORATION)
    expect(segs.some(s => s.kind === 'unbacked-figure')).toBe(false)
  })

  it('does not treat a bare year as a figure claim', () => {
    const segs = validateProse('The escalation began in 2026.', NO_CORROBORATION)
    expect(segs.some(s => s.kind === 'unbacked-figure')).toBe(false)
  })

  it('ignores small unqualified integers that are not quantity claims', () => {
    const segs = validateProse('The strike lasted 3 hours.', NO_CORROBORATION)
    // "3" is not thousands-separated, not near a quantity keyword, not a % — pass.
    expect(segs.some(s => s.kind === 'unbacked-figure')).toBe(false)
  })
})

// Frank test 2026-08-12 (break d.3): the lede rendered "2026⚠-08⚠-10⚠" — every
// component of an ISO date read as an unbacked figure because a quantity keyword
// ("outlets") sat inside the 40-char window. A date is never a figure claim.
describe('dates are never figure claims (Frank witness "2026-08-10")', () => {
  it('leaves an ISO date untouched even beside a quantity keyword', () => {
    const prose = 'The deal was reported by multiple outlets on 2026-08-10 and 2026-08-12 [2][3].'
    const segs = validateProse(prose, NO_CORROBORATION)
    expect(segs.some(s => s.kind === 'unbacked-figure')).toBe(false)
    expect(joinValidatedText(segs)).toBe(prose)
  })

  it('leaves DD-MM-YYYY and slashed dates untouched', () => {
    for (const prose of [
      'Outlets reported 10-08-2026 as the announcement date.',
      'Outlets reported 2026/08/10 as the announcement date.',
      'Outlets reported 08/10/2026 as the announcement date.',
    ]) {
      const segs = validateProse(prose, NO_CORROBORATION)
      expect(segs.some(s => s.kind === 'unbacked-figure'), prose).toBe(false)
    }
  })

  it('leaves long-form dates untouched', () => {
    for (const prose of [
      'Sources say the memorandum was signed on August 10, 2026.',
      'Sources say the memorandum was signed on 10 August 2026.',
      'Sources say the memorandum was signed on Aug. 10.',
    ]) {
      const segs = validateProse(prose, NO_CORROBORATION)
      expect(segs.some(s => s.kind === 'unbacked-figure'), prose).toBe(false)
    }
  })

  it('still flags a real count that sits next to a date', () => {
    const segs = validateProse(
      'At least 4,930 dead were reported on 2026-08-10.',
      { figures: [4734], corroborationBacked: false },
    )
    const flagged = segs.filter(s => s.kind === 'unbacked-figure').map(s => s.original)
    expect(flagged).toEqual(['4,930'])
  })

  it('still flags a count inside a month-named sentence (March is not a date here)', () => {
    const segs = validateProse(
      'The March left 5,000 dead.',
      { figures: [], corroborationBacked: false },
    )
    expect(segs.find(s => s.kind === 'unbacked-figure')?.original).toBe('5,000')
  })
})

// Frank test 2026-08-12 (break d.2): when the corroboration lane 502s, the
// substitution spliced the phrase into NEGATED clauses and destroyed both the
// grammar and the meaning ("could not be verified" → "could not be reported
// (uncorroborated)" claims the opposite). A negated confirmation word is already
// an honest statement of absence — never downgrade it.
describe('degraded copy stays grammatical (Frank 502-run witnesses)', () => {
  const rendered = (prose: string) => joinValidatedText(validateProse(prose, NO_CORROBORATION))

  it('witness 1 — "not confirmed connected" is left verbatim', () => {
    const prose = 'They are topically adjacent but not confirmed connected to the Syria-Russia bases deal.'
    expect(rendered(prose)).toBe(prose)
    expect(rendered(prose)).not.toContain('reported (uncorroborated) connected')
  })

  it('witness 2 — "share no confirmed actor" is left verbatim', () => {
    const prose = 'They share no confirmed actor with it.'
    expect(rendered(prose)).toBe(prose)
  })

  it('witness 3 — "could not be verified or linked to the confirmed deal" is left verbatim', () => {
    const prose = 'Their content could not be verified or linked to the confirmed deal [2][3].'
    expect(rendered(prose)).toBe(prose)
    expect(rendered(prose)).not.toContain('reported (uncorroborated) or linked')
  })

  it('covers the contracted and lexical negations', () => {
    for (const prose of [
      "The link wasn't confirmed by any outlet.",
      'The link was never confirmed by any outlet.',
      'The link cannot be verified from the frozen evidence.',
      'The transfer went ahead without corroborated receipts.',
    ]) {
      expect(rendered(prose), prose).toBe(prose)
    }
  })

  it('an honest negative is not counted as unbacked prose', () => {
    const segs = validateProse('Their content could not be verified.', NO_CORROBORATION)
    expect(hasUnbacked(segs)).toBe(false)
  })

  it('still downgrades the ASSERTION in a later clause of the same sentence', () => {
    // The negation scopes to its own clause: "was confirmed by AFP" after the
    // comma is a fresh, unbacked assertion and must still be softened.
    const out = rendered('The report was not published, but the strike was confirmed by AFP.')
    expect(out).toBe('The report was not published, but the strike was reported (uncorroborated) by AFP.')
  })

  it('still downgrades a plain unbacked assertion', () => {
    expect(rendered('Israel confirmed the strike on the depot.'))
      .toBe('Israel reported (uncorroborated) the strike on the depot.')
  })
})

describe('a properly-backed claim passes untouched', () => {
  it('returns a single ok segment when nothing is unbacked', () => {
    const ctx: MeasuredContext = { figures: [4734], corroborationBacked: true }
    const prose = 'Reuters confirmed at least 4,734 dead across the region.'
    const segs = validateProse(prose, ctx)
    expect(hasUnbacked(segs)).toBe(false)
    expect(segs).toHaveLength(1)
    expect(segs[0].kind).toBe('ok')
    expect(joinValidatedText(segs)).toBe(prose)
  })
})

describe('mixed prose interleaves ok text with flagged segments', () => {
  it('carves out both an unbacked figure and an unbacked confirmation, in order', () => {
    const prose = 'AFP confirmed 4,930 dead.'
    const segs = validateProse(prose, { figures: [4734], corroborationBacked: false })
    const kinds = segs.map(s => s.kind)
    expect(kinds).toContain('unbacked-confirmation')
    expect(kinds).toContain('unbacked-figure')
    expect(joinValidatedText(segs)).toBe('AFP reported (uncorroborated) 4,930 dead.')
  })
})

describe('empty / degenerate input', () => {
  it('returns [] for empty prose', () => {
    expect(validateProse('', NO_CORROBORATION)).toEqual([])
  })

  it('returns a single ok segment for plain prose with no claims', () => {
    const segs = validateProse('The situation remains fluid.', NO_CORROBORATION)
    expect(segs).toEqual([{ text: 'The situation remains fluid.', kind: 'ok' }])
  })
})

describe('corroborationBackedFrom', () => {
  const base: Omit<CorroborationData, 'pins'> = {
    contract: 'dossier-corroboration-v1',
    measured_at: new Date().toISOString(),
    search_available: true,
    search_source: 'gdelt-doc-2.0',
    window_days: 14,
    coverage_asymmetry: null,
  }
  const pin = (status: CorroborationData['pins'][number]['status']) => ({
    id: 'p', label: 'l', status, independent_outlets: 2, total_articles: 3,
    syndicated_clusters: 0, single_source: false, citations: [], note: '', queries: [],
  })

  it('is false when corroboration was never run', () => {
    expect(corroborationBackedFrom(null)).toBe(false)
  })

  it('is false when the search lane was unavailable', () => {
    expect(corroborationBackedFrom({ ...base, search_available: false, pins: [pin('established')] })).toBe(false)
  })

  it('is true when at least one pin is established', () => {
    expect(corroborationBackedFrom({ ...base, pins: [pin('unverified'), pin('established')] })).toBe(true)
  })

  it('is false when every pin is unverified / contested / not_applicable', () => {
    expect(corroborationBackedFrom({ ...base, pins: [pin('unverified'), pin('contested'), pin('not_applicable')] })).toBe(false)
  })
})
