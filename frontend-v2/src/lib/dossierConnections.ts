// Dossier connection analysis (contract dossier-connections-v0).
//
// L3 is about CONNECTING many pinned stories to validate whether/how they form
// one narrative. This lib fetches the MEASURED relations from the backend
// (semantic centroid cosine + shared-country + rarity-weighted shared-person)
// and derives, PURELY (so it is unit-testable), the sub-clusters, the isolated
// pins, and a deterministic field layout for the scoped "investigative
// universe". Measured at generation time — never mixed with the frozen pins.
import type { Investigation } from './workbench'
import { resolveThreadTopicId } from './dossierEnrichment'

export type ConnectionBasis = 'semantic' | 'shared_country' | 'shared_person'

export interface ConnectionNode {
  id: string
  base_id: string
  label: string
  category: string | null
  pos: { x: number; y: number } | null
  countries: Array<{ cc: string; n: number }>
  persons: string[]
  languages: Array<{ lang: string; n: number }>
  sentiment: number | null
  roleCounts: { evidence: number; discussion: number; mood: number }
  timeline: Array<{ day: string; n: number }>
  has_centroid: boolean
  n: number
  // Constellation assembly (dossier-connections-v1): an umbrella node folds N
  // near-duplicate children into ONE story exposing typed sub-facets.
  is_umbrella?: boolean
  child_count?: number
  collapsed_from?: string[]
  facets?: ConnectionFacet[]
}

export interface ConnectionFacet {
  facet: string
  topic_count: number
  evidence_n: number
  countries: Array<{ cc: string; n: number }>
  topics: Array<{ id: string; label: string }>
}

export interface ConnectionEdge {
  a: string
  b: string
  basis: ConnectionBasis[]
  weight: number
  semantic_sim: number | null
  shared_countries: string[]
  shared_persons: string[]
}

export interface ConnectionDistributions {
  countries: Array<{ cc: string; n: number }>
  languages: Array<{ lang: string; n: number }>
  roles: { press: number; public: number }
  sentimentByNode: Array<{ id: string; label: string; sentiment: number }>
  timeline: Array<{ day: string; n: number }>
}

export interface ConnectionNeighbor {
  base_id: string
  label: string
  category: string | null
  // which pinned nodes this unpinned story sits near (>1 = a bridge).
  links: Array<{ pin: string; sim: number }>
}

export interface ConnectionsData {
  contract: string
  measured_at?: string
  nodes: ConnectionNode[]
  edges: ConnectionEdge[]
  neighbors?: ConnectionNeighbor[]
  distributions: ConnectionDistributions | null
  unresolved: string[]
  meta?: Record<string, unknown>
  reason?: string
}

/** The pinned topic ids the connection endpoint can resolve (thread/theme pins).
 *  Country/person pins have no topic centroid, so they don't enter the graph —
 *  the graph is a story-relation view. */
export function connectionTopicIds(inv: Investigation): string[] {
  const out: string[] = []
  for (const p of inv.pins) {
    const id = resolveThreadTopicId(p)
    if (id && !out.includes(id)) out.push(id)
  }
  return out
}

export async function fetchConnections(
  inv: Investigation, days = 30,
): Promise<ConnectionsData | null> {
  const topicIds = connectionTopicIds(inv)
  if (topicIds.length < 2) return null // nothing to connect
  try {
    const res = await fetch('/api/v2/dossier/connections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic_ids: topicIds, days }),
    })
    if (!res.ok) return null
    const d = await res.json() as ConnectionsData
    if (!Array.isArray(d.nodes)) return null
    return d
  } catch {
    return null // degrades to absence — the frozen report stands alone
  }
}

// ── Pure clustering ─────────────────────────────────────────────────────────

interface UnionFind {
  find: (x: string) => string
  union: (a: string, b: string) => void
}

function makeUnionFind(ids: string[]): UnionFind {
  const parent = new Map<string, string>(ids.map(i => [i, i]))
  const find = (x: string): string => {
    let r = x
    while (parent.get(r) !== r) r = parent.get(r)!
    // path-compress
    let c = x
    while (parent.get(c) !== r) { const nx = parent.get(c)!; parent.set(c, r); c = nx }
    return r
  }
  const union = (a: string, b: string) => {
    const ra = find(a), rb = find(b)
    if (ra !== rb) parent.set(ra, rb)
  }
  return { find, union }
}

export interface ClusterResult {
  /** Connected components with ≥2 members, largest first. */
  clusters: ConnectionNode[][]
  /** Nodes with no connection to any other pin. */
  isolated: ConnectionNode[]
  /** id -> cluster index (isolated share index -1). */
  clusterOf: Map<string, number>
}

/** Connected components of the relation graph — the sub-narratives, and the
 *  pins that connect to nothing (the honest "does this belong?" flag). */
export function deriveClusters(nodes: ConnectionNode[], edges: ConnectionEdge[]): ClusterResult {
  const ids = nodes.map(n => n.id)
  const uf = makeUnionFind(ids)
  const known = new Set(ids)
  for (const e of edges) {
    if (known.has(e.a) && known.has(e.b)) uf.union(e.a, e.b)
  }
  const groups = new Map<string, ConnectionNode[]>()
  for (const n of nodes) {
    const root = uf.find(n.id)
    groups.set(root, [...(groups.get(root) ?? []), n])
  }
  const components = [...groups.values()]
  const clusters = components.filter(g => g.length >= 2)
    .sort((a, b) => b.length - a.length)
  const isolated = components.filter(g => g.length === 1).map(g => g[0])
  const clusterOf = new Map<string, number>()
  clusters.forEach((g, i) => g.forEach(n => clusterOf.set(n.id, i)))
  isolated.forEach(n => clusterOf.set(n.id, -1))
  return { clusters, isolated, clusterOf }
}

// ── Basis-weighted strength (the correlation≠causation guard) ─────────────────
// A pin↔pin link is STRONG when it rests on a shared ACTOR or shared COUNTRY (a
// real overlap of reference points) and WEAK when it is semantic-ONLY (embedding
// proximity). For same-language coverage of related topics, high cosine is
// largely a linguistic/topical artifact — so a semantic-only cluster must NEVER
// be presented as "one connected narrative". The verdict + the graph both read
// off this distinction.
export type LinkStrength = 'strong' | 'weak'

/** shared actor / shared country present → strong; semantic-only → weak. */
export function edgeStrength(e: ConnectionEdge): LinkStrength {
  return e.shared_persons.length > 0 || e.shared_countries.length > 0 ? 'strong' : 'weak'
}

export type ClusterStrength = 'confirmed' | 'caution'

/** Classify a cluster (≥2 nodes) by the strongest basis on any INTERNAL edge.
 *  'confirmed' = at least one shared-actor/shared-country edge inside it (one
 *  real thread is enough to call the group connected); 'caution' = every internal
 *  edge is semantic-only (similar topics, no shared reference points). */
export function clusterStrength(nodes: ConnectionNode[], edges: ConnectionEdge[]): ClusterStrength {
  const ids = new Set(nodes.map(n => n.id))
  const internal = edges.filter(e => ids.has(e.a) && ids.has(e.b))
  if (internal.length === 0) return 'caution' // defensive — a ≥2 cluster always has one
  return internal.some(e => edgeStrength(e) === 'strong') ? 'confirmed' : 'caution'
}

export type ConnectionState = 'grounded' | 'similar-only' | 'split' | 'isolated'

/** The single basis-weighted verdict state over the whole pinned set — shared by
 *  the synthesis request and (conceptually) the verdict box. 'grounded' = one
 *  cluster held by shared actors/places; 'similar-only' = one cluster, semantic
 *  proximity only; 'split' = ≥2 sub-narratives; 'isolated' = nothing connects. */
export function connectionState(cluster: ClusterResult, edges: ConnectionEdge[]): ConnectionState {
  if (cluster.clusters.length === 0) return 'isolated'
  if (cluster.clusters.length >= 2) return 'split'
  return clusterStrength(cluster.clusters[0], edges) === 'confirmed' ? 'grounded' : 'similar-only'
}

/** The concrete shared actors + countries that link a cluster's members — the
 *  "linked via …" evidence for a confirmed verdict. Deduped, actors first. */
export function sharedBasisNames(nodes: ConnectionNode[], edges: ConnectionEdge[], max = 4): string[] {
  const ids = new Set(nodes.map(n => n.id))
  const persons = new Set<string>()
  const countries = new Set<string>()
  for (const e of edges) {
    if (!ids.has(e.a) || !ids.has(e.b)) continue
    for (const p of e.shared_persons) persons.add(p)
    for (const c of e.shared_countries) countries.add(c)
  }
  return [...persons, ...countries].slice(0, max)
}

// ── Pure field layout ───────────────────────────────────────────────────────

export interface PlacedNode extends ConnectionNode {
  px: number
  py: number
}

function hash(id: string): number {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0
  return Math.abs(h)
}

/** Deterministic scoped-universe layout. Nodes with a backend PCA position sit
 *  in the semantic field; nodes without one settle to the average of their
 *  placed relation-neighbors (a light force pass), and any still-unplaced land
 *  on a ring near the center. Pure + deterministic (jitter from id hash). */
export function layoutInvestigativeUniverse(
  nodes: ConnectionNode[], edges: ConnectionEdge[],
  width: number, height: number, pad = 30,
): PlacedNode[] {
  const W = Math.max(1, width), H = Math.max(1, height)
  const innerW = Math.max(1, W - 2 * pad), innerH = Math.max(1, H - 2 * pad)
  const placed = new Map<string, { x: number; y: number }>()

  for (const n of nodes) {
    if (n.pos) placed.set(n.id, { x: pad + n.pos.x * innerW, y: pad + n.pos.y * innerH })
  }

  const adj = new Map<string, string[]>()
  for (const e of edges) {
    adj.set(e.a, [...(adj.get(e.a) ?? []), e.b])
    adj.set(e.b, [...(adj.get(e.b) ?? []), e.a])
  }
  const unplaced = nodes.filter(n => !placed.has(n.id))
  for (let pass = 0; pass < 3; pass++) {
    for (const n of unplaced) {
      const neigh = (adj.get(n.id) ?? []).filter(id => placed.has(id))
      if (neigh.length === 0) continue
      let sx = 0, sy = 0
      for (const id of neigh) { const p = placed.get(id)!; sx += p.x; sy += p.y }
      const jx = ((hash(n.id) % 40) - 20)
      const jy = ((hash(n.id + '~') % 40) - 20)
      placed.set(n.id, {
        x: Math.max(pad, Math.min(W - pad, sx / neigh.length + jx)),
        y: Math.max(pad, Math.min(H - pad, sy / neigh.length + jy)),
      })
    }
  }
  // Still unplaced (no placed neighbor): ring near center.
  const stragglers = nodes.filter(n => !placed.has(n.id))
  stragglers.forEach((n, i) => {
    const ang = (i / Math.max(1, stragglers.length)) * Math.PI * 2
    const r = Math.min(innerW, innerH) * 0.32
    placed.set(n.id, { x: W / 2 + Math.cos(ang) * r, y: H / 2 + Math.sin(ang) * r })
  })

  return nodes.map(n => {
    const p = placed.get(n.id)!
    return { ...n, px: p.x, py: p.y }
  })
}

// ── Label de-overlap ─────────────────────────────────────────────────────────

export interface LabelItem {
  id: string
  /** center x of the label */
  cx: number
  /** half of the label's rendered width */
  halfW: number
  /** desired text baseline y (labels sit ABOVE their node) */
  y: number
}

/** Push horizontally-overlapping labels UPWARD so none collide, stacking them
 *  in vertical lanes. Deterministic (stable sort with id tiebreak); pure so it
 *  is unit-testable. Returns id -> resolved baseline y. Labels are only ever
 *  moved up (away from their node circle), never sideways — so a label stays
 *  horizontally over its node and reads unambiguously. */
export function deOverlapLabels(items: LabelItem[], lineH = 11): Map<string, number> {
  const sorted = [...items].sort((a, b) => a.y - b.y || (a.id < b.id ? -1 : 1))
  const out = new Map<string, number>()
  const placed: LabelItem[] = []
  for (const it of sorted) {
    let y = it.y
    let moved = true
    let guard = 0
    while (moved && guard++ < 400) {
      moved = false
      for (const p of placed) {
        const py = out.get(p.id)!
        const xOverlap = Math.abs(it.cx - p.cx) < it.halfW + p.halfW
        if (xOverlap && Math.abs(y - py) < lineH) {
          y = py - lineH // stack this label above the one it collides with
          moved = true
        }
      }
    }
    out.set(it.id, y)
    placed.push(it)
  }
  return out
}

// ── Labels + export ─────────────────────────────────────────────────────────

const BASIS_LABEL: Record<ConnectionBasis, string> = {
  semantic: 'semantic proximity',
  shared_country: 'shared country',
  shared_person: 'shared actor',
}

export function edgeReason(e: ConnectionEdge): string {
  const parts: string[] = []
  if (e.basis.includes('semantic') && e.semantic_sim !== null) {
    parts.push(`semantic ${(e.semantic_sim * 100).toFixed(0)}%`)
  }
  if (e.shared_countries.length) parts.push(`↔ ${e.shared_countries.join(', ')}`)
  if (e.shared_persons.length) parts.push(`↔ ${e.shared_persons.slice(0, 2).join(', ')}`)
  return parts.join(' · ') || e.basis.map(b => BASIS_LABEL[b]).join(' · ')
}

/** Connection findings as Markdown lines for the dossier export. */
export function connectionsSummaryLines(
  data: ConnectionsData, cluster: ClusterResult,
): string[] {
  const lines: string[] = []
  lines.push('## Connection analysis (measured at generation)')
  lines.push(
    `*How the ${data.nodes.length} pinned stories relate — semantic centroid `
    + 'proximity, shared country, and rarity-weighted shared actors. Positions '
    + 'approximate; relations measured.*',
  )
  if (cluster.clusters.length === 0 && cluster.isolated.length > 0) {
    lines.push('- No sub-narratives: every pinned story is isolated (they do not measurably relate).')
  }
  // Aggregate verdict — how many sub-narratives are confirmed by shared actors/
  // places vs similarity-only (must survive to the exported, hover-less report).
  if (cluster.clusters.length > 0) {
    const strengths = cluster.clusters.map(g => clusterStrength(g, data.edges))
    const confirmed = strengths.filter(s => s === 'confirmed').length
    const caution = strengths.length - confirmed
    lines.push(
      `- Of ${strengths.length} sub-narrative${strengths.length === 1 ? '' : 's'}, `
      + `${confirmed} confirmed by shared actors/places and ${caution} similarity-only `
      + '(topic/language proximity, not a proven connection).',
    )
  }
  cluster.clusters.forEach((g, i) => {
    const strong = clusterStrength(g, data.edges) === 'confirmed'
    const tag = strong ? '✓ CONFIRMED' : '⚠ SIMILAR ONLY'
    const via = strong ? sharedBasisNames(g, data.edges) : []
    const suffix = strong
      ? (via.length ? ` Linked via ${via.join(', ')}.` : '')
      : ' No shared actors or places — connection is semantic/topical proximity only; treat as a hypothesis.'
    lines.push(`- **${tag} — Sub-narrative ${i + 1}** (${g.length} stories): ${g.map(n => n.label).join('; ')}.${suffix}`)
  })
  if (cluster.isolated.length > 0) {
    lines.push(`- **Isolated** (connect to nothing pinned): ${cluster.isolated.map(n => n.label).join('; ')}.`)
  }
  const strong = data.edges.slice(0, 6)
  if (strong.length) {
    lines.push('- Strongest links:')
    for (const e of strong) {
      const a = data.nodes.find(n => n.id === e.a)?.label ?? e.a
      const b = data.nodes.find(n => n.id === e.b)?.label ?? e.b
      const mark = edgeStrength(e) === 'strong' ? '✓' : '≈'
      lines.push(`  - ${mark} ${a} ↔ ${b} — ${edgeReason(e)}`)
    }
  }
  if (data.unresolved.length) {
    lines.push(`- Not in the relation graph (no story centroid): ${data.unresolved.join(', ')}.`)
  }
  return lines
}
