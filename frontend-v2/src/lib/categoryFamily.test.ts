import { describe, it, expect } from 'vitest'
import { famOf, familyColor, familyGradient, FAMILY_HEX } from './categoryFamily'

// Dataviz audit fix 1: category color = deterministic FAMILY keyword map,
// never a string hash. Colors must survive data changes and re-ranks.
describe('famOf — deterministic category-family map', () => {
    it('maps conflict labels to the conflict family', () => {
        expect(famOf('Armed conflict escalation')).toBe('conflict')
        expect(famOf('armed-conflict-escalation')).toBe('conflict')
        expect(famOf('War in Ukraine')).toBe('conflict')
        expect(famOf('Missile strikes on infrastructure')).toBe('conflict')
    })

    it('maps unknown / empty / null categories to other', () => {
        expect(famOf('Xylophone quarterly digest')).toBe('other')
        expect(famOf('')).toBe('other')
        expect(famOf(null)).toBe('other')
        expect(famOf(undefined)).toBe('other')
    })

    it('is case-insensitive', () => {
        expect(famOf('ARMED CONFLICT ESCALATION')).toBe('conflict')
        expect(famOf('politics & governance')).toBe(famOf('Politics & Governance'))
        expect(famOf('WORLD CUP 2026')).toBe('culture')
    })

    it('is stable: same input always yields the same family', () => {
        for (let i = 0; i < 3; i++) {
            expect(famOf('Disease outbreak')).toBe('health')
        }
    })

    it('classifies the live Atlas category set into the audited families', () => {
        // Sampled from prod /api/v2/universe + /threads (2026-07-15).
        expect(famOf('Politics & Governance')).toBe('governance')
        expect(famOf('Constitutional or institutional crisis')).toBe('governance')
        expect(famOf('Corruption investigation')).toBe('governance')
        expect(famOf('Student and youth protest')).toBe('governance')
        expect(famOf('Disease outbreak')).toBe('health')
        expect(famOf('Earthquake or volcanic disaster')).toBe('health')
        expect(famOf('Wildfire or severe-storm disaster')).toBe('health')
        expect(famOf('Currency & Fiscal Policy')).toBe('economy')
        expect(famOf('Oil and gas supply risk')).toBe('economy')
        expect(famOf('Crime and Accidents')).toBe('society')
        expect(famOf('forced-displacement')).toBe('society')
        expect(famOf('World Cup 2026')).toBe('culture')
        expect(famOf('Sports & Recruitment')).toBe('culture')
    })

    it('mixed labels resolve by FIXED family order (conflict > governance > …), never by hash', () => {
        // 'Political & Health Incidents' contains both governance and health
        // keywords; governance is checked first in the fixed order.
        expect(famOf('Political & Health Incidents')).toBe('governance')
    })
})

describe('familyColor / familyGradient — CSS-var consumption with validated fallbacks', () => {
    it('returns a var(--fam-<key>) expression with the CVD-validated hex fallback', () => {
        expect(familyColor('Armed conflict escalation')).toBe(`var(--fam-conflict, ${FAMILY_HEX.conflict})`)
        expect(familyColor('mystery category')).toBe(`var(--fam-other, ${FAMILY_HEX.other})`)
    })

    it('carries the audited palette', () => {
        expect(FAMILY_HEX.conflict).toBe('#cc5d47')
        expect(FAMILY_HEX.governance).toBe('#b58733')
        expect(FAMILY_HEX.health).toBe('#0f92b0')
        expect(FAMILY_HEX.economy).toBe('#5183cc')
        expect(FAMILY_HEX.society).toBe('#c8659a')
        expect(FAMILY_HEX.culture).toBe('#8a949c')
    })

    it('gradient embeds the family color expression', () => {
        expect(familyGradient('Oil and gas supply risk')).toContain('var(--fam-economy')
        expect(familyGradient('Oil and gas supply risk')).toMatch(/^linear-gradient/)
    })
})
