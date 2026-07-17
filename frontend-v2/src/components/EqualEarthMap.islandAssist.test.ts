/**
 * Tiny-island click/hover assist (fix round 2026-07-17, item 7): country paths
 * down to 1.4×2.9px at world zoom were untargetable — no hover, no click. A
 * click/hover that misses every polygon now searches SMALL countries whose
 * bbox sits within ~ISLAND_NEAR_PX of the pointer and picks the nearest.
 * Marker-vs-polygon priority is unchanged: the assist only runs on true
 * misses (markers stopPropagation in capture; real polygon hits handle
 * themselves).
 */
import { describe, it, expect } from 'vitest'
import {
    pickNearestSmallCountry,
    ISLAND_NEAR_PX,
    ISLAND_SMALL_PX,
    type IslandCandidate,
} from './EqualEarthMap'

// Base (k=1) bboxes. malta ~1.4×1 base px; barbados ~1×1; france is huge.
const malta: IslandCandidate = { iso: 'MT', name: 'Malta', x0: 100, y0: 50, x1: 101.4, y1: 51 }
const barbados: IslandCandidate = { iso: 'BB', name: 'Barbados', x0: 108, y0: 50, x1: 109, y1: 51 }
const france: IslandCandidate = { iso: 'FR', name: 'France', x0: 90, y0: 30, x1: 140, y1: 70 }

describe('pickNearestSmallCountry', () => {
    it('picks a tiny country when the pointer is within the near-tolerance of its bbox', () => {
        // 3px right of Malta's bbox at k=1 → within ISLAND_NEAR_PX (5)
        const hit = pickNearestSmallCountry([malta, france], { x: 104.4, y: 50.5 }, 1)
        expect(hit?.iso).toBe('MT')
    })

    it('a pointer INSIDE a tiny bbox is distance 0 (the sub-pixel fill case)', () => {
        const hit = pickNearestSmallCountry([malta, barbados], { x: 100.7, y: 50.5 }, 1)
        expect(hit?.iso).toBe('MT')
    })

    it('picks the NEAREST small candidate when several are in range', () => {
        // Pointer between the two but closer to Barbados' bbox edge.
        const hit = pickNearestSmallCountry([malta, barbados], { x: 106, y: 50.5 }, 1)
        expect(hit?.iso).toBe('BB')
    })

    it('never assists LARGE countries — a miss near a coastline stays a miss', () => {
        // 2px from France's bbox, but France is far bigger than ISLAND_SMALL_PX.
        const hit = pickNearestSmallCountry([france], { x: 142, y: 50 }, 1)
        expect(hit).toBeNull()
    })

    it('returns null when nothing is within the tolerance', () => {
        const hit = pickNearestSmallCountry([malta, barbados], { x: 200, y: 200 }, 1)
        expect(hit).toBeNull()
    })

    it('smallness is measured in SCREEN px — a zoomed-in island graduates out of the assist', () => {
        // At k=12 Malta's bbox is ~17×12 screen px (> ISLAND_SMALL_PX): the real
        // path is now clickable, so the assist steps aside.
        const hit = pickNearestSmallCountry([malta], { x: 101.5, y: 50.5 }, 12)
        expect(hit).toBeNull()
    })

    it('the near-tolerance is in SCREEN px too (base distance shrinks with k)', () => {
        // 4 base px right of Malta at k=2 → 8 screen px - hmm 4*2=8 > 5 → miss;
        // 2 base px → 4 screen px → hit.
        expect(pickNearestSmallCountry([malta], { x: 105.4, y: 50.5 }, 2)).toBeNull()
        expect(pickNearestSmallCountry([malta], { x: 103.4, y: 50.5 }, 2)?.iso).toBe('MT')
    })

    it('constants: assist reaches ~5px, small means under ~12px drawn size', () => {
        expect(ISLAND_NEAR_PX).toBe(5)
        expect(ISLAND_SMALL_PX).toBe(12)
    })
})
