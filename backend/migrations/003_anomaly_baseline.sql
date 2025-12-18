-- Baseline statistics for anomaly detection
-- Works on plain Postgres (no TimescaleDB required)

CREATE TABLE IF NOT EXISTS country_baseline_stats (
    country_code VARCHAR(10) PRIMARY KEY,
    avg_daily_signals NUMERIC DEFAULT 0,
    stddev_daily_signals NUMERIC DEFAULT 0,
    last_7d_total INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_baseline_updated ON country_baseline_stats(updated_at);

-- Function to refresh baseline stats (call via cron or manually)
CREATE OR REPLACE FUNCTION refresh_country_baseline()
RETURNS void AS $$
BEGIN
    TRUNCATE country_baseline_stats;
    
    INSERT INTO country_baseline_stats (country_code, avg_daily_signals, stddev_daily_signals, last_7d_total, updated_at)
    SELECT 
        country_code,
        AVG(daily_count) as avg_daily_signals,
        COALESCE(STDDEV(daily_count), AVG(daily_count) * 0.3) as stddev_daily_signals,
        SUM(daily_count)::integer as last_7d_total,
        NOW() as updated_at
    FROM (
        SELECT 
            country_code,
            DATE(timestamp) as day,
            COUNT(*) as daily_count
        FROM signals_v2
        WHERE timestamp > NOW() - INTERVAL '7 days'
        GROUP BY country_code, DATE(timestamp)
    ) daily
    GROUP BY country_code;
END;
$$ LANGUAGE plpgsql;

-- Initial population
SELECT refresh_country_baseline();

COMMENT ON TABLE country_baseline_stats IS 'Pre-computed baseline for anomaly detection. Refresh daily via cron or manual call to refresh_country_baseline()';
