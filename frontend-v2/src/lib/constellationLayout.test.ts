import { describe, expect, it } from 'vitest'
import {
    ignitionGlow,
    placeConstellation,
    presenceAlphaField,
    radiusFraction,
    RADIUS_DOMAIN_MAX,
    type ConstellationGeom,
} from './constellationLayout'
import { seedAngle, type OrbitalBody } from './orbitalLayout'

const T0 = Date.parse('2026-06-26T12:00:00Z')
const HOUR = 3_600_000

function body(overrides: Partial<OrbitalBody> = {}): OrbitalBody {
    return {
        id: 'entity-test',
        label: 'test',
        type: 'person',
        n: 3,
        dist: 0.04,
        first_seen: '2026-06-26T12:00:00Z',
        last_seen: '2026-06-28T12:00:00Z',
        timestamps: ['2026-06-26T12:00:00Z', '2026-06-27T12:00:00Z', '2026-06-28T12:00:00Z'],
        ...overrides,
    }
}

const WINDOW = { start: '2026-06-20T00:00:00Z', end: '2026-06-30T00:00:00Z' }
const GEOM: ConstellationGeom = { cx: 280, cy: 190, rMin: 60, rMax: 200, ex: 1, ey: 1 }

describe('radiusFraction — FIXED cosine domain (cross-thread comparable, fixes U3)', () => {
    it('maps absolute distance onto [0,1] on a fixed domain, clamps past it', () => {
        expect(radiusFraction(0)).toBe(0)
        expect(radiusFraction(RADIUS_DOMAIN_MAX / 2)).toBeCloseTo(0.5)
        expect(radiusFraction(RADIUS_DOMAIN_MAX)).toBe(1)
        expect(radiusFraction(RADIUS_DOMAIN_MAX * 2)).toBe(1) // clamp
        expect(radiusFraction(-0.1)).toBe(0)                  // clamp
    })

    it('is thread-INDEPENDENT — the same distance maps identically regardless of neighbors', () => {
        // the orbit made this vary per-thread (min-max); the fixed domain does not
        expect(radiusFraction(0.05)).toBe(radiusFraction(0.05))
        expect(radiusFraction(0.05)).toBeCloseTo(0.25)
    })
})

describe('presenceAlphaField — decay unified with the universe field (72h / 0.14 floor)', () => {
    it('is 0 before entry, 1 at activity, decays to the field floor 0.14 (not the orbit 0.22)', () => {
        const b = body()
        expect(presenceAlphaField(b, T0 - HOUR)).toBe(0)
        expect(presenceAlphaField(b, T0)).toBe(1)
        const lastActivity = Date.parse(b.timestamps[2])
        // one 72h half-life after last activity → ~0.5 (a 36h model would be ~0.25)
        expect(presenceAlphaField(b, lastActivity + 72 * HOUR)).toBeCloseTo(0.5, 2)
        // long after → floored at the field's 0.14, never the orbit's 0.22
        expect(presenceAlphaField(b, lastActivity + 1000 * HOUR)).toBeCloseTo(0.14, 5)
    })
})

describe('ignitionGlow — re-codes the sweep as cumulative-activity luminosity', () => {
    it('is 0 before any interaction, grows to 1 once the whole story is in, clamps', () => {
        const b = body()
        expect(ignitionGlow(b, T0 - HOUR)).toBe(0)            // before birth
        expect(ignitionGlow(b, T0 + HOUR)).toBeCloseTo(1 / 3) // 1 of 3 landed
        expect(ignitionGlow(b, T0 + 49 * HOUR)).toBe(1)       // all 3 landed
        expect(ignitionGlow(b, T0 + 500 * HOUR)).toBe(1)      // clamps at 1
    })

    it('is 0 when a body has no timestamps (honest, no divide-by-zero)', () => {
        expect(ignitionGlow(body({ timestamps: [] }), T0)).toBe(0)
    })
})

describe('placeConstellation — fixed shape, radius = absolute distance, co-occ satellites', () => {
    it('radius grows with absolute distance to the centroid (comparable, not min-max)', () => {
        const near = body({ id: 'a', dist: 0.02 })
        const far = body({ id: 'b', dist: 0.16 })
        const placed = placeConstellation([near, far], T0, GEOM, WINDOW)
        const pa = placed.find(p => p.body.id === 'a')!
        const pb = placed.find(p => p.body.id === 'b')!
        const rA = Math.hypot(pa.x - GEOM.cx, pa.y - GEOM.cy)
        const rB = Math.hypot(pb.x - GEOM.cx, pb.y - GEOM.cy)
        expect(rA).toBeLessThan(rB)
        // fixed domain: a 0.02 star sits near rMin, a 0.16 star near rMax — the
        // SAME as it would in any other thread (the U3 comparability guarantee)
        expect(pa.distFraction).toBeCloseTo(0.1)
        expect(pb.distFraction).toBeCloseTo(0.8)
    })

    it('the shape is FIXED — a star sits at the same position across scrub time', () => {
        const b = body({ id: 'a' })
        const early = placeConstellation([b], T0, GEOM, WINDOW)[0]
        const late = placeConstellation([b], T0 + 60 * HOUR, GEOM, WINDOW)[0]
        expect(late.x).toBe(early.x)
        expect(late.y).toBe(early.y)
        expect(late.ignition).toBeGreaterThan(early.ignition)
    })

    it('angle is the deterministic seed only (no interaction sweep)', () => {
        const b = body({ id: 'entity-x', dist: 0.10 })
        const placed = placeConstellation([b], T0, GEOM, WINDOW)[0]
        const a = seedAngle('entity-x')
        const r = GEOM.rMin + 0.5 * (GEOM.rMax - GEOM.rMin) // dist 0.10 → fraction 0.5
        expect(placed.x).toBeCloseTo(GEOM.cx + r * Math.cos(a), 5)
        expect(placed.y).toBeCloseTo(GEOM.cy + r * Math.sin(a), 5)
    })

    it('a moon carries its parent id (drawn as a co-occurrence edge, not a sub-orbit)', () => {
        const parent = body({ id: 'entity-big', n: 20, dist: 0.03 })
        const moon = body({ id: 'entity-small', n: 2, dist: 0.12, moon_of: 'entity-big', moon_overlap: 0.9 })
        const placed = placeConstellation([parent, moon], T0, GEOM, WINDOW)
        const pm = placed.find(p => p.body.id === 'entity-small')!
        expect(pm.moon).toBe(true)
        expect(pm.moonParentId).toBe('entity-big')
        // the moon is placed by its OWN distance (0.12), NOT beside its parent —
        // its distance is no longer discarded (fixes the orbit's fake sub-orbit)
        expect(pm.distFraction).toBeCloseTo(0.6)
    })

    it('a non-moon has a null parent id', () => {
        const p = placeConstellation([body({ id: 'a' })], T0, GEOM, WINDOW)[0]
        expect(p.moon).toBe(false)
        expect(p.moonParentId).toBe(null)
    })
})
