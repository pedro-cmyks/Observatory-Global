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
  first_seen: string | null
  last_seen: string | null
  timeline: Array<{ day: string; n: number }>
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
