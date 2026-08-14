import { afterEach, describe, expect, it } from 'vitest'
import { setPageLanguage } from './pageLanguage'
import {
    UI_COPY,
    formatCopy,
    resolveCopy,
    uiLang,
    type UiCopyKey,
} from './uiCopy'

afterEach(() => setPageLanguage(null))

const KEYS = Object.keys(UI_COPY) as UiCopyKey[]

describe('uiLang', () => {
    it('maps the page language onto the chrome languages we actually wrote', () => {
        expect(uiLang('es')).toBe('es')
        expect(uiLang('en')).toBe('en')
    })

    it('falls back to English for a language whose chrome we have NOT written', () => {
        // Honest by construction: a French reader gets English chrome, not a
        // machine-translated interface we never reviewed.
        expect(uiLang('fr')).toBe('en')
        expect(uiLang('ru')).toBe('en')
        expect(uiLang('')).toBe('en')
    })

    it('accepts a BCP-47 tag (the browser hands us es-CO, not es)', () => {
        expect(uiLang('es-CO')).toBe('es')
        expect(uiLang('es-419')).toBe('es')
        expect(uiLang('ES')).toBe('es')
    })
})

describe('resolveCopy', () => {
    it('returns the Spanish string when one exists', () => {
        expect(resolveCopy('brief.action.home', 'es')).toBe('← Inicio')
    })

    it('returns English for the English reader', () => {
        expect(resolveCopy('brief.action.home', 'en')).toBe('← Home')
    })

    it('falls back to English when a key has no Spanish yet — never blank, never the key name', () => {
        const partial = { 'x.only.en': { en: 'Coverage gaps' } } as const
        expect(resolveCopy('x.only.en' as UiCopyKey, 'es', partial)).toBe('Coverage gaps')
    })

    it('an unknown key resolves to the explicit English fallback rather than a blank', () => {
        expect(resolveCopy('nope.not.a.key' as UiCopyKey, 'es', {}, 'Signals')).toBe('Signals')
    })
})

describe('formatCopy', () => {
    it('substitutes named placeholders', () => {
        expect(formatCopy('{n} of {total}', { n: 3, total: 48 })).toBe('3 of 48')
    })

    it('leaves an unprovided placeholder intact rather than printing undefined', () => {
        expect(formatCopy('{n} of {total}', { n: 3 })).toBe('3 of {total}')
    })
})

// ---------------------------------------------------------------------------
// Catalogue invariants — the rules that keep a translated page honest. These
// run over EVERY key, so a future entry cannot quietly break them.
// ---------------------------------------------------------------------------

describe('UI_COPY catalogue', () => {
    it('has keys', () => {
        expect(KEYS.length).toBeGreaterThan(0)
    })

    it('every key carries a non-empty English string (the universal fallback)', () => {
        for (const k of KEYS) {
            expect(UI_COPY[k].en, k).toBeTruthy()
            expect(UI_COPY[k].en.trim(), k).not.toBe('')
        }
    })

    it('no value is a key name leaking through', () => {
        for (const k of KEYS) {
            expect(UI_COPY[k].en, k).not.toBe(k)
            if (UI_COPY[k].es !== undefined) expect(UI_COPY[k].es, k).not.toBe(k)
        }
    })

    it('a Spanish string, when present, is non-empty', () => {
        for (const k of KEYS) {
            const es = UI_COPY[k].es
            if (es !== undefined) expect(es.trim(), k).not.toBe('')
        }
    })

    it('Spanish and English carry the SAME placeholders — a translation may not drop or invent a value', () => {
        const placeholders = (s: string) => (s.match(/\{[a-zA-Z_]+\}/g) ?? []).slice().sort()
        for (const k of KEYS) {
            const es = UI_COPY[k].es
            if (es === undefined) continue
            expect(placeholders(es), k).toEqual(placeholders(UI_COPY[k].en))
        }
    })

    it('HONESTY: a Spanish label never states a number the English one did not', () => {
        // The failure this guards: "24 horas" appearing under a label whose
        // English said only "last window", i.e. the translation asserting a
        // measurement nobody measured.
        const digits = (s: string) => (s.match(/\d+/g) ?? []).slice().sort()
        for (const k of KEYS) {
            const es = UI_COPY[k].es
            if (es === undefined) continue
            expect(digits(es), k).toEqual(digits(UI_COPY[k].en))
        }
    })

    it('Spanish is not simply a copy of English (a placeholder pretending to be a translation)', () => {
        // Symbol-only strings (arrows, glyphs) legitimately match; text does not.
        // A true cognate ("Global") is expressed by OMITTING `es`, so that
        // "has a Spanish string" keeps meaning "was translated".
        for (const k of KEYS) {
            const { en, es } = UI_COPY[k]
            if (es === undefined) continue
            if (!/[a-zA-Z]{4,}/.test(en)) continue
            expect(es, k).not.toBe(en)
        }
    })
})
