// NARRATIVE BIOGRAPHY spine layout (BUILD-B, 2026-07-18) — pure geometry over
// the theme-lineage-v0 weeks array. Honesty rules under test: time is the
// LITERAL axis (a missing week widens the spacing), drift is the MEASURED
// cosine (classified for style, number preserved), candidate stitches are
// flagged never hidden, gaps produce no fabricated node.
import { describe, it, expect } from 'vitest'
import { buildLineageSpine, normalizeEraLabel } from './lineageSpine'
import type { LineageWeek } from './lineage'

const era = (week: string, over: Partial<LineageWeek> = {}): LineageWeek => ({
    week,
    tier: 'archive',
    label: 'Venezuela Earthquake',
    n_signals: 100,
    n_units: 2,
    countries: ['VE'],
    drift_cos_prev: null,
    candidate: false,
    ...over,
})

describe('buildLineageSpine', () => {
    it('is absent (hasSpine=false) for empty and single-week input', () => {
        expect(buildLineageSpine([]).hasSpine).toBe(false)
        expect(buildLineageSpine([era('2026-06-01')]).hasSpine).toBe(false)
        // a gap entry is not a present era — still no spine
        expect(buildLineageSpine([era('2026-06-01'), { week: '2026-06-08', gap: true }]).hasSpine).toBe(false)
    })

    it('lays two adjacent weeks on the literal time axis with one steady edge', () => {
        const s = buildLineageSpine([
            era('2026-06-01'),
            era('2026-06-08', { drift_cos_prev: 0.93 }),
        ], { width: 600, padX: 50 })
        expect(s.hasSpine).toBe(true)
        expect(s.nodes).toHaveLength(2)
        expect(s.nodes[0].x).toBe(50)
        expect(s.nodes[1].x).toBe(550)
        expect(s.edges).toHaveLength(1)
        expect(s.edges[0].kind).toBe('steady')
        expect(s.edges[0].drift).toBe(0.93)
        expect(s.edges[0].spansGap).toBe(false)
    })

    it('classifies drift below the steady cut as shifting — number preserved', () => {
        const s = buildLineageSpine([
            era('2026-06-01'),
            era('2026-06-08', { drift_cos_prev: 0.61 }),
        ])
        expect(s.edges[0].kind).toBe('shifting')
        expect(s.edges[0].drift).toBe(0.61)
    })

    it('marks a missing drift measurement as unmeasured, never steady', () => {
        const s = buildLineageSpine([
            era('2026-06-01'),
            era('2026-06-08', { drift_cos_prev: null }),
        ])
        expect(s.edges[0].kind).toBe('unmeasured')
        expect(s.edges[0].drift).toBeNull()
    })

    it('keeps the time axis literal: a gap week doubles the spacing and the edge spansGap', () => {
        const s = buildLineageSpine([
            era('2026-06-01'),
            { week: '2026-06-08', gap: true },
            era('2026-06-15', { drift_cos_prev: 0.9 }),
        ], { width: 600, padX: 0 })
        // gap entries yield NO node — absence is honest
        expect(s.nodes).toHaveLength(2)
        expect(s.nodes[1].x).toBe(600) // index 2 of span 0..2
        expect(s.edges).toHaveLength(1)
        expect(s.edges[0].spansGap).toBe(true)
    })

    it('spaces sparse arrays by real week distance even without explicit gap entries', () => {
        const s = buildLineageSpine([
            era('2026-06-01'),
            era('2026-06-08', { drift_cos_prev: 0.9 }),
            era('2026-06-29', { drift_cos_prev: 0.9 }), // 3 weeks later
        ], { width: 400, padX: 0 })
        expect(s.nodes.map(n => n.x)).toEqual([0, 100, 400])
        expect(s.edges[1].spansGap).toBe(true)
    })

    it('flags candidate stitches on the edge when either endpoint is a candidate', () => {
        const s = buildLineageSpine([
            era('2026-06-01'),
            era('2026-06-08', { drift_cos_prev: 0.9, candidate: true }),
            era('2026-06-15', { drift_cos_prev: 0.92 }),
        ])
        expect(s.edges[0].candidate).toBe(true)
        expect(s.edges[1].candidate).toBe(true) // candidate endpoint on the from side
    })

    it('scales node radius by volume with a floor, monotonic', () => {
        const s = buildLineageSpine([
            era('2026-06-01', { n_signals: 10 }),
            era('2026-06-08', { n_signals: 1000, drift_cos_prev: 0.9 }),
        ], { rMin: 4, rMax: 14 })
        expect(s.nodes[0].r).toBeGreaterThanOrEqual(4)
        expect(s.nodes[1].r).toBe(14)
        expect(s.nodes[1].r).toBeGreaterThan(s.nodes[0].r)
    })

    it('shows the era label only when it CHANGED (renames tell the story)', () => {
        const s = buildLineageSpine([
            era('2026-06-01', { label: 'Venezuela Earthquake' }),
            era('2026-06-08', { label: 'Venezuela  earthquake!', drift_cos_prev: 0.9 }), // same after normalization
            era('2026-06-15', { label: 'Venezuela Reconstruction Aid', drift_cos_prev: 0.7 }),
        ])
        expect(s.nodes.map(n => n.showLabel)).toEqual([true, false, true])
    })

    it('carries tier through for hot vs archive coloring', () => {
        const s = buildLineageSpine([
            era('2026-06-01'),
            era('2026-06-08', { tier: 'hot', drift_cos_prev: 0.9 }),
        ])
        expect(s.nodes[0].tier).toBe('archive')
        expect(s.nodes[1].tier).toBe('hot')
    })

    it('sorts unordered input by week', () => {
        const s = buildLineageSpine([
            era('2026-06-15', { drift_cos_prev: 0.9 }),
            era('2026-06-01'),
        ])
        expect(s.nodes[0].week).toBe('2026-06-01')
        expect(s.nodes[1].week).toBe('2026-06-15')
    })
})

describe('normalizeEraLabel', () => {
    it('ignores case, punctuation and whitespace runs', () => {
        expect(normalizeEraLabel('Venezuela  Earthquake!')).toBe(normalizeEraLabel('venezuela earthquake'))
        expect(normalizeEraLabel('A — B')).toBe(normalizeEraLabel('a b'))
    })
    it('distinguishes genuinely different labels', () => {
        expect(normalizeEraLabel('Venezuela Earthquake'))
            .not.toBe(normalizeEraLabel('Venezuela Reconstruction Aid'))
    })
})
