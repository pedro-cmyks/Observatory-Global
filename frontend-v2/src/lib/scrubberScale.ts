// THE SCRUBBER IS TIME (Pedro, 2026-07-15): one bar with the WHOLE replayable
// history inside — no extra controls. The mapping is NON-LINEAR (exponential)
// so the recent past is granular (the right ~half of the track covers the
// last ~7-10 days at day-level) and the deep past compresses toward the left
// edge. This module is the pure scale; the App scrubber consumes it.
//
// Follow-up: the UNIVERSE scrubber still runs its own linear 30d scale (its
// data is per-topic 30d tracks) — unify it onto this module when the topic
// track history deepens.

/** Endpoint bound, probed 2026-07-16: GET /api/v2/map/replay?days=120 → 422
 *  ("less_than_equal", le=90). days=90 → 200. */
export const REPLAY_ENDPOINT_CAP_DAYS = 90

/** Oldest day the replay actually serves, probed 2026-07-16: the payload's
 *  first day is 2026-05-03 — the start of the archive-backed
 *  historical_topic_country_daily table. Days before this would replay as
 *  silence dressed as data; the scrubber stops here honestly. */
export const ARCHIVE_FLOOR_DAY = '2026-05-03'

/** Curve steepness. k=4.5 puts p=0.5 at ~8.6 days back for a 90-day span
 *  (and ~7.1 for a 74-day span) — inside the 7-10 day design target asserted
 *  by the tests. */
export const SCRUBBER_K = 4.5

const MS_PER_DAY = 86_400_000

function utcDayNumber(d: Date): number {
    return Math.floor(d.getTime() / MS_PER_DAY)
}

/** How many whole days the scrubber can reach back: the archive floor while
 *  it is nearer than the endpoint cap, the endpoint cap afterwards. */
export function maxReplayDays(now: Date = new Date()): number {
    const floorDaysBack = utcDayNumber(now) - utcDayNumber(new Date(`${ARCHIVE_FLOOR_DAY}T00:00:00Z`))
    return Math.max(1, Math.min(REPLAY_ENDPOINT_CAP_DAYS, floorDaysBack))
}

/** What binds the far-left edge right now — drives the honest edge label
 *  ("May 3 · archive floor" vs the 90-day replay cap). */
export function farEdgeKind(now: Date = new Date()): 'archive-floor' | 'endpoint-cap' {
    const floorDaysBack = utcDayNumber(now) - utcDayNumber(new Date(`${ARCHIVE_FLOOR_DAY}T00:00:00Z`))
    return floorDaysBack <= REPLAY_ENDPOINT_CAP_DAYS ? 'archive-floor' : 'endpoint-cap'
}

/** Position p ∈ [0,1] (1 = NOW, right edge) → continuous days back.
 *  daysBack = (e^{k(1-p)} - 1) / (e^k - 1) * maxDays. */
export function daysBackForPosition(p: number, maxDays: number): number {
    const clamped = Math.min(1, Math.max(0, p))
    const k = SCRUBBER_K
    return ((Math.exp(k * (1 - clamped)) - 1) / (Math.exp(k) - 1)) * maxDays
}

/** Inverse mapping — where a given days-back sits on the track (for thumb
 *  placement and day labels). */
export function positionForDaysBack(daysBack: number, maxDays: number): number {
    const d = Math.min(maxDays, Math.max(0, daysBack))
    const k = SCRUBBER_K
    const p = 1 - Math.log(1 + (d / maxDays) * (Math.exp(k) - 1)) / k
    return Math.min(1, Math.max(0, p))
}

/** Snap to whole days; the live edge (rounds to 0) means NOW. */
export function snapDaysBack(p: number, maxDays: number): number {
    return Math.round(daysBackForPosition(p, maxDays))
}

/** The real UTC calendar day for a days-back offset. */
export function isoDayForDaysBack(daysBack: number, now: Date = new Date()): string {
    return new Date((utcDayNumber(now) - daysBack) * MS_PER_DAY).toISOString().slice(0, 10)
}
