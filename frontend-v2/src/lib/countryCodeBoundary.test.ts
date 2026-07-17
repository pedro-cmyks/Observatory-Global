import { describe, it, expect } from 'vitest'
import { resolveInboundIso, LEGACY_GDELT_TO_ISO } from './countryCodeBoundary'

// The map polygons key ISO_A2 (Natural Earth). Atlas' app-wide country code
// system is ISO (backend FIPS_TO_ISO normalizes at ingest; countryNames,
// CountryBrief, day-evidence all key ISO). These tests freeze the ISO-FIRST
// rule that killed the "click China → Switzerland opens" collision.
const isoSet = new Set([
    'CN', 'CH', 'BN', 'BJ', 'ID', 'RS', 'XK', 'KR', 'KP', 'PS', 'GB', 'IE',
    'CD', 'CG', 'CF', 'KN', 'NI', 'AU', 'AT',
])
const hasIso = (c: string) => isoSet.has(c)

describe('resolveInboundIso — ISO wins over FIPS on collision codes', () => {
    it('CN is China, never converted', () => {
        expect(resolveInboundIso('CN', hasIso)).toBe('CN')
    })
    it('CH is Switzerland (ISO), NOT China (FIPS) — the acceptance repro', () => {
        expect(resolveInboundIso('CH', hasIso)).toBe('CH')
    })
    it('BN is Brunei (ISO), NOT Benin (FIPS) — same collision class', () => {
        expect(resolveInboundIso('BN', hasIso)).toBe('BN')
    })
    it('CD/CG/CF (the Congo triangle) stay ISO', () => {
        expect(resolveInboundIso('CD', hasIso)).toBe('CD')
        expect(resolveInboundIso('CG', hasIso)).toBe('CG')
        expect(resolveInboundIso('CF', hasIso)).toBe('CF')
    })
    it('KN is Saint Kitts (ISO), NOT North Korea (FIPS)', () => {
        expect(resolveInboundIso('KN', hasIso)).toBe('KN')
    })
    it('NI is Nicaragua (ISO), NOT Nigeria (FIPS); AU is Australia, not Austria', () => {
        expect(resolveInboundIso('NI', hasIso)).toBe('NI')
        expect(resolveInboundIso('AU', hasIso)).toBe('AU')
    })
})

describe('resolveInboundIso — legacy GDELT codes with NO ISO meaning still resolve', () => {
    it('GZ (Gaza, no ISO polygon) → PS', () => {
        expect(resolveInboundIso('GZ', hasIso)).toBe('PS')
    })
    it('KS → KR, RB → RS, RI → ID, KV → XK, EI → IE, UK → GB', () => {
        expect(resolveInboundIso('KS', hasIso)).toBe('KR')
        expect(resolveInboundIso('RB', hasIso)).toBe('RS')
        expect(resolveInboundIso('RI', hasIso)).toBe('ID')
        expect(resolveInboundIso('KV', hasIso)).toBe('XK')
        expect(resolveInboundIso('EI', hasIso)).toBe('IE')
        expect(resolveInboundIso('UK', hasIso)).toBe('GB')
    })
    it('unknown codes pass through unchanged', () => {
        expect(resolveInboundIso('ZZ', hasIso)).toBe('ZZ')
    })
    it('null/empty pass through as null', () => {
        expect(resolveInboundIso(null, hasIso)).toBeNull()
        expect(resolveInboundIso('', hasIso)).toBeNull()
    })
})

describe('LEGACY_GDELT_TO_ISO map hygiene', () => {
    it('never contains a key that is itself an assigned ISO 3166-1 alpha-2 code', () => {
        // These are the collision codes that caused the China→Switzerland bug.
        // A legacy alias must only exist for codes with NO ISO meaning.
        const assignedIso = ['CH', 'CG', 'CF', 'KN', 'BN', 'NI', 'AU', 'CN', 'ID', 'RS']
        for (const iso of assignedIso) {
            expect(LEGACY_GDELT_TO_ISO[iso]).toBeUndefined()
        }
    })
})
