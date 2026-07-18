// theme-lineage-v0 contract freeze: the fixture is the canonical example the
// backend endpoint must satisfy, and the surface's gating helpers must read it
// the way the honesty rules demand.
import { describe, it, expect } from 'vitest'
import { LINEAGE_FIXTURE, presentWeeks } from './lineage'
import { buildLineageSpine } from './lineageSpine'

describe('theme-lineage-v0 fixture', () => {
    it('declares the contract and the stitch method (glass-box)', () => {
        expect(LINEAGE_FIXTURE.contract).toBe('theme-lineage-v0')
        expect(LINEAGE_FIXTURE.stitch?.space).toContain('text-embedding-3-small')
        expect(LINEAGE_FIXTURE.stitch?.theta_topic_unit).toBeGreaterThan(0)
        expect(LINEAGE_FIXTURE.stitch?.member_coverage).toBeGreaterThan(0)
    })

    it('weeks ascend and era gaps are explicit, not silently skipped', () => {
        const ws = LINEAGE_FIXTURE.weeks.map(w => w.week)
        expect([...ws].sort()).toEqual(ws)
        expect(LINEAGE_FIXTURE.weeks.some(w => w.gap)).toBe(true)
    })

    it('carries both tiers across the hot/archive seam', () => {
        const tiers = new Set(presentWeeks(LINEAGE_FIXTURE.weeks).map(w => w.tier))
        expect(tiers.has('archive')).toBe(true)
        expect(tiers.has('hot')).toBe(true)
    })

    it('presentWeeks drops gaps and the fixture clears the >=2-week render gate', () => {
        const present = presentWeeks(LINEAGE_FIXTURE.weeks)
        expect(present.length).toBeGreaterThanOrEqual(2)
        expect(present.every(w => !w.gap)).toBe(true)
    })

    it('drives a full spine: measured drift on every subsequent era, a candidate edge, a rename', () => {
        const spine = buildLineageSpine(LINEAGE_FIXTURE.weeks)
        expect(spine.hasSpine).toBe(true)
        // every era after the first carries a measured drift number
        expect(spine.edges.every(e => e.drift != null)).toBe(true)
        expect(spine.edges.some(e => e.candidate)).toBe(true)
        // the mid-life rename shows its label (the renames tell the story)
        expect(spine.nodes.filter(n => n.showLabel).length).toBeGreaterThanOrEqual(2)
        // the gap week produced no node but a spanning edge
        expect(spine.nodes.some(n => n.week === '2026-06-08')).toBe(false)
        expect(spine.edges.some(e => e.spansGap)).toBe(true)
    })

    it('presentWeeks tolerates null/undefined', () => {
        expect(presentWeeks(null)).toEqual([])
        expect(presentWeeks(undefined)).toEqual([])
    })
})
