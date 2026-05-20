import { describe, expect, it } from 'vitest'
import { hasVisibleSearchResults } from './searchResults'

describe('hasVisibleSearchResults', () => {
  it('treats public attention and signal headline matches as visible results', () => {
    expect(hasVisibleSearchResults({
      themes: [{ theme: 'HEALTH', total_signals: 0, top_countries: [] }],
      persons: [],
      countries: [],
      public_attention: [{ title: 'Orthohantavirus', views: 100, country_count: 5 }],
      signal_matches: [],
    })).toBe(true)

    expect(hasVisibleSearchResults({
      themes: [],
      persons: [],
      countries: [],
      public_attention: [],
      signal_matches: [{ id: 1, headline: 'CDC reports hantavirus case', country: 'US', source: 'example.com', timestamp: '2026-05-07T00:00:00Z', themes: ['HEALTH'] }],
    })).toBe(true)
  })
})
