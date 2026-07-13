// Research plan API client (Phase 1a/1b/1.5 backend) + pin-event telemetry
// (#218). Telemetry is fire-and-forget: a failure must never interrupt the
// investigation UI.

export interface ResearchAnchor {
  anchor_type: string
  lane: string
  retrieval_lane?: string
  match_basis?: string
  id: string
  label: string
  evidence_label: 'direct_evidence' | 'context' | 'weak_support' | 'gap'
  matched_terms: string[]
  semantic_similarity?: number
  signal_count?: number
  investigative_score?: number
  visibility?: 'primary' | 'downranked'
  /** research-plan-v1 (W2d): R3 category lens. */
  category?: string | null
  crisis_relevant?: boolean | null
  /** research-plan-v1 (W2c): shared Kalman movement, changed_10h fallback. */
  movement?: {
    source: 'kalman-topic-movement' | 'changed_10h'
    velocity?: number | null
    surprise?: number | null
    trend?: string | null
    changed_10h?: number
  }
  open?: { surface: string; params: Record<string, unknown> } | null
}

export interface CoverageGap {
  gap_type: string
  lane?: string
  axis?: string
  country_code?: string
  note: string
}

export interface SemanticEvidenceItem {
  signal_id: number
  headline: string
  country_code?: string | null
  source_name?: string | null
  timestamp?: string | null
  similarity: number
  /** research-plan-v1 (W2b): two-tier gate labels (was assigned|below_gate). */
  gate_status: 'verified' | 'extended' | 'assigned' | 'below_gate'
  topic_slug?: string | null
  retrieval_lane: string
  match_basis: string
}

export interface ResearchPlan {
  contract: string
  plan_id?: string
  query: string
  hours: number
  intent: {
    main_intent: string
    geo_scope: string[]
    topic_axes: string[]
    subquestions: string[]
    branches: string[]
  }
  anchors: ResearchAnchor[]
  low_confidence_tray: ResearchAnchor[]
  pin_candidates: string[]
  coverage_gaps: CoverageGap[]
  suggested_next_steps: string[]
  semantic_evidence?: SemanticEvidenceItem[]
  downranking_ledger?: {
    candidate_count: number
    shown_count: number
    primary_count?: number
    downranked_count: number
    omitted_count: number
    accessible_count?: number
    complete?: boolean
    semantic_ceiling?: boolean
    reason_codes: Record<string, number>
    appeal_action?: string
  }
}

export function researchLedgerSummary(
  ledger: NonNullable<ResearchPlan['downranking_ledger']>,
): string {
  const primary = ledger.primary_count ?? ledger.shown_count
  const accessible = ledger.accessible_count
    ?? primary + ledger.downranked_count + ledger.omitted_count
  const completion = ledger.complete && ledger.omitted_count === 0
    ? 'complete · no candidates excluded'
    : ledger.complete === false
      ? 'partial ledger · lane degradation disclosed'
      : `${ledger.omitted_count} excluded with disclosed reasons`
  return [
    `${ledger.candidate_count} candidates evaluated`,
    `${primary} primary`,
    `${ledger.downranked_count} low confidence`,
    `${accessible} accessible`,
    completion,
  ].join(' · ')
}

export async function fetchResearchPlan(
  query: string,
  opts: { hours?: number; countryCode?: string | null } = {},
): Promise<ResearchPlan> {
  const res = await fetch('/api/v2/research/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      hours: opts.hours ?? 168,
      ...(opts.countryCode ? { country_code: opts.countryCode } : {}),
    }),
  })
  if (!res.ok) throw new Error(`research plan HTTP ${res.status}`)
  return res.json() as Promise<ResearchPlan>
}

// Archive activity for a STORY query (time-as-dimension, #236). The research
// plan is hot-only (~7d); this reaches the processed archive (~61 days) so the
// panel can plot when a topic spiked and jump to a past day's receipts.
export interface StoryHistoryDayItem {
  tier: 'archive'
  cluster_label: string
  headlines: string[]
  n_signals: number
  sim: number
  top_cc: string[]
}

export interface StoryHistory {
  contract: string
  available: boolean
  reason?: string
  label?: string
  match_tau?: number
  matched_units?: number
  horizon?: { min_day: string; max_day: string; days: number } | null
  series?: Array<{ day: string; units: number; signals: number; peak_sim?: number }>
  day?: { date: string; items: StoryHistoryDayItem[]; empty_reason?: string | null }
}

export async function fetchStoryHistory(
  query: string,
  opts: { day?: string } = {},
): Promise<StoryHistory> {
  const params = new URLSearchParams({ query })
  if (opts.day) params.set('day', opts.day)
  const res = await fetch(`/api/v2/research/history?${params.toString()}`)
  if (!res.ok) throw new Error(`story history HTTP ${res.status}`)
  return res.json() as Promise<StoryHistory>
}

export interface PinEventInput {
  anchor_id: string
  event_type: 'impression' | 'open' | 'pin' | 'unpin' | 'dismiss'
  anchor_type?: string
  rank_shown?: number
  visibility?: string
  investigative_score?: number
  dwell_ms?: number
}

export function sendPinEvents(
  planId: string,
  events: PinEventInput[],
  opts: { investigationId?: string | null; queryText?: string } = {},
): void {
  if (!planId || events.length === 0) return
  try {
    void fetch('/api/v2/research/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plan_id: planId,
        investigation_id: opts.investigationId ?? null,
        query_text: opts.queryText,
        events,
      }),
      keepalive: true, // survives panel unmount / tab close
    }).catch(() => undefined)
  } catch {
    // telemetry only — never interrupt the UI
  }
}

export function impressionEvents(plan: ResearchPlan): PinEventInput[] {
  return plan.anchors.map((a, i) => ({
    anchor_id: a.id,
    event_type: 'impression' as const,
    anchor_type: a.anchor_type,
    rank_shown: i,
    visibility: a.visibility ?? 'primary',
    investigative_score: a.investigative_score,
  }))
}
