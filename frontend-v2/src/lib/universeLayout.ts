/**
 * Universe view layout math (pure).
 * Spec: docs/specs/2026-07-02-universe-view.md
 *
 * Same honesty rules as orbitalLayout: presence decays (§I, no cliff),
 * every visual quantity maps to engine data. Positions/edges come from the
 * backend (positions approximate by design; edges measured in full space).
 */

export interface UniverseNode {
  id: string
  label: string
  category: string
  crisis_relevant: boolean | null
  n: number
  x: number
  y: number
  /** PCA third component — rotatable depth (spec §7.2). */
  z?: number
  /** Best full-space neighbor similarity — low = semantic orphan. */
  nn_sim?: number
  first_seen: string | null
  last_seen: string | null
  timeline: Array<{ day: string; n: number }>
  /** Historical positions: per-snapshot cluster centroids projected into the
      CURRENT layout frame — the topic's real path through the field. */
  track?: TrackPoint[]
}

export interface TrackPoint {
  t: string
  x: number
  y: number
  z?: number
}

export interface UniverseEdge {
  a: string
  b: string
  sim: number
}

const DECAY_HOURS = 72
const MIN_ALIVE_ALPHA = 0.14

/** Story exists at t once first seen. */
export function aliveAt(node: UniverseNode, t: number): boolean {
  if (!node.first_seen) return true
  return Date.parse(node.first_seen) <= t
}

/** Latest activity at or before t: last timeline day ≤ t, else first_seen. */
export function lastActivityBefore(node: UniverseNode, t: number): number {
  let last = node.first_seen ? Date.parse(node.first_seen) : t
  for (const bucket of node.timeline) {
    const ms = Date.parse(`${bucket.day}T00:00:00Z`)
    if (ms <= t && ms > last) last = ms
  }
  return last
}

/** Presence opacity at t — exponential decay after last activity, floored. */
export function universeAlpha(node: UniverseNode, t: number): number {
  if (!aliveAt(node, t)) return 0
  const ageHours = (t - lastActivityBefore(node, t)) / 3_600_000
  const alpha = Math.exp(-Math.LN2 * (ageHours / DECAY_HOURS))
  return Math.max(MIN_ALIVE_ALPHA, Math.min(1, alpha))
}

/** Stories whose first appearance falls within [t - windowMs, t]. */
export function bornBetween(nodes: UniverseNode[], t: number, windowMs: number): UniverseNode[] {
  return nodes.filter(n => {
    if (!n.first_seen) return false
    const first = Date.parse(n.first_seen)
    return first >= t - windowMs && first <= t
  })
}

/** Node dot radius from lifetime volume (log-damped, matches thread ranking's volume honesty). */
export function universeRadius(n: number): number {
  return Math.max(2.5, Math.min(13, 2 + Math.log2(1 + n) * 1.15))
}

/** Deterministic category color — stable hue per category label. */
export function categoryColor(category: string): string {
  let hash = 0
  for (let i = 0; i < category.length; i++) hash = (hash * 31 + category.charCodeAt(i)) | 0
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 62%, 62%)`
}

/** Edge stroke opacity from full-space similarity: 0.90 → faint, 0.99+ → strong. */
export function edgeOpacity(sim: number): number {
  return Math.max(0.05, Math.min(0.6, (sim - 0.9) * 6))
}

/**
 * Yaw the cloud around its vertical axis (spec §7.2 — rotation is honest
 * depth: x/z are real PCA components, so turning the cloud separates points
 * any single 2D projection overlaps).
 *
 * The rotation axis passes through (cx, cz) — callers should pass the cloud's
 * CENTER OF MASS, not the bounding-box center: normalized [0,1] coords put
 * the bbox center at 0.5, but the mass can sit off-center, which made the
 * cloud orbit an external axis (Pedro's "rota como por fuera", 2026-07-02).
 * The projected x is re-centered so the mass center lands back on 0.5 (the
 * panel center after screen mapping).
 */
export function yawProject(
  x: number,
  z: number | undefined,
  yaw: number,
  cx = 0.5,
  cz = 0.5,
): { px: number; depth: number } {
  const zc = (z ?? cz) - cz
  const xc = x - cx
  const cos = Math.cos(yaw)
  const sin = Math.sin(yaw)
  return {
    px: xc * cos - zc * sin + 0.5,
    depth: xc * sin + zc * cos + 0.5,
  }
}

/**
 * Free 3D rotation via an accumulated 3x3 matrix (trackball/arcball — Pedro
 * 2026-07-03: "roll disponible 3D... moverme para donde sea, sin restringir a
 * un eje"). Replaces the clamped yaw/pitch Euler pair: no gimbal lock, any
 * orientation, roll included. Rows are the matrix, row-major [r00..r22].
 */
export type Rot3 = [number, number, number, number, number, number, number, number, number]

export const IDENTITY_ROT: Rot3 = [1, 0, 0, 0, 1, 0, 0, 0, 1]

export function rotX(a: number): Rot3 {
  const c = Math.cos(a), s = Math.sin(a)
  return [1, 0, 0, 0, c, -s, 0, s, c]
}
export function rotY(a: number): Rot3 {
  const c = Math.cos(a), s = Math.sin(a)
  return [c, 0, s, 0, 1, 0, -s, 0, c]
}
export function rotZ(a: number): Rot3 {
  const c = Math.cos(a), s = Math.sin(a)
  return [c, -s, 0, s, c, 0, 0, 0, 1]
}

/** Matrix product A·B (both row-major 3x3). */
export function mul3(a: Rot3, b: Rot3): Rot3 {
  const o = new Array(9) as number[]
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 3; c++) {
      o[r * 3 + c] = a[r * 3] * b[c] + a[r * 3 + 1] * b[3 + c] + a[r * 3 + 2] * b[6 + c]
    }
  }
  return o as Rot3
}

/**
 * Project a point through the rotation about the cloud center (cx,cy,cz):
 * translate to center, apply rot, re-center to 0.5. Returns normalized px,py
 * (screen frame) + depth (0 near … 1 far, for painter order + depth cues).
 */
export function applyRot(
  rot: Rot3, x: number, y: number, z: number | undefined,
  cx = 0.5, cy = 0.5, cz = 0.5,
): { px: number; py: number; depth: number } {
  const xc = x - cx, yc = y - cy, zc = (z ?? cz) - cz
  return {
    px: rot[0] * xc + rot[1] * yc + rot[2] * zc + 0.5,
    py: rot[3] * xc + rot[4] * yc + rot[5] * zc + 0.5,
    depth: rot[6] * xc + rot[7] * yc + rot[8] * zc + 0.5,
  }
}

/** Center of mass of the cloud (x and z means) — the honest rotation axis. */
export function cloudCenter(nodes: UniverseNode[]): { cx: number; cz: number } {
  if (nodes.length === 0) return { cx: 0.5, cz: 0.5 }
  let sx = 0
  let sz = 0
  for (const n of nodes) {
    sx += n.x
    sz += n.z ?? 0.5
  }
  return { cx: sx / nodes.length, cz: sz / nodes.length }
}

/** Depth cue: near bodies render larger (depth 0 → 1.25×, depth 1 → 0.75×). */
export function depthScale(depth: number): number {
  return 1.25 - 0.5 * Math.max(0, Math.min(1, depth))
}

/** Depth cue: far bodies dim (never below 0.45 — depth is a cue, not a filter). */
export function depthAlpha(depth: number): number {
  return Math.max(0.45, 1 - 0.55 * Math.max(0, Math.min(1, depth)))
}

/**
 * Semantic orphan: best full-space neighbor below the population's isolated
 * band (measured NN-sim p10 ≈ 0.893 on 2026-07-02). A story unlike every
 * other living story — the open-set frontier (P8).
 */
export const ORPHAN_NN_SIM = 0.893

export function isOrphan(node: UniverseNode): boolean {
  return node.nn_sim !== undefined && node.nn_sim < ORPHAN_NN_SIM
}

/**
 * Position of a node at scrub time t: linear interpolation along its REAL
 * historical track (spec §7.2 trajectories — measured drift, no fabricated
 * motion). Before the first snapshot → first point; at/after the last →
 * the node's current position (the "now" centroid). No track → static.
 */
export function positionAt(node: UniverseNode, t: number): { x: number; y: number; z: number } {
  const nowPos = { x: node.x, y: node.y, z: node.z ?? 0.5 }
  const track = node.track
  if (!track || track.length === 0) return nowPos
  const times = track.map(p => Date.parse(p.t))
  if (t <= times[0]) return { x: track[0].x, y: track[0].y, z: track[0].z ?? 0.5 }
  if (t >= times[times.length - 1]) {
    // between the last snapshot and NOW, ease toward the current centroid
    const last = track[track.length - 1]
    const lastT = times[times.length - 1]
    const nowT = Date.now()
    if (nowT <= lastT) return nowPos
    const f = Math.min(1, (t - lastT) / (nowT - lastT))
    return {
      x: last.x + (nowPos.x - last.x) * f,
      y: last.y + (nowPos.y - last.y) * f,
      z: (last.z ?? 0.5) + (nowPos.z - (last.z ?? 0.5)) * f,
    }
  }
  let i = 1
  while (times[i] < t) i++
  const a = track[i - 1]
  const b = track[i]
  const f = (t - times[i - 1]) / (times[i] - times[i - 1])
  return {
    x: a.x + (b.x - a.x) * f,
    y: a.y + (b.y - a.y) * f,
    z: (a.z ?? 0.5) + ((b.z ?? 0.5) - (a.z ?? 0.5)) * f,
  }
}
