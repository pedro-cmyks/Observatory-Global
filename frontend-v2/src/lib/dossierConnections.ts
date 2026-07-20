// Dossier connection analysis (contract dossier-connections-v0).
//
// L3 is about CONNECTING many pinned stories to validate whether/how they form
// one narrative. This lib fetches the MEASURED relations from the backend
// (semantic centroid cosine + coverage-country + rarity-weighted shared-person)
// and derives, PURELY (so it is unit-testable), the sub-clusters, the isolated
// pins, and a deterministic field layout for the scoped "investigative
// universe". Measured at generation time — never mixed with the frozen pins.
import type { Investigation, WorkbenchPin } from './workbench'
import { resolveThreadTopicId } from './dossierEnrichment'

export type ConnectionBasis = 'semantic' | 'shared_country' | 'shared_person' | 'text_mention' | 'body_mention'

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
  /** dynamic_topics.first_seen — the start of the story window (P0.3). */
  first_seen?: string | null
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
  /** RAW e5 centroid cosine — display-only. Floods 0.88-0.96 (anisotropic
   *  cone), so it reads misleadingly high ("99% similar"). */
  semantic_sim: number | null
  /** Whitened (all-but-top k=1) cosine — the space the CONNECT decision runs
   *  in. Optional: absent on old payloads or when the whitening asset is off. */
  whitened_sim?: number | null
  shared_countries: string[]
  shared_persons: string[]
  /** Frank v2 blocker 1: verbatim terms of the other pin found in this pair's
   *  evidence headlines ("nato summit") — entity extraction missed the link,
   *  the TEXT states it. Weaker than shared_person, stronger than semantic. */
  text_mentions?: string[]
  /** F3a: terms of the other pin found in this pair's FETCHED ARTICLE BODIES
   *  (pinned_articles cache) — the paragraph-6 reference headlines hide.
   *  Weaker than a headline text_mention, never silently mixed with it. */
  body_mentions?: string[]
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
  /** F3b: basis 'centroid' (topic centroid) | 'body-e5-whitened' (mean of the
   *  pin's fetched-body embeds — measurement-gated lane, 2026-07-20). */
  links: Array<{ pin: string; sim: number; basis?: string }>
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

/** F3a: per-resolvable-pin FROZEN evidence urls — lets the backend mention
 *  scan read the fetched bodies (shared pinned_articles cache). */
export function connectionEvidenceUrls(inv: Investigation): Record<string, string[]> {
  const out: Record<string, string[]> = {}
  for (const p of inv.pins) {
    const id = resolveThreadTopicId(p)
    if (!id) continue
    const urls = (p.snapshot?.evidence ?? [])
      .map(e => (e.url ?? '').trim())
      .filter(u => u.startsWith('http'))
    if (urls.length === 0) continue
    out[id] = Array.from(new Set([...(out[id] ?? []), ...urls])).slice(0, 4)
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
      body: JSON.stringify({ topic_ids: topicIds, days, evidence_urls: connectionEvidenceUrls(inv) }),
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
export type LinkStrength = 'strong' | 'text' | 'context' | 'weak'

/** Shared actor → strong; evidence-TEXT mention → text; shared coverage country
 *  → context (not subject identity or causality); semantic-only → weak. */
export function edgeStrength(e: ConnectionEdge): LinkStrength {
  if (e.shared_persons.length > 0) return 'strong'
  if (e.basis.includes('text_mention') && (e.text_mentions?.length ?? 0) > 0) return 'text'
  if (e.basis.includes('body_mention') && (e.body_mentions?.length ?? 0) > 0) return 'text'
  if (e.shared_countries.length > 0) return 'context'
  return 'weak'
}

export type ClusterStrength = 'confirmed' | 'text' | 'context' | 'caution'

/** Classify a cluster by its strongest internal truth tier. Only a distinctive
 *  shared actor confirms; country overlap remains coverage context. */
export function clusterStrength(nodes: ConnectionNode[], edges: ConnectionEdge[]): ClusterStrength {
  const ids = new Set(nodes.map(n => n.id))
  const internal = edges.filter(e => ids.has(e.a) && ids.has(e.b))
  if (internal.length === 0) return 'caution' // defensive — a ≥2 cluster always has one
  const strengths = internal.map(edgeStrength)
  if (strengths.includes('strong')) return 'confirmed'
  if (strengths.includes('text')) return 'text'
  if (strengths.includes('context')) return 'context'
  return 'caution'
}

export type ConnectionState = 'grounded' | 'text-linked' | 'context-only' | 'similar-only' | 'split' | 'isolated'

/** The single basis-weighted verdict state over the whole pinned set. Grounded
 *  requires a distinctive shared actor; context-only is coverage geography. */
export function connectionState(cluster: ClusterResult, edges: ConnectionEdge[]): ConnectionState {
  if (cluster.clusters.length === 0) return 'isolated'
  if (cluster.clusters.length >= 2) return 'split'
  const s = clusterStrength(cluster.clusters[0], edges)
  return s === 'confirmed' ? 'grounded'
    : s === 'text' ? 'text-linked'
      : s === 'context' ? 'context-only' : 'similar-only'
}

/** The concrete distinctive actors that support a confirmed verdict. Coverage
 *  countries are deliberately excluded: same coverage geography is context. */
export function sharedBasisNames(nodes: ConnectionNode[], edges: ConnectionEdge[], max = 4): string[] {
  const ids = new Set(nodes.map(n => n.id))
  const persons = new Set<string>()
  for (const e of edges) {
    if (!ids.has(e.a) || !ids.has(e.b)) continue
    for (const p of e.shared_persons) persons.add(p)
  }
  return [...persons].slice(0, max)
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

// ── Text cross-reference (client mirror of the backend rule) ─────────────────
// Frank v2 blocker 1, frozen-evidence side: the backend cross-refs MEASURED
// member headlines; this mirrors the same token rule over the FROZEN pin
// evidence (which may predate the backend's window), so an "isolated" verdict
// can never stand uncontradicted by a headline the report itself displays.

const LABEL_STOPWORDS = new Set([
  'the', 'a', 'an', 'of', 'and', 'or', 'in', 'on', 'for', 'with', 'to', 'at',
  'as', 'by', 'from', 'over', 'after', 'before', 'amid', 'during', 'between',
  'against', 'under', 'into', 'near', 'his', 'her', 'its', 'their',
  'news', 'update', 'updates', 'report', 'reports', 'latest', 'live',
  'daily', 'roundup', 'new', 'crisis', 'situation', 'developments',
  'coverage', 'story', 'stories', 'talks',
  'de', 'del', 'la', 'el', 'los', 'las', 'le', 'les', 'du', 'des', 'und',
])

export function labelKeyTokens(label: string): string[] {
  return (label || '').toLowerCase().split(/[^\p{L}\p{N}_]+/u)
    .filter(t => t.length >= 3 && !LABEL_STOPWORDS.has(t))
}

/** Term of `labelTokens` found in `headline` under the backend rule (≥2 key
 *  tokens in one headline, or the single token of a 1-token label), or null. */
export function headlineMentionTerm(headline: string, labelTokens: string[]): string | null {
  if (labelTokens.length === 0) return null
  const hset = new Set(headline.toLowerCase().split(/[^\p{L}\p{N}_]+/u))
  const matched = labelTokens.filter(t => hset.has(t))
  if (matched.length >= 2 || (labelTokens.length === 1 && matched.length === 1)) {
    return matched.slice(0, 3).join(' ')
  }
  return null
}

export interface TextCrossRef {
  /** label of the pin whose FROZEN evidence text carries the mention */
  pinLabel: string
  /** label of the pin being mentioned */
  otherLabel: string
  /** the verbatim matched term ("nato summit") */
  term: string
  /** the frozen headline that carries it */
  headline: string
}

/** Cross-reference each pin's FROZEN evidence headlines against every other
 *  pin's label key-tokens, skipping pairs the measured graph already links.
 *  Pure; feeds the isolation warning + the synthesis. */
export function buildFrozenCrossRefs(
  pins: WorkbenchPin[], data: ConnectionsData, max = 6,
): TextCrossRef[] {
  // pairs already linked by ANY measured edge → no warning needed.
  const nodeIdOf = new Map<string, string>()
  for (const n of data.nodes) {
    nodeIdOf.set(n.id, n.id)
    for (const raw of n.collapsed_from ?? []) nodeIdOf.set(raw, n.id)
  }
  const linked = new Set<string>()
  for (const e of data.edges) linked.add([e.a, e.b].sort().join('|'))

  const entries = pins.map(p => ({
    pin: p,
    nodeId: nodeIdOf.get(resolveThreadTopicId(p) ?? '') ?? null,
    headlines: (p.snapshot?.evidence ?? []).map(e => e.headline).filter(Boolean),
  }))
  const out: TextCrossRef[] = []
  for (const a of entries) {
    if (a.headlines.length === 0) continue
    for (const b of entries) {
      if (a === b || a.pin.label === b.pin.label) continue
      if (a.nodeId && b.nodeId) {
        if (a.nodeId === b.nodeId) continue
        if (linked.has([a.nodeId, b.nodeId].sort().join('|'))) continue
      }
      const tokens = labelKeyTokens(b.pin.label)
      for (const h of a.headlines) {
        const term = headlineMentionTerm(h, tokens)
        if (term) {
          out.push({ pinLabel: a.pin.label, otherLabel: b.pin.label, term, headline: h })
          break // one warning per pair is enough
        }
      }
      if (out.length >= max) return out
    }
  }
  return out
}

// ── Coverage lens (Frank v2 blocker 6) ────────────────────────────────────────
const LANG_NAMES: Record<string, string> = {
  en: 'English', ro: 'Romanian', es: 'Spanish', fr: 'French', de: 'German',
  ru: 'Russian', ar: 'Arabic', zh: 'Chinese', tr: 'Turkish', pt: 'Portuguese',
  it: 'Italian', fa: 'Persian', hi: 'Hindi', ja: 'Japanese', ko: 'Korean',
  uk: 'Ukrainian', pl: 'Polish', nl: 'Dutch', sv: 'Swedish', he: 'Hebrew',
  id: 'Indonesian', bn: 'Bengali', ur: 'Urdu', el: 'Greek', hu: 'Hungarian',
  cs: 'Czech', sr: 'Serbian', bg: 'Bulgarian', fi: 'Finnish', da: 'Danish',
  no: 'Norwegian', vi: 'Vietnamese', th: 'Thai',
}

/** Automatic lens note when a language dominates the pinned evidence — the
 *  report must acknowledge its vantage (math only, no LLM). Fires when any
 *  non-English language carries ≥30% of language-known evidence, or when
 *  English alone carries ≥80%. Null when coverage is balanced or too thin. */
export function coverageLensNote(
  languages: Array<{ lang: string; n: number }>, minTotal = 8,
): string | null {
  const total = languages.reduce((s, l) => s + l.n, 0)
  if (total < minTotal) return null
  const name = (l: { lang: string; n: number }) =>
    `${LANG_NAMES[l.lang] ?? l.lang.toUpperCase()}-language sources (${Math.round((l.n / total) * 100)}%)`
  const dominantNonEn = languages.filter(l => l.lang !== 'en' && l.n / total >= 0.3)
  if (dominantNonEn.length > 0) {
    const names = dominantNonEn.slice(0, 2).map(name).join(' and ')
    return `Coverage lens: this investigation's evidence leans ${names} — findings reflect that vantage.`
  }
  const en = languages.find(l => l.lang === 'en')
  if (en && en.n / total >= 0.8) {
    return `Coverage lens: this investigation's evidence is ${Math.round((en.n / total) * 100)}% English-language sources — findings reflect that vantage.`
  }
  return null
}

// ── Umbrella-fold guard (Frank v2 blocker 5) ──────────────────────────────────
/** Share of an umbrella's child topics whose label shares NO key token with the
 *  parent label — high divergence means the fold is NOT near-duplicates of one
 *  event (e.g. "Khamenei Funeral" under "Trump-Putin Talks"). Null when the
 *  umbrella exposes no child labels or the parent label has no key tokens. */
export function umbrellaChildDivergence(u: ConnectionNode): number | null {
  const childLabels = (u.facets ?? []).flatMap(f => f.topics.map(t => t.label))
  if (childLabels.length === 0) return null
  const parent = new Set(labelKeyTokens(u.label))
  if (parent.size === 0) return null
  // A child counts as coherent only on ≥2 shared key tokens — one shared token
  // ("Khamenei Funeral and Trump Threats" sharing just "trump" with
  // "Trump-Putin Talks on Ukraine") is exactly the garbage-fold signature.
  // Short labels (≤2 tokens) and 1-token parents settle for 1 shared token.
  const coherentChild = (l: string) => {
    const tokens = labelKeyTokens(l)
    const shared = tokens.filter(t => parent.has(t)).length
    return shared >= 2 || (shared >= 1 && (tokens.length <= 2 || parent.size <= 1))
  }
  const diverging = childLabels.filter(l => !coherentChild(l)).length
  return diverging / childLabels.length
}

/** Divergence above this → render "related topics grouped by the engine", never
 *  "near-duplicate fragments of one event". */
export const UMBRELLA_DIVERGENCE_MAX = 0.5

// ── Story windows (P0.3 dates) ────────────────────────────────────────────────
/** first_seen (or first evidence day) → last evidence day, ISO days. */
export function nodeStoryWindow(n: ConnectionNode): { first: string; last: string } | null {
  const days = (n.timeline ?? []).map(t => t.day)
  const last = days.length > 0 ? days[days.length - 1] : null
  const first = n.first_seen ? n.first_seen.slice(0, 10) : (days[0] ?? null)
  if (!first || !last) return null
  return { first, last }
}

/** The whole investigation's window: earliest first → latest last across nodes. */
export function investigationStoryWindow(nodes: ConnectionNode[]): { first: string; last: string } | null {
  const windows = nodes.map(nodeStoryWindow).filter((w): w is { first: string; last: string } => !!w)
  if (windows.length === 0) return null
  return {
    first: windows.map(w => w.first).sort()[0],
    last: windows.map(w => w.last).sort().slice(-1)[0],
  }
}

function fmtDayShort(isoDay: string): string {
  const d = new Date(isoDay.length === 10 ? `${isoDay}T00:00:00Z` : isoDay)
  if (Number.isNaN(d.getTime())) return isoDay
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

// ── Labels + export ─────────────────────────────────────────────────────────

const BASIS_LABEL: Record<ConnectionBasis, string> = {
  semantic: 'semantic proximity',
  shared_country: 'shared coverage country (context only)',
  shared_person: 'shared actor',
  text_mention: 'evidence-text mention',
  body_mention: 'article-body mention (fetched text)',
}

export function edgeReason(e: ConnectionEdge): string {
  const parts: string[] = []
  if (e.basis.includes('semantic')) {
    // Quote the DECISION-space number (whitened) when available — the raw
    // cosine reads ~99% for merely same-language pins and misled the
    // synthesis ("semantic similarity of 99%"). Raw stays on the payload for
    // any display that wants it, but the reason string reasons on whitened.
    if (e.whitened_sim !== null && e.whitened_sim !== undefined) {
      parts.push(`decorrelated similarity ${(e.whitened_sim * 100).toFixed(0)}%`)
    } else if (e.semantic_sim !== null) {
      parts.push(`semantic ${(e.semantic_sim * 100).toFixed(0)}%`)
    }
  }
  if (e.shared_countries.length) parts.push(`↔ ${e.shared_countries.join(', ')}`)
  if (e.shared_persons.length) parts.push(`↔ ${e.shared_persons.slice(0, 2).join(', ')}`)
  if ((e.text_mentions?.length ?? 0) > 0) {
    parts.push(`evidence text mentions “${e.text_mentions!.slice(0, 2).join('”, “')}”`)
  }
  if ((e.body_mentions?.length ?? 0) > 0) {
    parts.push(`article body mentions “${e.body_mentions!.slice(0, 2).join('”, “')}”`)
  }
  return parts.join(' · ') || e.basis.map(b => BASIS_LABEL[b]).join(' · ')
}

/** Connection findings as Markdown lines for the dossier export. `extras`
 *  carries the lens note + frozen-evidence cross-refs so the hover-less
 *  exported report keeps every honesty layer. */
export function connectionsSummaryLines(
  data: ConnectionsData, cluster: ClusterResult,
  extras?: { lensNote?: string | null; crossRefs?: TextCrossRef[] },
): string[] {
  const lines: string[] = []
  lines.push('## Connection analysis (measured at generation)')
  lines.push(
    `*How the ${data.nodes.length} pinned stories relate — semantic centroid `
    + 'proximity, coverage-country context, rarity-weighted shared actors, and evidence-'
    + 'text mentions. Positions approximate; relations measured.*',
  )
  if (extras?.lensNote) lines.push(`- *${extras.lensNote}*`)
  // Story windows (P0.3): firstSeen → last activity per pin.
  const windows = data.nodes
    .map(n => ({ label: n.label, w: nodeStoryWindow(n) }))
    .filter((x): x is { label: string; w: { first: string; last: string } } => !!x.w)
  if (windows.length > 0) {
    lines.push('- Story windows: ' + windows
      .map(x => `${x.label} ${fmtDayShort(x.w.first)} → ${fmtDayShort(x.w.last)}`)
      .join('; ') + '.')
  }
  if (cluster.clusters.length === 0 && cluster.isolated.length > 0) {
    lines.push('- No sub-narratives: every pinned story is isolated (no measured entity or text relation).')
  }
  // Aggregate verdict — distinguish actors, text, coverage context and semantic
  // proximity (the truth tier must survive to the exported,
  // hover-less report).
  if (cluster.clusters.length > 0) {
    const strengths = cluster.clusters.map(g => clusterStrength(g, data.edges))
    const confirmed = strengths.filter(s => s === 'confirmed').length
    const text = strengths.filter(s => s === 'text').length
    const context = strengths.filter(s => s === 'context').length
    const caution = strengths.length - confirmed - text - context
    lines.push(
      `- Of ${strengths.length} sub-narrative${strengths.length === 1 ? '' : 's'}, `
      + `${confirmed} confirmed by distinctive shared actors`
      + (text > 0 ? `, ${text} text-linked (headline text references the other story — verify)` : '')
      + (context > 0 ? `, ${context} coverage-context only (same coverage country; not subject identity or causality)` : '')
      + ` and ${caution} similarity-only (topic/language proximity, not a proven connection).`,
    )
  }
  cluster.clusters.forEach((g, i) => {
    const s = clusterStrength(g, data.edges)
    const tag = s === 'confirmed' ? '✓ CONFIRMED'
      : s === 'text' ? '✎ TEXT-LINKED'
        : s === 'context' ? '◇ COVERAGE CONTEXT' : '⚠ SIMILAR ONLY'
    const via = s === 'confirmed' ? sharedBasisNames(g, data.edges) : []
    const suffix = s === 'confirmed'
      ? (via.length ? ` Linked via ${via.join(', ')}.` : '')
      : s === 'text'
        ? ' No shared actors or places, but one story\'s evidence TEXT mentions the other — verify before treating as one narrative.'
        : s === 'context'
          ? ' The same country appears in coverage of both stories; this is context, not shared subject identity or causality.'
          : ' No shared actors or places — connection is semantic/topical proximity only; treat as a hypothesis.'
    lines.push(`- **${tag} — Sub-narrative ${i + 1}** (${g.length} stories): ${g.map(n => n.label).join('; ')}.${suffix}`)
  })
  if (cluster.isolated.length > 0) {
    lines.push(`- **Isolated** (connect to nothing pinned): ${cluster.isolated.map(n => n.label).join('; ')}.`)
  }
  // Frank v2 blocker 1: an isolation claim must never stand uncontradicted by a
  // frozen headline the report itself displays.
  for (const x of extras?.crossRefs ?? []) {
    lines.push(
      `- ⚠ **Verify before calling “${x.pinLabel}” unrelated**: entity extraction found no `
      + `overlap with “${x.otherLabel}”, but its frozen evidence text mentions “${x.term}” `
      + `(“${x.headline}”).`,
    )
  }
  const strong = data.edges.slice(0, 6)
  if (strong.length) {
    lines.push('- Strongest links:')
    for (const e of strong) {
      const a = data.nodes.find(n => n.id === e.a)?.label ?? e.a
      const b = data.nodes.find(n => n.id === e.b)?.label ?? e.b
      const s = edgeStrength(e)
      const mark = s === 'strong' ? '✓' : s === 'text' ? '✎' : s === 'context' ? '◇' : '≈'
      lines.push(`  - ${mark} ${a} ↔ ${b} — ${edgeReason(e)}`)
    }
  }
  if (data.unresolved.length) {
    lines.push(`- Not in the relation graph (no story centroid): ${data.unresolved.join(', ')}.`)
  }
  return lines
}
