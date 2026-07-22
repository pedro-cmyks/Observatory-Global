/**
 * Shared 3D constellation projection (pure).
 * Spec: docs/superpowers/specs/2026-07-22-constellation-3d-mds-design.md §3
 *
 * The backend solves classical metric MDS and serves `pos3` per node, so the
 * SPATIAL distance between two nodes IS their measured distance. This module
 * only turns those coordinates into screen space: the rotation math is the
 * universe's (`applyRot` / `depthScale` / `depthAlpha` — already pure and
 * unit-tested, reused verbatim), plus a perspective divide and the honest
 * wording for the served distortion.
 *
 * Because positions are now a measured claim, `stress` is never optional and
 * never rounded away: above STRESS_HIGH the surface says so in words.
 */
import { applyRot, depthAlpha, depthScale, type Rot3 } from './universeLayout'

export type Pos3 = [number, number, number]

/** The `mds` block served alongside the nodes. */
export interface Mds3dMeta {
  /** Kruskal stress-1 — the measured distortion of the 3D squeeze. */
  stress: number
  /** What the distance MEANS on this surface ('cosine' | 'edge-weight-5basis'). */
  basis: string
  n: number
  /** Story path: bodies with no vector — rendered as chips, never placed. */
  unplaced?: string[]
  /** Dossier path: how the six bases collapse into the one scalar. */
  collapse?: string
  note?: string
}

export interface Projected {
  /** Normalized screen-frame coords (0..1 before pan/zoom). */
  px: number
  py: number
  /** 0 = nearest … 1 = furthest. Painter order + depth cues. */
  depth: number
  /** Perspective size factor (>1 near, <1 far). */
  scale: number
}

export interface CloudCenter3 { cx: number; cy: number; cz: number }

/** Rotation axis = the cloud's center of mass, so it never orbits an
 *  external point (the universe's "rota como por fuera" lesson). */
export function centerOfMass(points: Pos3[]): CloudCenter3 {
  if (points.length === 0) return { cx: 0.5, cy: 0.5, cz: 0.5 }
  let sx = 0, sy = 0, sz = 0
  for (const p of points) { sx += p[0]; sy += p[1]; sz += p[2] }
  const n = points.length
  return { cx: sx / n, cy: sy / n, cz: sz / n }
}

/** Perspective strengthens with zoom; at k ≤ 1 the view is orthographic —
 *  the honest map, where screen distance is exactly measured distance. */
export function perspectiveSpread(k: number): number {
  return Math.min(1.6, Math.max(0, (k - 1) * 0.8))
}

export function projectPos3(
  pos: Pos3, rot: Rot3, center: CloudCenter3, spread: number,
): Projected {
  const p = applyRot(rot, pos[0], pos[1], pos[2], center.cx, center.cy, center.cz)
  const scale = 1 / (1 + (p.depth - 0.5) * 2.4 * spread)
  return {
    px: 0.5 + (p.px - 0.5) * scale,
    py: 0.5 + (p.py - 0.5) * scale,
    depth: p.depth,
    scale,
  }
}

export interface ScreenBox {
  w: number
  h: number
  margin: number
  view: { k: number; tx: number; ty: number }
}

/** Normalized projection → canvas pixels, with the surface's pan/zoom. */
export function screenXY(p: { px: number; py: number }, box: ScreenBox): { sx: number; sy: number } {
  const { w, h, margin, view } = box
  return {
    sx: (margin + p.px * (w - 2 * margin)) * view.k + view.tx,
    sy: (margin + p.py * (h - 2 * margin)) * view.k + view.ty,
  }
}

/**
 * Distortion bands. STRESS_HIGH is MEASURED, not guessed: calibrated against
 * real stories and real pin sets (see the plan's Task 8 and the spec addendum).
 */
export const STRESS_EXACT = 0.05
export const STRESS_HIGH = 0.20

export type StressTier = 'exact' | 'good' | 'high'

export function stressTier(stress: number): StressTier {
  if (stress >= STRESS_HIGH) return 'high'
  if (stress <= STRESS_EXACT) return 'exact'
  return 'good'
}

export function stressPct(stress: number): number {
  return Math.floor(stress * 100)
}

/** The honest sentence for a served stress value. */
export function stressNote(stress: number): string {
  const tier = stressTier(stress)
  if (tier === 'high') return 'high distortion — rotate to see the real geometry'
  if (tier === 'exact') return 'near-exact — this geometry is trustworthy'
  return 'low distortion'
}

export { depthAlpha, depthScale }
