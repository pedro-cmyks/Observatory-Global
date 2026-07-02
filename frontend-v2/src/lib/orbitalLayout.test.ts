import { describe, expect, it } from 'vitest'
import {
  angleAt,
  entrantsBetween,
  interactionsUpTo,
  isComet,
  normalizeDistances,
  presenceAlpha,
  seedAngle,
  type OrbitalBody,
} from './orbitalLayout'

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

describe('normalizeDistances', () => {
  it('maps min->0, max->1, lone body -> 0.5', () => {
    const near = body({ id: 'a', dist: 0.03 })
    const far = body({ id: 'b', dist: 0.05 })
    const norm = normalizeDistances([near, far])
    expect(norm.get('a')).toBe(0)
    expect(norm.get('b')).toBe(1)
    expect(normalizeDistances([near]).get('a')).toBe(0.5)
  })
})

describe('angle = velocity from cumulative interactions', () => {
  it('advances with each interaction as time scrubs forward', () => {
    const b = body()
    expect(interactionsUpTo(b, T0 - HOUR)).toBe(0)
    expect(interactionsUpTo(b, T0 + 25 * HOUR)).toBe(2)
    const before = angleAt(b, T0)
    const after = angleAt(b, T0 + 49 * HOUR)
    expect(after).toBeGreaterThan(before)
  })

  it('seed angle is deterministic per id', () => {
    expect(seedAngle('entity-x')).toBe(seedAngle('entity-x'))
    expect(seedAngle('entity-x')).not.toBe(seedAngle('entity-y'))
  })
})

describe('presence decays, never cliffs (§I)', () => {
  it('is 0 before entry, 1 at activity, decays after, floors above 0', () => {
    const b = body()
    expect(presenceAlpha(b, T0 - HOUR)).toBe(0)
    expect(presenceAlpha(b, T0)).toBe(1)
    const lastActivity = Date.parse(b.timestamps[2])
    const soonAfter = presenceAlpha(b, lastActivity + 12 * HOUR)
    const longAfter = presenceAlpha(b, lastActivity + 200 * HOUR)
    expect(soonAfter).toBeLessThan(1)
    expect(soonAfter).toBeGreaterThan(longAfter)
    expect(longAfter).toBeGreaterThanOrEqual(0.22) // dims, never disappears
  })
})

describe('comets', () => {
  const window = { start: '2026-06-20T00:00:00Z', end: '2026-06-30T00:00:00Z' } // 10 days
  it('short visitors are comets, long residents are not', () => {
    const comet = body({
      first_seen: '2026-06-26T00:00:00Z',
      last_seen: '2026-06-27T00:00:00Z', // 1 of 10 days
    })
    const resident = body({
      first_seen: '2026-06-20T12:00:00Z',
      last_seen: '2026-06-29T12:00:00Z',
    })
    expect(isComet(comet, window)).toBe(true)
    expect(isComet(resident, window)).toBe(false)
  })
})

describe('entrantsBetween — the acceptance question', () => {
  it('answers "who entered this story this week?"', () => {
    const early = body({ id: 'a', first_seen: '2026-06-20T00:00:00Z' })
    const recent = body({ id: 'b', first_seen: '2026-06-27T00:00:00Z' })
    const found = entrantsBetween(
      [early, recent],
      Date.parse('2026-06-25T00:00:00Z'),
      Date.parse('2026-06-30T00:00:00Z'),
    )
    expect(found.map(b => b.id)).toEqual(['b'])
  })
})
