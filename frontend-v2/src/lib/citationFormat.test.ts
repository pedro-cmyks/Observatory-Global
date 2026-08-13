import { describe, it, expect } from 'vitest'
import { citationLanguageLabel, citationDay, formatCitation, formatSourceList } from './citationFormat'

describe('citationLanguageLabel', () => {
  it('names a known ISO 639-1 code', () => {
    expect(citationLanguageLabel('ro')).toBe('Romanian')
    expect(citationLanguageLabel('es')).toBe('Spanish')
    expect(citationLanguageLabel('uk')).toBe('Ukrainian')
  })

  it('reduces a BCP-47 tag to its base language', () => {
    expect(citationLanguageLabel('pt-BR')).toBe('Portuguese')
    expect(citationLanguageLabel('zh-Hans')).toBe('Chinese')
  })

  it('falls back to the uppercased code rather than guessing a name', () => {
    expect(citationLanguageLabel('mk')).toBe('MK')
  })

  it('is null for absent or unknown-language markers — never "Unknown"', () => {
    expect(citationLanguageLabel(null)).toBeNull()
    expect(citationLanguageLabel(undefined)).toBeNull()
    expect(citationLanguageLabel('')).toBeNull()
    expect(citationLanguageLabel('xx')).toBeNull()
    expect(citationLanguageLabel('und')).toBeNull()
  })
})

describe('citationDay', () => {
  it('keeps an ISO day', () => {
    expect(citationDay('2026-08-13')).toBe('2026-08-13')
  })

  it('trims a timestamp to its day', () => {
    expect(citationDay('2026-08-13T04:15:00Z')).toBe('2026-08-13')
  })

  it('is null when there is no date — a citation never invents one', () => {
    expect(citationDay(null)).toBeNull()
    expect(citationDay('')).toBeNull()
    expect(citationDay('not a date')).toBeNull()
  })
})

describe('formatCitation', () => {
  it('emits outlet — “headline” (language), date. url', () => {
    expect(formatCitation({
      headline: 'Cutremur de 7,4 grade în Columbia',
      source: 'digi24.ro',
      url: 'https://digi24.ro/x',
      sourceLang: 'ro',
      publishedDate: '2026-08-13T06:00:00Z',
    })).toBe('digi24.ro — “Cutremur de 7,4 grade în Columbia” (Romanian), 2026-08-13. https://digi24.ro/x')
  })

  it('omits every field it does not have instead of filling a placeholder', () => {
    expect(formatCitation({ headline: 'A headline' })).toBe('“A headline”')
    expect(formatCitation({ headline: 'A headline', source: 'bbc.com' }))
      .toBe('bbc.com — “A headline”')
    expect(formatCitation({ headline: 'A headline', publishedDate: '2026-08-13' }))
      .toBe('“A headline”, 2026-08-13')
    expect(formatCitation({ headline: 'A headline', url: 'https://x.test/a' }))
      .toBe('“A headline”. https://x.test/a')
  })

  it('decodes HTML entities — a citation carrying &#8217; is not citable (council C6)', () => {
    expect(formatCitation({ headline: 'Ukraine&#8217;s drone strike', source: 'kyivpost.com' }))
      .toBe('kyivpost.com — “Ukraine’s drone strike”')
  })

  it('collapses newlines and runaway whitespace into one pasteable line', () => {
    expect(formatCitation({ headline: '  Two\n\nlines   here  ', source: 'x.com' }))
      .toBe('x.com — “Two lines here”')
  })

  it('cites an outlet + date + url even when the headline is missing', () => {
    expect(formatCitation({ headline: '', source: 'ria.ru', url: 'https://ria.ru/a', publishedDate: '2026-08-12' }))
      .toBe('ria.ru, 2026-08-12. https://ria.ru/a')
  })

  it('is empty when the receipt carries nothing citable', () => {
    expect(formatCitation({ headline: '   ' })).toBe('')
  })
})

describe('formatSourceList', () => {
  const rows = [
    { headline: 'One', source: 'a.com', url: 'https://a.com/1', publishedDate: '2026-08-13' },
    { headline: 'Two', source: 'b.com', url: 'https://b.com/2', sourceLang: 'uk' },
  ]

  it('numbers the visible receipts under a titled header', () => {
    expect(formatSourceList(rows, { title: 'Ukraine' })).toBe(
      'Sources — Ukraine · 2 receipts\n\n' +
      '1. a.com — “One”, 2026-08-13. https://a.com/1\n' +
      '2. b.com — “Two” (Ukrainian). https://b.com/2',
    )
  })

  it('names the retrieval day when the caller supplies one', () => {
    const out = formatSourceList(rows, { title: 'Ukraine', retrievedAt: '2026-08-13' })
    expect(out.split('\n')[0]).toBe('Sources — Ukraine · 2 receipts · retrieved 2026-08-13')
  })

  it('drops the title segment rather than inventing one', () => {
    expect(formatSourceList(rows).split('\n')[0]).toBe('Sources · 2 receipts')
  })

  it('singularizes one receipt', () => {
    expect(formatSourceList([rows[0]]).split('\n')[0]).toBe('Sources · 1 receipt')
  })

  it('dedupes by url so one story syndicated twice is cited once', () => {
    const dup = [...rows, { headline: 'One (repost)', source: 'a.com', url: 'https://a.com/1' }]
    const out = formatSourceList(dup, { title: 'Ukraine' })
    expect(out.split('\n')[0]).toBe('Sources — Ukraine · 2 receipts')
    expect(out).not.toContain('repost')
  })

  it('dedupes url-less rows on outlet + headline', () => {
    const dup = [{ headline: 'One', source: 'a.com' }, { headline: 'One', source: 'a.com' }]
    expect(formatSourceList(dup).split('\n')[0]).toBe('Sources · 1 receipt')
  })

  it('is empty for no citable rows — the caller renders no button', () => {
    expect(formatSourceList([])).toBe('')
    expect(formatSourceList([{ headline: '  ' }])).toBe('')
  })
})
