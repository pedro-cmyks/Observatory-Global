import { describe, it, expect } from 'vitest'
import { buildStoryShareCaption, buildStoryFirstComment, computeShareFinding } from './storyShare'

const DEEP_LINK = 'https://atlas.example/app?theme=dynamic-topic-42'

describe('buildStoryShareCaption', () => {
  it('renders the full caption: label, windowed vitals, receipts — and NO link', () => {
    const caption = buildStoryShareCaption({
      label: 'Caspian Pipeline Standoff',
      signals: 1234,
      signalsWindow: 'last 24 hours',
      countries: 12,
      sources: 36,
      sourcesBasis: 'receipt_sample',
      receipts: [
        { headline: 'Pipeline halted after talks collapse', outlet: 'Reuters', lang: 'en' },
        { headline: 'Los mercados reaccionan al cierre', outlet: 'El País', lang: 'es' },
      ],
      deepLink: DEEP_LINK,
    })
    expect(caption).toContain('Caspian Pipeline Standoff — measurement, not opinion.')
    expect(caption).toContain('1,234 signals (last 24 hours)')
    expect(caption).toContain('12 countries')
    expect(caption).toContain('36 sources (distinct outlets in the sampled receipts)')
    expect(caption).toContain('Receipts — sampled coverage:')
    expect(caption).toContain('• “Pipeline halted after talks collapse” — Reuters (en)')
    expect(caption).toContain('• “Los mercados reaccionan al cierre” — El País (es)')
    // LinkedIn split: the caption never carries the link — it goes in the
    // first comment (the algorithm penalizes links in the post body).
    expect(caption).not.toContain(DEEP_LINK)
    expect(caption).not.toContain('Open the measured story')
    // Neither outlet is state media — the marker must not appear.
    expect(caption).not.toContain('STATE MEDIA')
  })

  it('absent fields produce absent lines — nothing invented', () => {
    // Countries/sources not served → those segments gone; signals stays.
    const partial = buildStoryShareCaption({
      label: 'Story',
      signals: 50,
      signalsWindow: 'last 24 hours',
      deepLink: DEEP_LINK,
    })
    expect(partial).toContain('Measured coverage: 50 signals (last 24 hours).')
    expect(partial).not.toContain('countries')
    expect(partial).not.toContain('sources')

    // A count with no declared window never prints (N19: no assumed windows).
    const unwindowed = buildStoryShareCaption({
      label: 'Story',
      signals: 50,
      countries: 3,
      deepLink: DEEP_LINK,
    })
    expect(unwindowed).not.toContain('signals')
    expect(unwindowed).toContain('Measured coverage: 3 countries.')

    // Nothing measured → no coverage line at all, the label remains.
    const bare = buildStoryShareCaption({ label: 'Story', deepLink: DEEP_LINK })
    expect(bare).not.toContain('Measured coverage')
    expect(bare).toContain('Story — measurement, not opinion.')
    expect(bare).not.toContain(DEEP_LINK)
  })

  it('marks a state-media receipt STATE MEDIA via the shared classifier', () => {
    const caption = buildStoryShareCaption({
      label: 'Story',
      receipts: [
        { headline: 'Official statement issued', outlet: 'rt.com', lang: 'ru' },
        { headline: 'Independent account differs', outlet: 'The Guardian' },
      ],
      deepLink: DEEP_LINK,
    })
    expect(caption).toContain('• “Official statement issued” — rt.com (ru) — STATE MEDIA')
    expect(caption).toContain('• “Independent account differs” — The Guardian')
    expect(caption).not.toContain('The Guardian — STATE MEDIA')
  })

  it('v2: a quote-gated lede replaces the tagline and renames the receipts header', () => {
    const caption = buildStoryShareCaption({
      label: 'Colombia Earthquake',
      lede: 'A 7.4 quake killed 25 in Colombia. Rescue teams reached the zone, according to RT.',
      receipts: [{ headline: 'Terremoto de 7.4 sacude Colombia', outlet: 'El Tiempo', lang: 'es' }],
      deepLink: DEEP_LINK,
    })
    // label opens alone; the v1 tagline would be false over an editorial lede
    expect(caption.startsWith('Colombia Earthquake\n\n')).toBe(true)
    expect(caption).not.toContain('measurement, not opinion')
    expect(caption).toContain('A 7.4 quake killed 25 in Colombia.')
    expect(caption).toContain('Receipts — the lede above is synthesized only from these, quote-checked:')
    // the LinkedIn split holds with a lede too — still no link in the body
    expect(caption).not.toContain(DEEP_LINK)
    // absent/blank lede → v1 template untouched
    const noLede = buildStoryShareCaption({ label: 'Story', lede: '  ', deepLink: DEEP_LINK })
    expect(noLede).toContain('Story — measurement, not opinion.')
  })

  it('v2: the measured finding prints with its Measured: prefix, absent when null', () => {
    const caption = buildStoryShareCaption({
      label: 'Story',
      finding: 'The sampled receipts span 5 languages.',
      deepLink: DEEP_LINK,
    })
    expect(caption).toContain('Measured: The sampled receipts span 5 languages.')
    expect(buildStoryShareCaption({ label: 'Story', deepLink: DEEP_LINK })).not.toContain('Measured:')
  })

  it('v2: a translated receipt shows the translation and says what it came from', () => {
    const caption = buildStoryShareCaption({
      label: 'Story',
      receipts: [{
        headline: 'Los mercados reaccionan al cierre',
        translated: 'Markets react to the shutdown',
        translatedFrom: 'es',
        outlet: 'El País',
        lang: 'es',
      }],
      deepLink: DEEP_LINK,
    })
    expect(caption).toContain('• “Markets react to the shutdown” — El País (translated from es)')
    expect(caption).not.toContain('Los mercados')

    // Unknown source lang ('xx'/absent): the mark never invents a language.
    const unknownFrom = buildStoryShareCaption({
      label: 'Story',
      receipts: [{ headline: 'Оригинал', translated: 'The original', outlet: 'iz.ru' }],
      deepLink: DEEP_LINK,
    })
    expect(unknownFrom).toContain('• “The original” — iz.ru (translated)')
  })

  it('omits the receipts section without receipts, caps at 3, drops headline-less rows', () => {
    const none = buildStoryShareCaption({ label: 'Story', deepLink: DEEP_LINK, receipts: [] })
    expect(none).not.toContain('Receipts')

    const capped = buildStoryShareCaption({
      label: 'Story',
      receipts: [
        { headline: 'One' },
        { headline: '' , outlet: 'Ghost Outlet' },
        { headline: 'Two' },
        { headline: 'Three' },
        { headline: 'Four' },
      ],
      deepLink: DEEP_LINK,
    })
    expect(capped).toContain('• “One”')
    expect(capped).toContain('• “Three”')
    expect(capped).not.toContain('• “Four”')
    expect(capped).not.toContain('Ghost Outlet')
    // A receipt with no outlet is just the quoted headline.
    expect(capped).toContain('• “One”\n')
  })
})

describe('buildStoryFirstComment', () => {
  it('carries the deep link — the one place the link appears', () => {
    const comment = buildStoryFirstComment(DEEP_LINK)
    expect(comment).toBe(`Read the full measured story on Atlas (free): ${DEEP_LINK}`)
    expect(comment).toContain(DEEP_LINK)
  })
})

describe('computeShareFinding', () => {
  it('reports language spread at 3+ distinct langs, never below', () => {
    const three = computeShareFinding({
      receipts: [{ lang: 'es' }, { lang: 'ru' }, { lang: 'EN ' }, { lang: 'es' }],
    })
    expect(three).toBe('The sampled receipts span 3 languages.')
    expect(computeShareFinding({ receipts: [{ lang: 'es' }, { lang: 'en' }] })).toBeNull()
  })

  it('counts state-media receipts via the shared classifier', () => {
    const out = computeShareFinding({
      receipts: [
        { outlet: 'rt.com', lang: 'ru' },
        { outlet: 'The Guardian', lang: 'en' },
        { outlet: 'El País', lang: 'en' },
      ],
    })
    expect(out).toBe('1 of 3 sampled receipts are from state-media outlets.')
  })

  it('combines at most two clauses, languages first', () => {
    const out = computeShareFinding({
      receipts: [
        { outlet: 'rt.com', lang: 'ru' },
        { outlet: 'a', lang: 'es' },
        { outlet: 'b', lang: 'en' },
        { outlet: 'c', lang: 'fa' },
      ],
    })
    expect(out).toBe(
      'The sampled receipts span 4 languages; 1 of 4 sampled receipts are from state-media outlets.',
    )
  })

  it('tone split needs 2 countries at the count floor and a real gap', () => {
    const split = computeShareFinding({
      receipts: [],
      countries: [
        { code: 'US', count: 10, sentiment: -0.62 },
        { code: 'CO', count: 5, sentiment: 0.11 },
        { code: 'FR', count: 1, sentiment: 3.0 }, // below floor — never anchors
      ],
    })
    expect(split).toContain('Coverage tone splits by country')
    expect(split).toContain('-0.62')
    expect(split).toContain('(avg tone, full window)')
    expect(split).not.toContain('3.00')
    // gap under the floor → no claim
    expect(computeShareFinding({
      receipts: [],
      countries: [
        { code: 'US', count: 10, sentiment: 0.1 },
        { code: 'CO', count: 5, sentiment: 0.2 },
      ],
    })).toBeNull()
  })

  it('nothing clears a floor → null, never a manufactured hook', () => {
    expect(computeShareFinding({ receipts: [{ outlet: 'The Guardian', lang: 'en' }] })).toBeNull()
    expect(computeShareFinding({ receipts: [] })).toBeNull()
  })
})
