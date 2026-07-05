import { describe, expect, it } from 'vitest'
import {
  buildCountryBriefMarkdown,
  buildThemeBriefingMarkdown,
  buildThemeSignalsCsv,
} from './exportFormatters'

const generatedAt = new Date('2026-05-06T12:00:00Z')

describe('exportFormatters', () => {
  it('builds theme briefing markdown from the actual ThemeDetail response shape', () => {
    const md = buildThemeBriefingMarkdown({
      themeName: 'Armed Conflict',
      generatedAt,
      insight: 'Coverage is rising across several regions.',
      data: {
        total: 42,
        avgSentiment: -1.25,
        topSources: [{ name: 'reuters.com', count: 12, sentiment: -0.2, family: 'wire' }],
        countryBreakdown: [{ code: 'CO', count: 8, sentiment: -0.4 }],
        relatedThemes: [{ theme: 'PROTEST', count: 7 }],
        signals: [],
      },
    })

    expect(md).toContain('# Atlas Intelligence Briefing: Armed Conflict')
    expect(md).toContain('- **Total Signals:** 42')
    expect(md).toContain('- reuters.com: 12 signals (wire)')
    expect(md).toContain('- CO: 8 signals')
    // #204 taxonomy label rename: PROTEST -> "Protests & Unrest"
    expect(md).toContain('- Protests & Unrest: 7 co-occurrences')
  })

  it('escapes theme signal CSV fields with commas and quotes', () => {
    const csv = buildThemeSignalsCsv([
      {
        timestamp: '2026-05-06T12:00:00Z',
        source: 'example.com',
        title: 'Quoted "headline", with comma',
        sentiment: -0.5,
        url: 'https://example.com/a,b',
      },
    ])

    expect(csv).toContain('"Quoted ""headline"", with comma"')
    expect(csv).toContain('"https://example.com/a,b"')
  })

  it('builds country brief markdown with themes, sources, people, and recent signals', () => {
    const md = buildCountryBriefMarkdown({
      countryName: 'Colombia',
      generatedAt,
      data: {
        country_code: 'CO',
        hours: 24,
        signal_count: 100,
        avg_sentiment: -0.15,
        sentiment_trend: 'stable',
        top_themes: [{ name: 'ARMEDCONFLICT', count: 21 }],
        top_sources: [{ name: 'elpais.com.co', count: 9 }],
        keyPersons: [{ name: 'gustavo petro', count: 5 }],
        top_stories: [{ source: 'elpais.com.co', url: 'https://example.com', timestamp: '2026-05-06T10:00:00Z', sentiment: -1, themeCode: 'ARMEDCONFLICT' }],
      },
    })

    expect(md).toContain('# Atlas Country Brief: Colombia')
    expect(md).toContain('- **Signals:** 100')
    expect(md).toContain('- Armed Conflict: 21 signals')
    expect(md).toContain('- elpais.com.co: 9 signals')
    expect(md).toContain('- gustavo petro: 5 mentions')
    expect(md).toContain('- elpais.com.co — Armed Conflict — https://example.com')
  })

})
