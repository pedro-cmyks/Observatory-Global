-- Migration 027: index fast-lane hot-window enrichment.
--
-- The fast-lane worker tags recent rows with nlp_method='lexicon' or
-- 'fast_neutral' while leaving nlp_processed_at NULL so transformer NLP can
-- still overwrite the row later. This partial index keeps the hot-window
-- selector bounded by created_at instead of scanning rows that already have a
-- fast-lane method.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_fast_lane_pending_created_at
    ON signals_v2 (created_at DESC)
    WHERE nlp_method IS NULL
      AND headline IS NOT NULL;
