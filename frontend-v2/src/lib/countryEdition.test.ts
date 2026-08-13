import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  composeCountrySections,
  editionAgeNote,
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

  // X1 (2026-08-13): an empty country section is a fact about Atlas's ingest,
  // never about the country. "Quiet in the last 24h" read as a calm country
  // when the truth was a thin domestic feed set — the inversion the veracity
  // scorecard refuted on Colombia.
  it('empty reasons name the ingest, never call the country quiet', () => {
    const [today, radar, culture] = composeCountrySections([], [])
    for (const s of [today, radar, culture]) {
      expect(s.empty_reason).toContain('Atlas')
    }
    expect(today.empty_reason).not.toContain('quiet')
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

  it('bounds the wait so "assembling…" can never become forever', async () => {
    // Judge §4.3: 30+ seconds on the assembling message, twice, no resolution.
    // The request must carry an abort signal; without one the page has no way
    // to turn a hang into an honest failure state with a retry.
    const spy = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(init?.signal).toBeTruthy()
      return { ok: true, json: async () => ({ contract: 'country-edition-v0', country: 'CO' }) }
    })
    vi.stubGlobal('fetch', spy)
    await fetchCountryEdition('CO')
    expect(spy).toHaveBeenCalledOnce()
  })

  it('degrades to null when the wait is aborted', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw Object.assign(new Error('aborted'), { name: 'AbortError' })
    }))
    expect(await fetchCountryEdition('CO')).toBeNull()
  })
})

// ── precomputed-door age note (council R4 N26) ───────────────────────────────
// The door now serves a nightly artifact when one is fresh. That is the fix for
// the cold 503, but it introduces staleness the reader cannot see anywhere else
// on the page: the vitals beside the edition ("Signals · in the last 24h") are
// live. So an artifact-served edition says how old it is.
describe('editionAgeNote', () => {
  it('says nothing for a live build — there is nothing to disclose', () => {
    expect(editionAgeNote(null)).toBeNull()
    expect(editionAgeNote(undefined)).toBeNull()
    expect(editionAgeNote({ source: 'precomputed_artifact' })).toBeNull()
  })

  it('says nothing for a fresh artifact under an hour old', () => {
    expect(editionAgeNote({ age_hours: 0.4, stale: false })).toBeNull()
  })

  it('names the age of a same-day artifact', () => {
    expect(editionAgeNote({ age_hours: 9.2, stale: false })).toBe('Assembled 9h ago')
  })

  it('switches to days once the build is older than a day', () => {
    expect(editionAgeNote({ age_hours: 30, stale: true }))
      .toBe('Assembled 1d ago — serving the last edition Atlas could build')
  })

  it('always speaks when the artifact is a degraded fallback, however young', () => {
    // the live rebuild failed: age alone would have kept this silent
    expect(editionAgeNote({ age_hours: 0.2, degraded: true }))
      .toBe('Assembled less than an hour ago — serving the last edition Atlas could build')
  })
})
