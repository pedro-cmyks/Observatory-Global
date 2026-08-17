// Last-read mark (spec §7/§8, 2026-08-17). Epoch-ms integers, NEVER ISO
// strings — Postgres re-serialization made lexicographic ISO compare a real
// bug in accounts-v1. A null previous mark is a first visit and is reported
// as null, never as "0 hours ago".
export const LAST_READ_KEY = 'atlas.reader.lastread.v1'

export function touchLastRead(nowMs: number): number | null {
    let prev: number | null = null
    try {
        const raw = localStorage.getItem(LAST_READ_KEY)
        if (raw != null) {
            const n = Number(raw)
            prev = Number.isFinite(n) && n > 0 ? n : null
        }
        localStorage.setItem(LAST_READ_KEY, String(nowMs))
    } catch { /* storage unavailable → behaves as first visit */ }
    return prev
}

export function hoursSince(prevMs: number | null, nowMs: number): number | null {
    if (prevMs == null) return null
    return Math.round(((nowMs - prevMs) / 3_600_000) * 10) / 10
}
