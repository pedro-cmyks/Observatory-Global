import { afterEach, describe, expect, it } from 'vitest'
import {
    PAGE_LANGUAGE_OPTIONS,
    browserLanguage,
    getPageLanguage,
    getStoredPageLanguage,
    normalizeLang,
    setPageLanguage,
} from './pageLanguage'

// vitest runs in the node env: navigator/localStorage/window are undefined, so
// the browser fallback resolves to 'en' and persistence rides the in-memory
// session fallback (the same path a privacy-mode browser takes).

afterEach(() => setPageLanguage(null))

describe('normalizeLang', () => {
    it('reduces BCP-47 tags to the ISO 639-1 base', () => {
        expect(normalizeLang('es-CO')).toBe('es')
        expect(normalizeLang('pt-BR')).toBe('pt')
        expect(normalizeLang('zh-Hans')).toBe('zh')
        expect(normalizeLang('EN')).toBe('en')
    })

    it('rejects unusable values', () => {
        expect(normalizeLang('')).toBe(null)
        expect(normalizeLang(null)).toBe(null)
        expect(normalizeLang(undefined)).toBe(null)
        expect(normalizeLang('7!')).toBe(null)
    })
})

describe('page language store', () => {
    it('defaults to the browser language (en in node) with nothing stored', () => {
        expect(getStoredPageLanguage()).toBe(null)
        expect(browserLanguage()).toBe('en')
        expect(getPageLanguage()).toBe('en')
    })

    it('set → get round-trips and wins over the browser default', () => {
        setPageLanguage('es')
        expect(getStoredPageLanguage()).toBe('es')
        expect(getPageLanguage()).toBe('es')
    })

    it('normalizes on write', () => {
        setPageLanguage('PT-br')
        expect(getPageLanguage()).toBe('pt')
    })

    it('null clears back to auto (browser)', () => {
        setPageLanguage('ru')
        setPageLanguage(null)
        expect(getStoredPageLanguage()).toBe(null)
        expect(getPageLanguage()).toBe('en')
    })

    it('an invalid write clears rather than storing garbage', () => {
        setPageLanguage('es')
        setPageLanguage('!!')
        expect(getStoredPageLanguage()).toBe(null)
    })
})

describe('PAGE_LANGUAGE_OPTIONS', () => {
    it('every option code is a normalized ISO 639-1 base (endpoint contract: exactly 2 chars)', () => {
        for (const o of PAGE_LANGUAGE_OPTIONS) {
            expect(normalizeLang(o.code)).toBe(o.code)
        }
    })

    it('includes the minimum set (es, en)', () => {
        const codes = PAGE_LANGUAGE_OPTIONS.map(o => o.code)
        expect(codes).toContain('en')
        expect(codes).toContain('es')
    })
})
