import { describe, expect, it } from 'vitest'
import {
  aliveAt,
  bornBetween,
  categoryColor,
  edgeOpacity,
  lastActivityBefore,
  universeAlpha,
  universeRadius,
  type UniverseNode,
} from './universeLayout'

const HOUR = 3_600_000
const T = Date.parse('2026-07-01T12:00:00Z')

function node(overrides: Partial<UniverseNode> = {}): UniverseNode {
  return {
    id: 'dynamic-topic-1',
    label: 'Test Story',
    category: 'Armed Conflict Escalation',
    crisis_relevant: true,
    n: 50,
    x: 0.5,
    y: 0.5,
    first_seen: '2026-06-20T00:00:00Z',
    last_seen: '2026-06-30T00:00:00Z',
    timeline: [
      { day: '2026-06-20', n: 10 },
      { day: '2026-06-25', n: 30 },
      { day: '2026-06-30', n: 10 },
    ],
    ...overrides,
  }
}

describe('presence over time (§I decay, no cliff)', () => {
  it('not alive before first_seen; full at activity; decays after; floors', () => {
    const b = node()
    expect(aliveAt(b, Date.parse('2026-06-19T00:00:00Z'))).toBe(false)
    expect(universeAlpha(b, Date.parse('2026-06-19T00:00:00Z'))).toBe(0)
    expect(universeAlpha(b, Date.parse('2026-06-30T00:00:00Z'))).toBe(1)
    const after3d = universeAlpha(b, Date.parse('2026-06-30T00:00:00Z') + 72 * HOUR)
    expect(after3d).toBeCloseTo(0.5, 1) // half-life 72h
    const monthLater = universeAlpha(b, Date.parse('2026-06-30T00:00:00Z') + 1000 * HOUR)
    expect(monthLater).toBeGreaterThanOrEqual(0.14) // dims, never disappears
  })

  it('lastActivityBefore respects scrubbed time', () => {
    const b = node()
    expect(lastActivityBefore(b, Date.parse('2026-06-26T00:00:00Z'))).toBe(
      Date.parse('2026-06-25T00:00:00Z'),
    )
  })
})

describe('bornBetween — new stories in a trailing window', () => {
  it('finds only stories born inside the window', () => {
    const old = node({ id: 'a', first_seen: '2026-06-01T00:00:00Z' })
    const fresh = node({ id: 'b', first_seen: '2026-06-30T00:00:00Z' })
    const found = bornBetween([old, fresh], T, 7 * 24 * HOUR)
    expect(found.map(n => n.id)).toEqual(['b'])
  })
})

describe('visual encodings', () => {
  it('radius log-damps volume so a 3K story cannot bury a 50-signal story', () => {
    expect(universeRadius(3000) / universeRadius(50)).toBeLessThan(2.5)
    expect(universeRadius(3000)).toBeLessThanOrEqual(13)
  })

  it('category color is deterministic; edge opacity maps sim band', () => {
    expect(categoryColor('Politics & Governance')).toBe(categoryColor('Politics & Governance'))
    expect(edgeOpacity(0.99)).toBeGreaterThan(edgeOpacity(0.91))
    expect(edgeOpacity(0.9)).toBeGreaterThanOrEqual(0.05)
  })
})
