-- 096: #261 item 3 — widen the Label Court verdict vocabulary with 'too_broad'.
--
-- Migration 080's inline CHECK on dynamic_topics.label_status permits only
-- 'entailed' | 'partial' | 'failed' | NULL. The mega-topic failure mode the
-- issue named ("8 random receipts don't entail one label for a 3,000-signal
-- topic") was folded into 'failed', which reads as "wrong label" when the
-- honest finding is "no SINGLE label could describe this topic — it is a
-- fusion". label_court.py's story lane now emits 'too_broad' for that case;
-- a too_broad row gets no neutral-label proposal and is never selected by
-- relabel_court_failed.py (WHERE label_status='failed').
--
-- Additive + reversible:
--   UPDATE dynamic_topics SET label_status=NULL WHERE label_status='too_broad';
--   then re-add the narrower CHECK if ever needed.

DO $$
DECLARE con text;
BEGIN
  SELECT conname INTO con
  FROM pg_constraint
  WHERE conrelid = 'dynamic_topics'::regclass
    AND contype = 'c'
    AND pg_get_constraintdef(oid) ILIKE '%label_status%';
  IF con IS NOT NULL THEN
    EXECUTE format('ALTER TABLE dynamic_topics DROP CONSTRAINT %I', con);
  END IF;
END $$;

ALTER TABLE dynamic_topics
  ADD CONSTRAINT dynamic_topics_label_status_check
  CHECK (label_status IS NULL OR label_status IN ('entailed', 'partial', 'failed', 'too_broad'));
