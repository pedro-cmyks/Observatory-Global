import { describe, expect, it } from 'vitest'
import { buildSearchSection, parseSearchRows, SEARCH_ROW_CAP } from './searchSheet'

describe('buildSearchSection — phases without a response body', () => {
  it('idle: invites a search, never a blank sheet', () => {
    const s = buildSearchSection('', { kind: 'idle' })
    expect(s.state).toBe('empty')
    expect(s.reason).toBeTruthy()
    expect(s.rows).toEqual([])
  })

  it('too_short: names the floor, distinct from a measured "no results"', () => {
    const s = buildSearchSection('a', { kind: 'too_short' })
    expect(s.state).toBe('empty')
    expect(s.reason).toMatch(/2 characters/i)
  })

  it('loading is its own state, not folded into empty', () => {
    const s = buildSearchSection('iran', { kind: 'loading' })
    expect(s.state).toBe('loading')
    expect(s.rows).toEqual([])
    expect(s.reason).toBeTruthy()
  })

  it('network_error degrades — it must never claim a measured absence', () => {
    const s = buildSearchSection('iran', { kind: 'network_error' })
    expect(s.state).toBe('degraded')
    expect(s.reason).toBeTruthy()
    expect(s.reason).not.toMatch(/no results/i)
  })
})

describe('buildSearchSection — http errors, 429 named specifically', () => {
  it('a 429 reads as a rate limit, not a generic failure', () => {
    const s = buildSearchSection('iran', { kind: 'http_error', status: 429 })
    expect(s.state).toBe('degraded')
    expect(s.reason).toMatch(/too many|rate|wait/i)
  })

  it('a different status gets a different, generic reason than 429', () => {
    const s500 = buildSearchSection('iran', { kind: 'http_error', status: 500 })
    const s429 = buildSearchSection('iran', { kind: 'http_error', status: 429 })
    expect(s500.state).toBe('degraded')
    expect(s500.reason).toBeTruthy()
    expect(s500.reason).not.toBe(s429.reason)
    expect(s500.reason).not.toMatch(/too many|rate/i)
  })
})

const okJson = {
  live_threads: [
    { id: 'dynamic-topic-1', label: 'Berlin Pride Attack', category: 'protest', total_signals: 40, is_umbrella: false, match: 'all' },
  ],
  themes: [
    { theme: 'ARMEDCONFLICT', label: 'stale legacy label', category: null, total_signals: 12 },
  ],
  countries: [{ code: 'IR', name: 'Iran' }],
  persons: [{ person: 'trump', total_signals: 500 }],
  signal_matches: [
    { id: 9, country: 'US', source: 'example.com', headline: 'A real headline', themes: ['ARMEDCONFLICT'] },
  ],
}

describe('parseSearchRows — the row model', () => {
  it('tags every row with what it is', () => {
    const rows = parseSearchRows(okJson)
    expect(rows.map((r) => r.kind)).toEqual(['thread', 'thread', 'country', 'person', 'signal'])
  })

  it('orders threads, then countries, then people, then signals', () => {
    const kinds = parseSearchRows(okJson).map((r) => r.kind)
    expect(kinds.indexOf('thread')).toBeLessThan(kinds.indexOf('country'))
    expect(kinds.indexOf('country')).toBeLessThan(kinds.indexOf('person'))
    expect(kinds.indexOf('person')).toBeLessThan(kinds.indexOf('signal'))
  })

  it('keeps every live thread regardless of total_signals — the server already filtered them', () => {
    const rows = parseSearchRows({
      live_threads: [{ id: 't1', label: 'x', total_signals: 0 }],
      themes: [], countries: [], persons: [], signal_matches: [],
    })
    expect(rows.map((r) => r.id)).toEqual(['t1'])
  })

  it('drops zero-signal legacy themes and persons — the same floor SearchBar applies', () => {
    const rows = parseSearchRows({
      live_threads: [],
      themes: [{ theme: 'A', total_signals: 0 }, { theme: 'B', total_signals: 5 }],
      persons: [{ person: 'nobody', total_signals: 0 }, { person: 'somebody', total_signals: 3 }],
      countries: [], signal_matches: [],
    })
    expect(rows.filter((r) => r.kind === 'thread').map((r) => r.id)).toEqual(['B'])
    expect(rows.filter((r) => r.kind === 'person').map((r) => r.label)).toEqual(['somebody'])
  })

  it('translates a legacy theme code through the injected labeler, defaulting to identity', () => {
    const raw = { live_threads: [], themes: [{ theme: 'ARMEDCONFLICT', total_signals: 3 }], countries: [], persons: [], signal_matches: [] }
    const labeled = parseSearchRows(raw, { labelForTheme: (code) => (code === 'ARMEDCONFLICT' ? 'Armed Conflict' : code) })
    expect(labeled[0].label).toBe('Armed Conflict')
    const identity = parseSearchRows(raw)
    expect(identity[0].label).toBe('ARMEDCONFLICT')
  })

  it('ignores the raw t.label field for legacy themes — SearchBar renders getThemeLabel(theme), not it', () => {
    const rows = parseSearchRows({
      live_threads: [], themes: [{ theme: 'ARMEDCONFLICT', label: 'stale legacy label', total_signals: 3 }],
      countries: [], persons: [], signal_matches: [],
    })
    expect(rows[0].label).toBe('ARMEDCONFLICT')
  })

  it('a signal row falls back to naming its source when the headline is null', () => {
    const rows = parseSearchRows({
      live_threads: [], themes: [], countries: [], persons: [],
      signal_matches: [{ id: 3, country: 'US', source: 'wire.example', headline: null, themes: [] }],
    })
    expect(rows[0].label).toBe('Signal from wire.example')
  })

  it('drops a signal with neither a thread nor a country — no door for a tap to open', () => {
    const rows = parseSearchRows({
      live_threads: [], themes: [], countries: [], persons: [],
      signal_matches: [
        { id: 1, country: null, source: 'x', headline: 'dead end', themes: [] },
        { id: 2, country: 'US', source: 'x', headline: 'has a country', themes: [] },
        { id: 3, country: null, source: 'x', headline: 'has a theme', themes: ['ARMEDCONFLICT'] },
      ],
    })
    expect(rows.map((r) => r.id)).toEqual(['2', '3'])
  })

  it('caps each kind rather than rendering an unbounded phone list', () => {
    const many = Array.from({ length: SEARCH_ROW_CAP + 8 }, (_, i) => ({ code: `C${i}`, name: `Country ${i}` }))
    const rows = parseSearchRows({ live_threads: [], themes: [], persons: [], signal_matches: [], countries: many })
    expect(rows.filter((r) => r.kind === 'country').length).toBe(SEARCH_ROW_CAP)
  })

  it('returns nothing for a malformed body instead of throwing', () => {
    expect(parseSearchRows('not an object')).toEqual([])
    expect(parseSearchRows(null)).toEqual([])
    expect(parseSearchRows(undefined)).toEqual([])
  })
})

describe('buildSearchSection — ok responses', () => {
  it('state ok, rows shaped and counted', () => {
    const s = buildSearchSection('iran', { kind: 'ok', json: okJson })
    expect(s.state).toBe('ok')
    expect(s.rows.length).toBe(5)
    expect(s.reason).toBeUndefined()
  })

  it('zero rows and no failed lane: measured absence, names the query', () => {
    const s = buildSearchSection('xyzzy', {
      kind: 'ok',
      json: { live_threads: [], themes: [], countries: [], persons: [], signal_matches: [] },
    })
    expect(s.state).toBe('empty')
    expect(s.reason).toContain('xyzzy')
  })

  it('zero rows WITH a failed lane: a failed lookup, never phrased as absence', () => {
    const s = buildSearchSection('xyzzy', {
      kind: 'ok',
      json: {
        live_threads: [], themes: [], countries: [], persons: [], signal_matches: [],
        degraded: true, degraded_segments: ['signal_matches'],
      },
    })
    expect(s.state).toBe('degraded')
    expect(s.reason).not.toMatch(/no results/i)
    expect(s.rows).toEqual([])
  })

  it('real rows alongside a failed sibling lane: rows stand, the gap rides beside them (not instead of them)', () => {
    const s = buildSearchSection('iran', {
      kind: 'ok',
      json: { ...okJson, degraded: true, degraded_segments: ['public_attention'] },
    })
    expect(s.state).toBe('ok')
    expect(s.rows.length).toBe(5)
    expect(s.partialFailure).toBeTruthy()
  })

  it('a non-object body degrades rather than throwing', () => {
    expect(() => buildSearchSection('iran', { kind: 'ok', json: 'not an object' })).not.toThrow()
    const s = buildSearchSection('iran', { kind: 'ok', json: 'not an object' })
    expect(s.state).toBe('degraded')
    expect(s.rows).toEqual([])
  })

  it('a null body (failed JSON parse, upstream) degrades rather than throwing', () => {
    const s = buildSearchSection('iran', { kind: 'ok', json: null })
    expect(s.state).toBe('degraded')
  })
})
