import type { PublicationPackage } from './investigationPublication'

export interface DailyPublicationEvidence {
  id?: string | number
  headline: string
  source_name?: string
  source_url?: string
  source_lang?: string | null
  timestamp?: string | null
  country_code?: string | null
  /** OUTLET origin (source_origin_country) — sealed rows carry it. */
  source_origin_country?: string | null
}

export interface DailyPublicationStoryNode {
  node_id: string
  node_type: string
  label: string
  live_ref: { kind: string; id: string }
  snapshot: {
    edition_role?: 'lead' | 'supporting' | string
    live?: {
      thread_id?: string
      signal_count?: number
      source_count?: number
      top_countries?: string[]
      movement?: {
        velocity?: number
        surprise?: number
        prediction_claim?: boolean
      }
      evidence_samples?: DailyPublicationEvidence[]
    }
  }
}

export interface DailyPublicationArtifact {
  contract: 'atlas-daily-publication-v1'
  edition_date: string | null
  /** Seal moment (generated_at) surfaced top-level for the staleness banner. */
  sealed_at?: string | null
  /** Council N10: next-attempt truth from the actual launchd schedule
   * constant — never a hardcoded banner promise. */
  seal_schedule?: {
    next_attempt_at?: string | null
    next_attempt_local?: string
    attempt_window_open?: boolean
    basis?: string
  } | null
  status: 'ready' | 'degraded' | string
  graph: {
    contract: 'atlas-investigation-graph-v1'
    nodes: DailyPublicationStoryNode[]
    edges: Array<Record<string, unknown>>
    completion: { truncated?: boolean; [key: string]: unknown }
  }
  package: PublicationPackage
  completion: {
    cursor_exhausted?: boolean
    truncated?: boolean
    candidate_count?: number
    rows_scanned?: number
    data_lag_hours?: number
    edition_start?: string
    edition_end?: string
    [key: string]: unknown
  }
}

export interface DailyPublicationThread {
  thread_id: string
  label: string
  signal_count: number
  source_count?: number
  top_countries?: string[]
  why_now?: string
  edition_role?: string
  // Edition sectioning (briefEdition.ts): the sealed graph does not carry a
  // category today — optional so the Brief's culture-lane split type-checks
  // and simply falls back to label keywords for shared-package threads.
  category?: string | null
  parent_domain?: string | null
  changed_10h?: number
  trend?: string
  hourly_timeline?: Array<{ hour: string; count: number; avg_sentiment: number }>
  evidence_samples?: Array<{
    id?: string | number
    headline: string
    source?: string
    url?: string
    source_lang?: string | null
    timestamp?: string | null
    /** Story SUBJECT/coverage country — never rendered as origin (N1). */
    country_code?: string | null
    /** OUTLET origin (source_origin_country) — basis for the origin chip. */
    source_origin_country?: string | null
  }>
}

/** Compatibility gate for the L1 cutover. A degraded or incomplete shared
 * artifact never silently replaces the known newspaper. The fallback remains
 * explicit while the full-universe builder catches up. */
export function assessDailyPublication(artifact: DailyPublicationArtifact | null): {
  useSharedPackage: boolean
  reasonCodes: string[]
} {
  if (!artifact) return { useSharedPackage: false, reasonCodes: ['edition_unavailable'] }
  const reasonCodes: string[] = []
  if (artifact.contract !== 'atlas-daily-publication-v1'
    || artifact.graph?.contract !== 'atlas-investigation-graph-v1'
    || artifact.package?.contract !== 'atlas-publication-package-v1') {
    reasonCodes.push('contract_mismatch')
  }
  if (artifact.status !== 'ready') reasonCodes.push('edition_degraded')
  if (!artifact.completion?.cursor_exhausted
    || artifact.completion?.truncated
    || artifact.graph?.completion?.truncated) {
    reasonCodes.push('candidate_universe_incomplete')
  }
  if (!artifact.graph?.nodes?.some(node => node.node_type === 'story')) {
    reasonCodes.push('no_story_nodes')
  }
  return { useSharedPackage: reasonCodes.length === 0, reasonCodes }
}

function movementLine(node: DailyPublicationStoryNode): string | undefined {
  const movement = node.snapshot.live?.movement
  const bits: string[] = []
  if (typeof movement?.velocity === 'number') {
    bits.push(`velocity ${movement.velocity >= 0 ? '+' : ''}${movement.velocity.toFixed(4)}`)
  }
  if (typeof movement?.surprise === 'number') bits.push(`surprise ${movement.surprise.toFixed(4)}`)
  if (bits.length === 0) return undefined
  return `Measured movement: ${bits.join(' · ')}. Not a forecast.`
}

/** Maps the shared graph into the current newspaper row contract without
 * re-ranking or dropping story nodes. Layout order is the sealed graph order. */
export function publicationThreads(artifact: DailyPublicationArtifact | null): DailyPublicationThread[] {
  if (!artifact) return []
  return artifact.graph.nodes
    .filter(node => node.node_type === 'story' && node.live_ref?.id)
    .map(node => {
      const live = node.snapshot.live ?? {}
      return {
        thread_id: live.thread_id ?? node.live_ref.id,
        label: node.label,
        signal_count: live.signal_count ?? 0,
        ...(typeof live.source_count === 'number' ? { source_count: live.source_count } : {}),
        ...(live.top_countries ? { top_countries: live.top_countries } : {}),
        ...(node.snapshot.edition_role ? { edition_role: node.snapshot.edition_role } : {}),
        ...(movementLine(node) ? { why_now: movementLine(node) } : {}),
        evidence_samples: (live.evidence_samples ?? []).map(receipt => ({
          id: receipt.id,
          headline: receipt.headline,
          source: receipt.source_name,
          url: receipt.source_url,
          source_lang: receipt.source_lang,
          timestamp: receipt.timestamp,
          country_code: receipt.country_code,
          // N1: the sealed rows carry the outlet's recorded origin
          // (_DAILY_EVIDENCE_SQL selects source_origin_country) — thread it
          // through so sealed receipts render honest origin chips too.
          source_origin_country: receipt.source_origin_country,
        })),
      }
    })
}
