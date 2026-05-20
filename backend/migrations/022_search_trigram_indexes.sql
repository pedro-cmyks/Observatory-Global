-- Migration 022: Trigram indexes for production search and topic lexicon backfill.
-- Issue #170.
--
-- Run each CREATE INDEX CONCURRENTLY outside a transaction. These indexes support:
--   - /api/v2/search/unified headline matches
--   - wiki public-attention search on lower(article_title)
--   - Track B.2 SQL lexicon topic classifier over lower(headline)

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_headline_trgm
    ON signals_v2 USING gin (lower(headline) gin_trgm_ops)
    WHERE headline IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_source_name_trgm
    ON signals_v2 USING gin (lower(source_name) gin_trgm_ops)
    WHERE source_name IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_themes_gin
    ON signals_v2 USING gin (themes)
    WHERE themes IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_created_id_headline
    ON signals_v2 (created_at DESC, id DESC)
    WHERE headline IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wiki_pageviews_v2_article_title_lower_trgm
    ON wiki_pageviews_v2 USING gin (lower(article_title) gin_trgm_ops);
