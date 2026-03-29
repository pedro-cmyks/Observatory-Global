-- Hourly aggregate tables for Plain Postgres
-- (TimescaleDB continuous aggregates not available)

-- Country hourly aggregate
CREATE TABLE IF NOT EXISTS signals_country_hourly (
    bucket TIMESTAMP NOT NULL,
    country_code VARCHAR(10) NOT NULL,
    signal_count INTEGER NOT NULL DEFAULT 0,
    avg_sentiment NUMERIC(5,2),
    unique_sources INTEGER DEFAULT 0,
    PRIMARY KEY (bucket, country_code)
);

CREATE INDEX IF NOT EXISTS idx_country_hourly_bucket ON signals_country_hourly(bucket DESC);
CREATE INDEX IF NOT EXISTS idx_country_hourly_country ON signals_country_hourly(country_code);

-- Theme hourly aggregate
CREATE TABLE IF NOT EXISTS signals_theme_hourly (
    bucket TIMESTAMP NOT NULL,
    theme VARCHAR(255) NOT NULL,
    signal_count INTEGER NOT NULL DEFAULT 0,
    avg_sentiment NUMERIC(5,2),
    PRIMARY KEY (bucket, theme)
);

CREATE INDEX IF NOT EXISTS idx_theme_hourly_bucket ON signals_theme_hourly(bucket DESC);

-- Source hourly aggregate
CREATE TABLE IF NOT EXISTS signals_source_hourly (
    bucket TIMESTAMP NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    signal_count INTEGER NOT NULL DEFAULT 0,
    avg_sentiment NUMERIC(5,2),
    PRIMARY KEY (bucket, source_name)
);

CREATE INDEX IF NOT EXISTS idx_source_hourly_bucket ON signals_source_hourly(bucket DESC);

-- Refresh function (call via cron hourly or after ingestion)
CREATE OR REPLACE FUNCTION refresh_aggregates(hours_back INTEGER DEFAULT 48)
RETURNS TABLE(countries_updated INT, themes_updated INT, sources_updated INT) AS $$
DECLARE
    country_count INT := 0;
    theme_count INT := 0;
    source_count INT := 0;
BEGIN
    -- Country hourly
    INSERT INTO signals_country_hourly (bucket, country_code, signal_count, avg_sentiment, unique_sources)
    SELECT 
        date_trunc('hour', timestamp) AS bucket,
        country_code,
        COUNT(*) AS signal_count,
        ROUND(AVG(sentiment)::numeric, 2) AS avg_sentiment,
        COUNT(DISTINCT source_name) AS unique_sources
    FROM signals_v2
    WHERE timestamp > NOW() - (hours_back * INTERVAL '1 hour')
      AND country_code IS NOT NULL
    GROUP BY 1, 2
    ON CONFLICT (bucket, country_code) DO UPDATE SET
        signal_count = EXCLUDED.signal_count,
        avg_sentiment = EXCLUDED.avg_sentiment,
        unique_sources = EXCLUDED.unique_sources;
    GET DIAGNOSTICS country_count = ROW_COUNT;
    
    -- Theme hourly (unnest themes array)
    INSERT INTO signals_theme_hourly (bucket, theme, signal_count, avg_sentiment)
    SELECT 
        date_trunc('hour', timestamp) AS bucket,
        unnest(themes) AS theme,
        COUNT(*) AS signal_count,
        ROUND(AVG(sentiment)::numeric, 2) AS avg_sentiment
    FROM signals_v2
    WHERE timestamp > NOW() - (hours_back * INTERVAL '1 hour')
      AND themes IS NOT NULL AND array_length(themes, 1) > 0
    GROUP BY 1, 2
    ON CONFLICT (bucket, theme) DO UPDATE SET
        signal_count = EXCLUDED.signal_count,
        avg_sentiment = EXCLUDED.avg_sentiment;
    GET DIAGNOSTICS theme_count = ROW_COUNT;
    
    -- Source hourly
    INSERT INTO signals_source_hourly (bucket, source_name, signal_count, avg_sentiment)
    SELECT 
        date_trunc('hour', timestamp) AS bucket,
        source_name,
        COUNT(*) AS signal_count,
        ROUND(AVG(sentiment)::numeric, 2) AS avg_sentiment
    FROM signals_v2
    WHERE timestamp > NOW() - (hours_back * INTERVAL '1 hour')
      AND source_name IS NOT NULL
    GROUP BY 1, 2
    ON CONFLICT (bucket, source_name) DO UPDATE SET
        signal_count = EXCLUDED.signal_count,
        avg_sentiment = EXCLUDED.avg_sentiment;
    GET DIAGNOSTICS source_count = ROW_COUNT;
    
    RAISE NOTICE 'Aggregates refreshed: % countries, % themes, % sources', country_count, theme_count, source_count;
    
    RETURN QUERY SELECT country_count, theme_count, source_count;
END;
$$ LANGUAGE plpgsql;

-- Safe retention cleanup function
CREATE OR REPLACE FUNCTION safe_retention_cleanup()
RETURNS INTEGER AS $$
DECLARE
    retention_days INTEGER;
    policy_active BOOLEAN;
    deleted_count INTEGER := 0;
BEGIN
    SELECT value::boolean INTO policy_active 
    FROM data_lifecycle_config 
    WHERE key = 'retention_policy_active';
    
    IF NOT COALESCE(policy_active, false) THEN
        RAISE NOTICE 'Retention policy not active. Set retention_policy_active=true to enable.';
        RETURN 0;
    END IF;
    
    SELECT value::integer INTO retention_days 
    FROM data_lifecycle_config 
    WHERE key = 'raw_retention_days';
    
    -- Delete in batches to avoid long locks
    DELETE FROM signals_v2 
    WHERE id IN (
        SELECT id FROM signals_v2 
        WHERE timestamp < NOW() - (retention_days * INTERVAL '1 day')
        LIMIT 10000
    );
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE 'Deleted % old signals', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
