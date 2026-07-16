import { describe, it, expect } from 'vitest'
import { shouldTranslate } from './translatableText'

// #204(b): decision helper for free-text (thread label) translation.
// Contract: translate unless (a) the text is a raw thread-id / fallback label,
// (b) it's empty, or (c) it looks ASCII-English-ish AND the viewer is English.
describe('shouldTranslate', () => {
    it('never translates fallback thread-id labels', () => {
        expect(shouldTranslate('dynamic topic 123', 'es')).toBe(false)
        expect(shouldTranslate('dynamic-topic-123', 'es')).toBe(false)
        expect(shouldTranslate('Dynamic Topic 9', 'fr')).toBe(false)
        expect(shouldTranslate('cluster 42', 'es')).toBe(false)
        expect(shouldTranslate('cluster-42', 'en')).toBe(false)
    })

    it('skips empty / whitespace-only text', () => {
        expect(shouldTranslate('', 'es')).toBe(false)
        expect(shouldTranslate('   ', 'es')).toBe(false)
    })

    it('renders ASCII-English-ish text plain for English viewers', () => {
        expect(shouldTranslate('NATO Ankara Summit Tensions', 'en')).toBe(false)
        // Typographic punctuation does not make text "foreign".
        expect(shouldTranslate('Trump’s tariff threat — markets react…', 'en')).toBe(false)
    })

    it('translates ASCII text for non-English viewers', () => {
        expect(shouldTranslate('NATO Ankara Summit Tensions', 'es')).toBe(true)
        expect(shouldTranslate('Russia Ukraine ceasefire talks', 'pt')).toBe(true)
    })

    it('translates non-ASCII text even for English viewers', () => {
        expect(shouldTranslate('Crisis hídrica en Teherán', 'en')).toBe(true)
        expect(shouldTranslate('地震による被害拡大', 'en')).toBe(true)
    })

    it('normalizes BCP-47 viewer tags to the 2-letter base', () => {
        expect(shouldTranslate('NATO Ankara Summit Tensions', 'en-US')).toBe(false)
        expect(shouldTranslate('NATO Ankara Summit Tensions', 'es-419')).toBe(true)
    })

    it('does not translate when the viewer language is unknown', () => {
        expect(shouldTranslate('NATO Ankara Summit Tensions', '')).toBe(false)
    })
})
