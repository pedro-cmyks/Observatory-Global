import { describe, it, expect } from 'vitest'
import {
  WALK_COLORS,
  degreeLabel,
  hopColorRole,
  hopDash,
  hopWidth,
  layoutWalkRadial,
  nextDegree,
  nodeOpacity,
  nodeRadius,
  receiptLine,
  visibleKin,
  type WalkKin,
  type WalkSeed,
} from './constellationWalk'

function kin(over: Partial<WalkKin>): WalkKin {
  return {
    id: 'dynamic-topic-1', label: 'A story', category: 'Armed conflict',
    degree: 1, kinship: 'hermano', acc_weight: 0.5,
    via: { parent_id: 'dynamic-topic-0', parent_label: 'Seed', basis: 'semantic', weight: 0.5, through_blob: false },
    is_blob: false, folded_count: 0, folded_labels: [], destination: null,
    ...over,
  }
}

// ── degree filter (analyst walks it one degree at a time) ─────────────────────
describe('degree reveal', () => {
  const ks = [kin({ degree: 1 }), kin({ degree: 2 }), kin({ degree: 3 })]
  it('visibleKin gates by revealed depth', () => {
    expect(visibleKin(ks, 1).map(k => k.degree)).toEqual([1])
    expect(visibleKin(ks, 2).map(k => k.degree)).toEqual([1, 2])
  })
  it('nextDegree finds the next hop or null when exhausted', () => {
    expect(nextDegree(ks, 1)).toBe(2)
    expect(nextDegree(ks, 3)).toBeNull()
  })
})

// ── honesty grammar (spec §1.5) ───────────────────────────────────────────────
describe('honesty grammar', () => {
  it('solid line for a hermano, dashed for a primo with wider gaps further out', () => {
    expect(hopDash(kin({ kinship: 'hermano' }))).toBeUndefined()
    expect(hopDash(kin({ kinship: 'primo', degree: 2 }))).toBe('3 2')
    expect(hopDash(kin({ kinship: 'primo', degree: 3 }))).toBe('3 4')
  })
  it('thickness grows with accumulated weight', () => {
    expect(hopWidth(kin({ acc_weight: 0 }))).toBeLessThan(hopWidth(kin({ acc_weight: 1 })))
  })
  it('node size + opacity recede with degree', () => {
    expect(nodeRadius(0)).toBeGreaterThan(nodeRadius(3))
    expect(nodeOpacity(0)).toBeGreaterThan(nodeOpacity(3))
  })
  it('color role: destination > blob > kinship', () => {
    expect(hopColorRole(kin({ destination: 'oil', via: { ...kin({}).via, through_blob: true } }))).toBe('destination')
    expect(hopColorRole(kin({ via: { ...kin({}).via, through_blob: true } }))).toBe('blob')
    expect(hopColorRole(kin({ is_blob: true }))).toBe('blob')
    expect(hopColorRole(kin({ kinship: 'primo', degree: 2 }))).toBe('primo')
    expect(WALK_COLORS.hermano).toBeTruthy()
  })
  it('degree label carries honest distance', () => {
    expect(degreeLabel(kin({ kinship: 'hermano' }))).toBe('hermano')
    expect(degreeLabel(kin({ kinship: 'primo', degree: 3 }))).toBe('primo 3º')
  })
  it('receipt line is glass-box: names the hop, weight, blob + fold caveats', () => {
    const r = receiptLine(kin({
      kinship: 'primo', degree: 2, via: { parent_id: 'x', parent_label: 'Hormuz fees', basis: 'semantic', weight: 0.6, through_blob: true },
      folded_count: 2, destination: 'oil',
    }))
    expect(r).toContain('via Hormuz fees')
    expect(r).toContain('60%')
    expect(r).toContain('grab-bag')
    expect(r).toContain('2 same-event fragments')
    expect(r).toContain('typed destination: oil')
  })
})

// ── radial layout (FORBID left-to-right; spec §1.5) ───────────────────────────
describe('radial layout', () => {
  const seeds: WalkSeed[] = [{ id: 'dynamic-topic-0', label: 'Seed', category: 'x' }]
  const chain = [
    kin({ id: 'h1', degree: 1, kinship: 'hermano', via: { parent_id: 'dynamic-topic-0', parent_label: 'Seed', basis: 'semantic', weight: 0.6, through_blob: false } }),
    kin({ id: 'p2', degree: 2, kinship: 'primo', via: { parent_id: 'h1', parent_label: 'H1', basis: 'semantic', weight: 0.6, through_blob: false } }),
    kin({ id: 'p3', degree: 3, kinship: 'primo', via: { parent_id: 'p2', parent_label: 'P2', basis: 'semantic', weight: 0.6, through_blob: false } }),
  ]

  it('places the single seed at the field center', () => {
    const placed = layoutWalkRadial(seeds, chain, 400, 400)
    const s = placed.find(p => p.id === 'dynamic-topic-0')!
    expect(s.px).toBeCloseTo(200, 0)
    expect(s.py).toBeCloseTo(200, 0)
    expect(s.kinship).toBe('seed')
  })

  it('radius grows strictly with degree (concentric rings, not a row)', () => {
    const placed = layoutWalkRadial(seeds, chain, 400, 400)
    const rOf = (id: string) => {
      const n = placed.find(p => p.id === id)!
      return Math.hypot(n.px - 200, n.py - 200)
    }
    expect(rOf('h1')).toBeLessThan(rOf('p2'))
    expect(rOf('p2')).toBeLessThan(rOf('p3'))
  })

  it('a primo sits near its parent angle (trail reads outward, contiguous)', () => {
    const placed = layoutWalkRadial(seeds, chain, 400, 400)
    const a = (id: string) => placed.find(p => p.id === id)!.angle
    // single-child chains inherit the parent angle exactly
    expect(a('p2')).toBeCloseTo(a('h1'), 5)
    expect(a('p3')).toBeCloseTo(a('p2'), 5)
  })

  it('is NOT a left-to-right chain: same-degree siblings differ in angle, not a monotone x-row', () => {
    const sibs = [
      kin({ id: 's1', degree: 1, kinship: 'hermano', via: { parent_id: 'dynamic-topic-0', parent_label: 'Seed', basis: 'semantic', weight: 0.6, through_blob: false } }),
      kin({ id: 's2', degree: 1, kinship: 'hermano', via: { parent_id: 'dynamic-topic-0', parent_label: 'Seed', basis: 'semantic', weight: 0.6, through_blob: false } }),
      kin({ id: 's3', degree: 1, kinship: 'hermano', via: { parent_id: 'dynamic-topic-0', parent_label: 'Seed', basis: 'semantic', weight: 0.6, through_blob: false } }),
    ]
    const placed = layoutWalkRadial(seeds, sibs, 400, 400)
    const ys = ['s1', 's2', 's3'].map(id => placed.find(p => p.id === id)!.py)
    // a horizontal row would share one y; radial siblings spread in y too
    expect(new Set(ys.map(y => Math.round(y))).size).toBeGreaterThan(1)
  })

  it('is deterministic', () => {
    const a = layoutWalkRadial(seeds, chain, 400, 400)
    const b = layoutWalkRadial(seeds, chain, 400, 400)
    expect(a.map(p => [p.px, p.py])).toEqual(b.map(p => [p.px, p.py]))
  })
})
