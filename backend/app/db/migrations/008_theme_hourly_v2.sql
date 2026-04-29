-- theme_hourly_v2: pre-aggregated theme counts by hour
-- Populated by ingest_v2 after each batch (last 2h window)
-- Allows narratives endpoint to query any time window instantly

CREATE TABLE IF NOT EXISTS theme_hourly_v2 (
    hour            TIMESTAMPTZ NOT NULL,
    theme           TEXT        NOT NULL,
    signal_count    INT         NOT NULL DEFAULT 0,
    country_count   INT         NOT NULL DEFAULT 0,
    source_count    INT         NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    PRIMARY KEY (hour, theme)
);

CREATE INDEX IF NOT EXISTS idx_theme_hourly_v2_hour
    ON theme_hourly_v2 (hour DESC);
CREATE INDEX IF NOT EXISTS idx_theme_hourly_v2_theme
    ON theme_hourly_v2 (theme, hour DESC);

-- Backfill last 48h from existing signals_v2 data
INSERT INTO theme_hourly_v2 (hour, theme, signal_count, country_count, source_count, avg_sentiment)
SELECT
    date_trunc('hour', timestamp) AS hour,
    unnest(themes)                AS theme,
    COUNT(*)                      AS signal_count,
    COUNT(DISTINCT country_code)  AS country_count,
    COUNT(DISTINCT source_name)   AS source_count,
    AVG(sentiment)                AS avg_sentiment
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '48 hours'
  AND themes IS NOT NULL
GROUP BY 1, 2
ON CONFLICT (hour, theme) DO UPDATE SET
    signal_count  = EXCLUDED.signal_count,
    country_count = EXCLUDED.country_count,
    source_count  = EXCLUDED.source_count,
    avg_sentiment = EXCLUDED.avg_sentiment;
