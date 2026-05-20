-- Migration 023: shadow-mode NLP priority indexes.
-- Mirrors migration 020 for nlp_processed_at_xlm so multilingual shadow runs
-- can use the same hot-lane and progress queries without sorting the backlog.
-- Run from Supabase SQL editor or a direct DATABASE_URL session.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_nlp_xlm_unprocessed_created_at
    ON signals_v2 (created_at ASC)
    WHERE nlp_processed_at_xlm IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_nlp_xlm_unprocessed_recent
    ON signals_v2 (created_at DESC)
    WHERE nlp_processed_at_xlm IS NULL;
