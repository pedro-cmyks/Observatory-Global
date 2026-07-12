import { resolveCountryName, COUNTRY_NAMES } from './countryNames'

// Conflict events → country relation (#232 UX slice). The relation is
// GEOGRAPHY-ONLY — an event relates to a country because it happened there,
// never because we matched it to a story. Surfaces that consume this must
// label it ("related by country, not by story").
//
// Country field shape differs by source: the GDELT Events fallback carries a
// 2-letter FIPS/GDELT code (action_country_code — the same code space the map
// nodes use), ACLED carries a full country NAME ("Ukraine"). Match both.
export interface ConflictCountryRef {
    location: { country: string }
}

export function conflictMatchesCountry(c: ConflictCountryRef, countryCode: string | null | undefined): boolean {
    const loc = c.location?.country || ''
    if (!loc || !countryCode) return false
    if (loc.toUpperCase() === countryCode.toUpperCase()) return true
    return loc.toLowerCase() === resolveCountryName(countryCode).toLowerCase()
}

// Focus needs a 2-letter CODE. GDELT events already carry one; ACLED carries
// a full name — reverse-map it. Returns '' when un-attributable (caller must
// not focus on it).
let NAME_TO_CODE: Record<string, string> | null = null
export function conflictCountryCode(c: ConflictCountryRef): string {
    const loc = c.location?.country || ''
    if (!loc) return ''
    if (loc.length === 2) return loc.toUpperCase()
    if (!NAME_TO_CODE) {
        NAME_TO_CODE = {}
        for (const [code, name] of Object.entries(COUNTRY_NAMES)) {
            const key = name.toLowerCase()
            // first mapping wins — the map lists canonical ISO codes first,
            // FIPS aliases later (e.g. YE before YM for Yemen).
            if (!(key in NAME_TO_CODE)) NAME_TO_CODE[key] = code
        }
    }
    return NAME_TO_CODE[loc.toLowerCase()] || ''
}

export function conflictsForCountry<T extends ConflictCountryRef>(
    conflicts: T[] | null | undefined,
    countryCode: string | null | undefined,
): T[] {
    if (!conflicts || !countryCode) return []
    return conflicts.filter(c => conflictMatchesCountry(c, countryCode))
}
