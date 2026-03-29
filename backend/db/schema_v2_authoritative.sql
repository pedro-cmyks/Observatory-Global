-- ===========================================================================
-- schema_v2_authoritative.sql
-- Generated from LIVE Observatory Global database — 2026-03-13
--
-- This file represents the ACTUAL database state, not the original
-- schema_v2.sql which was missing 30+ tables, crisis columns, and
-- all v1-era structures.
--
-- CATEGORIES:
--   [CORE-V2]     Active v2 tables used by current ingestion + API
--   [AGGREGATE]   Materialized views / rollup tables refreshed by triggers
--   [BASELINE]    Statistical baseline tables for anomaly detection
--   [CORE-V1]     Legacy v1 tables (gdelt_signals, countries, etc.) — still contain data
--   [V1-DERIVED]  Derived v1 tables — mostly empty, may be deprecated
--   [CONFIG]      System configuration / migrations
--   [VIEW]        Database views and materialized views
-- ===========================================================================

-- ============================================================
-- [CORE-V2] signals_v2 — Primary signal storage (2.25M rows, 1.2GB)
-- ============================================================
CREATE TABLE IF NOT EXISTS signals_v2 (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL,
    country_code    CHAR(2) NOT NULL,
    latitude        NUMERIC,
    longitude       NUMERIC,
    sentiment       NUMERIC,
    source_url      TEXT,
    source_name     TEXT,
    themes          TEXT[],
    persons         TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    -- Crisis classification (added post-schema, v3 intel layer)
    is_crisis       BOOLEAN DEFAULT FALSE,
    crisis_score    DOUBLE PRECISION DEFAULT 0,
    crisis_themes   TEXT[] DEFAULT '{}',
    severity        VARCHAR DEFAULT 'low',
    event_type      VARCHAR DEFAULT 'other'
);

CREATE INDEX IF NOT EXISTS idx_signals_v2_timestamp
    ON signals_v2 (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_v2_country_time
    ON signals_v2 (country_code, timestamp DESC);

-- ============================================================
-- [CORE-V2] countries_v2 — Country reference (292 rows)
-- ============================================================
CREATE TABLE IF NOT EXISTS countries_v2 (
    code        CHAR(2) PRIMARY KEY,
    name        TEXT,
    latitude    NUMERIC,
    longitude   NUMERIC,
    updated_at  TIMESTAMPTZ
);

-- ============================================================
-- [AGGREGATE] country_hourly_v2 — Materialized view (hourly rollup)
-- Refreshed: REFRESH MATERIALIZED VIEW CONCURRENTLY after each ingestion
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS country_hourly_v2 AS
SELECT
    date_trunc('hour', timestamp) AS hour,
    country_code,
    COUNT(*) AS signal_count,
    AVG(sentiment) AS avg_sentiment,
    MIN(sentiment) AS min_sentiment,
    MAX(sentiment) AS max_sentiment,
    COUNT(DISTINCT source_name) AS unique_sources
FROM signals_v2
GROUP BY date_trunc('hour', timestamp), country_code;

CREATE UNIQUE INDEX IF NOT EXISTS idx_country_hourly_v2_unique
    ON country_hourly_v2 (hour, country_code);
CREATE INDEX IF NOT EXISTS idx_country_hourly_v2_hour
    ON country_hourly_v2 (hour DESC);

-- ============================================================
-- [AGGREGATE] country_daily_v2 — Daily rollup table (7,798 rows)
-- Used by: /api/v2/nodes for extended time ranges (1m, 3m, record)
-- ============================================================
CREATE TABLE IF NOT EXISTS country_daily_v2 (
    day             DATE NOT NULL,
    country_code    CHAR(2) NOT NULL,
    signal_count    INTEGER NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    min_sentiment   NUMERIC,
    max_sentiment   NUMERIC,
    unique_sources  INTEGER DEFAULT 0,
    PRIMARY KEY (day, country_code)
);

-- ============================================================
-- [AGGREGATE] signals_country_hourly — Hourly per-country rollup (19,882 rows)
-- Used by: /api/v2/trends (entity_type='country'), /api/v2/compare
-- ============================================================
CREATE TABLE IF NOT EXISTS signals_country_hourly (
    bucket          TIMESTAMP NOT NULL,
    country_code    VARCHAR NOT NULL,
    signal_count    INTEGER NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    PRIMARY KEY (bucket, country_code)
);

-- ============================================================
-- [AGGREGATE] signals_theme_hourly — Hourly per-theme rollup (277,022 rows)
-- Used by: /api/v2/trends (entity_type='theme'), /api/v2/compare
-- ============================================================
CREATE TABLE IF NOT EXISTS signals_theme_hourly (
    bucket          TIMESTAMP NOT NULL,
    theme           VARCHAR NOT NULL,
    signal_count    INTEGER NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    PRIMARY KEY (bucket, theme)
);

-- ============================================================
-- [AGGREGATE] signals_source_hourly — Hourly per-source rollup (122,983 rows)
-- Used by: /api/v2/trends (entity_type='source')
-- ============================================================
CREATE TABLE IF NOT EXISTS signals_source_hourly (
    bucket          TIMESTAMP NOT NULL,
    source_name     VARCHAR NOT NULL,
    signal_count    INTEGER NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    PRIMARY KEY (bucket, source_name)
);

-- ============================================================
-- [AGGREGATE] theme_daily_v2 — Daily theme rollup (162,950 rows)
-- ============================================================
CREATE TABLE IF NOT EXISTS theme_daily_v2 (
    day             DATE NOT NULL,
    theme           VARCHAR NOT NULL,
    signal_count    INTEGER NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    country_count   INTEGER DEFAULT 0,
    PRIMARY KEY (day, theme)
);

-- ============================================================
-- [AGGREGATE] theme_aggregations_1h — Detailed hourly theme stats (13,546 rows)
-- Includes outlet lists, sample URLs, polarity, intensity
-- ============================================================
CREATE TABLE IF NOT EXISTS theme_aggregations_1h (
    id              BIGSERIAL PRIMARY KEY,
    hour_bucket     TIMESTAMPTZ NOT NULL,
    country_code    VARCHAR NOT NULL,
    theme_code      VARCHAR NOT NULL,
    signal_count    INTEGER NOT NULL DEFAULT 0,
    total_theme_mentions INTEGER NOT NULL DEFAULT 0,
    avg_tone        NUMERIC,
    min_tone        NUMERIC,
    max_tone        NUMERIC,
    avg_polarity    NUMERIC,
    avg_intensity   NUMERIC,
    max_intensity   NUMERIC,
    unique_outlets  INTEGER DEFAULT 0,
    outlet_list     TEXT[],
    sample_urls     TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- [BASELINE] country_baseline_stats — 7-day rolling stats for anomaly detection (189 rows)
-- Used by: /api/v2/anomalies endpoint
-- Refreshed by: refresh_country_baseline() function
-- ============================================================
CREATE TABLE IF NOT EXISTS country_baseline_stats (
    country_code        VARCHAR PRIMARY KEY,
    avg_daily_signals   NUMERIC DEFAULT 0,
    stddev_daily_signals NUMERIC DEFAULT 0,
    last_7d_total       INTEGER DEFAULT 0,
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- [AGGREGATE] trending_themes — Theme anomaly tracking (0 rows — likely unused)
-- ============================================================
CREATE TABLE IF NOT EXISTS trending_themes (
    id              BIGSERIAL PRIMARY KEY,
    theme_code      VARCHAR NOT NULL,
    theme_name      VARCHAR,
    window_start    TIMESTAMPTZ NOT NULL,
    window_end      TIMESTAMPTZ NOT NULL,
    window_type     VARCHAR NOT NULL,
    event_count     INTEGER DEFAULT 0,
    country_count   INTEGER DEFAULT 0,
    avg_tone        NUMERIC,
    baseline_avg    NUMERIC,
    current_value   NUMERIC,
    anomaly_score   NUMERIC,
    is_trending     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (theme_code, window_start, window_type)
);

-- ============================================================
-- [CORE-V1] gdelt_signals — Legacy v1 signal table (48,606 rows)
-- Richer schema than signals_v2 (includes confidence, intensity, 
-- geographic_precision, duplicate tracking, per-field tone)
-- NOT used by v2 API. Kept for reference.
-- ============================================================
-- (Schema omitted for brevity — see live DB for full definition)

-- ============================================================
-- [CORE-V1] countries — Legacy v1 country reference (240 rows)
-- Includes region, subregion, population, languages, timezone
-- Used by: mv_active_flows, mv_recent_hotspots materialized views
-- ============================================================
-- (Schema omitted — superseded by countries_v2 for v2 API)

-- ============================================================
-- [V1-DERIVED] actor_stats, country_aggregates, country_flows,
--              flows, historical_baselines, hotspots, signal_entities,
--              signal_themes, stance_history, topics, topic_snapshots,
--              trends_archive — All 0 or near-0 rows. Legacy v1 structures.
-- ============================================================

-- ============================================================
-- [CONFIG] schema_migrations (4 rows), data_lifecycle_config (4 rows),
--          ingest_file_log (0 rows), ingest_watermark (1 row)
-- ============================================================
CREATE TABLE IF NOT EXISTS data_lifecycle_config (
    key         VARCHAR PRIMARY KEY,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- [VIEW] Materialized views (besides country_hourly_v2)
-- ============================================================

-- mv_active_flows — joins flows + countries (v1 schema). 0 rows.
-- mv_recent_hotspots — joins hotspots + countries (v1 schema). 0 rows.

-- ============================================================
-- [VIEW] Regular views
-- ============================================================
-- v_row_counts — shows row counts for all tables
-- v_table_sizes — shows table sizes

-- ============================================================
-- FUNCTIONS (relevant to v2)
-- ============================================================

-- refresh_country_hourly() — refreshes country_hourly_v2 materialized view
-- refresh_country_baseline() — recalculates country_baseline_stats
-- refresh_aggregates() — combined aggregate refresh
-- bucket_15min(ts) / bucket_1h(ts) — time bucketing helpers
-- sentiment_label(score) — maps numeric sentiment to label
-- safe_retention_cleanup() — data retention / pruning

-- ============================================================
-- ENDPOINT → TABLE MAPPING (for reference)
-- ============================================================
--
-- /api/v2/nodes          → country_hourly_v2 (short range) / country_daily_v2 (extended)
-- /api/v2/flows          → signals_v2 + countries_v2
-- /api/v2/anomalies      → signals_v2 + country_baseline_stats
-- /api/v2/search         → signals_v2 + countries_v2
-- /api/v2/focus          → signals_v2
-- /api/v2/theme/{code}   → signals_v2
-- /api/v2/signals        → signals_v2
-- /api/v2/country/{code} → country_hourly_v2 + signals_v2
-- /api/v2/briefing       → signals_v2 + countries_v2
-- /api/v2/trends         → signals_country_hourly / signals_theme_hourly / signals_source_hourly
-- /api/v2/compare        → signals_country_hourly / signals_theme_hourly
-- /api/v2/stats          → signals_v2
-- /api/v3/crisis/signals → signals_v2 (crisis columns)
-- /api/v3/crisis/summary → signals_v2 (crisis columns)
-- /api/indicators/*      → signals_v2 (calculated at query time)
-- /health                → signals_v2
