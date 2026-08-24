import { describe, it, expect } from 'vitest'
import { buildStoryShareCaption } from './storyShare'

const DEEP_LINK = 'https://atlas.example/app?theme=dynamic-topic-42'

describe('buildStoryShareCaption', () => {
  it('renders the full caption: label, windowed vitals, receipts, deep link', () => {
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
    expect(caption).toContain('Caspian Pipeline Standoff — measured, not editorialized.')
    expect(caption).toContain('1,234 signals (last 24 hours)')
    expect(caption).toContain('12 countries')
    expect(caption).toContain('36 sources (distinct outlets among sampled receipts)')
    expect(caption).toContain('Receipts (sampled coverage):')
    expect(caption).toContain('• “Pipeline halted after talks collapse” — Reuters (en)')
    expect(caption).toContain('• “Los mercados reaccionan al cierre” — El País (es)')
    expect(caption).toContain(`Open the measured story on Atlas → ${DEEP_LINK}`)
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

    // Nothing measured → no coverage line at all, label + link remain.
    const bare = buildStoryShareCaption({ label: 'Story', deepLink: DEEP_LINK })
    expect(bare).not.toContain('Measured coverage')
    expect(bare).toContain('Story — measured, not editorialized.')
    expect(bare).toContain(DEEP_LINK)
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
