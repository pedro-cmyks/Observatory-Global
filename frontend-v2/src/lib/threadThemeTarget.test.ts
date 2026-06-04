import { describe, expect, it } from 'vitest'
import { resolveThreadThemeTarget } from './threadThemeTarget'

describe('resolveThreadThemeTarget', () => {
  it('routes dynamic threads to the dynamic-topic ThemeDetail slug', () => {
    const target = resolveThreadThemeTarget({
      thread_id: 'dynamic-topic-17',
      label: 'Infrastructure and Public Services',
      anchor_topics: ['infrastructure-public-services'],
      top_countries: ['ID', 'BR'],
      top_country_names: ['Indonesia', 'Brazil'],
    })

    expect(target).toEqual({
      theme: 'dynamic-topic-17',
      originCountry: undefined,
      originCountryName: undefined,
      thread: {
        thread_id: 'dynamic-topic-17',
        label: 'Infrastructure and Public Services',
      },
    })
  })

  it('routes atlas threads through their anchor topic and preserves single-country context', () => {
    const target = resolveThreadThemeTarget({
      thread_id: 'election-legitimacy-dispute--co',
      label: 'Election legitimacy dispute in Colombia',
      anchor_topics: ['election-legitimacy-dispute'],
      top_countries: ['CO'],
      top_country_names: ['Colombia'],
    })

    expect(target).toEqual({
      theme: 'election-legitimacy-dispute',
      originCountry: 'CO',
      originCountryName: 'Colombia',
      thread: {
        thread_id: 'election-legitimacy-dispute--co',
        label: 'Election legitimacy dispute in Colombia',
      },
    })
  })

  it('keeps emergent-only threads on the fallback panel until ThemeDetail supports them', () => {
    expect(resolveThreadThemeTarget({
      thread_id: 'emergent-cluster-44',
      label: 'Fresh cluster',
      anchor_topics: [],
      top_countries: ['CO'],
      top_country_names: ['Colombia'],
    })).toBeNull()
  })
})
