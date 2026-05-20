const ISO2_REGION: Record<string, string> = {
    // North America
    US: 'North America', CA: 'North America',
    // Latin America
    MX: 'Latin America', BR: 'Latin America', AR: 'Latin America', CO: 'Latin America',
    CL: 'Latin America', PE: 'Latin America', VE: 'Latin America', EC: 'Latin America',
    BO: 'Latin America', PY: 'Latin America', UY: 'Latin America', CU: 'Latin America',
    // Europe
    GB: 'Europe', DE: 'Europe', FR: 'Europe', IT: 'Europe', ES: 'Europe',
    PL: 'Europe', NL: 'Europe', BE: 'Europe', SE: 'Europe', NO: 'Europe',
    CH: 'Europe', AT: 'Europe', PT: 'Europe', GR: 'Europe', CZ: 'Europe',
    HU: 'Europe', RO: 'Europe', UA: 'Europe', RU: 'Europe', FI: 'Europe',
    DK: 'Europe', SK: 'Europe', BG: 'Europe', HR: 'Europe', RS: 'Europe',
    // Middle East
    SA: 'Middle East', IR: 'Middle East', IL: 'Middle East', TR: 'Middle East',
    AE: 'Middle East', IQ: 'Middle East', SY: 'Middle East', JO: 'Middle East',
    LB: 'Middle East', KW: 'Middle East', QA: 'Middle East', YE: 'Middle East',
    OM: 'Middle East', PS: 'Middle East', BH: 'Middle East',
    // Asia
    CN: 'Asia', JP: 'Asia', IN: 'Asia', KR: 'Asia', ID: 'Asia',
    PK: 'Asia', BD: 'Asia', VN: 'Asia', TH: 'Asia', MY: 'Asia',
    PH: 'Asia', TW: 'Asia', SG: 'Asia', MM: 'Asia', KZ: 'Asia',
    UZ: 'Asia', AF: 'Asia', NP: 'Asia', LK: 'Asia',
    // Africa
    NG: 'Africa', ZA: 'Africa', EG: 'Africa', ET: 'Africa', KE: 'Africa',
    GH: 'Africa', TZ: 'Africa', DZ: 'Africa', MA: 'Africa', AO: 'Africa',
    MZ: 'Africa', CI: 'Africa', MG: 'Africa', CM: 'Africa', SN: 'Africa',
    // Oceania
    AU: 'Oceania', NZ: 'Oceania',
}

interface GeoNode {
    country_code: string
    signal_count: number
}

export function buildGeoNarrative(nodes: GeoNode[]): string | null {
    if (nodes.length < 3) return null

    const total = nodes.reduce((s, n) => s + n.signal_count, 0)
    if (total === 0) return null

    // Aggregate by region
    const regionTotals: Record<string, number> = {}
    for (const n of nodes) {
        const region = ISO2_REGION[n.country_code.toUpperCase()]
        if (!region) continue
        regionTotals[region] = (regionTotals[region] || 0) + n.signal_count
    }

    const sorted = Object.entries(regionTotals)
        .sort((a, b) => b[1] - a[1])
        .map(([region, count]) => ({ region, pct: Math.round((count / total) * 100) }))

    if (sorted.length === 0) return null

    const top = sorted[0]

    // Concentrated in one region
    if (top.pct >= 65) {
        return `Coverage concentrated in ${top.region} (${top.pct}%)`
    }

    // Two dominant regions
    if (sorted.length >= 2 && sorted[1].pct >= 15) {
        const second = sorted[1]
        const combined = top.pct + second.pct
        if (combined >= 70) {
            return `Predominantly ${top.region} and ${second.region} · Limited elsewhere`
        }
        return `Led by ${top.region} (${top.pct}%) and ${second.region} (${second.pct}%)`
    }

    // Wide spread across many regions
    if (sorted.length >= 4 && top.pct < 40) {
        return `Global coverage across ${sorted.length} regions`
    }

    return `Strongest in ${top.region} (${top.pct}%) · ${nodes.length} countries reporting`
}
