import { describe, expect, it } from 'vitest'
import { buildHistoricalCoverageCue } from './historicalCoverageCue'

describe('historical coverage cue', () => {
  it('builds a visible cue for processed historical app windows', () => {
    expect(buildHistoricalCoverageCue({
      source: 'historical_topic_country_daily',
      coverage: {
        source: 'historical_processed',
        modelVersion: 'atlas-hist-v1',
        requestedHours: 720,
        partialCoverage: false,
      },
    })).toEqual({
      label: 'Historical processed',
      tip: 'This long-window map is served from compact processed historical aggregates (atlas-hist-v1), not raw hot-store rows.',
    })
  })
})
