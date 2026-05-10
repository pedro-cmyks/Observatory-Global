-- Migration 011: NLP enrichment columns (Phase 1 — sentiment only)
-- Run ONCE in Supabase SQL editor.
--
-- Adds nullable NLP columns to signals_v2. GDELT signals keep their
-- existing sentiment. RSS/ReliefWeb signals get nlp_sentiment filled
-- by nlp_pipeline.py. API uses COALESCE(nlp_sentiment, sentiment).

BEGIN;

ALTER TABLE signals_v2
    ADD COLUMN IF NOT EXISTS nlp_sentiment      FLOAT        DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS nlp_framing        VARCHAR(30)  DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS nlp_persons        JSONB        DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS nlp_confidence     FLOAT        DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS nlp_processed_at   TIMESTAMPTZ  DEFAULT NULL;

-- Index: pipeline fetches unprocessed curated signals
CREATE INDEX IF NOT EXISTS idx_signals_v2_nlp_unprocessed
    ON signals_v2 (attribution_method, nlp_processed_at, timestamp DESC)
    WHERE nlp_processed_at IS NULL;

COMMIT;
