-- 080_label_court.sql
-- LABEL COURT (#204/#224, council Move 1): a nightly DeepSeek entailment check
-- of every ACTIVE dynamic topic's served label against its own receipts
-- (topic_members evidence headlines).
--
--   label_status      = the court verdict: 'entailed' (label describes the
--                       majority of receipts), 'partial', or 'failed' (the
--                       dt-320 "17-Year-Old British Teen Fall"-over-Greek-
--                       traffic-news class). NULL = never checked.
--   label_checked_at  = when the verdict was rendered.
--   label_court_model = which judge rendered it (e.g. 'label-court-v0/deepseek-chat').
--   label_proposed    = on 'failed' only: a receipt-derived NEUTRAL label
--                       ("<dominant-geo>: <subject> — from N receipts").
--                       NEVER auto-served: the script only replaces `label`
--                       when ATLAS_LABEL_COURT_APPLY=on (default off).
--
-- Serving reads label_status only (additive; existing queries unaffected).
-- Fully reversible:
--   UPDATE dynamic_topics SET label_status=NULL, label_checked_at=NULL,
--          label_court_model=NULL, label_proposed=NULL;

ALTER TABLE dynamic_topics
  ADD COLUMN IF NOT EXISTS label_status TEXT
    CHECK (label_status IS NULL OR label_status IN ('entailed', 'partial', 'failed')),
  ADD COLUMN IF NOT EXISTS label_checked_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS label_court_model TEXT,
  ADD COLUMN IF NOT EXISTS label_proposed TEXT;

-- The nightly court re-checks active topics; a partial index keeps the
-- "failed labels" review query cheap.
CREATE INDEX IF NOT EXISTS idx_dynamic_topics_label_failed
  ON dynamic_topics (id) WHERE label_status = 'failed';
