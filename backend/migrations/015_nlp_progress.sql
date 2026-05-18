-- Migration 015: NLP worker progress + lag telemetry.
-- Backs the `nlp` block of GET /health and the priority queue checkpoint.
-- See issue #163 and docs/superpowers/plans/2026-05-18-creative-solutions-execution.md (Phase 2).

CREATE TABLE IF NOT EXISTS nlp_progress (
    worker_id                 TEXT PRIMARY KEY,
    last_signal_id            BIGINT,
    rows_processed_total      BIGINT      NOT NULL DEFAULT 0,
    lag_minutes               INT,
    oldest_unprocessed_at     TIMESTAMPTZ,
    unprocessed_24h           INT,
    unprocessed_total         BIGINT,
    current_phase             TEXT,
    last_run_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_run_duration_seconds REAL,
    last_error                TEXT
);

-- Convenience materialised view for "low volume" priority boost.
-- Refreshed by the worker on a daily cadence.
CREATE MATERIALIZED VIEW IF NOT EXISTS low_volume_countries AS
SELECT country_code, COUNT(*)::BIGINT AS daily_avg
FROM signals_v2
WHERE created_at > NOW() - INTERVAL '7 days'
  AND country_code IS NOT NULL
GROUP BY country_code
HAVING COUNT(*) < 200 * 7;  -- under 200 rows/day average

CREATE UNIQUE INDEX IF NOT EXISTS idx_low_volume_countries_pk
    ON low_volume_countries (country_code);
