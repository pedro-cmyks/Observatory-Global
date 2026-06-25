// Pure data helper: shapes raw /api/v2/threads items into deterministic hero
// "movers" for the HeroThread component. Deterministic (no Math.random) so the
// layout is stable between renders and unit-testable.

export interface RawThread {
  thread_id: string
  label: string
  trend?: 'accelerating' | 'stable' | 'fading' | string
  velocity?: number
  top_countries?: string[]
}

export type NodeType = 'story' | 'country' | 'source' | 'actor' | 'attention'

export interface HeroNode {
  type: NodeType
  label: string
  x: number
  y: number
}

export interface HeroMover {
  id: string
  title: string
  trend: string
  velocity: number
  center: HeroNode
  satellites: HeroNode[]
  route: { x: number; y: number }[]
}

// viewBox is 0..W x, 0..H y (must match HeroThread.tsx).
const W = 640
const H = 240

// deterministic hash → [0, 1)
function hash01(s: string): number {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return ((h >>> 0) % 100000) / 100000
}

function place(seed: string, xMin: number, xMax: number, yMin: number, yMax: number): { x: number; y: number } {
  const a = hash01(seed)
  const b = hash01(seed + '#y')
  return {
    x: Math.round(xMin + a * (xMax - xMin)),
    y: Math.round(yMin + b * (yMax - yMin)),
  }
}

export function buildHeroThreads(threads: RawThread[], opts: { max: number }): HeroMover[] {
  if (!Array.isArray(threads)) return []
  return threads.slice(0, opts.max).map((t): HeroMover => {
    const center: HeroNode = { type: 'story', label: t.label, ...place(t.thread_id + 'C', 0.56 * W, 0.72 * W, 0.29 * H, 0.46 * H) }
    const countries = (t.top_countries ?? []).slice(0, 3).map((cc, i): HeroNode => ({
      type: 'country',
      label: cc,
      ...place(t.thread_id + 'cc' + cc + i, 0.14 * W, 0.50 * W, 0.16 * H, 0.71 * H),
    }))
    // fixed evidence-layer satellites (source / actor / attention)
    const fixed: HeroNode[] = [
      { type: 'source', label: 'SOURCES', ...place(t.thread_id + 'src', 0.72 * W, 0.88 * W, 0.12 * H, 0.30 * H) },
      { type: 'actor', label: 'ACTORS', ...place(t.thread_id + 'act', 0.56 * W, 0.69 * W, 0.54 * H, 0.73 * H) },
      { type: 'attention', label: 'ATTENTION', ...place(t.thread_id + 'att', 0.69 * W, 0.91 * W, 0.42 * H, 0.63 * H) },
    ]
    const satellites = [...countries, ...fixed]
    // route: travel the satellites then end at the center (the investigation)
    const route = [...satellites.map(s => ({ x: s.x, y: s.y })), { x: center.x, y: center.y }]
    return {
      id: t.thread_id,
      title: t.label,
      trend: t.trend ?? 'stable',
      velocity: typeof t.velocity === 'number' ? t.velocity : 0,
      center,
      satellites,
      route,
    }
  })
}
