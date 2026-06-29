/**
 * Per-country heat + intensity — the single source of truth shared by the
 * MapLibre map (feature-states) and the Equal Earth map (#212). Extracted from
 * the inline App.tsx effect so the two render engines can never diverge on what
 * a country's heat is.
 *
 * - `heat` (0..1) drives FILL COLOR. It is the baseline-normalized composite
 *   (#231), NOT volume-rank — a country absent from the composite is not
 *   anomalously hot (0). Under focus it becomes relation relevance.
 * - `intensity` (0..1) drives GLOW WIDTH only (log-normalized volume), a
 *   secondary encoding — never the color.
 *
 * Focus semantics (#234):
 * - country focus  → light the focused country + its flow-co-occurrence partners
 *   (weighted by flow strength), dim everything else.
 * - person/theme focus (`entityFocus`) → nodes are already focus-scoped, so
 *   their volume IS the concentration; light by volume.
 * - no focus → the baseline composite.
 */

export interface HeatNode {
    id: string
    signalCount: number
    heat?: number
}

export interface HeatFlow {
    sourceCountry: string
    targetCountry: string
    strength?: number
}

export interface CountryHeatInput {
    enhancedNodes: HeatNode[]
    heatComposite: Map<string, number>
    visibleFlows: HeatFlow[]
    /** country focus code, or null */
    selectedCountryCode: string | null
    /** true when a person/theme is focused (nodes already focus-scoped) */
    entityFocus: boolean
}

export interface HeatState {
    heat: number
    intensity: number
}

export type CountryHeatStates = Map<string, HeatState>

export function computeCountryHeatStates(input: CountryHeatInput): CountryHeatStates {
    const { enhancedNodes, heatComposite, visibleFlows, selectedCountryCode, entityFocus } = input
    const out: CountryHeatStates = new Map()
    if (enhancedNodes.length === 0) return out

    const counts = enhancedNodes.map(n => n.signalCount)
    const logMin = Math.log(Math.min(...counts) + 1)
    const logMax = Math.log(Math.max(...counts, 1) + 1)
    const logRange = Math.max(logMax - logMin, 0.001)

    const focusCode = selectedCountryCode
    const relation = new Map<string, number>()
    if (focusCode) {
        let maxStr = 0.001
        visibleFlows.forEach(f => { maxStr = Math.max(maxStr, f.strength || 0) })
        relation.set(focusCode, 1.0)
        visibleFlows.forEach(f => {
            const partner = f.sourceCountry === focusCode ? f.targetCountry
                : f.targetCountry === focusCode ? f.sourceCountry : null
            if (partner && partner !== focusCode) {
                relation.set(partner, Math.max(
                    relation.get(partner) ?? 0,
                    0.25 + 0.75 * ((f.strength || 0) / maxStr),
                ))
            }
        })
    }

    enhancedNodes.forEach(node => {
        const normalized = (Math.log(node.signalCount + 1) - logMin) / logRange
        const intensity = 0.15 + normalized * 0.85
        let heat: number
        if (focusCode) {
            heat = relation.get(node.id) ?? 0
        } else if (entityFocus) {
            heat = intensity
        } else {
            const composite = heatComposite.get(node.id)
            heat = heatComposite.size > 0
                ? (composite ?? 0)
                : (node.heat != null ? node.heat : intensity)
        }
        out.set(node.id, { heat, intensity })
    })

    if (focusCode) {
        // Relation partners may sit outside the top-100 nodes — light them too.
        relation.forEach((relHeat, code) => {
            if (out.has(code)) return
            out.set(code, { heat: relHeat, intensity: 0.15 })
        })
    } else if (!entityFocus && heatComposite.size > 0) {
        // #231: a hot country can sit OUTSIDE the top-100-by-volume nodes
        // (e.g. Lebanon at 3 signals but high surprise). Color those too.
        heatComposite.forEach((compHeat, code) => {
            if (out.has(code)) return
            out.set(code, { heat: compHeat, intensity: 0.15 })
        })
    }

    return out
}

/**
 * Weather-radar fill color for a heat value (0..1). Mirrors the MapLibre
 * `country-heat-fill` interpolate stops (#231) so both engines read identically.
 * Returns an rgba() string; transparent below the 0.1 floor.
 */
export function heatFillColor(heat: number): string {
    // Wide, vivid weather-radar ramp: faint heat barely tints (stays near land,
    // so most countries read as land and only real heat pops), then a clearly
    // separated blue→cyan→green→yellow→orange→red climb so values differentiate.
    const stops: Array<[number, [number, number, number, number]]> = [
        [0, [0, 0, 0, 0]],
        [0.12, [40, 100, 210, 0.30]],
        [0.30, [25, 175, 205, 0.55]],
        [0.48, [45, 200, 120, 0.72]],
        [0.64, [235, 205, 45, 0.88]],
        [0.80, [240, 130, 30, 0.96]],
        [1.0, [242, 45, 30, 1.0]],
    ]
    return rgbaInterpolate(heat, stops)
}

/** Border-glow color for a heat value (0..1), mirroring `country-heat-glow`. */
export function heatGlowColor(heat: number): string {
    const stops: Array<[number, [number, number, number, number]]> = [
        [0, [0, 0, 0, 0]],
        [0.1, [30, 60, 140, 0.30]],
        [0.3, [35, 110, 160, 0.50]],
        [0.5, [50, 160, 130, 0.65]],
        [0.65, [205, 140, 35, 0.80]],
        [0.82, [230, 80, 20, 1.0]],
        [1.0, [248, 45, 10, 1.0]],
    ]
    return rgbaInterpolate(heat, stops)
}

/** Glow stroke width (px) for an intensity value (0..1), mirroring line-width. */
export function glowWidth(intensity: number): number {
    const stops: Array<[number, number]> = [
        [0, 0], [0.05, 2], [0.5, 6], [1.0, 10],
    ]
    let prev = stops[0]
    for (const s of stops) {
        if (intensity <= s[0]) {
            if (s[0] === prev[0]) return s[1]
            const t = (intensity - prev[0]) / (s[0] - prev[0])
            return prev[1] + t * (s[1] - prev[1])
        }
        prev = s
    }
    return stops[stops.length - 1][1]
}

function rgbaInterpolate(
    v: number,
    stops: Array<[number, [number, number, number, number]]>,
): string {
    const x = Math.max(0, Math.min(1, v))
    let lo = stops[0]
    let hi = stops[stops.length - 1]
    for (let i = 0; i < stops.length - 1; i++) {
        if (x >= stops[i][0] && x <= stops[i + 1][0]) {
            lo = stops[i]
            hi = stops[i + 1]
            break
        }
    }
    const span = hi[0] - lo[0] || 1
    const t = (x - lo[0]) / span
    const c = (idx: number) => Math.round(lo[1][idx] + t * (hi[1][idx] - lo[1][idx]))
    const a = (lo[1][3] + t * (hi[1][3] - lo[1][3])).toFixed(3)
    return `rgba(${c(0)}, ${c(1)}, ${c(2)}, ${a})`
}
