import { describe, it, expect } from 'vitest'
import { computeFocusRelation } from './focusRelation'

describe('computeFocusRelation (#234 shared focus-relation context)', () => {
  it('no focus → inactive, panels stay global', () => {
    const r = computeFocusRelation({ focusType: null, focusValue: null, filterCountry: null, nodes: [] })
    expect(r.relationActive).toBe(false)
    expect(r.dominantCountry).toBeNull()
  })

  it('country focus → the country is its own dominant', () => {
    const r = computeFocusRelation({ focusType: 'country', focusValue: 'CO', filterCountry: 'CO', nodes: [] })
    expect(r.kind).toBe('country')
    expect(r.dominantCountry).toBe('CO')
    expect(r.relationActive).toBe(true)
  })

  it('person focus → dominant is the top-volume node, relations volume-normalised', () => {
    const r = computeFocusRelation({
      focusType: 'person', focusValue: 'trump', filterCountry: null,
      nodes: [{ id: 'US', signalCount: 2497 }, { id: 'IR', signalCount: 917 }, { id: 'IL', signalCount: 325 }],
    })
    expect(r.dominantCountry).toBe('US')
    expect(r.relationActive).toBe(true)
    expect(r.relationCountries['US']).toBe(1)               // max → weight 1
    expect(r.relationCountries['IR']).toBeCloseTo(917 / 2497, 4)
  })

  it('entity focus with no nodes → inactive (no fabricated relation)', () => {
    const r = computeFocusRelation({ focusType: 'person', focusValue: 'nobody', filterCountry: null, nodes: [] })
    expect(r.relationActive).toBe(false)
  })

  it('theme/thread focus also resolves a dominant country', () => {
    const r = computeFocusRelation({
      focusType: 'theme', focusValue: 'flood', filterCountry: null,
      nodes: [{ id: 'IN', signalCount: 50 }, { id: 'US', signalCount: 80 }],
    })
    expect(r.dominantCountry).toBe('US')
    expect(r.kind).toBe('theme')
  })
})
