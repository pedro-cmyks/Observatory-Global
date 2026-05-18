-- Migration 016: nlp_method tag for hybrid coverage (ADR-0004, issue #164).
-- Marks each NLP-processed row with the method used so downstream API queries
-- can pick a confidence floor: transformer for narrative-aware aggregates,
-- lexicon (allowed) for historical trend surfaces.

ALTER TABLE signals_v2
    ADD COLUMN IF NOT EXISTS nlp_method VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_signals_v2_nlp_method
    ON signals_v2 (nlp_method, timestamp DESC)
    WHERE nlp_method IS NOT NULL;

-- Stratified sample queue: worker drains this strictly before the global
-- priority queue so every bucket gets coverage even under capacity pressure.
CREATE TABLE IF NOT EXISTS nlp_sample_queue (
    id BIGINT PRIMARY KEY,
    enqueued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nlp_sample_queue_age
    ON nlp_sample_queue (enqueued_at);
