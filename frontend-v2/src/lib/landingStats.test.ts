import { describe, it, expect } from 'vitest'
import { formatSignalCount, formatCountriesCovering, resolveLiveStat } from './landingStats'

// Council P1-12: landing template failures — literal "$ countries covering",
// triplicated "5 countries covering" (a capped top-5 list read as a count),
// and the SIGNALS em-dash on fresh load with no honest state label.

describe('formatSignalCount', () => {
    it('abbreviates millions with one decimal', () => {
        expect(formatSignalCount(1_234_567)).toBe('1.2M')
    })
    it('abbreviates thousands with floor', () => {
        expect(formatSignalCount(45_678)).toBe('45k')
    })
    it('passes small numbers through', () => {
        expect(formatSignalCount(812)).toBe('812')
    })
})

describe('formatCountriesCovering', () => {
    it('uses the served country_count when it is a real number above the cap', () => {
        expect(formatCountriesCovering(7, 5)).toEqual({ value: '7', noun: 'countries', approx: false })
    })

    it('treats a served count AT the top-list cap as a floor (measured: the API derives country_count from the capped top-5 list — every busy thread "counts" exactly 5)', () => {
        expect(formatCountriesCovering(5, 5)).toEqual({ value: '5+', noun: 'countries', approx: true })
    })

    it('a served count below the cap with a matching list is exact (the list was complete)', () => {
        expect(formatCountriesCovering(3, 3)).toEqual({ value: '3', noun: 'countries', approx: false })
    })

    it('singularizes a count of one', () => {
        expect(formatCountriesCovering(1, 1)).toEqual({ value: '1', noun: 'country', approx: false })
    })

    it('falls back to the capped top-countries list length as a FLOOR, marked approximate', () => {
        // the "5 countries covering ×3" reproduction: top_countries is a top-5
        // list, so its length is a lower bound, never an exact count.
        expect(formatCountriesCovering(undefined, 5)).toEqual({ value: '5+', noun: 'countries', approx: true })
    })

    it('rejects non-numeric garbage instead of interpolating it into the template', () => {
        // the literal "$ countries covering" class: a non-number must never render
        expect(formatCountriesCovering('$' as unknown as number, 0)).toBeNull()
        expect(formatCountriesCovering(Number.NaN, 0)).toBeNull()
    })

    it('omits the line entirely when nothing is known', () => {
        expect(formatCountriesCovering(undefined, 0)).toBeNull()
        expect(formatCountriesCovering(0, 0)).toBeNull()
    })
})

describe('resolveLiveStat', () => {
    it('serves the live value when present', () => {
        expect(resolveLiveStat('1.2M', false)).toEqual({ display: '1.2M', state: 'live', note: null })
    })

    it('labels the fresh-load em-dash as loading, not silence', () => {
        expect(resolveLiveStat(null, false)).toEqual({ display: '—', state: 'loading', note: 'loading live count…' })
    })

    it('labels a failed fetch as unavailable, honestly', () => {
        expect(resolveLiveStat(null, true)).toEqual({ display: '—', state: 'unavailable', note: 'live count unavailable' })
    })
})
