-- Migration 026: country_hourly_v2 matview adds NLP coverage columns.
-- Companion to migration 025 (theme_hourly_v2 + theme_country_hourly_v2 already
-- ship nlp_signal_count + avg_nlp_sentiment).
--
-- Why a swap instead of DROP/CREATE in place:
--   Postgres matviews cannot be ALTER ADD COLUMN. The two options are
--     (a) DROP + CREATE, which leaves the matview empty until REFRESH
--         completes (briefing reads against the empty matview during that window),
--     (b) build a new matview, populate it, then atomic rename swap.
--   This migration uses (b) to keep briefing reads serving real data the
--   entire time.
--
-- Execution order (each statement issued separately by the operator or runner):
--   1. CREATE MATERIALIZED VIEW country_hourly_v2_new ... WITH NO DATA;
--   2. CREATE UNIQUE INDEX idx_country_hourly_v2_new_unique ...;
--   3. CREATE INDEX idx_country_hourly_v2_new_hour ...;
--   4. REFRESH MATERIALIZED VIEW country_hourly_v2_new;  -- full scan
--   5. BEGIN;
--        ALTER MATERIALIZED VIEW country_hourly_v2 RENAME TO country_hourly_v2_old;
--        ALTER MATERIALIZED VIEW country_hourly_v2_new RENAME TO country_hourly_v2;
--        ALTER INDEX idx_country_hourly_v2_unique RENAME TO idx_country_hourly_v2_old_unique;
--        ALTER INDEX idx_country_hourly_v2_hour   RENAME TO idx_country_hourly_v2_old_hour;
--        ALTER INDEX idx_country_hourly_v2_new_unique RENAME TO idx_country_hourly_v2_unique;
--        ALTER INDEX idx_country_hourly_v2_new_hour   RENAME TO idx_country_hourly_v2_hour;
--      COMMIT;
--   6. DROP MATERIALIZED VIEW country_hourly_v2_old CASCADE;
--
-- After step 5 ingest_v2.refresh_aggregates keeps working untouched because the
-- matview name is preserved.

-- =============================================================================
-- Step 1 — schema only (instant)
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS country_hourly_v2_new AS
SELECT
    date_trunc('hour', "timestamp")                                            AS hour,
    country_code,
    count(*)                                                                   AS signal_count,
    avg(sentiment)                                                             AS avg_sentiment,
    min(sentiment)                                                             AS min_sentiment,
    max(sentiment)                                                             AS max_sentiment,
    count(DISTINCT source_name)                                                AS unique_sources,
    count(*) FILTER (WHERE nlp_sentiment IS NOT NULL)                          AS nlp_signal_count,
    avg(nlp_sentiment) FILTER (WHERE nlp_sentiment IS NOT NULL)                AS avg_nlp_sentiment
FROM signals_v2
GROUP BY date_trunc('hour', "timestamp"), country_code
WITH NO DATA;

-- =============================================================================
-- Step 2 + 3 — indexes (unique required for REFRESH MATERIALIZED VIEW CONCURRENTLY)
-- =============================================================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_country_hourly_v2_new_unique
    ON country_hourly_v2_new (hour, country_code);

CREATE INDEX IF NOT EXISTS idx_country_hourly_v2_new_hour
    ON country_hourly_v2_new (hour DESC);

-- =============================================================================
-- Step 4 — populate
-- =============================================================================
REFRESH MATERIALIZED VIEW country_hourly_v2_new;

-- =============================================================================
-- Step 5 — atomic swap
-- =============================================================================
BEGIN;
ALTER MATERIALIZED VIEW country_hourly_v2          RENAME TO country_hourly_v2_old;
ALTER MATERIALIZED VIEW country_hourly_v2_new      RENAME TO country_hourly_v2;
ALTER INDEX idx_country_hourly_v2_unique           RENAME TO idx_country_hourly_v2_old_unique;
ALTER INDEX idx_country_hourly_v2_hour             RENAME TO idx_country_hourly_v2_old_hour;
ALTER INDEX idx_country_hourly_v2_new_unique       RENAME TO idx_country_hourly_v2_unique;
ALTER INDEX idx_country_hourly_v2_new_hour         RENAME TO idx_country_hourly_v2_hour;
COMMIT;

-- =============================================================================
-- Step 6 — cleanup
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS country_hourly_v2_old CASCADE;
