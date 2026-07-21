import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  composeCountrySections,
  fetchCountryEdition,
  type CountryGap,
} from './countryEdition'

const worldA = { label: 'Election dispute', category: 'election-legitimacy' }
const worldB = { label: 'Flood disaster', category: 'weather-and-climate' }
const gap: CountryGap = {
  slug: 'labor', label: 'Labor strike', raw_signals: 12, verified: 0, scored: 12,
}

describe('composeCountrySections', () => {
  it('returns the three kinds in order and drops nothing', () => {
    const [today, radar, culture] = composeCountrySections([worldA, worldB], [gap])
    expect([today.kind, radar.kind, culture.kind]).toEqual([
      'country_today', 'under_radar', 'culture_sport_life',
    ])
    // every thread lands in exactly one of today/culture (split is total)
    expect(today.threads.length + culture.threads.length).toBe(2)
    expect(radar.gaps).toHaveLength(1)
    expect(radar.threads).toHaveLength(0)
  })

  it('thin country: sections with no content are honest-empty, never invented', () => {
    const [today, radar, culture] = composeCountrySections([worldA], [])
    expect(radar.present).toBe(false)
    expect(radar.empty_reason).toBeTruthy()
    expect(radar.gaps).toHaveLength(0)
    if (!culture.present) expect(culture.empty_reason).toBeTruthy()
    expect(today.present || today.empty_reason).toBeTruthy()
  })

  it('zero threads and zero gaps: all three honest-empty', () => {
    const [today, radar, culture] = composeCountrySections([], [])
    expect(today.present).toBe(false)
    expect(radar.present).toBe(false)
    expect(culture.present).toBe(false)
    for (const s of [today, radar, culture]) expect(s.empty_reason).toBeTruthy()
  })

  it('present flag matches content presence', () => {
    const [today, radar] = composeCountrySections([worldA], [gap])
    expect(today.present).toBe(today.threads.length > 0)
    expect(radar.present).toBe(radar.gaps.length > 0)
  })
})

describe('fetchCountryEdition (honest degrade)', () => {
  afterEach(() => { vi.restoreAllMocks() })

  it('returns the edition on a valid contract response', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: true,
      json: async () => ({ contract: 'country-edition-v0', country: 'CO' }),
    })))
    const ed = await fetchCountryEdition('CO')
    expect(ed?.country).toBe('CO')
  })

  it('returns null on non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, json: async () => ({}) })))
    expect(await fetchCountryEdition('CO')).toBeNull()
  })

  it('returns null on wrong contract', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: true, json: async () => ({ contract: 'something-else' }),
    })))
    expect(await fetchCountryEdition('CO')).toBeNull()
  })

  it('returns null when fetch throws', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('net') }))
    expect(await fetchCountryEdition('CO')).toBeNull()
  })
})
