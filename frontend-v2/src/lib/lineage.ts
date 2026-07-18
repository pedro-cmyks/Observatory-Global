// NARRATIVE BIOGRAPHY — theme-lineage-v0 contract (BUILD-B, 2026-07-18).
//
// The backend endpoint `GET /api/v2/theme/{id}/lineage` is produced by the
// narrative-lineage census lane (backend/scripts/narrative_lineage_census.py):
// live dynamic topics stitched to archive_story_units ENTIRELY in OpenAI
// text-embedding-3-small space (never e5-vs-OpenAI). This file freezes the
// CONTRACT the surface consumes, plus the fixture the endpoint must satisfy.
//
// Contract shape (theme-lineage-v0):
//   {
//     contract: 'theme-lineage-v0',
//     topic_id: string,              // the thread id the panel asked about
//     lineage_id: string | null,     // census lineage ('lin-<min unit id>')
//     weeks: LineageWeek[],          // ascending; era gaps EXPLICIT via gap:true
//     stitch: {                      // glass-box method line
//       space, theta_topic_unit, theta_unit_unit,
//       topic_sim,                   // topic↔lineage best cosine (the stitch)
//       member_coverage,             // share of member headlines found in shards
//       candidate,                   // stitch below-threshold → candidate only
//     },
//     empty_reason?: string | null,  // honest absence ('no_lineage', ...)
//   }
//
// Honesty rules encoded here:
// - absence is honest: <2 present weeks → the surface renders NOTHING;
// - drift_cos_prev is the MEASURED cosine of adjacent era centroids — the
//   surface classifies for styling but always shows the number;
// - candidate stitches render dashed and labeled, never asserted;
// - tier 'hot' (live topic weeks) vs 'archive' (weekly archive clusters) is
//   explicit per week, mirroring the DayEvidencePanel tier discipline.

export interface LineageReceipt {
    headline: string
    url?: string | null
    source?: string | null
    source_lang?: string | null
    /** present for hot-tier receipts (enables translation); archive samples may lack it */
    signal_id?: number | null
    day?: string | null
}

export interface LineageWeek {
    /** ISO Monday of the era week */
    week: string
    /** era gap inside the lineage — the story went quiet that week */
    gap?: boolean
    tier?: 'hot' | 'archive'
    /** label-of-era (largest unit's label, or the live topic label for hot) */
    label?: string | null
    n_signals?: number
    n_units?: number
    countries?: string[]
    /** MEASURED cosine of this era's centroid vs the previous present era's */
    drift_cos_prev?: number | null
    /** this era joined the lineage below the asserted threshold */
    candidate?: boolean
    /** SEAM week: two (or more) census lineages meet here, joined ONLY by the
     *  live thread — the union is labeled (meta.lineage_ids), never silent */
    joined?: boolean
    receipts?: LineageReceipt[]
}

export interface LineageMeta {
    /** all census lineages merged into this spine; >1 = labeled union whose
     *  seam week carries joined:true */
    lineage_ids?: string[]
    /** where the hot node's count comes from: 'members' = count(*) over
     *  topic_members evidence, 'aggregate' = dynamic_topics.agg_n_signals */
    hot_n_signals_source?: 'members' | 'aggregate' | null
    weeks_spanned?: number
    weeks_present?: number
    coverage_pct?: number
    n_units?: number
    n_unit_edges?: number
    method?: string | null
}

export interface LineageStitch {
    space: string
    /** measured taus — null when the loader's method string did not carry them */
    theta_topic_unit: number | null
    theta_unit_unit: number | null
    topic_sim: number | null
    member_coverage: number | null
    candidate: boolean
    /** loader provenance string (backend passes it through verbatim) */
    method?: string | null
}

export interface LineageResponse {
    contract: string
    topic_id: string
    lineage_id: string | null
    weeks: LineageWeek[]
    stitch: LineageStitch | null
    meta?: LineageMeta | null
    empty_reason?: string | null
}

/** Present eras = the weeks that actually carry story mass. */
export function presentWeeks(weeks: LineageWeek[] | null | undefined): LineageWeek[] {
    return (weeks ?? []).filter(w => !w.gap)
}

// ── Fixture: the canonical example the endpoint must satisfy ────────────────
// Modeled on the census lane's real top-living lineage shape (VE earthquake
// class): archive eras May→early-July, the Stage-B unit hole crossed by the
// stitch to the live topic (hot tier), one rename mid-life, one candidate era,
// and a LABELED UNION: the live thread stitches to units of TWO census
// lineages (lin-2041 + lin-3105) — the hot week is the seam (joined:true).
export const LINEAGE_FIXTURE: LineageResponse = {
    contract: 'theme-lineage-v0',
    topic_id: 'dynamic-topic-1837',
    lineage_id: 'lin-2041',
    meta: {
        lineage_ids: ['lin-2041', 'lin-3105'],
        hot_n_signals_source: 'members',
    },
    stitch: {
        space: 'openai/text-embedding-3-small',
        theta_topic_unit: 0.62,
        theta_unit_unit: 0.55,
        topic_sim: 0.714,
        member_coverage: 0.84,
        candidate: false,
    },
    weeks: [
        {
            week: '2026-05-25', tier: 'archive', label: 'Venezuela Earthquake Casualties',
            n_signals: 812, n_units: 3, countries: ['VE', 'CO'], drift_cos_prev: null, candidate: false,
            receipts: [
                { headline: 'Terremoto en Venezuela deja más de 3.000 muertos', source: 'El Nacional', url: 'https://example.com/a', source_lang: 'es', day: '2026-05-27' },
                { headline: 'Séisme au Venezuela: le bilan s’alourdit', source: 'Le Monde', url: 'https://example.com/b', source_lang: 'fr', day: '2026-05-28' },
            ],
        },
        {
            week: '2026-06-01', tier: 'archive', label: 'Venezuela Earthquake Casualties',
            n_signals: 640, n_units: 2, countries: ['VE'], drift_cos_prev: 0.94, candidate: false,
            receipts: [
                { headline: 'Rescue teams reach remote Andean towns', source: 'Reuters', url: 'https://example.com/c', source_lang: 'en', day: '2026-06-03' },
            ],
        },
        { week: '2026-06-08', gap: true },
        {
            week: '2026-06-15', tier: 'archive', label: 'Venezuela Reconstruction Aid Debate',
            n_signals: 210, n_units: 1, countries: ['VE', 'US'], drift_cos_prev: 0.71, candidate: false,
            receipts: [
                { headline: 'Ayuda internacional para la reconstrucción divide al gobierno', source: 'El País', url: 'https://example.com/d', source_lang: 'es', day: '2026-06-17' },
            ],
        },
        {
            week: '2026-06-22', tier: 'archive', label: 'Venezuela Reconstruction Aid Debate',
            n_signals: 155, n_units: 1, countries: ['VE'], drift_cos_prev: 0.89, candidate: true,
            receipts: [],
        },
        {
            week: '2026-07-13', tier: 'hot', label: 'Venezuela Earthquake Recovery',
            n_signals: 96, n_units: 1, countries: ['VE'], drift_cos_prev: 0.66, candidate: false, joined: true,
            receipts: [
                { headline: 'Damnificados exigen viviendas dos meses después del sismo', source: 'Efecto Cocuyo', url: 'https://example.com/e', source_lang: 'es', signal_id: 123456, day: '2026-07-15' },
            ],
        },
    ],
    empty_reason: null,
}

/** Dev-only mock switch: `?lineageMock=1` on a dev build serves the fixture
 *  (browser verification path). NEVER active on a production build. */
function mockRequested(): boolean {
    try {
        return import.meta.env.DEV
            && new URLSearchParams(window.location.search).has('lineageMock')
    } catch {
        return false
    }
}

/** Fetch the lineage for a thread. Resolves null on ANY failure or on an
 *  endpoint that is not deployed yet (404) — absence is honest, the section
 *  simply does not render. */
export async function fetchLineage(themeId: string): Promise<LineageResponse | null> {
    if (mockRequested()) {
        return { ...LINEAGE_FIXTURE, topic_id: themeId }
    }
    try {
        const r = await fetch(`/api/v2/theme/${encodeURIComponent(themeId)}/lineage`)
        if (!r.ok) return null
        const d = (await r.json()) as LineageResponse
        if (!d || !Array.isArray(d.weeks)) return null
        return d
    } catch {
        return null
    }
}
