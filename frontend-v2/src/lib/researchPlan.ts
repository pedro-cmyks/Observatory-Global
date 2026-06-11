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
  open?: { surface: string; params: Record<string, unknown> } | null
}

export interface CoverageGap {
  gap_type: string
  lane?: string
  axis?: string
  country_code?: string
  note: string
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
  downranking_ledger?: {
    candidate_count: number
    shown_count: number
    downranked_count: number
    omitted_count: number
    reason_codes: Record<string, number>
    appeal_action?: string
  }
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
