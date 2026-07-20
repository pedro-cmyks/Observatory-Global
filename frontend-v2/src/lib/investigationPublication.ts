// Workbench → Investigation Graph → PublicationPackage bridge.
//
// This is the shared editorial contract between an analyst-authored L3 report
// and the system-authored L1 edition. It is deliberately LLM-free: pins are
// normalized, relations are measured by the backend, and 5W+H readiness is a
// transparent inventory of receipts and gaps. Prose generation remains a
// separate final step.
import type { Investigation, WorkbenchPin } from './workbench'
import { resolveThreadTopicId } from './dossierEnrichment'

export type InvestigationNodeType =
  | 'story' | 'evidence' | 'subject' | 'country' | 'source'
  | 'event' | 'anomaly' | 'attention' | 'asset' | 'temporal_slice'

export interface ResolveNodeInput {
  node_type: InvestigationNodeType
  subtype: string
  ref_id: string
  label: string
  observation_window: {
    range_start: string
    range_end: string
    cursor_at?: string
    mode: 'live' | 'historical'
  }
  snapshot: Record<string, unknown>
  analyst_note: string | null
  quality: Record<string, unknown>
}

export interface InvestigationNode extends ResolveNodeInput {
  contract: 'atlas-investigation-v2'
  node_id: string
  live_ref: { kind: string; id: string }
  pinned_at: string
  resolution_status: 'resolved' | 'partial' | 'metadata_only' | 'unavailable'
  resolution_receipt: {
    adapter: string
    resolved_at: string
    retryable: boolean
    caveat: string | null
  }
}

export interface InvestigationGraph {
  contract: 'atlas-investigation-graph-v1'
  nodes: InvestigationNode[]
  edges: Array<Record<string, unknown>>
  suggestions: Array<Record<string, unknown>>
  relation_context: Record<string, unknown>
  unresolved_ledger: string[]
  completion: {
    requested_nodes: number
    resolved_nodes: number
    requested_pairs: number
    processed_pairs: number
    engines: Record<string, 'complete' | 'degraded' | 'unavailable'>
    truncated: boolean
  }
  measured_at: string
}

export type ReadinessStatus = 'ready' | 'partial' | 'missing'

export interface PublicationReadinessItem {
  status: ReadinessStatus
  values: string[]
  reason_codes: string[]
}

export interface PublicationPackage {
  contract: 'atlas-publication-package-v1'
  title: string
  authorship: 'system' | 'analyst'
  generated_at: string
  readiness: Record<'who' | 'what' | 'when' | 'where' | 'how' | 'why', PublicationReadinessItem>
  narrative_spine: Array<Record<string, unknown>>
  who_says_what: Record<string, unknown>
  corroboration?: Record<string, unknown> | null
  gaps: string[]
  receipts: Array<Record<string, unknown>>
  method: Record<string, unknown>
  reproducibility: Record<string, unknown>
  selection_ledger?: Record<string, unknown> | null
  prose_status: 'not_requested' | 'generated' | 'unavailable'
  article: Record<string, unknown> | null
  /** Enrichment bridge (spec 2026-07-20): server-fetched page excerpts for the
   *  edition's receipt URLs, frozen at seal time. Absent on pre-bridge editions. */
  article_enrichment?: {
    contract?: string
    yield?: { ok: number; attempted: number }
    note?: string
    articles?: Record<string, {
      status?: string
      via?: string
      excerpt?: string | null
      outlet?: string | null
      fetched_at?: string | null
    }>
  } | null
  /** Cross-read over the LEAD story's fetched bodies — possible corroborations/
   *  tensions with verbatim quotes. Absent when not run / nothing readable. */
  coverage_check?: {
    findings?: Array<{
      kind: 'corroboration' | 'tension'
      a: { url: string; text: string; quote: string }
      b: { url: string; text: string; quote: string }
      note: string
    }>
    articles_read?: number
    articles_with_claims?: number
    model?: string
    note?: string
    story_id?: string
  } | null
}

export interface InvestigationPublicationResult {
  graph: InvestigationGraph
  package: PublicationPackage
}

function param(pin: WorkbenchPin, name: string): string | null {
  const params = (pin.open?.params ?? {}) as Record<string, unknown>
  if (params[name] !== undefined && params[name] !== null) return String(params[name])
  if (typeof params.urlParams === 'string') {
    return new URLSearchParams(params.urlParams.replace(/^\?/, '')).get(name)
  }
  return null
}

function strippedRef(pin: WorkbenchPin, prefixes: string[]): string {
  for (const prefix of prefixes) {
    if (pin.anchorId.toLowerCase().startsWith(prefix.toLowerCase())) {
      return pin.anchorId.slice(prefix.length)
    }
  }
  return pin.anchorId
}

function nodeIdentity(pin: WorkbenchPin): {
  node_type: InvestigationNodeType
  subtype: string
  ref_id: string
  mapping_status: 'canonical' | 'explicit_context'
} {
  const kind = pin.anchorType.trim().toLowerCase().replace(/[\s-]+/g, '_')
  const threadId = resolveThreadTopicId(pin)
  if (threadId || ['thread', 'theme', 'story', 'narrative_thread'].includes(kind)) {
    return { node_type: 'story', subtype: 'thread', ref_id: threadId ?? pin.anchorId, mapping_status: 'canonical' }
  }
  if (kind === 'country') {
    return {
      node_type: 'country', subtype: 'country',
      ref_id: (param(pin, 'country_code') ?? param(pin, 'country') ?? strippedRef(pin, ['country-'])).toUpperCase(),
      mapping_status: 'canonical',
    }
  }
  if (['signal', 'evidence', 'news', 'article'].includes(kind)) {
    return {
      node_type: 'evidence', subtype: 'signal',
      ref_id: param(pin, 'signal_id') ?? strippedRef(pin, ['signal-', 'news-', 'article-']),
      mapping_status: 'canonical',
    }
  }
  if (kind === 'person') return { node_type: 'subject', subtype: 'person', ref_id: pin.anchorId, mapping_status: 'canonical' }
  if (['entity', 'actor', 'subject', 'organization', 'place'].includes(kind)) {
    return { node_type: 'subject', subtype: kind, ref_id: pin.anchorId, mapping_status: 'canonical' }
  }
  if (['source', 'outlet'].includes(kind)) return { node_type: 'source', subtype: 'outlet', ref_id: pin.anchorId, mapping_status: 'canonical' }
  if (['natural_hazard', 'hazard', 'conflict_event', 'event'].includes(kind)) {
    return { node_type: 'event', subtype: kind, ref_id: pin.anchorId, mapping_status: 'canonical' }
  }
  if (['anomaly', 'anomaly_alert', 'baseline_spike'].includes(kind)) {
    return { node_type: 'anomaly', subtype: kind, ref_id: pin.anchorId, mapping_status: 'canonical' }
  }
  if (['aircraft', 'flight', 'ship', 'vessel', 'asset'].includes(kind)) {
    return { node_type: 'asset', subtype: kind, ref_id: pin.anchorId, mapping_status: 'canonical' }
  }
  if (['time', 'temporal_slice', 'historical_window'].includes(kind)) {
    return { node_type: 'temporal_slice', subtype: kind, ref_id: pin.anchorId, mapping_status: 'canonical' }
  }
  if (['public_attention', 'attention', 'forum'].includes(kind)) {
    return { node_type: 'attention', subtype: kind, ref_id: pin.anchorId, mapping_status: 'canonical' }
  }
  // Research branches, gaps and future L2 pin types remain visible as explicit
  // context. We do not guess that an unknown label is a person, place or story.
  return { node_type: 'attention', subtype: kind || 'context_anchor', ref_id: pin.anchorId, mapping_status: 'explicit_context' }
}

function observationWindow(pin: WorkbenchPin): ResolveNodeInput['observation_window'] {
  const endDate = new Date(pin.pinnedAt)
  const safeEnd = Number.isNaN(endDate.getTime()) ? new Date() : endDate
  const candidates = (pin.snapshot?.evidence ?? [])
    .map(row => row.date ? new Date(row.date.length === 10 ? `${row.date}T00:00:00.000Z` : row.date) : null)
    .filter((value): value is Date => value !== null && !Number.isNaN(value.getTime()) && value <= safeEnd)
  const start = candidates.length
    ? new Date(Math.min(...candidates.map(value => value.getTime())))
    : new Date(safeEnd.getTime() - 24 * 60 * 60 * 1000)
  const cursor = param(pin, 'cursor_at') ?? param(pin, 'cursor')
  const cursorDate = cursor ? new Date(cursor) : null
  const validCursor = cursorDate && !Number.isNaN(cursorDate.getTime()) && cursorDate >= start && cursorDate <= safeEnd
    ? cursorDate.toISOString()
    : undefined
  return {
    range_start: start.toISOString(),
    range_end: safeEnd.toISOString(),
    ...(validCursor ? { cursor_at: validCursor } : {}),
    mode: validCursor ? 'historical' : 'live',
  }
}

export function buildResolveNodeInput(pin: WorkbenchPin): ResolveNodeInput {
  const identity = nodeIdentity(pin)
  const evidence = (pin.snapshot?.evidence ?? []).map(row => ({
    ...row,
    source_name: row.source,
    source_url: row.url,
  }))
  return {
    node_type: identity.node_type,
    subtype: identity.subtype,
    ref_id: identity.ref_id,
    label: pin.label,
    observation_window: observationWindow(pin),
    snapshot: {
      captured_at: pin.snapshot?.capturedAt ?? pin.pinnedAt,
      summary: pin.snapshot?.summary,
      metrics: pin.snapshot?.metrics ?? {},
      country_code: pin.snapshot?.countryCode,
      evidence,
      anchor_type: pin.anchorType,
      retrieval_lane: pin.retrievalLane,
      open: pin.open ?? null,
    },
    analyst_note: pin.note ?? null,
    quality: {
      mapping_status: identity.mapping_status,
      match_basis: pin.matchBasis,
      investigative_score: pin.investigativeScore,
      category_lens: pin.category,
    },
  }
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(`${url}:${response.status}`)
  return await response.json() as T
}

/** Resolve every pin. There is deliberately no semantic top-N selection here:
 * all pins enter the graph, while backend completion ledgers disclose any
 * unavailable relation engine. */
export async function buildInvestigationPublication(
  investigation: Investigation,
  title = investigation.title,
): Promise<InvestigationPublicationResult | null> {
  if (investigation.pins.length === 0) return null
  try {
    const resolved = await postJson<{
      nodes: InvestigationNode[]
      completion: { requested: number; processed: number; truncated: boolean }
    }>('/api/v2/investigation/resolve-nodes', {
      nodes: investigation.pins.map(buildResolveNodeInput),
    })
    const nodes = resolved.nodes
    const graph = await postJson<InvestigationGraph>('/api/v2/investigation/graph', {
      nodes,
      enabled_engines: ['exact', 'context'],
      relation_payloads: {},
    })
    const publicationPackage = await postJson<PublicationPackage>(
      '/api/v2/investigation/publication-package',
      {
        title,
        authorship: 'analyst',
        graph,
        input_gaps: [],
      },
    )
    return { graph, package: publicationPackage }
  } catch {
    return null
  }
}

const QUESTION_LABELS: Record<keyof PublicationPackage['readiness'], string> = {
  who: 'Who', what: 'What', when: 'When', where: 'Where', how: 'How', why: 'Why',
}

export function readableReasonCode(code: string): string {
  return code.replaceAll('_', ' ')
}

export function buildPublicationReadinessMarkdown(pkg: PublicationPackage): string {
  const lines = ['## Editorial readiness (5W+H)', '']
  for (const key of ['who', 'what', 'when', 'where', 'how', 'why'] as const) {
    const item = pkg.readiness[key]
    const details = [...item.values, ...item.reason_codes.map(readableReasonCode)]
    lines.push(`- **${QUESTION_LABELS[key]} — ${item.status}**${details.length ? `: ${details.join(' · ')}` : ''}`)
  }
  if (pkg.gaps.length > 0) {
    lines.push('', `**Graph/package gaps:** ${pkg.gaps.map(readableReasonCode).join(' · ')}`)
  }
  lines.push('')
  return lines.join('\n')
}

/** One inspectable typed relation between two pinned nodes. */
export interface InvestigationEdgeRow {
  relation: string
  tier: string
  source: string
  target: string
  receiptCount: number
  caveats: string[]
}

const EDGE_TIER_ORDER: Record<string, number> = {
  measured: 0, analyst: 1, inferred: 2, contextual: 3,
}

function humanizeRelation(raw: string): string {
  const cleaned = raw.replace(/_/g, ' ').trim()
  return cleaned ? cleaned.charAt(0).toUpperCase() + cleaned.slice(1) : raw
}

/**
 * Turn the graph's typed edges into inspectable rows: which relation connects
 * which two pinned nodes, its truth tier, its receipt count and caveats. Node
 * ids resolve to their labels; rows sort by tier (measured first) so the
 * strongest relations lead. This makes the connection layer inspectable
 * instead of a bare relation count.
 */
export function summarizeInvestigationEdges(graph: InvestigationGraph): InvestigationEdgeRow[] {
  const labels = new Map<string, string>()
  for (const node of graph.nodes ?? []) {
    if (node.node_id) labels.set(node.node_id, node.label ?? node.node_id)
  }
  const rows: InvestigationEdgeRow[] = (graph.edges ?? []).map(edge => {
    const receipts = Array.isArray(edge.receipts) ? edge.receipts : []
    const caveats = Array.isArray(edge.caveats) ? edge.caveats.map(String) : []
    const source = String(edge.source_node_id ?? '')
    const target = String(edge.target_node_id ?? '')
    return {
      relation: humanizeRelation(String(edge.relation_type ?? 'related')),
      tier: String(edge.truth_tier ?? 'contextual'),
      source: labels.get(source) ?? source,
      target: labels.get(target) ?? target,
      receiptCount: receipts.length,
      caveats,
    }
  })
  rows.sort((a, b) =>
    (EDGE_TIER_ORDER[a.tier] ?? 9) - (EDGE_TIER_ORDER[b.tier] ?? 9) ||
    a.relation.localeCompare(b.relation) ||
    a.source.localeCompare(b.source),
  )
  return rows
}

/** Portable typed-relations section for the exported dossier. Empty when the
 * graph has no measured/inferred/contextual relation. */
export function buildRelationsMarkdown(graph: InvestigationGraph): string {
  const rows = summarizeInvestigationEdges(graph)
  if (rows.length === 0) return ''
  const lines = ['## Typed relations', '']
  for (const row of rows) {
    const receipt = row.receiptCount === 1 ? '1 receipt' : `${row.receiptCount} receipts`
    const caveat = row.caveats.length ? ` · ${row.caveats.map(readableReasonCode).join(' · ')}` : ''
    lines.push(`- **${row.relation}** (${row.tier}) — ${row.source} ↔ ${row.target} · ${receipt}${caveat}`)
  }
  lines.push('')
  return lines.join('\n')
}
