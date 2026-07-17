/**
 * Map click reliability (council 2026-07-17, P1-8 / wish 14):
 *  - country clicks died silently at world zoom (any 1px jitter during the
 *    click marked the gesture as a pan and swallowed the select)
 *  - a click near Brazil opened a Cape Town event card (marker hit-test used
 *    a fixed generous screen tolerance and array order, not distance)
 * These pure helpers freeze the fixed behavior.
 */
import { describe, it, expect } from 'vitest'
import { markerHitTolerance, pickMarkerHit, gestureMoved, flyAnchor } from './EqualEarthMap'

describe('markerHitTolerance', () => {
    it('tightens to near the drawn glyph at world zoom (k < 2)', () => {
        // drawn radii: acled ≤5.5, disaster ≤8, chokepoint ≤9
        expect(markerHitTolerance('acled', 1)).toBe(8)
        expect(markerHitTolerance('disaster', 1)).toBe(10.5)
        expect(markerHitTolerance('chokepoint', 1)).toBe(11.5)
    })

    it('stays generous (finger-friendly) once zoomed in', () => {
        expect(markerHitTolerance('acled', 4)).toBe(12)
        expect(markerHitTolerance('disaster', 4)).toBe(14.5)
        expect(markerHitTolerance('chokepoint', 4)).toBe(15.5)
    })
})

describe('pickMarkerHit', () => {
    it('nearest marker wins regardless of layer priority order', () => {
        const hit = pickMarkerHit([
            { kind: 'acled', dist: 7, index: 0 },
            { kind: 'chokepoint', dist: 3, index: 1 },
        ], 1)
        expect(hit?.kind).toBe('chokepoint')
    })

    it('rejects far markers at world zoom so the country polygon wins (Cape Town-from-Brazil class)', () => {
        expect(pickMarkerHit([{ kind: 'acled', dist: 10, index: 0 }], 1)).toBeNull()
    })

    it('the same distance hits once zoomed in (tolerance grows with k)', () => {
        const hit = pickMarkerHit([{ kind: 'acled', dist: 10, index: 0 }], 4)
        expect(hit?.kind).toBe('acled')
    })

    it('empty candidates → null', () => {
        expect(pickMarkerHit([], 3)).toBeNull()
    })
})

describe('gestureMoved', () => {
    it('sub-slop jitter during a click is NOT a pan (the silent dead-click fix)', () => {
        expect(gestureMoved({ x: 0, y: 0, k: 1 }, { x: 3, y: 2, k: 1 })).toBe(false)
    })

    it('a real drag is a pan', () => {
        expect(gestureMoved({ x: 0, y: 0, k: 1 }, { x: 14, y: 0, k: 1 })).toBe(true)
    })

    it('any zoom change is a gesture', () => {
        expect(gestureMoved({ x: 0, y: 0, k: 1 }, { x: 0, y: 0, k: 1.2 })).toBe(true)
    })
})

describe('flyAnchor', () => {
    // Square ring helper (lon/lat degrees), wound so d3-geo's spherical
    // convention reads the SMALL area as the interior (matches the winding of
    // the production countries.geojson, which renders correctly today).
    const ring = (cx: number, cy: number, half: number): [number, number][] => [
        [cx - half, cy - half], [cx - half, cy + half],
        [cx + half, cy + half], [cx + half, cy - half],
        [cx - half, cy - half],
    ]

    it('MultiPolygon: anchors on the LARGEST landmass, not the average of scattered territories (Mongolia-bug class)', () => {
        // "France": big mainland near (2E,47N) + small far territory near (-53W,4N).
        const geom = {
            type: 'MultiPolygon',
            coordinates: [
                [ring(2, 47, 4)],     // mainland — the big polygon
                [ring(-53, 4, 1)],    // faraway territory
            ],
        }
        const [lon, lat] = flyAnchor(geom)!
        expect(Math.abs(lon - 2)).toBeLessThan(1)
        expect(Math.abs(lat - 47)).toBeLessThan(1)
    })

    it('plain Polygon: centroid of the shape', () => {
        const geom = { type: 'Polygon', coordinates: [ring(10, 20, 3)] }
        const [lon, lat] = flyAnchor(geom)!
        expect(Math.abs(lon - 10)).toBeLessThan(0.5)
        expect(Math.abs(lat - 20)).toBeLessThan(0.5)
    })

    it('degenerate geometry → null (fly is skipped, never a wild jump)', () => {
        expect(flyAnchor({ type: 'MultiPolygon', coordinates: [] })).toBeNull()
    })
})
