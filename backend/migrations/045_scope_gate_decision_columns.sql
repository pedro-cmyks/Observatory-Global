-- Migration 045 — scope-gate decision columns on signal_topic_assignments.
--
-- The Phase B scope gate (embedding + Atlas-confidence logistic, multilingual
-- e5-base, per-topic calibrated to >=90% precision on the 3-vendor LLM
-- consensus corpus) judges whether an Atlas topic assignment is real evidence
-- (keep) or only context/noise (abstain). These columns persist that decision
-- so the API can serve gated, high-precision topic counts alongside the raw
-- lexicon counts.
--
-- Design:
--   * Additive + nullable -> reversible (DROP COLUMN) and fully back-compat.
--     Existing readers ignore the columns; gate_kept IS NULL = not yet scored,
--     which the API treats as "keep" (COALESCE(gate_kept, TRUE)) so the
--     surface never empties during backfill.
--   * Scoring runs locally (off-iCloud mlvenv + e5-base, $0/signal, MPS)
--     alongside the atlas-classifier cron: backfill_lexicon_topics.py writes
--     the assignment, score_assignments_gate.py fills these columns.
--   * RLS: signal_topic_assignments already has RLS enabled (migration 030).
--     Adding columns does not change the policy; the backend connects as
--     postgres (bypasses RLS), anon/authenticated remain locked out.

ALTER TABLE signal_topic_assignments
    ADD COLUMN IF NOT EXISTS gate_score  DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS gate_kept   BOOLEAN,
    ADD COLUMN IF NOT EXISTS gate_model  TEXT;

-- Partial index for the API's gated ranking: only the kept rows are scanned.
-- Stays small (kept rows are the minority) and matches the briefing filter
-- (model_version + assigned_at window).
CREATE INDEX IF NOT EXISTS idx_sta_gate_kept
    ON signal_topic_assignments (model_version, assigned_at)
    WHERE gate_kept = TRUE;

COMMENT ON COLUMN signal_topic_assignments.gate_score IS
    'Scope-gate P(evidence) in [0,1]; NULL = not yet scored.';
COMMENT ON COLUMN signal_topic_assignments.gate_kept IS
    'Scope-gate keep decision (score >= per-topic 90%-precision threshold); NULL = not scored.';
COMMENT ON COLUMN signal_topic_assignments.gate_model IS
    'Gate artifact id, e.g. atlas-scope-gate-v1-e5base.';
