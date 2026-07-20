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

  it('shows the gated count (not raw) once the gate has scored a thread', () => {
    const summary = buildCountryBriefThreadSummary({
      threads: [
        {
          thread_id: 'dynamic-topic-50',
          label: 'Water stress',
          signal_count: 44,
          gated_signal_count: 5,
          gate_scored_count: 44,
        },
      ],
      fallbackThemes: [],
    })
    const row = summary.rows[0]
    expect(row.count).toBe(5) // gated, not 44
    expect(row.rawCount).toBe(44)
    expect(row.belowGate).toBe(false)
    expect(summary.count).toBe(1)
  })

  it('flags a scored-but-zero-kept thread as below gate and drops it from the count', () => {
    const summary = buildCountryBriefThreadSummary({
      threads: [
        {
          thread_id: 'dynamic-topic-51',
          label: 'Election legitimacy',
          signal_count: 44,
          gated_signal_count: 0,
          gate_scored_count: 44,
        },
      ],
      fallbackThemes: [],
    })
    expect(summary.rows[0].belowGate).toBe(true)
    expect(summary.rows[0].rawCount).toBe(44)
    expect(summary.count).toBe(0) // not a confident thread
  })

  it('carries the Label Court verdict through to the row (N15 — chip on every label surface)', () => {
    const summary = buildCountryBriefThreadSummary({
      threads: [
        { thread_id: 'dynamic-topic-7', label: 'Failed label', signal_count: 12, label_status: 'failed' },
        { thread_id: 'dynamic-topic-8', label: 'Unchecked label', signal_count: 9 },
      ],
      fallbackThemes: [],
    })
    expect(summary.rows[0].labelStatus).toBe('failed')
    expect(summary.rows[1].labelStatus).toBeNull()
  })
})
