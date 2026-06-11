-- Migration 053: research_pin_events (Phase 2 day-one deliverable, #218)
--
-- Logs anchor impressions -> opens -> pins from research plans and Workbench.
-- These are graded relevance labels: the future calibration dataset for
-- research ranking (replaces spec-derived gold constraints with real
-- judgments), Paper 7 analyst-workflow evidence, and the input for
-- suggestion-guided search. Spec amendment P3 (2026-06-10): cheap at build
-- time, impossible to retrofit.
--
-- plan_id joins events back to the ranked anchor list: research-plan
-- responses carry a plan_id, and the cached plan payload (Redis, 120s) plus
-- the ranking_explanations embedded in the response preserve what was shown.
-- rank_shown is denormalized here so events survive cache expiry.
--
-- Single-user local deployment: no user identity column on purpose. Add an
-- investigation_id (client-generated, localStorage) so pins from different
-- investigations never silently mix (spec Workbench rule).

CREATE TABLE IF NOT EXISTS research_pin_events (
    id               BIGSERIAL PRIMARY KEY,
    plan_id          TEXT        NOT NULL,             -- research-plan response id
    investigation_id TEXT        NULL,                 -- client localStorage investigation
    anchor_id        TEXT        NOT NULL,             -- anchor id from the plan
    anchor_type      TEXT        NULL,                 -- thread/country/public_attention/...
    event_type       TEXT        NOT NULL
                     CHECK (event_type IN ('impression', 'open', 'pin', 'unpin', 'dismiss')),
    rank_shown       INT         NULL,                 -- position in the primary list (0-based)
    visibility       TEXT        NULL,                 -- primary | downranked
    investigative_score NUMERIC  NULL,                 -- score at render time
    query_text       TEXT        NULL,                 -- the originating query
    dwell_ms         INT         NULL,                 -- for open events, time on surface
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Calibration reads: all events for a plan, in order.
CREATE INDEX IF NOT EXISTS idx_research_pin_events_plan
    ON research_pin_events (plan_id, created_at);

-- Investigation reconstruction (server-side recovery of localStorage state).
CREATE INDEX IF NOT EXISTS idx_research_pin_events_investigation
    ON research_pin_events (investigation_id, created_at)
    WHERE investigation_id IS NOT NULL;

-- Relevance-label extraction: per-anchor outcome aggregation.
CREATE INDEX IF NOT EXISTS idx_research_pin_events_anchor
    ON research_pin_events (anchor_id, event_type);

ALTER TABLE research_pin_events ENABLE ROW LEVEL SECURITY;
-- No public policies on purpose: only the backend service role writes/reads.
