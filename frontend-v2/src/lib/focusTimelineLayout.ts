/**
 * Track C4b — pure layout/scale math for the combined activity timeline
 * (spec §3). Kept side-effect-free (no React, no DOM, no fetch) so every
 * encoding decision — the diverging volume split, stable per-subject color,
 * where a trend line ENDS, degraded-channel handling — is unit-tested with
 * zero I/O. `FocusTimeline.tsx` consumes these and does only the SVG drawing.
 *
 * Spec: docs/superpowers/specs/2026-07-21-time-axis-versioned-relationships.md
 * §3 (diverging bars + rarity-normalized key-subject lines + voice-mix band),
 * §7 (honesty: a line that ends = connection died; never fake a shared axis;
 * degraded channel is a grey gap, never zero).
 */

// ---------------------------------------------------------------- API shapes
// Mirror the backend contracts focus-timeline-v0 (C4a) + focus-edge-diff-v0
// (C3). Only the fields this chart reads are typed.
export type ChannelStatus = 'live' | 'degraded' | 'unavailable'

export interface TimelineVolume {
    count: number
    avg_sentiment: number | null
}

export interface KeySubjectPoint {
    name: string
    type: string | null
    unverified: boolean
    rarity_weight: number | null
    mentions: number
    presence: number
}

export interface VoiceMixBucket {
    top_languages: Array<{ lang: string; n: number }>
    top_origins: Array<{ cc: string; n: number }>
    language_entropy_norm: number
    origin_entropy_norm: number
}

export interface TimelineBucket {
    bucket_start: string
    volume: TimelineVolume
    key_subjects: KeySubjectPoint[] | null
    voice_mix: VoiceMixBucket | null
}

export interface KeySubjectCandidate {
    name: string
    type: string | null
    unverified: boolean
    signal_count: number
    rarity_weight: number | null
}

export interface FocusTimelineResponse {
    contract: string
    ref: string
    focus_type: string
    resolved?: Record<string, unknown>
    hours?: number
    granularity?: string
    buckets: TimelineBucket[]
    key_subjects_candidates: KeySubjectCandidate[]
    channels: {
        volume: ChannelStatus
        key_subjects: ChannelStatus
        voice_mix: ChannelStatus
    }
    reason?: string
}

export interface EdgeChange {
    identity_key_a: string
    identity_key_b: string
    // Backend `CHANGE_TYPES` (app/services/edge_diff.py): 'formed' | 'weakened'
    // | 'narrative_change' | 'substrate_churn' | 'stable'. A dissolved edge is
    // ALREADY classified by cause on the wire — there is no generic 'died'
    // type (an earlier version of this client looked for one, so every
    // dissolved edge fell through both the chips and the caveat).
    change_type: string
    weight_t0: number | null
    weight_t1: number | null
    delta: number | null
    reason: string | null
    basis: string | null
}

/** Mirrors the backend `snapshot_interval_out` shape: how far apart the two
 *  compared snapshot passes ACTUALLY are. Stored passes are not evenly spaced
 *  (2026-07-25's half-written snapshot was deleted, so 07-24 -> 07-26 are
 *  consecutive rows 48h apart), so a diff must be labeled by its real span. */
export interface SnapshotIntervalInfo {
    hours: number
    expected_hours: number
    intermediate_snapshots: number
    missing_snapshot_passes: number
    is_standard: boolean
    note: string
}

export interface DormantRelationship {
    entity_a: string
    entity_b: string
    cooccur_count: number
    rarity_weight: number | null
    reason: string | null
}

export interface EdgeDiffResponse {
    contract: string
    ref: string
    focus_identity_key?: string
    since?: string
    matched_since_snapshot_at?: string
    latest_snapshot_at?: string
    interval?: SnapshotIntervalInfo
    changes: EdgeChange[]
    dormant: DormantRelationship[]
    dormant_reason?: string
    reason?: string
}

// ---------------------------------------------------------------- primitives
export function clamp(x: number, lo: number, hi: number): number {
    return x < lo ? lo : x > hi ? hi : x
}

/**
 * Split a bucket's total volume into a positive-tone UP portion and a
 * negative-tone DOWN portion, by its AVERAGE sentiment (spec §3: sentiment by
 * POSITION, not color; total extent = volume). We only have an average tone
 * per bucket, not a real per-signal polarity count, so the split is DERIVED:
 * fractionUp = 0.5 + 0.5*clamp(avg/sentFull, -1, 1). A neutral bucket splits
 * 50/50 (reads as balanced), a fully-positive bucket is all UP, fully-negative
 * all DOWN. `up + down === count` exactly, so the bar's total extent is always
 * the honest volume — only the balance is modeled. Callers must label the tone
 * as "average", never as a hard positive/negative signal count.
 */
export function divergingSplit(
    count: number,
    avgSentiment: number | null,
    sentFull = 1,
): { up: number; down: number; total: number } {
    const c = Math.max(0, count)
    if (c === 0) return { up: 0, down: 0, total: 0 }
    const s = avgSentiment == null ? 0 : clamp(avgSentiment / sentFull, -1, 1)
    const fractionUp = 0.5 + 0.5 * s
    const up = c * fractionUp
    return { up, down: c - up, total: c }
}

/**
 * Pixel heights for a diverging bar. `maxCount` is the max bucket volume across
 * the series, mapped to `halfBandPx` — so a full-volume all-positive bucket
 * reaches the top of the up-band, and a neutral bucket of the same volume fills
 * half of each band. Both sides share ONE volume scale (honest: they are the
 * same quantity, just signed by tone).
 */
export function barPixels(
    count: number,
    avgSentiment: number | null,
    maxCount: number,
    halfBandPx: number,
    sentFull = 1,
): { upH: number; downH: number } {
    if (maxCount <= 0 || halfBandPx <= 0) return { upH: 0, downH: 0 }
    const { up, down } = divergingSplit(count, avgSentiment, sentFull)
    return {
        upH: (up / maxCount) * halfBandPx,
        downH: (down / maxCount) * halfBandPx,
    }
}

export function maxVolume(buckets: TimelineBucket[]): number {
    let m = 0
    for (const b of buckets) {
        const c = b.volume?.count ?? 0
        if (c > m) m = c
    }
    return m
}

// ---------------------------------------------------------------- color
/**
 * Categorical palette for the key-subject trend lines. Mid-saturation,
 * mid-lightness hues chosen to read on BOTH the emerald-light paper (#eef1ef)
 * and the dark grounds (#0d1512 / #070d17) — never so pale it vanishes on
 * paper, never so dark it vanishes at night. Color is freed for the lines
 * precisely because sentiment moved to bar POSITION (spec §3).
 */
export const SUBJECT_LINE_PALETTE: string[] = [
    '#2fa8b8', // teal
    '#e0912f', // amber
    '#9b6bd6', // violet
    '#e06a8a', // rose
    '#4a90d9', // blue
    '#4caf6a', // green
    '#d9744a', // burnt orange
    '#b85fb0', // magenta
    '#8a9a3a', // olive
    '#c9556a', // brick
    '#5b8def', // periwinkle
    '#c08a2f', // ochre
]

/**
 * Stable color per subject. The backend hands `key_subjects_candidates` in a
 * STABLE order (descending rarity, then name), so the same subject keeps the
 * same color across every bucket AND across refetches — the property spec §3
 * requires ("stable color per entity"). Keyed by lowercased name so a casing
 * wobble upstream never re-colors a line.
 */
export function assignSubjectColors(candidateNames: string[]): Map<string, string> {
    const m = new Map<string, string>()
    let i = 0
    for (const raw of candidateNames) {
        const key = (raw || '').trim().toLowerCase()
        if (!key || m.has(key)) continue
        m.set(key, SUBJECT_LINE_PALETTE[i % SUBJECT_LINE_PALETTE.length])
        i++
    }
    return m
}

// ---------------------------------------------------------------- line shape
/** Index of the last bucket where the subject has any presence; -1 if never. */
export function lastPresentIndex(presences: number[]): number {
    for (let i = presences.length - 1; i >= 0; i--) {
        if (presences[i] > 0) return i
    }
    return -1
}

/**
 * Points to draw the line through — from bucket 0 up to and including the last
 * bucket with presence. Trailing zeros are DROPPED so the polyline visibly
 * ENDS at the last mention (spec §3: "a line that ends = connection died").
 * Interior zeros are KEPT (the line honestly dips to the baseline that bucket,
 * a real "went quiet then came back"). All-zero series → no points.
 */
export function subjectLinePoints(presences: number[]): Array<{ index: number; value: number }> {
    const last = lastPresentIndex(presences)
    if (last < 0) return []
    const pts: Array<{ index: number; value: number }> = []
    for (let i = 0; i <= last; i++) pts.push({ index: i, value: presences[i] })
    return pts
}

/** True when a subject's line stops before the final bucket (its relationship
 *  died mid-window) — the endpoint then carries the churn-vs-narrative hover. */
export function subjectEndsEarly(presences: number[], bucketCount: number): boolean {
    const last = lastPresentIndex(presences)
    return last >= 0 && last < bucketCount - 1
}

export interface SubjectSeries {
    name: string
    type: string | null
    unverified: boolean
    color: string
    presences: number[]
    lastIndex: number
    endsEarly: boolean
}

/**
 * The whole key-subject matrix: one presence array per candidate across every
 * bucket, colored stably, with the line-end already resolved. Buckets whose
 * `key_subjects` is null (channel not measured that bucket) contribute a 0 —
 * but the CHANNEL status (`channels.key_subjects`) is what decides whether to
 * draw the lines at all; this only shapes the geometry when they ARE drawn.
 */
export function buildSubjectSeries(
    buckets: TimelineBucket[],
    candidates: KeySubjectCandidate[],
): SubjectSeries[] {
    const colors = assignSubjectColors(candidates.map(c => c.name))
    const n = buckets.length
    return candidates.map(cand => {
        const key = (cand.name || '').trim().toLowerCase()
        const presences = new Array<number>(n).fill(0)
        buckets.forEach((b, i) => {
            const ks = b.key_subjects
            if (!ks) return
            const hit = ks.find(p => (p.name || '').trim().toLowerCase() === key)
            if (hit) presences[i] = hit.presence
        })
        const lastIndex = lastPresentIndex(presences)
        return {
            name: cand.name,
            type: cand.type,
            unverified: cand.unverified,
            color: colors.get(key) || SUBJECT_LINE_PALETTE[0],
            presences,
            lastIndex,
            endsEarly: lastIndex >= 0 && lastIndex < n - 1,
        }
    })
}

/** Max presence across a set of series — the line channel's own y-scale top
 *  (a SEPARATE axis from the volume bars; never share a scale, spec §3). */
export function maxPresence(series: SubjectSeries[]): number {
    let m = 0
    for (const s of series) {
        for (const v of s.presences) if (v > m) m = v
    }
    return m
}

// ---------------------------------------------------------------- channels
export function isChannelUsable(status: ChannelStatus | undefined): boolean {
    return status === 'live'
}

/** Honest one-liner for a degraded/unavailable channel — never rendered as
 *  zero, always as a labeled grey gap (spec §7). */
export function channelGapLabel(status: ChannelStatus | undefined, reason?: string): string {
    if (status === 'degraded') {
        if (reason === 'db_busy') return 'not measured — the query timed out for this focus'
        if (reason === 'db_error') return 'not measured — data error'
        return 'not measured — timed out for this focus (large or unindexed)'
    }
    if (status === 'unavailable') {
        if (reason === 'db_unavailable') return 'unavailable — database offline'
        if (reason === 'topic_not_found') return 'unavailable — focus not resolvable'
        return 'not measured for this focus'
    }
    return ''
}

// ---------------------------------------------------------------- edge diff
export interface DiffSummary {
    formed: number
    died: number
    weakened: number
    diedNarrative: number
    diedChurn: number
}

/** Did this edge DISAPPEAR between the two passes? The backend names the cause
 *  in `change_type` (`narrative_change` / `substrate_churn`); `died` is
 *  tolerated only as a legacy alias. */
export function isDissolvedType(changeType: string | null | undefined): boolean {
    const t = (changeType || '').toLowerCase()
    return t === 'narrative_change' || t === 'substrate_churn' || t === 'died'
}

/** Is a dissolved edge a real NARRATIVE change (the story moved on) or
 *  SUBSTRATE churn (the topic re-founded / merged / retired)? The C2 classifier
 *  already decided it — read it off `change_type` first and only fall back to
 *  the prose `reason`, which legitimately mentions both words ("substrate
 *  churn, not a narrative change: …"), hence churn is tested first. */
export function dissolvedKind(
    c: { change_type?: string | null; reason?: string | null },
): 'narrative' | 'churn' | 'unknown' {
    const t = (c.change_type || '').toLowerCase()
    if (t === 'narrative_change') return 'narrative'
    if (t === 'substrate_churn') return 'churn'
    const r = (c.reason || '').toLowerCase()
    if (r.includes('substrate') || r.includes('churn') || r.includes('retired') ||
        r.includes('merged') || r.includes('refound') || r.includes('re-found')) return 'churn'
    if (r.includes('narrative')) return 'narrative'
    return 'unknown'
}

export function dissolvedLabel(
    c: { change_type?: string | null; reason?: string | null },
): string {
    switch (dissolvedKind(c)) {
        case 'narrative': return 'connection ended: narrative change'
        case 'churn': return 'connection ended: substrate churn'
        default: return 'connection ended: reason unrecorded'
    }
}

export function summarizeChanges(changes: EdgeChange[]): DiffSummary {
    const out: DiffSummary = { formed: 0, died: 0, weakened: 0, diedNarrative: 0, diedChurn: 0 }
    for (const c of changes) {
        const t = (c.change_type || '').toLowerCase()
        if (t === 'formed') out.formed++
        else if (t === 'weakened') out.weakened++
        else if (isDissolvedType(t)) {
            out.died++
            const k = dissolvedKind(c)
            if (k === 'narrative') out.diedNarrative++
            else if (k === 'churn') out.diedChurn++
        }
    }
    return out
}

// ------------------------------------------------------ diff window labeling
export interface DiffWindowLabel {
    /** ISO stamp the diff actually starts at — the matched SNAPSHOT, not the
     *  requested `since` (they differ whenever no pass sits on that date). */
    anchorIso: string | null
    /** Non-null ONLY when the compared step is not one standard pass: the
     *  short user-facing warning that must render next to the counts. */
    spanLabel: string | null
    isStandard: boolean
    /** Full backend receipt for the tooltip. */
    tip: string
}

/**
 * Label the window a diff actually covers (project rails: honest degradation,
 * no silent filtering).
 *
 * The forcing case is real: 2026-07-25's snapshot was a half-written partial
 * and was deleted, so the store holds 07-24 -> 07-26 as CONSECUTIVE passes 48h
 * apart. Measured on prod, that step reports ~50% more `formed` edges than
 * either adjacent 24h step. Rendered like every other day, two days of
 * accumulated change reads as a one-day burst of narrative change — precisely
 * the misreading these endpoints exist to prevent. So a non-standard interval
 * gets said out loud, and the counts stay visible (flagged, never filtered).
 *
 * `fallbackIso` is used only when the payload carries no snapshot stamp at all.
 */
export function describeDiffWindow(
    diff: Pick<EdgeDiffResponse, 'since' | 'matched_since_snapshot_at' | 'interval'> | null | undefined,
    fallbackIso?: string,
): DiffWindowLabel {
    const anchorIso = diff?.matched_since_snapshot_at || diff?.since || fallbackIso || null
    const iv = diff?.interval
    if (!iv) {
        // Older payload (pre-interval contract): we cannot claim the step is
        // standard, so say nothing about it rather than implying one day.
        return { anchorIso, spanLabel: null, isStandard: true, tip: '' }
    }
    if (iv.is_standard) {
        return { anchorIso, spanLabel: null, isStandard: true, tip: iv.note }
    }
    const hours = iv.hours
    let spanLabel: string
    if (hours === 0) {
        spanLabel = 'only one snapshot pass stored — nothing to compare yet'
    } else if (iv.missing_snapshot_passes > 0 && iv.intermediate_snapshots === 0) {
        const days = Math.round(hours / (iv.expected_hours || 24))
        spanLabel = `${formatSpanHours(hours)} apart — ${days} days of change in one step ` +
            `(${iv.missing_snapshot_passes} snapshot ` +
            `${iv.missing_snapshot_passes === 1 ? 'pass' : 'passes'} missing)`
    } else if (iv.intermediate_snapshots > 0) {
        spanLabel = `${formatSpanHours(hours)} apart — aggregates ` +
            `${iv.intermediate_snapshots + 1} snapshot steps, not one`
    } else if (hours < iv.expected_hours) {
        spanLabel = `${formatSpanHours(hours)} apart — less than one full snapshot pass`
    } else {
        spanLabel = `${formatSpanHours(hours)} apart — off the usual ` +
            `${formatSpanHours(iv.expected_hours)} cadence`
    }
    return { anchorIso, spanLabel, isStandard: false, tip: iv.note }
}

/** Hours as a compact span: whole hours stay hours, exact multiples of 24 read
 *  as days (a 48h gap is easier to judge as "2 days"). */
export function formatSpanHours(hours: number): string {
    if (!isFinite(hours) || hours <= 0) return '0h'
    if (hours >= 24 && Math.abs(hours % 24) < 0.01) {
        const d = Math.round(hours / 24)
        return `${d}d`
    }
    return `${Math.round(hours * 10) / 10}h`
}

/** Dormant backbone relationships touching a given subject NAME (§4 divergence
 *  = signal): the actors still co-appear but no current thread binds them. Used
 *  to enrich a subject line's endpoint hover honestly. Matched case-folded on
 *  either side of the entity pair. */
export function dormantForSubject(name: string, dormant: DormantRelationship[]): DormantRelationship[] {
    const key = (name || '').trim().toLowerCase()
    if (!key) return []
    return dormant.filter(d =>
        (d.entity_a || '').trim().toLowerCase() === key ||
        (d.entity_b || '').trim().toLowerCase() === key)
}
