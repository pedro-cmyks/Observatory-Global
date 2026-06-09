import { describe, expect, it } from 'vitest'
import { buildCountryBriefThreadSummary } from './countryBriefThreads'

describe('CountryBrief thread summary', () => {
  it('counts country-scoped Narrative Threads instead of the fixed GDELT theme cap', () => {
    const gdeltThemes = Array.from({ length: 12 }, (_, index) => ({
      name: `GDELT_THEME_${index}`,
      count: 100 - index,
    }))
    const threads = [
      {
        thread_id: 'dynamic-topic-17',
        label: 'Infrastructure pressure',
        signal_count: 44,
        anchor_topics: ['infrastructure-public-services'],
      },
      {
        thread_id: 'dynamic-topic-18',
        label: 'Election legitimacy dispute',
        signal_count: 22,
        anchor_topics: ['election-legitimacy-dispute'],
      },
      {
        thread_id: 'dynamic-topic-19',
        label: 'Border security escalation',
        signal_count: 9,
        anchor_topics: ['migration-border-pressure'],
      },
    ]

    const summary = buildCountryBriefThreadSummary({
      threads,
      fallbackThemes: gdeltThemes,
    })

    expect(summary.count).toBe(3)
    expect(summary.label).toBe('threads')
    expect(summary.rows.map(row => row.name)).toEqual([
      'dynamic-topic-17',
      'dynamic-topic-18',
      'dynamic-topic-19',
    ])
  })

  it('does not fall back to a forced theme count when no country threads clear the gate', () => {
    const gdeltThemes = Array.from({ length: 12 }, (_, index) => ({
      name: `GDELT_THEME_${index}`,
      count: 100 - index,
    }))

    const summary = buildCountryBriefThreadSummary({
      threads: [],
      fallbackThemes: gdeltThemes,
    })

    expect(summary.count).toBe(0)
    expect(summary.rows).toEqual([])
  })
})
