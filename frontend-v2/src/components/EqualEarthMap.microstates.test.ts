/**
 * Round-2 item 2 — polygon-less microstates (Malta class).
 *
 * The Natural Earth 110m basemap has NO feature for MT/SG/BB and the rest of
 * the microstates Atlas serves. Before this fix the island assist had nothing
 * to target and flyCountry silently no-op'd (searching "Malta" left the
 * camera over Yemen). Now: MICRO_CENTROIDS gives each an [lon,lat]; the
 * assist treats them as zero-size bboxes; flyTarget falls back to the
 * centroid.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import {
    pickNearestSmallCountry,
    featureIso,
    flyTarget,
    type IslandCandidate,
} from './EqualEarthMap'
import { MICRO_CENTROIDS } from '../lib/microstates'
import { COUNTRY_NAMES } from '../lib/countryNames'

const geojson = JSON.parse(
    readFileSync(join(__dirname, '../../public/data/countries.geojson'), 'utf8'),
) as { features: Array<{ geometry: { type: string; coordinates: unknown }; properties: Record<string, unknown> }> }

describe('MICRO_CENTROIDS (audit against the served basemap)', () => {
    const polygonIsos = new Set(geojson.features.map(f => featureIso(f.properties)))

    it('covers at least the repro trio MT / SG / BB', () => {
        for (const iso of ['MT', 'SG', 'BB']) {
            expect(MICRO_CENTROIDS[iso], `${iso} missing`).toBeDefined()
        }
    })

    it('every entry is a code the basemap genuinely lacks a polygon for', () => {
        for (const iso of Object.keys(MICRO_CENTROIDS)) {
            expect(polygonIsos.has(iso), `${iso} HAS a polygon — remove it from MICRO_CENTROIDS`).toBe(false)
        }
    })

    it('every entry is a code Atlas serves (COUNTRY_NAMES) with valid coordinates', () => {
        for (const [iso, [lon, lat]] of Object.entries(MICRO_CENTROIDS)) {
            expect(COUNTRY_NAMES[iso], `${iso} not in COUNTRY_NAMES`).toBeDefined()
            expect(lon).toBeGreaterThanOrEqual(-180)
            expect(lon).toBeLessThanOrEqual(180)
            expect(lat).toBeGreaterThanOrEqual(-90)
            expect(lat).toBeLessThanOrEqual(90)
        }
    })

    it('signals-bearing microstates from /heat/countries are covered (BH/MV/SC class)', () => {
        for (const iso of ['BH', 'MV', 'SC', 'HK', 'VC', 'CV', 'ST', 'WS', 'PM', 'RE']) {
            expect(MICRO_CENTROIDS[iso], `${iso} missing`).toBeDefined()
        }
    })
})

describe('featureIso', () => {
    it('uses a valid ISO_A2 as-is', () => {
        expect(featureIso({ ISO_A2: 'FR', ISO_A2_EH: 'FR' })).toBe('FR')
    })
    it("falls back to ISO_A2_EH for Natural Earth's -99 (Kosovo) and compounds (Taiwan CN-TW)", () => {
        expect(featureIso({ ISO_A2: '-99', ISO_A2_EH: 'XK' })).toBe('XK')
        expect(featureIso({ ISO_A2: 'CN-TW', ISO_A2_EH: 'TW' })).toBe('TW')
    })
    it('returns -99 when neither field is usable (N. Cyprus / Somaliland)', () => {
        expect(featureIso({ ISO_A2: '-99', ISO_A2_EH: '-99' })).toBe('-99')
    })
    it('Taiwan and Kosovo therefore have REAL polygons in the served basemap', () => {
        const isos = new Set(geojson.features.map(f => featureIso(f.properties)))
        expect(isos.has('TW')).toBe(true)
        expect(isos.has('XK')).toBe(true)
    })
})

describe('zero-size bbox assist (microstate hover/click)', () => {
    const malta: IslandCandidate = { iso: 'MT', name: 'Malta', x0: 100, y0: 50, x1: 100, y1: 50 }

    it('hits within the 5px tolerance at world zoom', () => {
        expect(pickNearestSmallCountry([malta], { x: 104, y: 50 }, 1)?.iso).toBe('MT')
        expect(pickNearestSmallCountry([malta], { x: 106, y: 50 }, 1)).toBeNull()
    })

    it('a zero-size bbox never graduates out of the assist (no polygon ever takes over)', () => {
        // 0.3 base px away at k=12 → 3.6 screen px, still within tolerance.
        expect(pickNearestSmallCountry([malta], { x: 100.3, y: 50 }, 12)?.iso).toBe('MT')
    })
})

describe('flyTarget (centroid fallback — the "Malta search left the camera over Yemen" repro)', () => {
    const franceFeature = {
        // Spherical winding (d3-geo right-hand rule): exterior ring runs CCW.
        geometry: { type: 'Polygon', coordinates: [[[0, 44], [0, 48], [4, 48], [4, 44], [0, 44]]] },
        properties: { ISO_A2: 'FR', ISO_A2_EH: 'FR' },
    }

    it('polygon-less microstate → its MICRO_CENTROIDS entry', () => {
        expect(flyTarget([franceFeature], 'MT')).toEqual(MICRO_CENTROIDS.MT)
        expect(flyTarget([], 'SG')).toEqual(MICRO_CENTROIDS.SG)
    })

    it('a real polygon wins over any table entry', () => {
        const c = flyTarget([franceFeature], 'FR')
        expect(c).not.toBeNull()
        expect(c![0]).toBeGreaterThan(-1)
        expect(c![0]).toBeLessThan(5)
        expect(c![1]).toBeGreaterThan(43)
        expect(c![1]).toBeLessThan(49)
    })

    it('unknown code → null (skip the fly, never a bogus jump)', () => {
        expect(flyTarget([franceFeature], 'ZZ')).toBeNull()
    })
})
