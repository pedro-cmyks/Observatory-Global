import { describe, it, expect } from 'vitest'
import { buildHeroThreads, type RawThread } from './heroThreads'

const sample: RawThread[] = [
  { thread_id: 't1', label: "Iran's water crisis", trend: 'accelerating', velocity: 9, top_countries: ['IR', 'IQ', 'SA'] },
  { thread_id: 't2', label: 'Sahel coup fallout', trend: 'stable', velocity: 3, top_countries: ['ML', 'NE'] },
]

describe('buildHeroThreads', () => {
  it('returns one mover per thread, capped at max', () => {
    const out = buildHeroThreads(sample, { max: 5 })
    expect(out).toHaveLength(2)
    expect(out[0].id).toBe('t1')
    expect(out[0].title).toBe("Iran's water crisis")
  })

  it('gives each mover a center node and typed satellites with deterministic positions', () => {
    const out = buildHeroThreads(sample, { max: 5 })
    const m = out[0]
    expect(m.center).toMatchObject({ type: 'story' })
    expect(m.satellites.length).toBeGreaterThanOrEqual(3)
    expect(m.satellites.some(s => s.type === 'country')).toBe(true)
    const again = buildHeroThreads(sample, { max: 5 })
    expect(again[0].center.x).toBe(m.center.x)
    expect(again[0].satellites[0].x).toBe(m.satellites[0].x)
  })

  it('orders the route through the satellites ending at the center (the investigation)', () => {
    const m = buildHeroThreads(sample, { max: 5 })[0]
    expect(m.route.length).toBeGreaterThanOrEqual(2)
    expect(m.route[m.route.length - 1]).toEqual({ x: m.center.x, y: m.center.y })
  })

  it('degrades to empty array on no/garbage input without throwing', () => {
    expect(buildHeroThreads([], { max: 5 })).toEqual([])
    // @ts-expect-error garbage input
    expect(buildHeroThreads(null, { max: 5 })).toEqual([])
  })

  it('respects max', () => {
    const many = Array.from({ length: 9 }, (_, i) => ({ ...sample[0], thread_id: `t${i}`, label: `s${i}` }))
    expect(buildHeroThreads(many, { max: 4 })).toHaveLength(4)
  })
})
