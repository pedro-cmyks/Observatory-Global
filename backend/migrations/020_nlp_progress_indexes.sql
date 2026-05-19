-- Migration 020: keep NLP worker progress checks index-backed.
-- Run from Supabase SQL editor or a direct DATABASE_URL session.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_nlp_unprocessed_created_at
    ON signals_v2 (created_at ASC)
    WHERE nlp_processed_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_nlp_unprocessed_recent
    ON signals_v2 (created_at DESC)
    WHERE nlp_processed_at IS NULL;
