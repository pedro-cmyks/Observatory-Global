import { describe, expect, it } from 'vitest'
import { buildCountryThreadEmptyState, getNarrativeFetchLimit, getNarrativesForDisplay } from './narrativeThreadLimits'

describe('NarrativeThreads limits', () => {
  it('fetches enough global narratives to fill the available panel space', () => {
    expect(getNarrativeFetchLimit(false)).toBeGreaterThanOrEqual(20)
  })

  it('does not cap rendered narratives to a fixed five-row list', () => {
    const narratives = Array.from({ length: 12 }, (_, index) => ({
      theme_code: `theme-${index}`,
      top_countries: ['US'],
    }))

    expect(getNarrativesForDisplay(narratives, undefined)).toHaveLength(12)
    expect(getNarrativesForDisplay(narratives, 'US')).toHaveLength(12)
  })

  it('explains a country-scoped empty state without implying the global story list is broken', () => {
    expect(buildCountryThreadEmptyState('CO', 'Colombia')).toEqual({
      title: 'No living Stories detected for Colombia in this window',
      body: 'Atlas asked for country-scoped stories. This usually means Colombia has signals, but no coherent story cleared the current quality gate for the selected time range.',
      actionLabel: 'Show global stories',
    })
  })
})
