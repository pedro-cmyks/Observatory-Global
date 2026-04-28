-- ===========================================================================
-- Atlas v2 Schema Migration
-- Creates all tables required by main_v2.py and ingest_v2.py
-- Safe to run on a DB that already has v1 tables (uses IF NOT EXISTS)
-- ===========================================================================

-- [CORE-V2] signals_v2 — primary signal storage
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
    headline        TEXT,
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
CREATE INDEX IF NOT EXISTS idx_signals_v2_themes
    ON signals_v2 USING GIN (themes);
CREATE INDEX IF NOT EXISTS idx_signals_v2_persons
    ON signals_v2 USING GIN (persons);
CREATE INDEX IF NOT EXISTS idx_signals_v2_crisis
    ON signals_v2 (is_crisis, timestamp DESC) WHERE is_crisis = TRUE;

-- [CORE-V2] countries_v2 — country reference
CREATE TABLE IF NOT EXISTS countries_v2 (
    code        CHAR(2) PRIMARY KEY,
    name        TEXT,
    latitude    NUMERIC,
    longitude   NUMERIC,
    updated_at  TIMESTAMPTZ
);

-- [AGGREGATE] country_hourly_v2 — materialized view (refreshed after each ingest)
CREATE MATERIALIZED VIEW IF NOT EXISTS country_hourly_v2 AS
SELECT
    date_trunc('hour', timestamp) AS hour,
    country_code,
    COUNT(*)                      AS signal_count,
    AVG(sentiment)                AS avg_sentiment,
    MIN(sentiment)                AS min_sentiment,
    MAX(sentiment)                AS max_sentiment,
    COUNT(DISTINCT source_name)   AS unique_sources
FROM signals_v2
GROUP BY date_trunc('hour', timestamp), country_code;

CREATE UNIQUE INDEX IF NOT EXISTS idx_country_hourly_v2_unique
    ON country_hourly_v2 (hour, country_code);
CREATE INDEX IF NOT EXISTS idx_country_hourly_v2_hour
    ON country_hourly_v2 (hour DESC);

-- [AGGREGATE] country_daily_v2 — daily rollup (for extended time ranges)
CREATE TABLE IF NOT EXISTS country_daily_v2 (
    day             DATE        NOT NULL,
    country_code    CHAR(2)     NOT NULL,
    signal_count    INTEGER     NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    min_sentiment   NUMERIC,
    max_sentiment   NUMERIC,
    unique_sources  INTEGER     DEFAULT 0,
    PRIMARY KEY (day, country_code)
);

-- [AGGREGATE] signals_country_hourly — used by /api/v2/trends and /api/v2/compare
CREATE TABLE IF NOT EXISTS signals_country_hourly (
    bucket          TIMESTAMP   NOT NULL,
    country_code    VARCHAR     NOT NULL,
    signal_count    INTEGER     NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    PRIMARY KEY (bucket, country_code)
);

-- [AGGREGATE] signals_theme_hourly — used by /api/v2/trends (entity_type='theme')
CREATE TABLE IF NOT EXISTS signals_theme_hourly (
    bucket          TIMESTAMP   NOT NULL,
    theme           VARCHAR     NOT NULL,
    signal_count    INTEGER     NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    PRIMARY KEY (bucket, theme)
);

-- [AGGREGATE] signals_source_hourly — used by /api/v2/trends (entity_type='source')
CREATE TABLE IF NOT EXISTS signals_source_hourly (
    bucket          TIMESTAMP   NOT NULL,
    source_name     VARCHAR     NOT NULL,
    signal_count    INTEGER     NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    PRIMARY KEY (bucket, source_name)
);

-- [AGGREGATE] theme_daily_v2 — daily theme rollup
CREATE TABLE IF NOT EXISTS theme_daily_v2 (
    day             DATE        NOT NULL,
    theme           VARCHAR     NOT NULL,
    signal_count    INTEGER     NOT NULL DEFAULT 0,
    avg_sentiment   NUMERIC,
    country_count   INTEGER     DEFAULT 0,
    PRIMARY KEY (day, theme)
);

-- [BASELINE] country_baseline_stats — for /api/v2/anomalies
CREATE TABLE IF NOT EXISTS country_baseline_stats (
    country_code            VARCHAR PRIMARY KEY,
    avg_daily_signals       NUMERIC DEFAULT 0,
    stddev_daily_signals    NUMERIC DEFAULT 0,
    last_7d_total           INTEGER DEFAULT 0,
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- [AGGREGATE] trending_themes
CREATE TABLE IF NOT EXISTS trending_themes (
    id              BIGSERIAL   PRIMARY KEY,
    theme_code      VARCHAR     NOT NULL,
    theme_name      VARCHAR,
    window_start    TIMESTAMPTZ NOT NULL,
    window_end      TIMESTAMPTZ NOT NULL,
    window_type     VARCHAR     NOT NULL,
    event_count     INTEGER     DEFAULT 0,
    country_count   INTEGER     DEFAULT 0,
    avg_tone        NUMERIC,
    baseline_avg    NUMERIC,
    current_value   NUMERIC,
    anomaly_score   NUMERIC,
    is_trending     BOOLEAN     DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (theme_code, window_start, window_type)
);

-- [CONFIG] data_lifecycle_config
CREATE TABLE IF NOT EXISTS data_lifecycle_config (
    key         VARCHAR     PRIMARY KEY,
    value       TEXT        NOT NULL,
    description TEXT,
    updated_at  TIMESTAMP   DEFAULT NOW()
);

-- [CONFIG] ingest_watermark — tracks last ingested file
CREATE TABLE IF NOT EXISTS ingest_watermark (
    id              SERIAL      PRIMARY KEY,
    last_file_ts    TIMESTAMPTZ,
    last_file_url   TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO ingest_watermark (id) VALUES (1) ON CONFLICT DO NOTHING;

-- [CONFIG] ingest_file_log — per-file ingest audit trail
CREATE TABLE IF NOT EXISTS ingest_file_log (
    id              BIGSERIAL   PRIMARY KEY,
    file_url        TEXT        NOT NULL,
    file_ts         TIMESTAMPTZ NOT NULL,
    rows_inserted   INTEGER     DEFAULT 0,
    duration_ms     INTEGER,
    status          VARCHAR     DEFAULT 'ok',
    error_msg       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================================================
-- FUNCTIONS
-- ===========================================================================

-- Refresh country_hourly_v2 materialized view (called by ingest_v2 after each batch)
CREATE OR REPLACE FUNCTION refresh_country_hourly()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY country_hourly_v2;
END;
$$;

-- Recalculate 7-day rolling baseline stats per country
CREATE OR REPLACE FUNCTION refresh_country_baseline()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO country_baseline_stats (country_code, avg_daily_signals, stddev_daily_signals, last_7d_total, updated_at)
    SELECT
        country_code,
        AVG(daily_count)    AS avg_daily_signals,
        STDDEV(daily_count) AS stddev_daily_signals,
        SUM(daily_count)    AS last_7d_total,
        NOW()
    FROM (
        SELECT
            country_code,
            DATE(timestamp) AS day,
            COUNT(*)        AS daily_count
        FROM signals_v2
        WHERE timestamp >= NOW() - INTERVAL '7 days'
        GROUP BY country_code, DATE(timestamp)
    ) daily
    GROUP BY country_code
    ON CONFLICT (country_code) DO UPDATE SET
        avg_daily_signals    = EXCLUDED.avg_daily_signals,
        stddev_daily_signals = EXCLUDED.stddev_daily_signals,
        last_7d_total        = EXCLUDED.last_7d_total,
        updated_at           = NOW();
END;
$$;

-- Combined refresh (called periodically)
CREATE OR REPLACE FUNCTION refresh_aggregates()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    PERFORM refresh_country_hourly();
    PERFORM refresh_country_baseline();
END;
$$;

-- ===========================================================================
-- SEED: countries_v2 (top monitored countries)
-- ===========================================================================
INSERT INTO countries_v2 (code, name, latitude, longitude, updated_at) VALUES
    ('US', 'United States',    37.0902,  -95.7129, NOW()),
    ('GB', 'United Kingdom',   55.3781,   -3.4360, NOW()),
    ('DE', 'Germany',          51.1657,   10.4515, NOW()),
    ('FR', 'France',           46.2276,    2.2137, NOW()),
    ('CN', 'China',            35.8617,  104.1954, NOW()),
    ('RU', 'Russia',           61.5240,  105.3188, NOW()),
    ('IN', 'India',            20.5937,   78.9629, NOW()),
    ('BR', 'Brazil',          -14.2350,  -51.9253, NOW()),
    ('AU', 'Australia',       -25.2744,  133.7751, NOW()),
    ('CA', 'Canada',           56.1304,  -106.3468, NOW()),
    ('MX', 'Mexico',           23.6345, -102.5528, NOW()),
    ('AR', 'Argentina',       -38.4161,  -63.6167, NOW()),
    ('CO', 'Colombia',          4.5709,  -74.2973, NOW()),
    ('ZA', 'South Africa',    -30.5595,   22.9375, NOW()),
    ('NG', 'Nigeria',           9.0820,    8.6753, NOW()),
    ('EG', 'Egypt',            26.8206,   30.8025, NOW()),
    ('SA', 'Saudi Arabia',     23.8859,   45.0792, NOW()),
    ('IL', 'Israel',           31.0461,   34.8516, NOW()),
    ('TR', 'Turkey',           38.9637,   35.2433, NOW()),
    ('JP', 'Japan',            36.2048,  138.2529, NOW()),
    ('KR', 'South Korea',      35.9078,  127.7669, NOW()),
    ('ID', 'Indonesia',        -0.7893,  113.9213, NOW()),
    ('PK', 'Pakistan',         30.3753,   69.3451, NOW()),
    ('UA', 'Ukraine',          48.3794,   31.1656, NOW()),
    ('PL', 'Poland',           51.9194,   19.1451, NOW()),
    ('ES', 'Spain',            40.4637,   -3.7492, NOW()),
    ('IT', 'Italy',            41.8719,   12.5674, NOW()),
    ('NL', 'Netherlands',      52.1326,    5.2913, NOW()),
    ('SE', 'Sweden',           60.1282,   18.6435, NOW()),
    ('CH', 'Switzerland',      46.8182,    8.2275, NOW()),
    ('VE', 'Venezuela',         6.4238,  -66.5897, NOW()),
    ('IR', 'Iran',             32.4279,   53.6880, NOW()),
    ('IQ', 'Iraq',             33.2232,   43.6793, NOW()),
    ('SY', 'Syria',            34.8021,   38.9968, NOW()),
    ('AF', 'Afghanistan',      33.9391,   67.7100, NOW()),
    ('KP', 'North Korea',      40.3399,  127.5101, NOW()),
    ('BY', 'Belarus',          53.7098,   27.9534, NOW()),
    ('CU', 'Cuba',             21.5218,  -77.7812, NOW()),
    ('MM', 'Myanmar',          21.9162,   95.9560, NOW()),
    ('ET', 'Ethiopia',          9.1450,   40.4897, NOW())
ON CONFLICT (code) DO UPDATE SET
    name       = EXCLUDED.name,
    latitude   = EXCLUDED.latitude,
    longitude  = EXCLUDED.longitude,
    updated_at = NOW();

-- Default lifecycle config
INSERT INTO data_lifecycle_config (key, value, description) VALUES
    ('hot_retention_days',    '7',   'Days to keep signals in hot storage'),
    ('warm_retention_days',   '30',  'Days to keep hourly aggregates'),
    ('cold_retention_days',   '365', 'Days to keep daily aggregates'),
    ('max_signals_per_file',  '5000', 'Max signals ingested per GDELT file')
ON CONFLICT (key) DO NOTHING;

DO $$
BEGIN
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Atlas v2 schema migration complete.';
    RAISE NOTICE 'Tables: signals_v2, countries_v2, country_daily_v2,';
    RAISE NOTICE '        signals_country_hourly, signals_theme_hourly,';
    RAISE NOTICE '        signals_source_hourly, theme_daily_v2,';
    RAISE NOTICE '        country_baseline_stats, trending_themes,';
    RAISE NOTICE '        data_lifecycle_config, ingest_watermark, ingest_file_log';
    RAISE NOTICE 'Views:  country_hourly_v2 (materialized)';
    RAISE NOTICE 'Funcs:  refresh_country_hourly, refresh_country_baseline, refresh_aggregates';
    RAISE NOTICE 'Seed:   40 countries in countries_v2';
    RAISE NOTICE '================================================';
END $$;
