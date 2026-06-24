-- Migration 055: dynamic_topic label refresh metadata (#229 lever 5, 2026-06-24)
--
-- Labels were frozen at topic creation, so an evolving story kept a stale or
-- (worse) hallucinated label long after its members drifted — e.g. a single
-- outlet's wire dump carried the label "Russian Shadow Fleet Interceptions"
-- (#214). The relabel cron (scripts/relabel_dynamic_topics.py) refreshes active
-- topic labels on a cadence using the LOCAL Claude CLI (Max subscription, $0
-- marginal — no external DeepSeek call). These columns let it pick stale rows
-- and record provenance.
--
-- Additive and nullable: existing rows read as "never refreshed" (label_updated_at
-- IS NULL) so the first cron pass treats them as due.

ALTER TABLE dynamic_topics
    ADD COLUMN IF NOT EXISTS label_updated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS label_model      TEXT;

-- The cron scans for stale labels by age.
CREATE INDEX IF NOT EXISTS idx_dynamic_topics_label_updated_at
    ON dynamic_topics (label_updated_at);
