-- Observatory Global v2 - Simplified Schema
-- NO TimescaleDB required (not available in current setup)
-- Uses standard PostgreSQL features for compatibility

-- Enable PostGIS if available (optional for geo queries)
CREATE EXTENSION IF NOT EXISTS postgis;

-- Core signals table (simplified from v1)
-- This is the ONLY table that stores raw signals
CREATE TABLE IF NOT EXISTS signals_v2 (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    country_code CHAR(2) NOT NULL,
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6),
    sentiment NUMERIC(4,2),  -- -10 to +10 (GDELT tone)
    source_url TEXT,
    source_name TEXT,
    themes TEXT[],  -- Array of theme codes
    persons TEXT[], -- Array of person names
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast time-based queries
CREATE INDEX IF NOT EXISTS idx_signals_v2_timestamp ON signals_v2(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_v2_country_time ON signals_v2(country_code, timestamp DESC);

-- Countries reference (auto-populated as we see them)
CREATE TABLE IF NOT EXISTS countries_v2 (
    code CHAR(2) PRIMARY KEY,
    name TEXT,
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Materialized view: hourly country stats
-- Replaces continuous aggregates (since TimescaleDB not available)
-- Refresh this with: REFRESH MATERIALIZED VIEW CONCURRENTLY country_hourly_v2;
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
GROUP BY hour, country_code;

-- Create unique index for CONCURRENT refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_country_hourly_v2_unique 
ON country_hourly_v2(hour, country_code);

-- Index for fast queries on the materialized view
CREATE INDEX IF NOT EXISTS idx_country_hourly_v2_hour ON country_hourly_v2(hour DESC);

-- Optional: Create a function to refresh the materialized view
-- Can be called manually or via cron
CREATE OR REPLACE FUNCTION refresh_country_hourly() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY country_hourly_v2;
END;
$$ LANGUAGE plpgsql;

-- Comment the tables for documentation
COMMENT ON TABLE signals_v2 IS 'v2: Simplified signals table - core GDELT data';
COMMENT ON TABLE countries_v2 IS 'v2: Country reference data';
COMMENT ON MATERIALIZED VIEW country_hourly_v2 IS 'v2: Hourly aggregated country statistics (refresh manually or via cron)';
