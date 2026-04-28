-- ============================================================================
-- Observatory Global - Google Trends Integration
-- Migration: 004_google_trends.sql
-- Purpose: Store trending search terms from Google Trends for public-attention signals
-- ============================================================================

CREATE TABLE IF NOT EXISTS trends_v2 (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    country_code VARCHAR(2) NOT NULL,
    keyword TEXT NOT NULL,
    rank INTEGER,                        -- Position in trending list (1 = hottest)
    approximate_volume INTEGER DEFAULT 0, -- Relative search volume if available
    -- Dedup key (hour bucket enforced by unique index below)
    hour_bucket TIMESTAMPTZ GENERATED ALWAYS AS (date_trunc('hour', timestamp)) STORED,
    UNIQUE(country_code, keyword, hour_bucket)
);

-- Indexes for common queries
CREATE INDEX idx_trends_v2_country_ts
    ON trends_v2(country_code, timestamp DESC);

CREATE INDEX idx_trends_v2_keyword
    ON trends_v2(keyword);

CREATE INDEX idx_trends_v2_ts
    ON trends_v2(timestamp DESC);

-- Full-text search on keywords
CREATE INDEX idx_trends_v2_keyword_trgm
    ON trends_v2 USING GIN(keyword gin_trgm_ops);

COMMENT ON TABLE trends_v2 IS 'Google Trends trending searches — what people are searching for, by country';
COMMENT ON COLUMN trends_v2.rank IS 'Position in trending list: 1 = hottest search term';
COMMENT ON COLUMN trends_v2.approximate_volume IS 'Relative search volume (pytrends does not always provide this)';

-- ============================================================================
-- Verify
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Migration 004_google_trends.sql completed successfully!';
    RAISE NOTICE 'Table created: trends_v2';
END $$;
