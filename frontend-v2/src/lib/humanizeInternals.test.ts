import { describe, it, expect } from 'vitest'
import { humanizeCameoEvent, humanizeReadinessValue } from './humanizeInternals'

// Jargon purge (council wish 7): progressive disclosure — a human sentence by
// default, the measured internal preserved for the hover. Information is never
// deleted, only moved behind the data-tip.
describe('humanizeCameoEvent', () => {
  it('rewrites CAMEO codebook imperatives into event nouns', () => {
    expect(humanizeCameoEvent('Use unconventional violence')).toBe('Unconventional violence')
    expect(humanizeCameoEvent('Use conventional military force')).toBe('Military force')
    expect(humanizeCameoEvent('Engage in political dissent')).toBe('Political dissent')
    expect(humanizeCameoEvent('Employ aerial weapons')).toBe('Aerial weapons use')
    expect(humanizeCameoEvent('Conduct suicide, car, or other non-military bombing')).toBe('Bombing')
  })

  it('passes already-human labels through unchanged', () => {
    expect(humanizeCameoEvent('Protest')).toBe('Protest')
    expect(humanizeCameoEvent('Armed clash')).toBe('Armed clash')
  })

  it('handles empty/null-ish input with a neutral fallback', () => {
    expect(humanizeCameoEvent('')).toBe('Conflict event')
  })
})

describe('humanizeReadinessValue', () => {
  it('flags changed_10h internals and paraphrases them', () => {
    const r = humanizeReadinessValue('changed_10h=-38')
    expect(r.internal).toBe(true)
    expect(r.raw).toBe('changed_10h=-38')
    expect(r.text).toMatch(/movement|volume/i)
    expect(r.text).toMatch(/10\s?h/i)
    expect(r.text).toMatch(/-38/)
    expect(r.text).not.toMatch(/changed_10h/)
  })

  it('handles the PRODUCTION "Label: key=value" shape (fix round item 4)', () => {
    // Exact shape seen live in the generated dossier WHY cell — the old regex
    // was anchored ^key=value and let this leak through verbatim.
    const r = humanizeReadinessValue('US Iran Exchange Strikes: changed_10h=+15')
    expect(r.internal).toBe(true)
    expect(r.raw).toBe('US Iran Exchange Strikes: changed_10h=+15')
    expect(r.text).toMatch(/^US Iran Exchange Strikes: /)
    expect(r.text).toMatch(/movement|volume/i)
    expect(r.text).toMatch(/\+15/)
    expect(r.text).not.toMatch(/changed_10h/)
  })

  it('replaces EVERY embedded key=value, keeping surrounding prose', () => {
    const r = humanizeReadinessValue('spike: changed_10h=-38 · gate_score=0.91')
    expect(r.internal).toBe(true)
    expect(r.text).not.toMatch(/changed_10h|gate_score/)
    expect(r.text).toMatch(/-38/)
    expect(r.text).toMatch(/0\.91/)
    expect(r.text).toMatch(/^spike: /)
  })

  it('flags bare snake_case key=value internals generically', () => {
    const r = humanizeReadinessValue('gate_score=0.91')
    expect(r.internal).toBe(true)
    expect(r.text).not.toMatch(/_/)
  })

  it('flags opaque node ids/hashes', () => {
    expect(humanizeReadinessValue('dynamic-topic-821').internal).toBe(true)
    expect(humanizeReadinessValue('a3f9c21b7d04e6f2').internal).toBe(true)
  })

  it('keeps human values untouched', () => {
    const r = humanizeReadinessValue('Venezuela earthquake response')
    expect(r.internal).toBe(false)
    expect(r.text).toBe('Venezuela earthquake response')
  })
})
