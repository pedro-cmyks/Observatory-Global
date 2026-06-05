import { describe, expect, it } from 'vitest'
import { buildThemeDetailEmptyState } from './themeDetailEmptyState'

describe('ThemeDetail empty state', () => {
  it('explains zero-result country-scoped thread detail as a quality gate, not missing data', () => {
    expect(buildThemeDetailEmptyState({
      label: 'Russia-Ukraine War Updates',
      countryName: 'Colombia',
      hours: 24,
      openedFrom: 'thread',
    })).toEqual({
      title: 'No country-scoped evidence for Russia-Ukraine War Updates in Colombia',
      body: 'Atlas opened the thread detail, but the Colombia slice has no signals that cleared the current thread quality gate in the last 24h. The country can still have signals in other threads.',
      primaryAction: 'Return to global thread',
      secondaryNote: 'Use global view to inspect the full thread, or change the time range if this should include older evidence.',
    })
  })
})
