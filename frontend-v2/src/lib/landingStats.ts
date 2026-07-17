// Landing (L0) stat formatting — council P1-12 template failures.
//
// Three failure classes, all fixed by construction here:
//   - literal "$ countries covering": a non-number reaching the template →
//     formatCountriesCovering rejects anything non-finite, the line is omitted;
//   - triplicated "5 countries covering": top_countries is a CAPPED top-5 list;
//     its length is a floor, not a count → rendered "5+" and marked approximate;
//   - SIGNALS em-dash on fresh load: resolveLiveStat names the state (loading
//     vs unavailable) instead of a silent dash.

export function formatSignalCount(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
    if (n >= 1_000) return `${Math.floor(n / 1_000)}k`
    return String(n)
}

export interface CountriesCovering {
    value: string
    noun: 'country' | 'countries'
    /** true when derived from the capped top-countries list (a floor) */
    approx: boolean
}

// Measured 2026-07-17 against prod /api/v2/threads: country_count is served as
// len(top_countries), and top_countries is a TOP-5 list — every busy thread
// "counts" exactly 5, which is what triplicated "5 countries covering" across
// all three landing cards. A count sitting at the cap is a floor, not a count.
export const TOP_COUNTRIES_CAP = 5

export function formatCountriesCovering(
    countryCount: number | null | undefined,
    topCountriesLength: number,
): CountriesCovering | null {
    const served = typeof countryCount === 'number' && Number.isFinite(countryCount)
        ? Math.floor(countryCount)
        : null
    if (served !== null && served > 0) {
        if (served >= TOP_COUNTRIES_CAP && served === Math.floor(topCountriesLength)) {
            return { value: `${served}+`, noun: 'countries', approx: true }
        }
        return { value: String(served), noun: served === 1 ? 'country' : 'countries', approx: false }
    }
    const floor = Number.isFinite(topCountriesLength) ? Math.floor(topCountriesLength) : 0
    if (floor > 0) {
        // "N+" is a floor, so the noun is always plural-ish honest
        return { value: `${floor}+`, noun: 'countries', approx: true }
    }
    return null
}

export type LiveStatState = 'live' | 'loading' | 'unavailable'

export interface LiveStat {
    display: string
    state: LiveStatState
    note: string | null
}

export function resolveLiveStat(value: string | null, failed: boolean): LiveStat {
    if (value !== null) return { display: value, state: 'live', note: null }
    if (failed) return { display: '—', state: 'unavailable', note: 'live count unavailable' }
    return { display: '—', state: 'loading', note: 'loading live count…' }
}
