// NARRATIVE BIOGRAPHY spine — pure layout over theme-lineage-v0 weeks
// (BUILD-B, 2026-07-18). No DOM, no fetch: geometry + honest classification
// only, so the whole visual grammar is unit-testable.
//
// Principles (mirrors the census lane's honesty rules):
// - TIME IS THE LITERAL AXIS: x is proportional to real week distance from
//   the first era — a quiet week widens the spacing instead of compressing it.
// - DRIFT IS MEASURED: edges classify the adjacent-era centroid cosine for
//   styling (steady/shifting) but the raw number rides along for the tooltip;
//   a missing measurement is 'unmeasured', never silently 'steady'.
// - GAPS PRODUCE NO NODE: an era gap renders as spanned distance (dotted
//   edge), never a fabricated point.
// - CANDIDATE STITCHES ARE FLAGGED: below-threshold joins mark their edges.

import type { LineageWeek } from './lineage'

export interface SpineConfig {
    width: number
    height: number
    padX: number
    rMin: number
    rMax: number
    /** display cut for the steady/shifting edge style — the measured cosine
     *  is always preserved on the edge; this only picks the stroke. */
    steadyDrift: number
}

const DEFAULTS: SpineConfig = {
    width: 720,
    height: 120,
    padX: 46,
    rMin: 5,
    rMax: 15,
    steadyDrift: 0.85,
}

export interface SpineNode {
    week: string
    /** literal-time index in weeks from the first present era */
    index: number
    x: number
    y: number
    r: number
    tier: 'hot' | 'archive'
    label: string | null
    /** render the era label — first era, or the label CHANGED vs the previous era */
    showLabel: boolean
    nSignals: number
    nUnits: number
    countries: string[]
    driftCosPrev: number | null
    candidate: boolean
    /** SEAM node: multiple census lineages meet here, joined by the live thread */
    joined: boolean
}

export interface SpineEdge {
    fromWeek: string
    toWeek: string
    x1: number
    x2: number
    y: number
    kind: 'steady' | 'shifting' | 'unmeasured'
    /** the measured cosine (to-era vs from-era centroid), null when unmeasured */
    drift: number | null
    /** the edge crosses at least one quiet/gap week */
    spansGap: boolean
    /** either endpoint joined the lineage below the asserted threshold */
    candidate: boolean
}

export interface LineageSpine {
    hasSpine: boolean
    nodes: SpineNode[]
    edges: SpineEdge[]
    /** total literal span in weeks (first..last present era inclusive) */
    weekSpan: number
    maxSignals: number
}

/** Label normalization for change detection: case/punctuation/whitespace-run
 *  insensitive so cosmetic relabels don't read as narrative renames. */
export function normalizeEraLabel(label: string | null | undefined): string {
    return (label ?? '')
        .toLowerCase()
        .replace(/[^\p{L}\p{N}]+/gu, ' ')
        .trim()
}

const WEEK_MS = 7 * 24 * 3600 * 1000

function weekTime(week: string): number {
    return Date.parse(week + 'T00:00:00Z')
}

export function buildLineageSpine(
    weeks: LineageWeek[],
    config: Partial<SpineConfig> = {},
): LineageSpine {
    const cfg = { ...DEFAULTS, ...config }
    const present = weeks
        .filter(w => !w.gap)
        .slice()
        .sort((a, b) => weekTime(a.week) - weekTime(b.week))

    if (present.length < 2) {
        return { hasSpine: false, nodes: [], edges: [], weekSpan: present.length, maxSignals: 0 }
    }

    const t0 = weekTime(present[0].week)
    const indices = present.map(w => Math.round((weekTime(w.week) - t0) / WEEK_MS))
    const maxIdx = indices[indices.length - 1]
    const innerW = cfg.width - 2 * cfg.padX
    const maxSignals = Math.max(1, ...present.map(w => w.n_signals ?? 0))
    const y = cfg.height / 2

    let prevShownLabel: string | null = null
    const nodes: SpineNode[] = present.map((w, i) => {
        const norm = normalizeEraLabel(w.label)
        const showLabel = i === 0 || (norm !== prevShownLabel && norm !== '')
        if (norm !== '') prevShownLabel = norm
        const vol = Math.max(0, w.n_signals ?? 0)
        return {
            week: w.week,
            index: indices[i],
            x: cfg.padX + (maxIdx === 0 ? innerW / 2 : (indices[i] / maxIdx) * innerW),
            y,
            r: cfg.rMin + (cfg.rMax - cfg.rMin) * Math.sqrt(vol / maxSignals),
            tier: w.tier === 'hot' ? 'hot' : 'archive',
            label: w.label ?? null,
            showLabel,
            nSignals: vol,
            nUnits: w.n_units ?? 0,
            countries: w.countries ?? [],
            driftCosPrev: w.drift_cos_prev ?? null,
            candidate: !!w.candidate,
            joined: !!w.joined,
        }
    })

    const edges: SpineEdge[] = []
    for (let i = 1; i < nodes.length; i++) {
        const from = nodes[i - 1]
        const to = nodes[i]
        const drift = to.driftCosPrev
        edges.push({
            fromWeek: from.week,
            toWeek: to.week,
            x1: from.x,
            x2: to.x,
            y,
            kind: drift == null ? 'unmeasured' : drift >= cfg.steadyDrift ? 'steady' : 'shifting',
            drift,
            spansGap: to.index - from.index > 1,
            candidate: from.candidate || to.candidate,
        })
    }

    return { hasSpine: true, nodes, edges, weekSpan: maxIdx + 1, maxSignals }
}
