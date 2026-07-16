/**
 * Marker hover card content (2026-07-12): a hazard triangle / conflict shape
 * must say what it IS before the click throws you onto an external page.
 */
import { describe, it, expect } from 'vitest'
import { markerHoverContent } from './EqualEarthMap'

describe('markerHoverContent', () => {
    it('disaster: names hazard type, magnitude, epicenter place, source + click hint', () => {
        const out = markerHoverContent('disaster', {
            dtype: 'earthquake',
            title: 'M 4.7 - northern Mid-Atlantic Ridge',
            magnitude: 4.7,
            alert: '',
            source: 'usgs',
            time: '2026-07-11T14:32:00Z',
            country: '',
        })
        expect(out.title).toBe('Earthquake')
        expect(out.meta).toContain('Magnitude 4.7')
        // USGS title prefix "M 4.7 - " stripped — place line = the epicenter,
        // which answers "why is there a dot in open ocean".
        expect(out.meta).toContain('northern Mid-Atlantic Ridge')
        expect(out.meta).toContain('Source: USGS')
        expect(out.hint).toBe('Click opens the USGS event page')
    })

    it('disaster: GDACS alert level shown when no magnitude', () => {
        const out = markerHoverContent('disaster', {
            dtype: 'cyclone',
            title: 'Tropical Cyclone FREDDY-26',
            magnitude: null,
            alert: 'orange',
            source: 'gdacs',
            time: '2026-07-10',
            country: 'MZ',
        })
        expect(out.title).toBe('Cyclone')
        expect(out.meta).toContain('ORANGE alert')
        expect(out.meta).toContain('Tropical Cyclone FREDDY-26')
        expect(out.meta.some(m => m.startsWith('Magnitude'))).toBe(false)
        expect(out.hint).toBe('Click opens the GDACS event page')
    })

    it('conflict: names the shape class (armed force / unrest / coercion)', () => {
        const battle = markerHoverContent('acled', {
            type: 'Fight with small arms and light weapons',
            place: 'Kharkiv', country: 'Ukraine', date: '2026-07-10', fatalities: 3,
        })
        expect(battle.title).toBe('Conflict event · Armed force')
        expect(battle.meta).toContain('Kharkiv, Ukraine')
        expect(battle.meta).toContain('3 reported killed')

        const unrest = markerHoverContent('acled', { type: 'Protest violently, riot', place: '', country: 'France', date: '', fatalities: 0 })
        expect(unrest.title).toBe('Conflict event · Unrest / repression')
        expect(unrest.meta).not.toContain('0 reported killed')

        const coercion = markerHoverContent('acled', { type: 'Impose blockade', place: '', country: '', date: '', fatalities: 0 })
        expect(coercion.title).toBe('Conflict event · Coercion / posture')
    })

    it('chokepoint: name + active state', () => {
        const out = markerHoverContent('chokepoint', { name: 'Strait of Hormuz', active: true })
        expect(out.title).toBe('Strait of Hormuz')
        expect(out.meta).toContain('Active vessel traffic')
    })

    it('anomaly: derived-signal receipt — multiplier, z, count, level, honest hint', () => {
        const out = markerHoverContent('anomaly', {
            country_code: 'AR', country_name: 'Argentina',
            multiplier: 2.63, zscore: 5.04, current_count: 4913, level: 'elevated',
        })
        expect(out.title).toBe('Baseline spike · Argentina')
        expect(out.meta).toContain('2.6× its own baseline volume')
        expect(out.meta).toContain('z-score 5.0')
        expect(out.meta).toContain('4,913 signals in the window')
        expect(out.meta).toContain('Level: elevated')
        expect(out.hint).toMatch(/Derived attention signal/)
        expect(out.hint).toMatch(/not a discrete event/)
    })

    it('anomaly: missing fields degrade to absence, never fabricate', () => {
        const out = markerHoverContent('anomaly', { country_code: 'DZ' })
        expect(out.title).toBe('Baseline spike · DZ')
        expect(out.meta).toEqual([])
    })
})
