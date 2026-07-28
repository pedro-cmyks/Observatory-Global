import { describe, expect, it } from 'vitest'
import {
  SEARCH_LOOKUP_FAILED,
  degradedSearchSegments,
  describeDegradedSegments,
  hasVisibleSearchResults,
  searchEmptyVariant,
} from './searchResults'

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

  it('does not treat curated concept-map hits as visible search results', () => {
    expect(hasVisibleSearchResults({
      themes: [],
      persons: [],
      countries: [],
      concepts: [{ slug: 'blood-diamonds', label: 'Blood Diamonds & Conflict Minerals' }],
      public_attention: [],
      signal_matches: [],
    })).toBe(false)
  })

  it('treats live threads as visible results (GQ-11: 4 threads rendered ABOVE "No results")', () => {
    // The gold UI eval caught 'No results for "…"' rendered below four visible
    // Live Threads rows because this predicate ignored the live_threads lane.
    expect(hasVisibleSearchResults({
      themes: [],
      persons: [],
      countries: [],
      live_threads: [{ id: 'dynamic-topic-1', label: 'HP India Fined for Bid Rigging' }],
      public_attention: [],
      signal_matches: [],
    })).toBe(true)
  })
})

describe('degradedSearchSegments', () => {
  it('returns no segments for a clean response or no response', () => {
    expect(degradedSearchSegments(null)).toEqual([])
    expect(degradedSearchSegments({ degraded: false, degraded_segments: [] })).toEqual([])
    expect(degradedSearchSegments({})).toEqual([])
  })

  it('returns the failed lanes of a degraded response', () => {
    expect(degradedSearchSegments({
      degraded: true,
      degraded_segments: ['live_threads', 'signal_matches'],
    })).toEqual(['live_threads', 'signal_matches'])
  })

  it('falls back to the lookup-failed sentinel when degraded carries no segment names', () => {
    expect(degradedSearchSegments({ degraded: true })).toEqual([SEARCH_LOOKUP_FAILED])
    expect(degradedSearchSegments({ degraded: true, degraded_segments: [] })).toEqual([SEARCH_LOOKUP_FAILED])
  })
})

describe('describeDegradedSegments', () => {
  it('names known lanes in analyst language', () => {
    expect(describeDegradedSegments(['live_threads', 'signal_matches'])).toBe('live threads, media signals')
    expect(describeDegradedSegments(['public_attention'])).toBe('public attention')
    expect(describeDegradedSegments([SEARCH_LOOKUP_FAILED])).toBe('the search request')
  })

  it('degrades unknown segment keys to readable words instead of dropping them', () => {
    expect(describeDegradedSegments(['future_lane'])).toBe('future lane')
  })
})

describe('searchEmptyVariant', () => {
  const empty = { themes: [], persons: [], countries: [] }

  it('claims nothing while loading or before any response landed', () => {
    expect(searchEmptyVariant(null, false)).toBe('none')
    expect(searchEmptyVariant({ ...empty, degraded: false }, true)).toBe('none')
    expect(searchEmptyVariant({ ...empty, degraded: true, degraded_segments: ['signal_matches'] }, true)).toBe('none')
  })

  it('renders measured absence only for a clean empty response', () => {
    expect(searchEmptyVariant({ ...empty, degraded: false, degraded_segments: [] }, false)).toBe('measured_absence')
  })

  it('renders a failed lookup — never "No results" — for a degraded empty response', () => {
    // GQ batch 3: 'Azad Kashmir elections first phase rigging allegations'
    // came back degraded_segments=['signal_matches'] and the UI printed
    // 'No results for "…"'. A timed-out lane is a failed lookup, not absence.
    expect(searchEmptyVariant(
      { ...empty, degraded: true, degraded_segments: ['signal_matches'] },
      false,
    )).toBe('failed_lookup')
  })

  it('shows results (not an empty state) when any lane rendered, even if others failed', () => {
    expect(searchEmptyVariant({
      ...empty,
      live_threads: [{ id: 'dynamic-topic-1' }],
      degraded: true,
      degraded_segments: ['signal_matches'],
    }, false)).toBe('none')
  })
})
