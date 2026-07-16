/**
 * Category → color FAMILY (dataviz audit 2026-07-13, fix 1+2).
 *
 * Rule: a topic category is assigned to one of seven fixed families via a
 * deterministic keyword map evaluated in FIXED order — never a string hash
 * (uncontrolled rainbow that repaints when data changes) and never a row
 * index (color would follow rank, not entity).
 *
 * The hexes are the CVD-validated palette from the audit, validated against
 * the product dark surface (#0c182b). They are defined once as CSS custom
 * properties in styles/variables.css (--fam-*); FAMILY_HEX here mirrors them
 * as the var() fallbacks + the testable source of truth. Color is never the
 * only encoding — every family-colored mark carries a text label.
 */

export type CategoryFamily =
    | 'conflict'
    | 'governance'
    | 'health'
    | 'economy'
    | 'society'
    | 'culture'
    | 'other'

/** CVD-validated family palette (dark surface #0c182b). Mirrored in variables.css. */
export const FAMILY_HEX: Record<CategoryFamily, string> = {
    conflict: '#cc5d47', // conflict / armed
    governance: '#b58733', // governance / politics
    health: '#0f92b0', // health / natural hazard
    economy: '#5183cc', // economy / energy
    society: '#c8659a', // migration / society
    culture: '#8a949c', // sports / culture — deliberately receding slate
    other: '#64748b', // uncategorized — gray slate
}

/**
 * Keyword map in FIXED evaluation order — first family whose keyword appears
 * in the (lowercased) category wins. Order is part of the contract: mixed
 * labels ("Political & Health Incidents") always resolve the same way.
 */
const FAMILY_KEYWORDS: Array<[CategoryFamily, string[]]> = [
    ['conflict', ['conflict', 'war ', ' war', 'war-', 'military', 'armed', 'terror', 'missile', 'invasion', 'ceasefire', 'insurgen', 'airstrike', 'hostage']],
    ['governance', ['politic', 'governance', 'election', 'corruption', 'constitutional', 'institutional', 'government', 'protest', 'diplomac', 'sanction', 'coup', 'legitimacy', 'public service', 'unrest']],
    ['health', ['health', 'disease', 'outbreak', 'pandemic', 'epidemic', 'earthquake', 'volcan', 'wildfire', 'storm', 'flood', 'disaster', 'hazard', 'drought', 'heatwave', 'heat-health', 'climate', 'weather', 'water']],
    ['economy', ['econom', 'energy', 'oil', 'gas', 'fuel', 'currency', 'fiscal', 'market', 'trade', 'financ', 'inflation', 'pipeline', 'subsid', 'debt', 'export']],
    ['society', ['migration', 'migrant', 'refugee', 'displacement', 'humanitarian', 'rights', 'gender', 'labor', 'crime', 'accident', 'society', 'social', 'housing', 'famine']],
    ['culture', ['sport', 'football', 'world cup', 'mundial', 'culture', 'entertainment', 'celebrity', 'lifestyle', 'recruitment', 'tourism', 'travel', 'music', 'film', 'festival', 'roundup']],
]

/** Deterministic category → family. Case-insensitive; unknown/empty → 'other'. */
export function famOf(category: string | null | undefined): CategoryFamily {
    if (!category) return 'other'
    const c = category.toLowerCase()
    for (const [family, keywords] of FAMILY_KEYWORDS) {
        for (const kw of keywords) {
            if (c.includes(kw)) return family
        }
    }
    return 'other'
}

/**
 * CSS color expression for a category — consumes the theme var with the
 * validated hex as fallback. Use in inline `style` (CSS context); SVG
 * presentation ATTRIBUTES do not substitute var(), so pass this via
 * style={{ fill/stroke }} there.
 */
export function familyColor(category: string | null | undefined): string {
    const fam = famOf(category)
    return `var(--fam-${fam}, ${FAMILY_HEX[fam]})`
}

/** Confidence-bar gradient: family color easing toward the text tone. */
export function familyGradient(category: string | null | undefined): string {
    const color = familyColor(category)
    return `linear-gradient(90deg, ${color}, color-mix(in srgb, ${color} 62%, #e2e8f0))`
}
