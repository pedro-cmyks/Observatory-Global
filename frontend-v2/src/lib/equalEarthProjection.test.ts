import { describe, it, expect } from 'vitest'
import { createEqualEarth, clampScale, IDENTITY_TRANSFORM } from './equalEarthProjection'

const W = 800
const H = 400

describe('createEqualEarth (cylindrical equal-area strip)', () => {
    const ee = createEqualEarth(W, H)

    it('projects [0,0] near the horizontal center (prime meridian centered)', () => {
        const p = ee.project([0, 0])
        expect(p).not.toBeNull()
        expect(Math.abs(p![0] - W / 2)).toBeLessThan(2)
    })

    it('fills the height pole-to-pole (worldHeight ~= panel height)', () => {
        expect(Math.abs(ee.worldHeight - H)).toBeLessThan(2)
    })

    it('is a wide strip: worldWidth exceeds the panel width', () => {
        // Cylindrical equal-area at parallel 30 is ~2.36:1 — fit to a square-ish
        // box by height, the width overflows (the strip the caller wraps).
        expect(ee.worldWidth).toBeGreaterThan(W)
    })

    it('project/invert round-trips for several points', () => {
        const points: [number, number][] = [
            [0, 0],
            [-74, 4.6], // Bogotá
            [139.7, 35.7], // Tokyo
            [37.6, 55.7], // Moscow
            [-0.1, 51.5], // London
        ]
        for (const ll of points) {
            const screen = ee.toScreen(ll)
            expect(screen).not.toBeNull()
            const back = ee.toLngLat(screen!)
            expect(back).not.toBeNull()
            expect(back![0]).toBeCloseTo(ll[0], 1)
            expect(back![1]).toBeCloseTo(ll[1], 1)
        }
    })

    it('poles sit at the top/bottom edges of the box', () => {
        const north = ee.project([0, 90])
        const south = ee.project([0, -90])
        expect(north).not.toBeNull()
        expect(south).not.toBeNull()
        expect(north![1]).toBeLessThan(2)
        expect(south![1]).toBeGreaterThan(H - 2)
    })

    it('applies the pan/zoom transform in toScreen', () => {
        const base = ee.project([0, 0])!
        const t = { k: 2, x: 50, y: 30 }
        const screen = ee.toScreen([0, 0], t)!
        expect(screen[0]).toBeCloseTo(base[0] * 2 + 50, 5)
        expect(screen[1]).toBeCloseTo(base[1] * 2 + 30, 5)
    })

    it('toLngLat undoes the transform (round-trip under zoom)', () => {
        const t = { k: 3.5, x: -120, y: 44 }
        const ll: [number, number] = [10, -20]
        const screen = ee.toScreen(ll, t)!
        const back = ee.toLngLat(screen, t)!
        expect(back[0]).toBeCloseTo(ll[0], 1)
        expect(back[1]).toBeCloseTo(ll[1], 1)
    })

    it('produces an SVG path string for a polygon feature', () => {
        const feature = {
            type: 'Feature',
            properties: {},
            geometry: {
                type: 'Polygon',
                coordinates: [[[-10, -10], [10, -10], [10, 10], [-10, 10], [-10, -10]]],
            },
        }
        const d = ee.pathString(feature)
        expect(d).toBeTruthy()
        expect(d!.startsWith('M')).toBe(true)
    })
})

describe('clampScale', () => {
    it('clamps below min and above max', () => {
        expect(clampScale(0.2)).toBe(1)
        expect(clampScale(99)).toBe(12)
        expect(clampScale(4)).toBe(4)
    })
})

describe('IDENTITY_TRANSFORM', () => {
    it('is k=1 at origin', () => {
        expect(IDENTITY_TRANSFORM).toEqual({ k: 1, x: 0, y: 0 })
    })
})
