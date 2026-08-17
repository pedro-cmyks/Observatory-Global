// Reader place — a DECLARED fact, country-grain only (spec §6, 2026-08-17).
// Locale may PROPOSE the initial value; `proposed: true` obliges the UI to
// show it as changeable. Never inferred silently: a wrong hidden place is
// the same defect class as the VE chip on a Colombian story.
export const PLACE_KEY = 'atlas.reader.place.v1'

export interface ReaderPlace {
    country: string | null
    proposed: boolean
}

const CC = /^[A-Z]{2}$/

export function loadReaderPlace(locale?: string): ReaderPlace {
    try {
        const stored = localStorage.getItem(PLACE_KEY)
        if (stored && CC.test(stored)) return { country: stored, proposed: false }
    } catch { /* storage unavailable → fall through to proposal */ }
    const region = locale?.split('-')[1]?.toUpperCase()
    if (region && CC.test(region)) return { country: region, proposed: true }
    return { country: null, proposed: false }
}

export function saveReaderPlace(cc: string | null): void {
    try {
        if (cc && CC.test(cc.toUpperCase())) localStorage.setItem(PLACE_KEY, cc.toUpperCase())
        else localStorage.removeItem(PLACE_KEY)
    } catch { /* best-effort */ }
}
