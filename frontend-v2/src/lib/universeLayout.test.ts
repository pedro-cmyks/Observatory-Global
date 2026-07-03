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

describe('rotation = honest depth (spec §7.2)', () => {
  it('yaw 0 keeps x; yaw π mirrors around center; depth stays bounded-ish', async () => {
    const { yawProject, depthScale, depthAlpha } = await import('./universeLayout')
    const at0 = yawProject(0.8, 0.5, 0)
    expect(at0.px).toBeCloseTo(0.8, 6)
    const atPi = yawProject(0.8, 0.5, Math.PI)
    expect(atPi.px).toBeCloseTo(0.2, 6)
    // quarter turn: x becomes depth — the rotation reveals the z structure
    const quarter = yawProject(0.8, 0.9, Math.PI / 2)
    expect(quarter.px).toBeCloseTo(0.1, 6)
    expect(quarter.depth).toBeCloseTo(0.8, 6)
    // depth cues: nearer = larger + brighter, and dimming floors (cue, not filter)
    expect(depthScale(0)).toBeGreaterThan(depthScale(1))
    expect(depthAlpha(1)).toBeGreaterThanOrEqual(0.45)
  })

  it('rotation axis = center of MASS, and mass re-centers to 0.5 (panel center)', async () => {
    const { yawProject, cloudCenter } = await import('./universeLayout')
    // off-center cloud: mass sits at x≈0.8 — bbox-center rotation would orbit externally
    const cloud = [
      node({ id: 'a', x: 0.7, z: 0.8 }),
      node({ id: 'b', x: 0.8, z: 0.8 }),
      node({ id: 'c', x: 0.9, z: 0.8 }),
    ]
    const { cx, cz } = cloudCenter(cloud)
    expect(cx).toBeCloseTo(0.8, 6)
    // at ANY yaw, the mass center projects to 0.5 — the axis stays in the panel center
    for (const yaw of [0, 1.1, Math.PI, 4.4]) {
      const projectedMean = cloud
        .map(n => yawProject(n.x, n.z, yaw, cx, cz).px)
        .reduce((a, b) => a + b, 0) / cloud.length
      expect(projectedMean).toBeCloseTo(0.5, 6)
    }
  })

  it('orphan = best neighbor below the measured isolated band', async () => {
    const { isOrphan } = await import('./universeLayout')
    expect(isOrphan(node({ nn_sim: 0.85 }))).toBe(true)
    expect(isOrphan(node({ nn_sim: 0.95 }))).toBe(false)
    expect(isOrphan(node({ nn_sim: undefined }))).toBe(false) // no data → never claim orphan
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

describe('trajectories — positions move along the REAL track', () => {
  it('interpolates between snapshots; clamps before; eases to now after', async () => {
    const { positionAt } = await import('./universeLayout')
    const b = node({
      x: 0.9, y: 0.9, z: 0.9, // current position
      track: [
        { t: '2026-06-20T00:00:00Z', x: 0.1, y: 0.1, z: 0.1 },
        { t: '2026-06-22T00:00:00Z', x: 0.3, y: 0.1, z: 0.1 },
      ],
    })
    const before = positionAt(b, Date.parse('2026-06-19T00:00:00Z'))
    expect(before.x).toBe(0.1)
    const mid = positionAt(b, Date.parse('2026-06-21T00:00:00Z'))
    expect(mid.x).toBeCloseTo(0.2, 6) // halfway between snapshots
    const nowish = positionAt(b, Date.now())
    expect(nowish.x).toBeCloseTo(0.9, 6) // at NOW = current centroid
  })

  it('no track → static current position', async () => {
    const { positionAt } = await import('./universeLayout')
    const b = node({ x: 0.4, y: 0.6, z: 0.5, track: [] })
    const p = positionAt(b, Date.parse('2026-06-21T00:00:00Z'))
    expect(p).toEqual({ x: 0.4, y: 0.6, z: 0.5 })
  })
})


describe('free 3D rotation matrix (arcball/trackball)', () => {
  it('identity passes through; Y-rot sends x into depth; Z-rot (roll) sends x into y', async () => {
    const { applyRot, IDENTITY_ROT, rotY, rotZ, mul3 } = await import('./universeLayout')
    const id = applyRot(IDENTITY_ROT, 0.8, 0.7, 0.5)
    expect(id.px).toBeCloseTo(0.8, 6); expect(id.py).toBeCloseTo(0.7, 6)
    // quarter yaw around Y: x(0.8, right of center) rotates into depth (near, 0.2)
    const y = applyRot(rotY(Math.PI / 2), 0.8, 0.5, 0.5)
    expect(y.depth).toBeCloseTo(0.2, 6)
    expect(y.px).toBeCloseTo(0.5, 6)
    // ROLL: quarter Z rotation spins the screen plane — x(0.8)→py
    const r = applyRot(rotZ(Math.PI / 2), 0.8, 0.5, 0.5)
    expect(r.py).toBeCloseTo(0.8, 6)
    expect(r.px).toBeCloseTo(0.5, 6)
    // composition is a valid rotation (orthonormal): applying then no-op stays put
    const composed = mul3(rotZ(0.3), rotY(0.4))
    const back = applyRot(mul3(composed, mul3(rotY(-0.4), rotZ(-0.3))), 0.9, 0.2, 0.7)
    expect(back.px).toBeCloseTo(0.9, 5); expect(back.py).toBeCloseTo(0.2, 5)
  })
})

describe('inverse-focus lens', () => {
  const nodes = [
    node({ id: 'a', category: 'War', countries: ['US','IR'], persons: ['donald trump'] }),
    node({ id: 'b', category: 'Economy', countries: ['GB'], persons: ['donald trump','jane doe'] }),
    node({ id: 'c', category: 'Health', countries: ['FR'], persons: ['someone else'] }),
    node({ id: 'd', category: 'Sports', countries: ['US'], persons: ['donald trump'] }),
  ]
  it('lights stories matching a focused country/person, nothing without focus', async () => {
    const { litNodeIds } = await import('./universeLayout')
    expect([...litNodeIds(nodes, 'person', 'Donald Trump')].sort()).toEqual(['a','b','d'])
    expect([...litNodeIds(nodes, 'country', 'us')].sort()).toEqual(['a','d'])
    expect(litNodeIds(nodes, null, null).size).toBe(0)
  })
  it('spread = concentrated vs cross-cutting by category count', async () => {
    const { entitySpread, litNodeIds } = await import('./universeLayout')
    const trump = nodes.filter(n => litNodeIds(nodes, 'person', 'donald trump').has(n.id))
    const s = entitySpread(trump)
    expect(s.stories).toBe(3)
    expect(s.categories).toBe(3) // War, Economy, Sports
    expect(s.shape).toBe('mixed')
    expect(entitySpread([nodes[0]]).shape).toBe('concentrated') // 1 category
  })
})
