import { describe, expect, it } from 'vitest'
import {
    REPLAY_ENDPOINT_CAP_DAYS,
    ARCHIVE_FLOOR_DAY,
    maxReplayDays,
    daysBackForPosition,
    positionForDaysBack,
    snapDaysBack,
    isoDayForDaysBack,
    farEdgeKind,
} from './scrubberScale'

// The scrubber IS time: one bar, whole history inside, log-scaled so the
// recent past is granular and the deep past compresses (Pedro, 2026-07-15).

describe('scrubber log scale — endpoints', () => {
    it('p=1 is NOW (0 days back) and p=0 is the full history', () => {
        expect(daysBackForPosition(1, 90)).toBe(0)
        expect(daysBackForPosition(0, 90)).toBe(90)
        expect(daysBackForPosition(0, 74)).toBe(74)
    })

    it('clamps out-of-range positions', () => {
        expect(daysBackForPosition(1.5, 90)).toBe(0)
        expect(daysBackForPosition(-0.2, 90)).toBe(90)
    })
})

describe('scrubber log scale — design target', () => {
    // DESIGN TARGET: the RIGHT half of the track covers roughly the last
    // 7-10 days (day-level granularity where news memory actually lives).
    it('the right half of the track spans ~7-10 days at the 90-day cap', () => {
        const mid = daysBackForPosition(0.5, 90)
        expect(mid).toBeGreaterThanOrEqual(7)
        expect(mid).toBeLessThanOrEqual(10)
    })

    it('holds the target at the current archive-floor span (~74 days)', () => {
        const mid = daysBackForPosition(0.5, 74)
        expect(mid).toBeGreaterThanOrEqual(7)
        expect(mid).toBeLessThanOrEqual(10)
    })

    it('is strictly monotonic: moving left goes further back', () => {
        let prev = daysBackForPosition(1, 90)
        for (let p = 0.95; p >= 0; p -= 0.05) {
            const d = daysBackForPosition(p, 90)
            expect(d).toBeGreaterThan(prev)
            prev = d
        }
    })
})

describe('scrubber log scale — inverse mapping', () => {
    it('positionForDaysBack round-trips through daysBackForPosition', () => {
        for (const d of [0, 1, 3, 7, 14, 30, 60, 90]) {
            const p = positionForDaysBack(d, 90)
            expect(p).toBeGreaterThanOrEqual(0)
            expect(p).toBeLessThanOrEqual(1)
            expect(daysBackForPosition(p, 90)).toBeCloseTo(d, 6)
        }
    })

    it('maps NOW to the right edge and the floor to the left edge', () => {
        expect(positionForDaysBack(0, 90)).toBe(1)
        expect(positionForDaysBack(90, 90)).toBe(0)
    })
})

describe('snapDaysBack — whole days except the live edge', () => {
    it('snaps to integer days', () => {
        for (const p of [0.1, 0.33, 0.5, 0.77, 0.9]) {
            const d = snapDaysBack(p, 90)
            expect(Number.isInteger(d)).toBe(true)
        }
    })

    it('the live edge snaps to 0 (NOW)', () => {
        expect(snapDaysBack(1, 90)).toBe(0)
        expect(snapDaysBack(0.999, 90)).toBe(0)
    })

    it('the far edge snaps to the full span', () => {
        expect(snapDaysBack(0, 90)).toBe(90)
    })
})

describe('maxReplayDays — honest data bound', () => {
    it('is limited by the archive floor while the floor is nearer than the endpoint cap', () => {
        // Probed 2026-07-16: replay serves data from 2026-05-03 (archive
        // daily table start) — 74 whole days back from 2026-07-16.
        const now = new Date('2026-07-16T12:00:00Z')
        expect(maxReplayDays(now)).toBe(74)
        expect(farEdgeKind(now)).toBe('archive-floor')
    })

    it('is capped at the endpoint bound (le=90, probed 422 above) once the floor recedes', () => {
        const now = new Date('2026-09-01T12:00:00Z')
        expect(maxReplayDays(now)).toBe(REPLAY_ENDPOINT_CAP_DAYS)
        expect(farEdgeKind(now)).toBe('endpoint-cap')
    })

    it('exposes the probed constants', () => {
        expect(REPLAY_ENDPOINT_CAP_DAYS).toBe(90)
        expect(ARCHIVE_FLOOR_DAY).toBe('2026-05-03')
    })
})

describe('isoDayForDaysBack', () => {
    it('maps days-back to the real UTC calendar day', () => {
        const now = new Date('2026-07-16T12:00:00Z')
        expect(isoDayForDaysBack(0, now)).toBe('2026-07-16')
        expect(isoDayForDaysBack(1, now)).toBe('2026-07-15')
        expect(isoDayForDaysBack(74, now)).toBe('2026-05-03')
    })
})
