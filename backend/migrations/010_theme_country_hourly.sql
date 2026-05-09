-- Migration 010: theme_country_hourly_v2 pre-aggregation table
--
-- Problem: GET /api/v2/concept/{slug}?hours=168 times out because it scans
-- signals_v2.themes (1.3M+ rows) with a GIN && filter + GROUP BY country.
-- Even with the GIN index, 168h GROUP BY at this volume exceeds 15s timeout.
--
-- Fix: pre-aggregate (hour, theme, country_code) each ingest cycle.
-- Concept endpoint queries this table instead of signals_v2 for windows > 24h.
-- 168h query = at most 168 * N_active_countries rows per theme — sub-second.

BEGIN;

CREATE TABLE IF NOT EXISTS theme_country_hourly_v2 (
    hour         TIMESTAMPTZ  NOT NULL,
    theme        TEXT         NOT NULL,
    country_code VARCHAR(3)   NOT NULL,
    signal_count INTEGER      NOT NULL DEFAULT 0,
    avg_sentiment NUMERIC,
    PRIMARY KEY (hour, theme, country_code)
);

-- Fast lookup: "all countries for theme X in last N hours"
CREATE INDEX IF NOT EXISTS idx_tch_theme_hour
    ON theme_country_hourly_v2 (theme, hour DESC);

-- Fast lookup: "all themes for country X in last N hours"
CREATE INDEX IF NOT EXISTS idx_tch_country_hour
    ON theme_country_hourly_v2 (country_code, hour DESC);

-- Backfill last 7 days so 168h queries work immediately after migration.
-- Runs once; ongoing population handled by ingest_v2.py each cycle.
INSERT INTO theme_country_hourly_v2
    (hour, theme, country_code, signal_count, avg_sentiment)
SELECT
    date_trunc('hour', timestamp) AS hour,
    unnest(themes)                AS theme,
    country_code,
    COUNT(*)                      AS signal_count,
    AVG(sentiment)                AS avg_sentiment
FROM signals_v2
WHERE timestamp  > NOW() - INTERVAL '7 days'
  AND themes     IS NOT NULL
  AND country_code IS NOT NULL
GROUP BY 1, 2, 3
ON CONFLICT (hour, theme, country_code) DO UPDATE SET
    signal_count  = EXCLUDED.signal_count,
    avg_sentiment = EXCLUDED.avg_sentiment;

COMMIT;
