import { describe, expect, it } from 'vitest'
import { getNarrativeFetchLimit, getNarrativesForDisplay } from './narrativeThreadLimits'

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
})
