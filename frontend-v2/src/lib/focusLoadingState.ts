/** Council R4 DESKTOP-N26 — the time-boxed, honest loading contract for the
 *  person/theme focus panel.
 *
 *  THE DEFECT. `EntityPanel` rendered eight shimmer bars off `/api/v2/focus`
 *  with no AbortController, no timer, and a swallowed `.catch(() => {})`.
 *  For a ubiquitous name the endpoint took 45-120s (measured: with the old
 *  unindexable predicate every one of its six lanes blew a 30s cap — 180s
 *  total), so the panel sat mute and there was no code path in the file that
 *  could ever say the fetch had failed. Sibling panels degraded honestly on
 *  the same data; only this one hung.
 *
 *  THREE STATES, not two. The codebase had exactly zero "this is taking
 *  longer" messages anywhere before this module, so every surface was
 *  binary: skeleton, or resolved. A heavy subject is a THIRD thing — still
 *  working, genuinely slow, and worth saying so:
 *
 *    loading  (< SLOW_MS)   the ordinary skeleton
 *    slow     (>= SLOW_MS)  "measuring a heavy subject…" + whatever answered
 *    settled                data, degraded gaps, or an honest failure
 *
 *  The precedents this follows: `UniverseView` for the bound itself (abort +
 *  retry + honest empty rather than an endless "Assembling…"), and
 *  `focusTimelineLayout.channelGapLabel` (C4a) for per-lane grey gaps that
 *  are never rendered as zero.
 */

export type LaneName = 'nodes' | 'headlines' | 'persons' | 'ner' | 'sources' | 'related'
export type LaneStatus = 'live' | 'degraded'
export type FocusPhase = 'loading' | 'slow' | 'settled'

/** When to admit the subject is heavy. Set against the measured backend
 *  distribution: an ordinary person resolves in 1.4-3.2s and even a cold
 *  heavy one lands by the backend's 9s global deadline, so 8s fires only
 *  when the request is genuinely in the tail — never on a normal load. */
export const FOCUS_SLOW_MS = 8000

/** Client-side hard bound. The backend now guarantees a reply by its own
 *  ~9s deadline, so anything still outstanding at 20s is a network or proxy
 *  failure, not a slow query. Same 20s the UniverseView precedent uses. */
export const FOCUS_TIMEOUT_MS = 20000

export interface FocusLanePayload {
    lanes?: Partial<Record<LaneName, LaneStatus>>
    degraded_lanes?: string[]
    degraded_reasons?: Record<string, string>
    summary?: { total_signals: number | null; total_countries: number | null }
}

/** Which of the three states the panel is in. `settled` wins over
 *  everything: once a payload (or an error) has landed, elapsed time is
 *  irrelevant. */
export function focusPhase(elapsedMs: number, settled: boolean): FocusPhase {
    if (settled) return 'settled'
    return elapsedMs >= FOCUS_SLOW_MS ? 'slow' : 'loading'
}

/** A lane is usable only when the server explicitly called it live.
 *  An ABSENT `lanes` map means an older/cached response shape that predates
 *  N26 — treat it as live so a stale deploy renders data rather than a wall
 *  of false "could not measure" gaps. */
export function laneStatus(data: FocusLanePayload | null, lane: LaneName): LaneStatus {
    if (!data) return 'degraded'
    if (!data.lanes) return 'live'
    return data.lanes[lane] ?? 'live'
}

export function isLaneUsable(data: FocusLanePayload | null, lane: LaneName): boolean {
    return laneStatus(data, lane) === 'live'
}

/** Honest one-liner for a degraded lane — the C4a convention, never a zero.
 *  Mirrors `channelGapLabel`'s reason codes so the two surfaces speak with
 *  one voice. */
export function laneGapLabel(data: FocusLanePayload | null, lane: LaneName): string {
    if (isLaneUsable(data, lane)) return ''
    const reason = data?.degraded_reasons?.[lane]
    if (reason === 'deadline') return 'not measured — the panel ran out of time on this subject'
    if (reason === 'db_busy') return 'not measured — the query timed out for this subject'
    if (reason === 'db_error') return 'not measured — data error'
    return 'not measured for this subject'
}

/** The zero-as-fact guard. When the `nodes` lane degraded the backend sends
 *  `total_signals: null` — we did not measure zero, we failed to measure.
 *  Returns null so callers render a gap instead of a confident "0". */
export function measuredTotal(data: FocusLanePayload | null,
                              field: 'total_signals' | 'total_countries'): number | null {
    if (!data?.summary) return null
    const v = data.summary[field]
    return typeof v === 'number' ? v : null
}

/** Copy for the slow state. Names the reason (the subject is heavy) rather
 *  than blaming the user's connection, and says what is happening. */
export const FOCUS_SLOW_MESSAGE = 'Measuring a heavy subject… this can take time'

/** Did anything at all come back? Used to decide whether the slow state can
 *  show partial content beneath its notice. */
export function hasAnyLiveLane(data: FocusLanePayload | null): boolean {
    if (!data) return false
    if (!data.lanes) return true
    return Object.values(data.lanes).some(s => s === 'live')
}

/** Every lane failed — the panel measured nothing. Distinct from "no data
 *  exists for this person", which is a live-but-empty result. */
export function allLanesDegraded(data: FocusLanePayload | null): boolean {
    if (!data?.lanes) return false
    const values = Object.values(data.lanes)
    return values.length > 0 && values.every(s => s !== 'live')
}
