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
