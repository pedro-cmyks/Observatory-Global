import { describe, it, expect } from 'vitest'
import { isPublicAttentionRelevant } from './publicAttentionFilters'

describe('isPublicAttentionRelevant', () => {
    it('drops Wikipedia namespace / meta pages (any language)', () => {
        // The actual #1 global "attention" item observed 2026-06-30.
        expect(isPublicAttentionRelevant('Wikipédia:Accueil principal')).toBe(false)
        expect(isPublicAttentionRelevant('Special:Search')).toBe(false)
        expect(isPublicAttentionRelevant('Portal:Current events')).toBe(false)
        expect(isPublicAttentionRelevant('Main Page')).toBe(false)
        expect(isPublicAttentionRelevant('Hauptseite')).toBe(false)
    })

    it('drops disambiguated film / TV / album articles', () => {
        expect(isPublicAttentionRelevant('Supergirl (2026 film)')).toBe(false)
        expect(isPublicAttentionRelevant('Wicked (2024 film)')).toBe(false)
    })

    it('drops non-English sports tournaments and leagues', () => {
        expect(isPublicAttentionRelevant('Copa Mundial de Fútbol de 2026')).toBe(false)
        expect(isPublicAttentionRelevant('Coupe du monde de football')).toBe(false)
        expect(isPublicAttentionRelevant('Erling Haaland')).toBe(false)
    })

    it('keeps real narrative-relevant attention', () => {
        expect(isPublicAttentionRelevant('Iran nuclear program')).toBe(true)
        expect(isPublicAttentionRelevant("Côte d'Ivoire election")).toBe(true)
        expect(isPublicAttentionRelevant('Flood in Pakistan')).toBe(true)
        expect(isPublicAttentionRelevant('Sudan ceasefire talks')).toBe(true)
    })
})
