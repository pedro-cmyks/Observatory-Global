import { describe, expect, it } from 'vitest'
import { IDENTITY_ROT, rotY } from './universeLayout'
import {
  STRESS_EXACT,
  STRESS_HIGH,
  centerOfMass,
  perspectiveSpread,
  projectPos3,
  screenXY,
  stressNote,
  stressPct,
  stressTier,
  type Pos3,
} from './mds3d'

const CENTER = { cx: 0.5, cy: 0.5, cz: 0.5 }

describe('centerOfMass', () => {
  it('averages the cloud', () => {
    const c = centerOfMass([[0, 0, 0], [1, 1, 1]] as Pos3[])
    expect(c).toEqual({ cx: 0.5, cy: 0.5, cz: 0.5 })
  })
  it('falls back to the cube center when empty', () => {
    expect(centerOfMass([])).toEqual({ cx: 0.5, cy: 0.5, cz: 0.5 })
  })
})

describe('projectPos3', () => {
  it('is the identity at rest with no perspective', () => {
    const p = projectPos3([0.25, 0.75, 0.5], IDENTITY_ROT, CENTER, 0)
    expect(p.px).toBeCloseTo(0.25, 9)
    expect(p.py).toBeCloseTo(0.75, 9)
    expect(p.scale).toBeCloseTo(1, 9)
  })

  it('preserves distance under rotation (the whole point of MDS)', () => {
    const a: Pos3 = [0.2, 0.3, 0.4]
    const b: Pos3 = [0.8, 0.6, 0.4]
    const dist = (r: typeof IDENTITY_ROT) => {
      const pa = projectPos3(a, r, CENTER, 0)
      const pb = projectPos3(b, r, CENTER, 0)
      return Math.hypot(pa.px - pb.px, pa.py - pb.py, pa.depth - pb.depth)
    }
    expect(dist(rotY(0.9))).toBeCloseTo(dist(IDENTITY_ROT), 9)
  })

  it('turns the cloud: a half turn about Y mirrors x', () => {
    const p = projectPos3([0.9, 0.5, 0.5], rotY(Math.PI), CENTER, 0)
    expect(p.px).toBeCloseTo(0.1, 6)
  })

  it('never lets the perspective divisor cross zero', () => {
    // Past spread ≈ 0.833 a near body drives the divisor negative: the scale
    // flips, radii go negative (invalid SVG — the body vanishes and stops being
    // clickable) and positions mirror through the cloud centre. perspectiveSpread
    // caps at 1.6, so this is four wheel notches away, not a theoretical case.
    // Depths outside [0,1] are reachable too: the centre of mass is not the
    // bounding-box centre, so a rotated outlier can sit beyond either end.
    for (let depth = -0.2; depth <= 1.2001; depth += 0.05) {
      const p = projectPos3([0.9, 0.5, depth] as Pos3, IDENTITY_ROT, CENTER, 1.6)
      expect(p.scale).toBeGreaterThan(0)
      expect(Number.isFinite(p.px)).toBe(true)
      expect(Number.isFinite(p.py)).toBe(true)
    }
  })

  it('perspective brings near bodies forward and pushes far ones back', () => {
    const near = projectPos3([0.9, 0.5, 0.1], IDENTITY_ROT, CENTER, 1)
    const far = projectPos3([0.9, 0.5, 0.9], IDENTITY_ROT, CENTER, 1)
    expect(near.scale).toBeGreaterThan(1)
    expect(far.scale).toBeLessThan(1)
    expect(Math.abs(near.px - 0.5)).toBeGreaterThan(Math.abs(far.px - 0.5))
  })
})

describe('perspectiveSpread', () => {
  it('is orthographic at rest and grows with zoom, capped', () => {
    expect(perspectiveSpread(1)).toBe(0)
    expect(perspectiveSpread(0.5)).toBe(0)
    expect(perspectiveSpread(2)).toBeCloseTo(0.8, 9)
    expect(perspectiveSpread(99)).toBeCloseTo(1.6, 9)
  })
})

describe('screenXY', () => {
  it('maps normalized coords into the padded canvas and honours pan/zoom', () => {
    const box = { w: 500, h: 300, margin: 50, view: { k: 1, tx: 0, ty: 0 } }
    expect(screenXY({ px: 0, py: 0 }, box)).toEqual({ sx: 50, sy: 50 })
    expect(screenXY({ px: 1, py: 1 }, box)).toEqual({ sx: 450, sy: 250 })
    const zoomed = screenXY({ px: 0, py: 0 }, { ...box, view: { k: 2, tx: 10, ty: -5 } })
    expect(zoomed).toEqual({ sx: 110, sy: 95 })
  })
})

describe('stress wording', () => {
  it('tiers the measured distortion', () => {
    expect(stressTier(0)).toBe('exact')
    expect(stressTier(0.02)).toBe('exact')
    expect(stressTier(0.1)).toBe('good')
    expect(stressTier(STRESS_HIGH)).toBe('high')
    expect(stressTier(0.9)).toBe('high')
  })
  it('reports whole percent, never rounding the number away', () => {
    expect(stressPct(0.1449)).toBe(14)
    expect(stressPct(0)).toBe(0)
  })

  it('pins the exact/good boundary', () => {
    expect(stressTier(STRESS_EXACT)).toBe('exact')
    expect(stressTier(STRESS_EXACT + 1e-9)).toBe('good')
    expect(stressTier(STRESS_HIGH - 1e-9)).toBe('good')
  })

  // stressNote is the one string in this module that is a PRODUCT CLAIM about
  // how much the picture can be trusted — it gets a test.
  it('says plainly when the geometry is distorted', () => {
    expect(stressNote(STRESS_HIGH)).toContain('high distortion')
    expect(stressNote(STRESS_HIGH)).toContain('rotate')
    expect(stressNote(0.01)).toContain('trustworthy')
    expect(stressNote(0.12)).toBe('low distortion')
  })
})

describe('the orthographic claim', () => {
  // "at k ≤ 1 the view is orthographic — the honest map" is a claim about
  // distance, so test both halves: at rest distance survives the projection,
  // and once zoomed the perspective divide measurably bends it.
  const a: Pos3 = [0.2, 0.3, 0.2]
  const b: Pos3 = [0.7, 0.6, 0.9]
  const projectedDist = (spread: number) => {
    const pa = projectPos3(a, IDENTITY_ROT, CENTER, spread)
    const pb = projectPos3(b, IDENTITY_ROT, CENTER, spread)
    return Math.hypot(pa.px - pb.px, pa.py - pb.py)
  }
  const flatDist = Math.hypot(a[0] - b[0], a[1] - b[1])

  it('preserves the measured distance while zoom stays at rest', () => {
    expect(projectedDist(perspectiveSpread(0.9))).toBeCloseTo(flatDist, 9)
    expect(projectedDist(perspectiveSpread(1))).toBeCloseTo(flatDist, 9)
  })

  it('and bends it once perspective kicks in', () => {
    expect(Math.abs(projectedDist(perspectiveSpread(2)) - flatDist)).toBeGreaterThan(1e-3)
  })
})
