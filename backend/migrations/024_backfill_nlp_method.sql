-- Migration 024: tag already-processed transformer sentiment rows.
--
-- Earlier multilingual NLP writes filled nlp_sentiment/nlp_confidence but left
-- nlp_method NULL. That makes downstream quality audits unable to distinguish
-- transformer-normalized rows from raw legacy sentiment.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_nlp_method_backfill
    ON signals_v2 (id)
    WHERE nlp_sentiment IS NOT NULL
      AND nlp_processed_at IS NOT NULL
      AND nlp_method IS NULL;

-- Repeat this bounded batch during low-traffic windows until it reports
-- UPDATE 0. Do not run a single all-table UPDATE; Supabase IO is sensitive
-- while the NLP worker and ingestion are active.
WITH candidates AS (
    SELECT id
    FROM signals_v2
    WHERE nlp_sentiment IS NOT NULL
      AND nlp_processed_at IS NOT NULL
      AND nlp_method IS NULL
    ORDER BY id
    LIMIT 1000
)
UPDATE signals_v2 s
SET nlp_method = 'transformer'
FROM candidates c
WHERE s.id = c.id;
