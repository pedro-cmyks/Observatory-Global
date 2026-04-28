-- ============================================================================
-- Observatory Global - Wikipedia Pageviews Integration
-- Migration: 005_wiki_pageviews.sql
-- Purpose: Store top Wikipedia articles by pageviews for public-attention signals
-- ============================================================================

CREATE TABLE IF NOT EXISTS wiki_pageviews_v2 (
    id SERIAL PRIMARY KEY,
    fetch_date DATE NOT NULL DEFAULT CURRENT_DATE,
    country_code VARCHAR(2) NOT NULL,    -- Mapped from language edition
    language VARCHAR(5) NOT NULL,         -- Wikipedia language code (en, es, fr, etc.)
    article_title TEXT NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,     -- Pageview count
    rank INTEGER,                         -- Position in top-viewed list
    -- One entry per article per country per day
    UNIQUE(fetch_date, country_code, article_title)
);

-- Indexes
CREATE INDEX idx_wiki_pv_country_date
    ON wiki_pageviews_v2(country_code, fetch_date DESC);

CREATE INDEX idx_wiki_pv_date
    ON wiki_pageviews_v2(fetch_date DESC);

CREATE INDEX idx_wiki_pv_title_trgm
    ON wiki_pageviews_v2 USING GIN(article_title gin_trgm_ops);

COMMENT ON TABLE wiki_pageviews_v2 IS 'Top Wikipedia articles by pageviews — what people are reading about, by country';

DO $$
BEGIN
    RAISE NOTICE 'Migration 005_wiki_pageviews.sql completed successfully!';
    RAISE NOTICE 'Table created: wiki_pageviews_v2';
END $$;
