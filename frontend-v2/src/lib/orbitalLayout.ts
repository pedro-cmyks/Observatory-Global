/**
 * Orbital Thread View layout math (E2/L11).
 * Spec: docs/specs/2026-07-02-orbital-thread-view.md
 *
 * Pure functions — every visual degree of freedom maps to a real engine
 * quantity and is deterministic for a given (bodies, scrub time):
 *   radius   = semantic distance (min-max normalized within the thread)
 *   angle    = golden-angle seed + cumulative interactions up to t (velocity = intensity)
 *   presence = hidden before first_seen; opacity DECAYS after last activity (no cliff)
 *   comet    = presence span < 25% of the thread window
 */

export interface OrbitalBody {
  id: string
  label: string
  type: 'person' | 'organization' | 'place' | 'event' | 'country'
  n: number
  dist: number
  /** Radial drift: late-half mean distance − early-half (backend-measured).
      Positive = receding from the story, negative = approaching. Null when
      too few signals to split honestly. */
  drift?: number | null
  first_seen: string
  last_seen: string
  timestamps: string[]
}

/**
 * Tail length in px for a measured drift, scaled by the thread's distance
 * span so tails are comparable within one system. Returns 0 (no tail) when
 * drift is unknown or negligible (<12% of the span — noise floor).
 */
export function driftTailLength(drift: number | null | undefined, distSpan: number, maxPx = 46): number {
  if (drift == null || distSpan <= 1e-9) return 0
  const rel = Math.abs(drift) / distSpan
  // Noise floor measured on dt-981 (2026-07-02): real drifts run 5-10% of the
  // thread's distance span, so 4% separates signal from jitter.
  if (rel < 0.04) return 0
  return Math.min(maxPx, 8 + rel * maxPx * 1.6)
}

export interface OrbitalWindow {
  start: string
  end: string
}

const GOLDEN_ANGLE = 2.399963229728653 // radians (137.508°)
/** Angle a body sweeps per interaction — velocity IS intensity. */
const RADIANS_PER_INTERACTION = 0.55
/** Opacity half-life after last activity, in hours (§I decay-not-cliff). */
const DECAY_HOURS = 36
const MIN_VISIBLE_ALPHA = 0.22
export const COMET_SPAN_RATIO = 0.25

/** Deterministic per-body seed angle so layouts are stable across renders. */
export function seedAngle(id: string): number {
  let hash = 0
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) | 0
  }
  return (Math.abs(hash) % 360) * (Math.PI / 180) + Math.abs(hash % 7) * GOLDEN_ANGLE
}

/** Min-max normalize distances onto [0,1]; a lone body sits mid-orbit. */
export function normalizeDistances(bodies: OrbitalBody[]): Map<string, number> {
  const out = new Map<string, number>()
  if (bodies.length === 0) return out
  const dists = bodies.map(b => b.dist)
  const min = Math.min(...dists)
  const max = Math.max(...dists)
  const span = max - min
  for (const b of bodies) {
    out.set(b.id, span > 1e-9 ? (b.dist - min) / span : 0.5)
  }
  return out
}

/** Orbit radius in px for a normalized distance. */
export function orbitRadius(norm: number, rMin: number, rMax: number): number {
  return rMin + norm * (rMax - rMin)
}

/** Interactions that happened at or before t. */
export function interactionsUpTo(body: OrbitalBody, t: number): number {
  let count = 0
  for (const ts of body.timestamps) {
    if (Date.parse(ts) <= t) count++
  }
  return count
}

/** Body angle at scrub time t: seed + cumulative-interaction sweep. */
export function angleAt(body: OrbitalBody, t: number): number {
  return seedAngle(body.id) + interactionsUpTo(body, t) * RADIANS_PER_INTERACTION
}

/**
 * Presence opacity at scrub time t.
 * 0 before entry; then exponential decay from the last activity before t,
 * floored at MIN_VISIBLE_ALPHA — a dormant body dims, it never cliffs out.
 */
export function presenceAlpha(body: OrbitalBody, t: number): number {
  const first = Date.parse(body.first_seen)
  if (t < first) return 0
  let lastActivity = first
  for (const ts of body.timestamps) {
    const ms = Date.parse(ts)
    if (ms <= t && ms > lastActivity) lastActivity = ms
  }
  const ageHours = (t - lastActivity) / 3_600_000
  const alpha = Math.exp(-Math.LN2 * (ageHours / DECAY_HOURS))
  return Math.max(MIN_VISIBLE_ALPHA, Math.min(1, alpha))
}

/** Transient visitor: present for < 25% of the thread window. */
export function isComet(body: OrbitalBody, window: OrbitalWindow): boolean {
  const span = Date.parse(body.last_seen) - Date.parse(body.first_seen)
  const windowSpan = Date.parse(window.end) - Date.parse(window.start)
  if (windowSpan <= 0) return false
  return span / windowSpan < COMET_SPAN_RATIO
}

/** Body dot radius from signal volume. */
export function bodyRadius(n: number): number {
  return Math.max(4, Math.min(14, 3 + Math.sqrt(n) * 2.2))
}

/** Bodies that ENTERED (first activity) within [tFrom, tTo] — the acceptance question. */
export function entrantsBetween(bodies: OrbitalBody[], tFrom: number, tTo: number): OrbitalBody[] {
  return bodies.filter(b => {
    const first = Date.parse(b.first_seen)
    return first >= tFrom && first <= tTo
  })
}
