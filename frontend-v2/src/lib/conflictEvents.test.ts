import { describe, it, expect } from 'vitest'
import { conflictMatchesCountry, conflictsForCountry, conflictCountryCode } from './conflictEvents'

const ev = (country: string) => ({ location: { country } })

describe('conflictMatchesCountry', () => {
    it('matches a 2-letter GDELT/FIPS code exactly', () => {
        expect(conflictMatchesCountry(ev('IR'), 'IR')).toBe(true)
        expect(conflictMatchesCountry(ev('NG'), 'NG')).toBe(true)
    })

    it('matches case-insensitively on the code', () => {
        expect(conflictMatchesCountry(ev('ir'), 'IR')).toBe(true)
        expect(conflictMatchesCountry(ev('US'), 'us')).toBe(true)
    })

    it('matches an ACLED full country name against the focus code', () => {
        expect(conflictMatchesCountry(ev('Ukraine'), 'UA')).toBe(true)
        expect(conflictMatchesCountry(ev('Iran'), 'IR')).toBe(true)
        expect(conflictMatchesCountry(ev('ukraine'), 'UA')).toBe(true)
    })

    it('does not cross-match different countries', () => {
        expect(conflictMatchesCountry(ev('IR'), 'US')).toBe(false)
        expect(conflictMatchesCountry(ev('Ukraine'), 'RU')).toBe(false)
    })

    it('never matches on empty inputs', () => {
        expect(conflictMatchesCountry(ev(''), 'US')).toBe(false)
        expect(conflictMatchesCountry(ev('US'), '')).toBe(false)
        expect(conflictMatchesCountry(ev('US'), null)).toBe(false)
        expect(conflictMatchesCountry(ev('US'), undefined)).toBe(false)
    })
})

describe('conflictCountryCode', () => {
    it('passes a 2-letter code through, uppercased', () => {
        expect(conflictCountryCode(ev('IR'))).toBe('IR')
        expect(conflictCountryCode(ev('ng'))).toBe('NG')
    })

    it('reverse-maps an ACLED full name to a code', () => {
        expect(conflictCountryCode(ev('Ukraine'))).toBe('UA')
        expect(conflictCountryCode(ev('iran'))).toBe('IR')
    })

    it('returns empty for unknown or missing countries', () => {
        expect(conflictCountryCode(ev(''))).toBe('')
        expect(conflictCountryCode(ev('Atlantis'))).toBe('')
    })
})

describe('conflictsForCountry', () => {
    const list = [ev('IR'), ev('Ukraine'), ev('US'), ev('IR'), ev('')]

    it('filters to the focused country across both code spaces', () => {
        expect(conflictsForCountry(list, 'IR')).toHaveLength(2)
        expect(conflictsForCountry(list, 'UA')).toHaveLength(1)
        expect(conflictsForCountry(list, 'US')).toHaveLength(1)
    })

    it('returns empty for no focus or no data', () => {
        expect(conflictsForCountry(list, null)).toEqual([])
        expect(conflictsForCountry(null, 'IR')).toEqual([])
        expect(conflictsForCountry(list, 'FR')).toEqual([])
    })
})
