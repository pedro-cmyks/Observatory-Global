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
  /** State-controlled/affiliated outlet (signals_v2.is_state_media) — a sealed
   *  receipt from RT/Sputnik/IRNA is flagged, never presented as neutral (R3 P0). */
  is_state_media?: boolean | null
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
  /** Optional grading the backend may attach to a degraded seal (T3.3): read
   *  defensively and shown verbatim — this page never needs to know the codes,
   *  only that a reason it did not author must still reach the reader. */
  status_reasons?: string[] | null
  status_reason?: string | null
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
    /** State-media flag threaded from the sealed receipt (R3 P0). */
    is_state_media?: boolean | null
  }>
}

/**
 * How old a seal may be and still be TODAY'S edition.
 *
 * The seal runs nightly at 02:30 local; 26 h is that cadence plus a two-hour
 * grace, so a night that ran late still serves its edition and a night that
 * never ran at all falls through to the live view instead of serving
 * yesterday's front page as today's.
 */
export const SEAL_FRESH_MAX_HOURS = 26

export interface EditionServing {
  /** What the newspaper is built from. */
  serve: 'sealed' | 'live'
  /** Hours since the seal, or null when it carries no readable seal moment. */
  ageHours: number | null
  fresh: boolean
  /** Why the live view is served (empty when the seal is). */
  reasonCodes: string[]
  /** Visible labels for a SERVED but degraded sealed edition. */
  degradation: string[]
}

/**
 * What a SERVED sealed edition has to admit about itself.
 *
 * Derived from fields the payload already carries — the 5W+H readiness map, the
 * completion flags — plus anything the backend chose to grade it with. Every
 * entry is rendered next to the edition, because under the T3.3 policy a
 * degraded seal is no longer hidden behind a fallback: it is published, and the
 * reader is told exactly how it is incomplete.
 */
export function editionDegradationLabels(artifact: DailyPublicationArtifact | null): string[] {
  if (!artifact) return []
  const labels: string[] = []

  if (artifact.status !== 'ready') {
    const readiness = artifact.package?.readiness
    const cells = readiness ? Object.values(readiness) : []
    // `partial` is counted separately rather than folded into "answered" — a
    // half-answered question is not an answered one, and the edition is already
    // admitting incompleteness here.
    const answered = cells.filter(cell => cell?.status === 'ready').length
    const partial = cells.filter(cell => cell?.status === 'partial').length
    labels.push(cells.length > 0
      ? `partial edition · ${answered} of ${cells.length} answered${partial > 0 ? `, ${partial} partial` : ''}`
      : 'partial edition')
  }
  if (artifact.completion?.truncated || artifact.graph?.completion?.truncated) {
    labels.push('candidate universe truncated')
  }
  if (artifact.completion && artifact.completion.cursor_exhausted === false) {
    labels.push('candidate scan did not finish')
  }
  for (const reason of [
    ...(artifact.status_reasons ?? []),
    ...(artifact.status_reason ? [artifact.status_reason] : []),
  ]) {
    const text = (reason ?? '').trim()
    if (text && !labels.includes(text)) labels.push(text)
  }
  return labels
}

/**
 * Decide what the front page is built from (T3.3, serving policy (b)).
 *
 * FRESHNESS decides, not status. The old gate (`assessDailyPublication`) refused
 * any seal that was not perfectly `ready` and complete — and measured on the
 * real record, 25 of 25 consecutive editions sealed `degraded`, so the gate had
 * quietly become "never serve the edition". A curated-but-incomplete edition
 * that says how it is incomplete beats a live list that was never edited; the
 * degradation becomes a visible label instead of a silent fallback.
 *
 * Freshness cannot override UNREADABLE, though. A wrong contract or an edition
 * with no story nodes is not a degraded newspaper, it is no newspaper: serving
 * it would render an empty front page. Those still fall through to live, with
 * the reason named.
 */
export function resolveEditionServing(
  artifact: DailyPublicationArtifact | null,
  now: Date = new Date(),
): EditionServing {
  if (!artifact) {
    return { serve: 'live', ageHours: null, fresh: false, reasonCodes: ['edition_unavailable'], degradation: [] }
  }

  const unreadable: string[] = []
  if (artifact.contract !== 'atlas-daily-publication-v1'
    || artifact.graph?.contract !== 'atlas-investigation-graph-v1'
    || artifact.package?.contract !== 'atlas-publication-package-v1') {
    unreadable.push('contract_mismatch')
  }
  if (!artifact.graph?.nodes?.some(node => node.node_type === 'story')) {
    unreadable.push('no_story_nodes')
  }

  const sealedAt = artifact.sealed_at
    ?? (artifact.completion?.generated_at as string | undefined)
    ?? null
  const sealedMs = sealedAt ? new Date(sealedAt).getTime() : NaN
  const ageHours = Number.isFinite(sealedMs)
    ? (now.getTime() - sealedMs) / 3_600_000
    : null
  const fresh = ageHours !== null && ageHours >= -1 && ageHours < SEAL_FRESH_MAX_HOURS

  const reasonCodes = [...unreadable]
  if (ageHours === null) reasonCodes.push('seal_time_unknown')
  else if (!fresh) reasonCodes.push('seal_stale')

  if (reasonCodes.length > 0) {
    return { serve: 'live', ageHours, fresh, reasonCodes, degradation: [] }
  }
  return {
    serve: 'sealed',
    ageHours: ageHours === null ? null : Math.floor(ageHours),
    fresh: true,
    reasonCodes: [],
    degradation: editionDegradationLabels(artifact),
  }
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
          // R3 P0: authoritative state-media flag (ingest is_state_media) rides
          // to the receipt chip so a state outlet is never shown as neutral.
          is_state_media: receipt.is_state_media,
        })),
      }
    })
}
