import { describe, it, expect } from 'vitest'
import { isKnownCountry } from './countryNames'

describe('isKnownCountry', () => {
    it('accepts real ISO country codes (case-insensitive)', () => {
        expect(isKnownCountry('US')).toBe(true)
        expect(isKnownCountry('PH')).toBe(true)
        expect(isKnownCountry('ci')).toBe(true) // lowercase
    })

    it('rejects placeholder / un-attributable codes (the "XX" anomaly)', () => {
        expect(isKnownCountry('XX')).toBe(false)
        expect(isKnownCountry('ZZ')).toBe(false)
        expect(isKnownCountry('')).toBe(false)
        expect(isKnownCountry(null)).toBe(false)
        expect(isKnownCountry(undefined)).toBe(false)
    })
})
