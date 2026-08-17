// The day anatomy (spec §3, 2026-08-17): one lead, then fixed layers —
// near → changed → odd → world. Tranche 2 builds the LAYERS only (no lead,
// no profile). Two structural rules live here, not in the component:
//   * an empty segment is ABSENT — never rendered hollow, never apologized;
//   * `world` is ALWAYS present: it is the shared edition, and its
//     unconditional presence is the §6.2 firewall (personalization adds
//     segments, never subtracts from the shared edition).
export const READER_ANATOMY = true // kill switch: false → pre-anatomy Brief render

export type SegmentId = 'near' | 'changed' | 'odd' | 'world'

export interface DaySegment {
    id: SegmentId
    count: number
}

export interface DayCounts {
    nearCount: number
    changedCount: number
    oddCount: number
}

export function composeDayAnatomy(c: DayCounts): DaySegment[] {
    const out: DaySegment[] = []
    if (c.nearCount > 0) out.push({ id: 'near', count: c.nearCount })
    if (c.changedCount > 0) out.push({ id: 'changed', count: c.changedCount })
    if (c.oddCount > 0) out.push({ id: 'odd', count: c.oddCount })
    out.push({ id: 'world', count: 0 }) // always — see header comment
    return out
}

export interface SignedThread {
    thread_id: string
    label: string
    temporal_signature: string | null
}

// "Changed" per the temporal signature the engine already measures (mig 085).
// recurrent/continuous are the steady state, not a change; null is unmeasured.
export function changedRowsFromThreads<T extends SignedThread>(threads: T[]): T[] {
    return threads.filter(t =>
        t.temporal_signature === 'new' || t.temporal_signature === 'resurrected')
}
