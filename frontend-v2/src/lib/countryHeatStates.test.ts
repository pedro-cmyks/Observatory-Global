import { describe, it, expect } from 'vitest'
import {
    computeCountryHeatStates,
    heatFillColor,
    glowWidth,
    type CountryHeatInput,
} from './countryHeatStates'

const base = (over: Partial<CountryHeatInput> = {}): CountryHeatInput => ({
    enhancedNodes: [
        { id: 'US', signalCount: 1000 },
        { id: 'CO', signalCount: 50 },
        { id: 'LB', signalCount: 3 },
    ],
    heatComposite: new Map(),
    visibleFlows: [],
    selectedCountryCode: null,
    entityFocus: false,
    ...over,
})

describe('computeCountryHeatStates', () => {
    it('no focus, no composite → falls back to volume intensity as heat', () => {
        const s = computeCountryHeatStates(base())
        expect(s.get('US')!.heat).toBeCloseTo(s.get('US')!.intensity, 5)
        // US has most volume → highest intensity
        expect(s.get('US')!.intensity).toBeGreaterThan(s.get('CO')!.intensity)
    })

    it('no focus WITH composite → heat is the composite, not volume rank', () => {
        const s = computeCountryHeatStates(base({
            heatComposite: new Map([['LB', 0.9], ['US', 0.2]]),
        }))
        expect(s.get('LB')!.heat).toBe(0.9)
        expect(s.get('US')!.heat).toBe(0.2)
        // a node absent from composite is not hot
        expect(s.get('CO')!.heat).toBe(0)
    })

    it('composite lights a country OUTSIDE the top nodes (#231)', () => {
        const s = computeCountryHeatStates(base({
            heatComposite: new Map([['GZ', 0.7]]),
        }))
        expect(s.get('GZ')).toEqual({ heat: 0.7, intensity: 0.15 })
    })

    it('country focus → focused=1.0, flow partner weighted, unrelated=0', () => {
        const s = computeCountryHeatStates(base({
            selectedCountryCode: 'US',
            visibleFlows: [{ sourceCountry: 'US', targetCountry: 'CO', strength: 10 }],
        }))
        expect(s.get('US')!.heat).toBe(1.0)
        expect(s.get('CO')!.heat).toBeCloseTo(0.25 + 0.75 * 1, 5)
        expect(s.get('LB')!.heat).toBe(0)
    })

    it('country focus lights a partner outside the node set', () => {
        const s = computeCountryHeatStates(base({
            selectedCountryCode: 'US',
            visibleFlows: [{ sourceCountry: 'US', targetCountry: 'XX', strength: 5 }],
        }))
        expect(s.get('XX')).toEqual({ heat: 0.25 + 0.75, intensity: 0.15 })
    })

    it('entity focus → heat = volume intensity', () => {
        const s = computeCountryHeatStates(base({
            entityFocus: true,
            heatComposite: new Map([['US', 0.1]]), // ignored under entity focus
        }))
        expect(s.get('US')!.heat).toBeCloseTo(s.get('US')!.intensity, 5)
    })

    it('empty nodes → empty map', () => {
        expect(computeCountryHeatStates(base({ enhancedNodes: [] })).size).toBe(0)
    })
})

describe('heatFillColor', () => {
    it('transparent below the floor, hot near 1', () => {
        expect(heatFillColor(0)).toBe('rgba(0, 0, 0, 0.000)')
        expect(heatFillColor(1)).toContain('242')
    })
})

describe('glowWidth', () => {
    it('zero at 0, max at 1, interpolates between', () => {
        expect(glowWidth(0)).toBe(0)
        expect(glowWidth(1)).toBe(10)
        expect(glowWidth(0.5)).toBeCloseTo(6, 5)
    })
})
