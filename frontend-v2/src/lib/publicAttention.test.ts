import { describe, expect, it } from 'vitest'
import {
  buildCountryPublicAttentionNarrative,
  getPublicAttentionTopUrl,
  getTrendingSearchesUrl,
} from './publicAttention'

describe('public attention helpers', () => {
  it('uses a seven-day wiki window so daily ingestion gaps do not look like endless loading', () => {
    expect(getPublicAttentionTopUrl(10)).toBe('/api/v2/wiki/top?days=7&limit=10')
  })

  it('scopes public attention URLs to a country when provided', () => {
    expect(getPublicAttentionTopUrl(6, 'co')).toBe('/api/v2/wiki/top?days=7&limit=6&country_code=CO')
    expect(getTrendingSearchesUrl(5, 24, 'co')).toBe('/api/v2/trends/search?hours=24&limit=5&country_code=CO')
  })

  it('builds a country narrative that combines media and public attention evidence', () => {
    const text = buildCountryPublicAttentionNarrative({
      countryName: 'Colombia',
      signalCount: 717,
      hours: 24,
      topThemes: [
        { name: 'PUBLIC_SECTOR', count: 96 },
        { name: 'ENVIRONMENT', count: 84 },
      ],
      topSearches: [{ keyword: 'elections colombia', rank: 1 }],
      topWikiArticles: [{ title: 'Colombia', views: 12000 }],
    })

    expect(text).toContain('Colombia shows 717 signals')
    expect(text).toContain('Public Sector')
    expect(text).toContain('public attention is visible around elections colombia')
    expect(text).toContain('Colombia')
  })
})
