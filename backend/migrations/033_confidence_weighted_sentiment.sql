-- Migration 033: confidence-weighted NLP sentiment in pre-aggregates.
--
-- Context:
--   docs/research/nlp-coverage/2026-05-22-effective-coverage-baseline.md and
--   the 2026-05-22 transformer-vs-lexicon agreement benchmark (~71% sign
--   agreement, 29% disagreement, median |diff|=1.65 on a 1.9K decided sample).
--   The current pre-aggregates compute `avg_nlp_sentiment` as a flat AVG over
--   any row with nlp_sentiment NOT NULL. That mixes:
--     transformer rows (avg confidence ~0.64)
--     lexicon rows     (avg confidence ~0.31, capped at 0.5)
--     fast_neutral rows (confidence 0.01, sentiment forced to 0.0)
--   at equal per-row weight, so the few transformer rows that disagree with the
--   lexicon get diluted and the lexicon's known sign errors propagate to the UI.
--
-- Design:
--   Add two columns per pre-agg bucket:
--     nlp_sentiment_weight_sum  — SUM(nlp_sentiment * nlp_confidence) FILTER (...)
--     nlp_confidence_sum        — SUM(nlp_confidence)               FILTER (...)
--   Downstream readers compute the weighted average as
--     nlp_sentiment_weight_sum / NULLIF(nlp_confidence_sum, 0)
--   The legacy `avg_nlp_sentiment` column is preserved unchanged so existing
--   readers do not break during rollout. New readers prefer the weighted ratio
--   when nlp_confidence_sum > 0; otherwise they fall back to avg_nlp_sentiment
--   (which itself falls back to avg_sentiment when nlp_signal_count = 0).
--
-- Empirical sample (24h hot, 2026-05-22, 80 country cells with >=200 rows):
--   sign flips:       0 / 80
--   |delta| > 0.5:    62 / 80 (77.5%)
--   |delta| > 1.0:    17 / 80 (21.3%)
--   max delta:        TH  -1.37 (flat -1.13  → weighted -2.50)
--   bulk direction:   negative shift — flat values were diluted toward zero
--                     by fast_neutral and low-confidence lexicon hits.
--
-- Safety:
--   theme_hourly_v2 + theme_country_hourly_v2 are regular tables — ALTER ADD
--   COLUMN with DEFAULT 0 on Postgres >=11 is a metadata-only operation. No
--   table rewrite, no long lock.
--
--   country_hourly_v2 is a materialized view, so the build-populate-rename
--   pattern from migration 026 is reused. Readers continue to see the
--   pre-existing matview the entire time.
--
-- Out of scope:
--   historical_topic_country_daily is the long-window processed table written
--   by backend/scripts/historical_process_partition.py. The miner does not
--   carry per-row nlp_confidence in the archive snapshots, so weighted
--   sentiment for historical days requires a separate reprocessing pass.
--   Tracked under the same #185/#186 quality umbrella; not part of this
--   migration.

-- =============================================================================
-- Part 1 — theme_hourly_v2 (regular table)
-- =============================================================================
ALTER TABLE theme_hourly_v2
    ADD COLUMN IF NOT EXISTS nlp_sentiment_weight_sum NUMERIC NOT NULL DEFAULT 0;

ALTER TABLE theme_hourly_v2
    ADD COLUMN IF NOT EXISTS nlp_confidence_sum       NUMERIC NOT NULL DEFAULT 0;

-- Backfill existing rows from signals_v2 for the same hour×theme bucket. Bounded
-- to the last 30 days so the migration does not scan the full table; older
-- buckets stay at default 0 and will refresh on next ingest cycle (next theme
-- update query covers a 2h window). Adjust window before running if needed.
WITH bucket AS (
    SELECT date_trunc('hour', timestamp) AS hour,
           unnest(themes)                AS theme,
           SUM(nlp_sentiment * nlp_confidence) FILTER (
               WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0
           )                              AS w_sum,
           SUM(nlp_confidence)            FILTER (
               WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0
           )                              AS c_sum
    FROM signals_v2
    WHERE themes IS NOT NULL
      AND timestamp > NOW() - INTERVAL '30 days'
    GROUP BY 1, 2
)
UPDATE theme_hourly_v2 t
   SET nlp_sentiment_weight_sum = COALESCE(b.w_sum, 0),
       nlp_confidence_sum       = COALESCE(b.c_sum, 0)
  FROM bucket b
 WHERE t.hour  = b.hour
   AND t.theme = b.theme;

-- =============================================================================
-- Part 2 — theme_country_hourly_v2 (regular table)
-- =============================================================================
ALTER TABLE theme_country_hourly_v2
    ADD COLUMN IF NOT EXISTS nlp_sentiment_weight_sum NUMERIC NOT NULL DEFAULT 0;

ALTER TABLE theme_country_hourly_v2
    ADD COLUMN IF NOT EXISTS nlp_confidence_sum       NUMERIC NOT NULL DEFAULT 0;

WITH bucket AS (
    SELECT date_trunc('hour', timestamp) AS hour,
           unnest(themes)                AS theme,
           country_code,
           SUM(nlp_sentiment * nlp_confidence) FILTER (
               WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0
           )                              AS w_sum,
           SUM(nlp_confidence)            FILTER (
               WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0
           )                              AS c_sum
    FROM signals_v2
    WHERE themes        IS NOT NULL
      AND country_code  IS NOT NULL
      AND timestamp > NOW() - INTERVAL '30 days'
    GROUP BY 1, 2, 3
)
UPDATE theme_country_hourly_v2 t
   SET nlp_sentiment_weight_sum = COALESCE(b.w_sum, 0),
       nlp_confidence_sum       = COALESCE(b.c_sum, 0)
  FROM bucket b
 WHERE t.hour         = b.hour
   AND t.theme        = b.theme
   AND t.country_code = b.country_code;

-- =============================================================================
-- Part 3 — country_hourly_v2 (matview) — build-populate-rename
-- Execution order (statements must be issued separately by the operator/runner):
--   1. CREATE MATERIALIZED VIEW ... WITH NO DATA   (instant)
--   2. CREATE UNIQUE INDEX + secondary index       (empty matview, instant)
--   3. REFRESH MATERIALIZED VIEW                   (one full scan)
--   4. BEGIN; rename swap; COMMIT;                 (atomic)
--   5. DROP _old                                   (cleanup)
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
    avg(nlp_sentiment) FILTER (WHERE nlp_sentiment IS NOT NULL)                AS avg_nlp_sentiment,
    sum(nlp_sentiment * nlp_confidence) FILTER (
        WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0
    )                                                                          AS nlp_sentiment_weight_sum,
    sum(nlp_confidence) FILTER (
        WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0
    )                                                                          AS nlp_confidence_sum
FROM signals_v2
GROUP BY date_trunc('hour', "timestamp"), country_code
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_country_hourly_v2_new_unique
    ON country_hourly_v2_new (hour, country_code);

CREATE INDEX IF NOT EXISTS idx_country_hourly_v2_new_hour
    ON country_hourly_v2_new (hour DESC);

REFRESH MATERIALIZED VIEW country_hourly_v2_new;

BEGIN;
ALTER MATERIALIZED VIEW country_hourly_v2          RENAME TO country_hourly_v2_old;
ALTER MATERIALIZED VIEW country_hourly_v2_new      RENAME TO country_hourly_v2;
ALTER INDEX idx_country_hourly_v2_unique           RENAME TO idx_country_hourly_v2_old_unique;
ALTER INDEX idx_country_hourly_v2_hour             RENAME TO idx_country_hourly_v2_old_hour;
ALTER INDEX idx_country_hourly_v2_new_unique       RENAME TO idx_country_hourly_v2_unique;
ALTER INDEX idx_country_hourly_v2_new_hour         RENAME TO idx_country_hourly_v2_hour;
COMMIT;

DROP MATERIALIZED VIEW IF EXISTS country_hourly_v2_old CASCADE;
