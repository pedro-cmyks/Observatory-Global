import { describe, it, expect } from 'vitest'
import { shouldTranslate } from './TranslatableHeadline'

// vitest runs in the node env: navigator is undefined, so TARGET_LANG resolves
// to 'en' (see the module). These assertions are therefore from an EN viewer.
const GREEK = 'Νεκρός 17χρονος Βρετανός τουρίστας μετά από πτώση'
const ENGLISH = '17-Year-Old British Teen Fall in Greece'

describe('shouldTranslate (honest unknown-source handling)', () => {
  it('attempts translation for a GDELT-unknown (xx) NON-English receipt — the flagship Greek case', () => {
    expect(shouldTranslate('xx', GREEK)).toBe(true)
  })

  it('treats un/und/empty the same as xx', () => {
    expect(shouldTranslate('un', GREEK)).toBe(true)
    expect(shouldTranslate('und', GREEK)).toBe(true)
    expect(shouldTranslate('', GREEK)).toBe(true)
    expect(shouldTranslate(null, GREEK)).toBe(true)
    expect(shouldTranslate(undefined, GREEK)).toBe(true)
  })

  it('does NOT attempt for an unknown-source ASCII-English headline (no wasted call, no loop)', () => {
    expect(shouldTranslate('xx', ENGLISH)).toBe(false)
    expect(shouldTranslate(null, ENGLISH)).toBe(false)
  })

  it('ignores typographic punctuation when judging "clearly non-English"', () => {
    expect(shouldTranslate('xx', 'Markets slip — again… as “risk” fades')).toBe(false)
  })

  it('still translates a KNOWN non-English source for an English viewer', () => {
    expect(shouldTranslate('el', GREEK)).toBe(true)
    expect(shouldTranslate('es', 'Titular en español')).toBe(true)
  })

  it('renders a same-language (en) headline plain', () => {
    expect(shouldTranslate('en', ENGLISH)).toBe(false)
  })
})

describe('explicit "Translate all" relaxes the unknown-source ASCII guard (W3)', () => {
    // Measured on the 2026-08-13 Brief: a GDELT receipt filed source_lang='xx'
    // whose German headline happens to carry no umlaut
    // ("Sprengstoff-Drohne in Leipzig: Spur nach Russland?") is indistinguishable
    // from English by shape alone, so the ambient lane leaves it alone — correct,
    // it must not pay a DeepSeek call for every English headline on the page.
    // But when the reader CLICKS "Translate all", "all" has to mean all: the ask
    // is explicit, the answer is cached forever server-side, and a no-op comes
    // back as `same` and settles silently.
    const ASCII_GERMAN = 'Sprengstoff-Drohne in Leipzig: Spur nach Russland?'

    it('ambient: unknown-source ASCII stays plain (no wasted call)', () => {
        expect(shouldTranslate('xx', ASCII_GERMAN, 'en')).toBe(false)
    })

    it('explicit: unknown-source text is attempted whatever its script', () => {
        expect(shouldTranslate('xx', ASCII_GERMAN, 'en', { explicit: true })).toBe(true)
        expect(shouldTranslate(null, ASCII_GERMAN, 'en', { explicit: true })).toBe(true)
    })

    it('explicit never overrides a KNOWN same-language source — that is measured, not unknown', () => {
        expect(shouldTranslate('en', 'A plain English headline', 'en', { explicit: true })).toBe(false)
        expect(shouldTranslate('es', 'Un titular', 'es', { explicit: true })).toBe(false)
    })

    it('explicit still translates a known foreign source', () => {
        expect(shouldTranslate('de', ASCII_GERMAN, 'en', { explicit: true })).toBe(true)
    })

    it('explicit does not resurrect empty text', () => {
        expect(shouldTranslate('xx', '   ', 'en', { explicit: true })).toBe(false)
    })
})
