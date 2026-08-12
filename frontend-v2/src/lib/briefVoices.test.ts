import { describe, expect, it } from 'vitest'

import { weaveVoices, type VoiceReceipt } from './briefVoices'

const receipt = (over: Partial<VoiceReceipt> = {}): VoiceReceipt => ({
  source: 'example.com',
  source_lang: 'en',
  source_origin_country: 'US',
  ...over,
})

describe('weaveVoices — the voice bar as prose', () => {
  it('returns null when the payload carries nothing to count', () => {
    expect(weaveVoices({})).toBeNull()
    expect(weaveVoices({ receipts: [], outlets: null })).toBeNull()
  })

  it('merges the measured outlet count and the receipt languages into one clause', () => {
    const woven = weaveVoices({
      outlets: 48,
      receipts: [
        receipt({ source_lang: 'en' }),
        receipt({ source_lang: 'ar' }),
        receipt({ source_lang: 'fr' }),
      ],
    })
    expect(woven?.clauses[0]).toEqual({
      kind: 'coverage',
      text: '48 outlets are carrying this, in at least 3 languages',
    })
  })

  it('never invents a count: no outlet total means no outlet clause', () => {
    const woven = weaveVoices({
      receipts: [receipt({ source_lang: 'en' }), receipt({ source_lang: 'es' })],
    })
    expect(woven?.clauses[0].text).toBe('The receipts carried here span at least 2 languages')
  })

  it('drops the language clause when only one language (or none) is named', () => {
    const woven = weaveVoices({
      outlets: 12,
      receipts: [receipt({ source_lang: 'en' }), receipt({ source_lang: 'EN' })],
    })
    expect(woven?.clauses[0].text).toBe('12 outlets are carrying this')
  })

  it('treats the xx placeholder as an unknown language, never as a language', () => {
    const woven = weaveVoices({
      outlets: 9,
      receipts: [
        receipt({ source_lang: 'xx' }),
        receipt({ source_lang: 'xx' }),
        receipt({ source_lang: null }),
      ],
    })
    expect(woven?.clauses[0].text).toBe('9 outlets are carrying this')
  })

  it('states the subject country own-press count over the KNOWN-origin receipts', () => {
    const woven = weaveVoices({
      outlets: 48,
      subjectCountries: ['SY'],
      subjectCountryNames: ['Syria'],
      receipts: [
        receipt({ source_origin_country: 'SY' }),
        receipt({ source_origin_country: 'SY' }),
        receipt({ source_origin_country: 'US' }),
        receipt({ source_origin_country: null }),
      ],
    })
    const own = woven?.clauses.find(c => c.kind === 'ownVoice')
    expect(own?.text).toBe("Syria's own press: 2 of the 3 receipts whose outlet home country is known")
  })

  it('says zero own-press plainly (the East-Timor-class finding)', () => {
    const woven = weaveVoices({
      subjectCountries: ['TL'],
      subjectCountryNames: ['Timor-Leste'],
      receipts: [
        receipt({ source_origin_country: 'AU' }),
        receipt({ source_origin_country: 'AU' }),
      ],
    })
    const own = woven?.clauses.find(c => c.kind === 'ownVoice')
    expect(own?.text).toBe(
      "none of the 2 receipts whose outlet home country is known come from Timor-Leste's own press",
    )
  })

  it('gives a name already ending in s the bare apostrophe', () => {
    const woven = weaveVoices({
      subjectCountries: ['US'],
      subjectCountryNames: ['United States'],
      receipts: [receipt({ source_origin_country: 'US' }), receipt({ source_origin_country: 'DE' })],
    })
    expect(woven?.clauses.find(c => c.kind === 'ownVoice')?.text).toBe(
      "United States' own press: 1 of the 2 receipts whose outlet home country is known",
    )
  })

  it('names both subject countries when the story is about more than one', () => {
    const woven = weaveVoices({
      subjectCountries: ['IR', 'US'],
      subjectCountryNames: ['Iran', 'United States'],
      receipts: [receipt({ source_origin_country: 'DE' }), receipt({ source_origin_country: 'IR' })],
    })
    expect(woven?.clauses.find(c => c.kind === 'ownVoice')?.text).toBe(
      'the press of Iran and United States: 1 of the 2 receipts whose outlet home country is known',
    )
  })

  it('omits the own-voice clause when no receipt names an outlet home country', () => {
    const woven = weaveVoices({
      outlets: 4,
      subjectCountries: ['SY'],
      subjectCountryNames: ['Syria'],
      receipts: [receipt({ source_origin_country: null }), receipt({ source_origin_country: '' })],
    })
    expect(woven?.clauses.some(c => c.kind === 'ownVoice')).toBe(false)
  })

  it('omits the own-voice clause when the subject country is not served', () => {
    const woven = weaveVoices({
      outlets: 4,
      receipts: [receipt({ source_origin_country: 'US' })],
    })
    expect(woven?.clauses.some(c => c.kind === 'ownVoice')).toBe(false)
  })

  it('counts state-controlled outlets only when the authoritative flag is true', () => {
    const woven = weaveVoices({
      outlets: 6,
      receipts: [
        receipt({ is_state_media: true }),
        receipt({ is_state_media: true }),
        receipt({ is_state_media: null }),
      ],
    })
    expect(woven?.clauses.find(c => c.kind === 'stateMedia')?.text).toBe(
      '2 of the receipts are state-controlled outlets',
    )
    const none = weaveVoices({ outlets: 6, receipts: [receipt({ is_state_media: null })] })
    expect(none?.clauses.some(c => c.kind === 'stateMedia')).toBe(false)
  })

  it('carries the cross-read tension with its attribution intact', () => {
    const woven = weaveVoices({
      outlets: 5,
      receipts: [receipt()],
      tension: {
        note: 'casualty figures differ',
        a: { outlet: 'cyprus-mail.com' },
        b: { outlet: 'xinhuanet.com' },
      },
    })
    expect(woven?.clauses.find(c => c.kind === 'disputed')?.text).toBe(
      'in dispute: casualty figures differ (cyprus-mail.com vs xinhuanet.com)',
    )
  })

  it('keeps a tension without outlet names rather than dropping the dispute', () => {
    const woven = weaveVoices({
      outlets: 5,
      receipts: [receipt()],
      tension: { note: 'the two accounts disagree on the date' },
    })
    expect(woven?.clauses.find(c => c.kind === 'disputed')?.text).toBe(
      'in dispute: the two accounts disagree on the date',
    )
  })

  it('ignores a tension with no note at all', () => {
    const woven = weaveVoices({ outlets: 5, receipts: [receipt()], tension: { note: '  ' } })
    expect(woven?.clauses.some(c => c.kind === 'disputed')).toBe(false)
  })

  it('joins the clauses into one sentence and states its basis', () => {
    const woven = weaveVoices({
      outlets: 48,
      subjectCountries: ['SY'],
      subjectCountryNames: ['Syria'],
      receipts: [
        receipt({ source_lang: 'ar', source_origin_country: 'SY' }),
        receipt({ source_lang: 'en', source_origin_country: 'US' }),
        receipt({ source_lang: 'fr', source_origin_country: 'FR', is_state_media: true }),
      ],
    })
    expect(woven?.sentence).toBe(
      '48 outlets are carrying this, in at least 3 languages; '
      + "Syria's own press: 1 of the 3 receipts whose outlet home country is known; "
      + '1 of the receipts is a state-controlled outlet.',
    )
    expect(woven?.basis).toBe(
      'Voices counted from the 3 receipts carried with this story; the outlet total is the '
      + "story's own measured source count.",
    )
  })

  it('states a receipt-only basis when there is no measured outlet total', () => {
    const woven = weaveVoices({
      receipts: [receipt({ source_lang: 'en' }), receipt({ source_lang: 'de' })],
    })
    expect(woven?.basis).toBe('Voices counted from the 2 receipts carried with this story.')
  })
})
