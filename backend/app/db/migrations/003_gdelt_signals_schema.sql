-- ============================================================================
-- Observatory Global - GDELT Signals Schema
-- Migration: 003_gdelt_signals_schema.sql
-- Purpose: Store raw GDELT GKG records with efficient querying for heatmaps and flows
-- Author: DataSignalArchitect
-- Date: 2025-01-15
-- Related: Issue #14, docs/GDELT_SCHEMA_ANALYSIS.md, docs/ITERATION_3_PLANNING.md
-- ============================================================================

-- ============================================================================
-- DESIGN DECISIONS
-- ============================================================================
--
-- 1. SEPARATE TABLES FOR THEMES/ENTITIES:
--    - signal_themes: Many-to-many relationship (articles have 5-30 themes)
--    - signal_entities: Persons and organizations extracted from articles
--    - Enables efficient filtering by theme/entity without full table scans
--
-- 2. TIME BUCKETING:
--    - bucket_15min: Matches GDELT publish cadence for real-time queries
--    - bucket_1h: Pre-computed for hourly aggregations (warm storage)
--    - Supports both real-time (6h) and trend analysis (30d) use cases
--
-- 3. TONE STORAGE:
--    - Store all 6 V2Tone components for full analysis capability
--    - tone_overall is primary sentiment indicator (-100 to +100)
--    - polarity indicates emotional intensity
--
-- 4. DEDUPLICATION:
--    - url_hash enables fast duplicate detection
--    - duplicate_count tracks merged articles
--    - Prevents same story from multiple outlets inflating metrics
--
-- 5. PERFORMANCE TARGETS:
--    - Query latency: < 100ms for heatmap/flow queries
--    - Ingestion: Support 1-2M rows/day (10-30K per 15-min file)
--    - Storage: ~500 bytes/row, ~500MB/day uncompressed
--
-- ============================================================================


-- ============================================================================
-- 1. GDELT SIGNALS (Core Table - Raw GKG Records)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gdelt_signals (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- GDELT Identity (Column 1, 2, 3)
    gkg_record_id VARCHAR(100) NOT NULL UNIQUE,  -- GKGRECORDID: YYYYMMDDHHMMSS-T##
    source_collection_id SMALLINT DEFAULT 1 CHECK (source_collection_id BETWEEN 1 AND 3),
    -- 1=Web, 2=CitizenMedia, 3=DiscussionForum

    -- Temporal (Column 2)
    timestamp TIMESTAMPTZ NOT NULL,  -- V2DATE: Article publication time (UTC)
    bucket_15min TIMESTAMPTZ NOT NULL,  -- Rounded to 15-min for GDELT cadence
    bucket_1h TIMESTAMPTZ NOT NULL,  -- Rounded to 1h for aggregations

    -- Geographic - Primary Location (Column 4)
    country_code VARCHAR(2) NOT NULL,  -- ISO 3166-1 alpha-2
    country_name VARCHAR(100),  -- Human-readable country name
    location_name VARCHAR(200),  -- City/region name if available
    latitude DECIMAL(9, 6),  -- Geographic latitude (-90 to 90)
    longitude DECIMAL(10, 6),  -- Geographic longitude (-180 to 180)
    location_type SMALLINT CHECK (location_type BETWEEN 1 AND 5),
    -- 1=Country, 2=US State, 3=US City, 4=World City, 5=World State
    feature_id VARCHAR(50),  -- GeoNames feature ID for precise geocoding

    -- All locations stored as JSONB for multi-location articles
    all_locations JSONB DEFAULT '[]'::jsonb,
    -- Format: [{"country_code": "US", "lat": 40.7, "lon": -74.0, ...}, ...]

    -- Tone/Sentiment (Column 7 - V2Tone: 6 values)
    tone_overall DECIMAL(5, 2) CHECK (tone_overall BETWEEN -100 AND 100),
    -- Overall sentiment: -100 (very negative) to +100 (very positive)
    tone_positive_pct DECIMAL(5, 2) CHECK (tone_positive_pct BETWEEN 0 AND 100),
    -- Percentage of positive words
    tone_negative_pct DECIMAL(5, 2) CHECK (tone_negative_pct BETWEEN 0 AND 100),
    -- Percentage of negative words
    polarity DECIMAL(5, 2) CHECK (polarity >= 0),
    -- Emotional intensity (distance from neutral)
    activity_density DECIMAL(5, 2) CHECK (activity_density >= 0),
    -- Action word density
    self_reference DECIMAL(5, 2) CHECK (self_reference >= 0),
    -- First-person plural references (we, us, our)

    -- Primary Theme (highest count from V2Counts)
    primary_theme VARCHAR(100) NOT NULL,  -- e.g., 'ECON_INFLATION'
    primary_theme_label VARCHAR(200),  -- e.g., 'Economic Inflation'
    primary_theme_count INTEGER DEFAULT 1 CHECK (primary_theme_count > 0),

    -- Total theme intensity (sum of all theme counts)
    total_theme_count INTEGER DEFAULT 1 CHECK (total_theme_count > 0),

    -- Derived/Computed Fields (for frontend efficiency)
    intensity DECIMAL(3, 2) CHECK (intensity BETWEEN 0 AND 1),
    -- Normalized: total_theme_count / global_max_count
    sentiment_label VARCHAR(20) CHECK (sentiment_label IN (
        'very_negative', 'negative', 'neutral', 'positive', 'very_positive'
    )),
    geographic_precision VARCHAR(10) CHECK (geographic_precision IN (
        'country', 'state', 'city'
    )),

    -- Source Information (Columns 20, 21)
    source_outlet VARCHAR(200),  -- V2SourceCommonName: e.g., 'nytimes.com'
    source_url TEXT,  -- V2DocumentIdentifier: Article URL

    -- Quality & Provenance
    confidence DECIMAL(3, 2) DEFAULT 1.0 CHECK (confidence BETWEEN 0 AND 1),
    -- Based on: source_reliability x location_precision x dedup_penalty
    source_gdelt BOOLEAN DEFAULT true,
    source_trends BOOLEAN DEFAULT false,
    source_wikipedia BOOLEAN DEFAULT false,

    -- Deduplication
    url_hash VARCHAR(32) NOT NULL,  -- MD5 hash of source_url
    duplicate_count INTEGER DEFAULT 1 CHECK (duplicate_count >= 1),
    duplicate_outlets TEXT[] DEFAULT '{}',  -- Other outlets with same story

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_coordinates CHECK (
        (latitude IS NULL AND longitude IS NULL) OR
        (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)
    )
);

-- Primary indexes for common query patterns
CREATE INDEX idx_gdelt_signals_country_bucket15
    ON gdelt_signals(country_code, bucket_15min DESC);
-- Most frequent query: Get signals for country in time window

CREATE INDEX idx_gdelt_signals_bucket15
    ON gdelt_signals(bucket_15min DESC);
-- Time-range queries across all countries

CREATE INDEX idx_gdelt_signals_bucket1h
    ON gdelt_signals(bucket_1h DESC);
-- Hourly aggregation queries

CREATE INDEX idx_gdelt_signals_primary_theme
    ON gdelt_signals(primary_theme, bucket_15min DESC);
-- Theme-based filtering

CREATE INDEX idx_gdelt_signals_country_theme
    ON gdelt_signals(country_code, primary_theme, bucket_15min DESC);
-- Country + theme filtering

CREATE INDEX idx_gdelt_signals_url_hash
    ON gdelt_signals(url_hash);
-- Fast deduplication lookup

CREATE INDEX idx_gdelt_signals_intensity
    ON gdelt_signals(intensity DESC)
    WHERE intensity > 0.5;
-- Filter high-intensity signals for heatmap

CREATE INDEX idx_gdelt_signals_sentiment
    ON gdelt_signals(sentiment_label, bucket_15min DESC);
-- Sentiment-based filtering

CREATE INDEX idx_gdelt_signals_source_outlet
    ON gdelt_signals(source_outlet)
    WHERE source_outlet IS NOT NULL;
-- Source diversity analysis

-- Composite index for heatmap queries (country + time + coordinates)
CREATE INDEX idx_gdelt_signals_heatmap
    ON gdelt_signals(country_code, bucket_15min DESC, latitude, longitude)
    WHERE latitude IS NOT NULL;

-- GIN index for all_locations JSONB queries
CREATE INDEX idx_gdelt_signals_all_locations
    ON gdelt_signals USING GIN(all_locations);

-- Comments
COMMENT ON TABLE gdelt_signals IS 'Raw GDELT GKG records - core signals table for narrative intelligence';
COMMENT ON COLUMN gdelt_signals.gkg_record_id IS 'GDELT unique ID format: YYYYMMDDHHMMSS-T## (e.g., 20250115120000-T52)';
COMMENT ON COLUMN gdelt_signals.bucket_15min IS 'Timestamp rounded to 15-min intervals matching GDELT publish cadence';
COMMENT ON COLUMN gdelt_signals.tone_overall IS 'GDELT V2Tone first value: -100 (very negative) to +100 (very positive)';
COMMENT ON COLUMN gdelt_signals.intensity IS 'Normalized theme intensity [0,1] for heatmap visualization';
COMMENT ON COLUMN gdelt_signals.url_hash IS 'MD5 hash of source_url for fast deduplication';


-- ============================================================================
-- 2. SIGNAL THEMES (Many-to-Many Theme Relationships)
-- ============================================================================

CREATE TABLE IF NOT EXISTS signal_themes (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Foreign key to signal
    signal_id BIGINT NOT NULL REFERENCES gdelt_signals(id) ON DELETE CASCADE,

    -- Theme data (from V2Themes and V2Counts)
    theme_code VARCHAR(100) NOT NULL,  -- Raw GDELT code: e.g., 'ECON_INFLATION'
    theme_label VARCHAR(200),  -- Human-readable: e.g., 'Economic Inflation'
    theme_count INTEGER DEFAULT 1 CHECK (theme_count >= 1),  -- From V2Counts

    -- Theme taxonomy
    theme_category VARCHAR(50),  -- High-level: 'economy', 'politics', 'security'
    theme_prefix VARCHAR(20),  -- Taxonomy prefix: 'ECON_', 'TAX_', 'WB_', etc.

    -- Relative importance within this signal
    weight DECIMAL(3, 2) CHECK (weight BETWEEN 0 AND 1),
    -- Calculated: theme_count / total_theme_count

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate theme entries per signal
    UNIQUE(signal_id, theme_code)
);

-- Indexes for efficient theme queries
CREATE INDEX idx_signal_themes_signal
    ON signal_themes(signal_id);
-- Join with gdelt_signals

CREATE INDEX idx_signal_themes_code
    ON signal_themes(theme_code);
-- Filter by specific theme

CREATE INDEX idx_signal_themes_category
    ON signal_themes(theme_category)
    WHERE theme_category IS NOT NULL;
-- Filter by theme category

CREATE INDEX idx_signal_themes_count
    ON signal_themes(theme_count DESC);
-- Sort by importance

-- Composite index for theme time-series queries
CREATE INDEX idx_signal_themes_code_signal
    ON signal_themes(theme_code, signal_id DESC);

-- Comments
COMMENT ON TABLE signal_themes IS 'Many-to-many relationship: signals to GDELT themes (V2Themes + V2Counts)';
COMMENT ON COLUMN signal_themes.theme_code IS 'Raw GDELT taxonomy code (e.g., TAX_TERROR, ECON_INFLATION, WB_632_*)';
COMMENT ON COLUMN signal_themes.theme_count IS 'Mention frequency from V2Counts - higher = more prominent in article';
COMMENT ON COLUMN signal_themes.weight IS 'Relative importance within signal [0,1]';


-- ============================================================================
-- 3. SIGNAL ENTITIES (Persons and Organizations)
-- ============================================================================

CREATE TABLE IF NOT EXISTS signal_entities (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Foreign key to signal
    signal_id BIGINT NOT NULL REFERENCES gdelt_signals(id) ON DELETE CASCADE,

    -- Entity data (from V2Persons and V2Organizations)
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('person', 'organization')),
    entity_name VARCHAR(500) NOT NULL,  -- e.g., 'Donald Trump', 'Federal Reserve'

    -- Normalized form for deduplication
    entity_name_normalized VARCHAR(500),  -- Lowercase, trimmed: 'donald trump'

    -- Position in article (if available)
    char_offset INTEGER,  -- Character position where first mentioned
    mention_count INTEGER DEFAULT 1 CHECK (mention_count >= 1),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate entity entries per signal
    UNIQUE(signal_id, entity_type, entity_name_normalized)
);

-- Indexes for entity queries
CREATE INDEX idx_signal_entities_signal
    ON signal_entities(signal_id);
-- Join with gdelt_signals

CREATE INDEX idx_signal_entities_type
    ON signal_entities(entity_type);
-- Filter by type

CREATE INDEX idx_signal_entities_name
    ON signal_entities(entity_name_normalized);
-- Search by entity name

CREATE INDEX idx_signal_entities_type_name
    ON signal_entities(entity_type, entity_name_normalized);
-- Combined filter

-- Text search index for entity names
CREATE INDEX idx_signal_entities_name_trgm
    ON signal_entities USING GIN(entity_name_normalized gin_trgm_ops);
-- Requires: CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Comments
COMMENT ON TABLE signal_entities IS 'Named entities extracted from GDELT signals (V2Persons, V2Organizations)';
COMMENT ON COLUMN signal_entities.entity_type IS 'Entity category: person or organization';
COMMENT ON COLUMN signal_entities.entity_name_normalized IS 'Lowercase, trimmed for deduplication and search';


-- ============================================================================
-- 4. THEME AGGREGATIONS (Hourly Rollups - Warm Storage)
-- ============================================================================

CREATE TABLE IF NOT EXISTS theme_aggregations_1h (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Dimensions
    hour_bucket TIMESTAMPTZ NOT NULL,  -- Rounded to hour
    country_code VARCHAR(2) NOT NULL,
    theme_code VARCHAR(100) NOT NULL,

    -- Volume metrics
    signal_count INTEGER NOT NULL DEFAULT 0 CHECK (signal_count >= 0),
    -- Number of signals with this theme in this hour
    total_theme_mentions INTEGER NOT NULL DEFAULT 0 CHECK (total_theme_mentions >= 0),
    -- Sum of theme_count across all signals

    -- Sentiment aggregates
    avg_tone DECIMAL(5, 2),  -- Average tone_overall
    min_tone DECIMAL(5, 2),
    max_tone DECIMAL(5, 2),
    avg_polarity DECIMAL(5, 2),

    -- Intensity
    avg_intensity DECIMAL(3, 2) CHECK (avg_intensity BETWEEN 0 AND 1),
    max_intensity DECIMAL(3, 2) CHECK (max_intensity BETWEEN 0 AND 1),

    -- Source diversity
    unique_outlets INTEGER DEFAULT 0,  -- Count of distinct source_outlet values
    outlet_list TEXT[],  -- Top outlets (max 10)

    -- Sample content (for UI preview)
    sample_urls TEXT[],  -- Up to 3 example URLs

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Composite unique constraint
    UNIQUE(hour_bucket, country_code, theme_code)
);

-- Indexes for aggregation queries
CREATE INDEX idx_theme_agg_1h_country_hour
    ON theme_aggregations_1h(country_code, hour_bucket DESC);
-- Country time-series

CREATE INDEX idx_theme_agg_1h_hour
    ON theme_aggregations_1h(hour_bucket DESC);
-- Global time-series

CREATE INDEX idx_theme_agg_1h_theme_hour
    ON theme_aggregations_1h(theme_code, hour_bucket DESC);
-- Theme time-series

CREATE INDEX idx_theme_agg_1h_country_theme
    ON theme_aggregations_1h(country_code, theme_code, hour_bucket DESC);
-- Country + theme time-series

CREATE INDEX idx_theme_agg_1h_signal_count
    ON theme_aggregations_1h(signal_count DESC)
    WHERE signal_count > 10;
-- High-volume themes

-- Comments
COMMENT ON TABLE theme_aggregations_1h IS 'Hourly rollups of theme activity by country - warm storage for trend analysis';
COMMENT ON COLUMN theme_aggregations_1h.signal_count IS 'Number of signals containing this theme in the hour';
COMMENT ON COLUMN theme_aggregations_1h.total_theme_mentions IS 'Sum of theme_count - total mentions across all signals';


-- ============================================================================
-- 5. HELPER FUNCTIONS
-- ============================================================================

-- Function: Calculate 15-minute bucket from timestamp
CREATE OR REPLACE FUNCTION bucket_15min(ts TIMESTAMPTZ)
RETURNS TIMESTAMPTZ AS $$
BEGIN
    RETURN date_trunc('hour', ts) +
           INTERVAL '15 minutes' * FLOOR(EXTRACT(MINUTE FROM ts) / 15);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION bucket_15min IS 'Round timestamp to 15-minute bucket for GDELT cadence';


-- Function: Calculate 1-hour bucket from timestamp
CREATE OR REPLACE FUNCTION bucket_1h(ts TIMESTAMPTZ)
RETURNS TIMESTAMPTZ AS $$
BEGIN
    RETURN date_trunc('hour', ts);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION bucket_1h IS 'Round timestamp to 1-hour bucket for aggregations';


-- Function: Derive sentiment label from tone
CREATE OR REPLACE FUNCTION sentiment_label(tone DECIMAL)
RETURNS VARCHAR(20) AS $$
BEGIN
    IF tone < -10 THEN
        RETURN 'very_negative';
    ELSIF tone < -2 THEN
        RETURN 'negative';
    ELSIF tone < 2 THEN
        RETURN 'neutral';
    ELSIF tone < 10 THEN
        RETURN 'positive';
    ELSE
        RETURN 'very_positive';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION sentiment_label IS 'Derive categorical sentiment from V2Tone overall score';


-- Function: Derive geographic precision from location type
CREATE OR REPLACE FUNCTION geographic_precision(loc_type SMALLINT)
RETURNS VARCHAR(10) AS $$
BEGIN
    CASE loc_type
        WHEN 1 THEN RETURN 'country';
        WHEN 2 THEN RETURN 'state';
        WHEN 5 THEN RETURN 'state';
        ELSE RETURN 'city';
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION geographic_precision IS 'Derive precision level from GDELT location type (1-5)';


-- ============================================================================
-- 6. TRIGGER: Auto-populate derived fields
-- ============================================================================

CREATE OR REPLACE FUNCTION populate_gdelt_derived_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- Set bucket timestamps if not provided
    IF NEW.bucket_15min IS NULL THEN
        NEW.bucket_15min := bucket_15min(NEW.timestamp);
    END IF;

    IF NEW.bucket_1h IS NULL THEN
        NEW.bucket_1h := bucket_1h(NEW.timestamp);
    END IF;

    -- Set sentiment label if not provided
    IF NEW.sentiment_label IS NULL AND NEW.tone_overall IS NOT NULL THEN
        NEW.sentiment_label := sentiment_label(NEW.tone_overall);
    END IF;

    -- Set geographic precision if not provided
    IF NEW.geographic_precision IS NULL AND NEW.location_type IS NOT NULL THEN
        NEW.geographic_precision := geographic_precision(NEW.location_type);
    END IF;

    -- Set updated_at
    NEW.updated_at := NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_gdelt_derived_fields
    BEFORE INSERT OR UPDATE ON gdelt_signals
    FOR EACH ROW
    EXECUTE FUNCTION populate_gdelt_derived_fields();

COMMENT ON FUNCTION populate_gdelt_derived_fields IS 'Auto-populate bucket timestamps and derived labels';


-- ============================================================================
-- 7. TRIGGER: Update theme aggregations on signal insert
-- ============================================================================

CREATE OR REPLACE FUNCTION update_theme_aggregations()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert or update hourly aggregation for each theme
    INSERT INTO theme_aggregations_1h (
        hour_bucket,
        country_code,
        theme_code,
        signal_count,
        total_theme_mentions,
        avg_tone,
        min_tone,
        max_tone,
        avg_polarity,
        avg_intensity,
        max_intensity
    )
    SELECT
        NEW.bucket_1h,
        NEW.country_code,
        st.theme_code,
        1,
        st.theme_count,
        NEW.tone_overall,
        NEW.tone_overall,
        NEW.tone_overall,
        NEW.polarity,
        NEW.intensity,
        NEW.intensity
    FROM signal_themes st
    WHERE st.signal_id = NEW.id
    ON CONFLICT (hour_bucket, country_code, theme_code)
    DO UPDATE SET
        signal_count = theme_aggregations_1h.signal_count + 1,
        total_theme_mentions = theme_aggregations_1h.total_theme_mentions + EXCLUDED.total_theme_mentions,
        avg_tone = (theme_aggregations_1h.avg_tone * theme_aggregations_1h.signal_count + EXCLUDED.avg_tone)
                   / (theme_aggregations_1h.signal_count + 1),
        min_tone = LEAST(theme_aggregations_1h.min_tone, EXCLUDED.min_tone),
        max_tone = GREATEST(theme_aggregations_1h.max_tone, EXCLUDED.max_tone),
        avg_polarity = (theme_aggregations_1h.avg_polarity * theme_aggregations_1h.signal_count + EXCLUDED.avg_polarity)
                       / (theme_aggregations_1h.signal_count + 1),
        avg_intensity = (theme_aggregations_1h.avg_intensity * theme_aggregations_1h.signal_count + EXCLUDED.avg_intensity)
                        / (theme_aggregations_1h.signal_count + 1),
        max_intensity = GREATEST(theme_aggregations_1h.max_intensity, EXCLUDED.max_intensity),
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: This trigger should be called AFTER signal_themes are inserted
-- It's typically better to handle this in application code for batch inserts

COMMENT ON FUNCTION update_theme_aggregations IS 'Update hourly aggregations when signal themes are inserted';


-- ============================================================================
-- 8. FOREIGN KEY TO COUNTRIES TABLE
-- ============================================================================

-- Add foreign key constraint if countries table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'countries') THEN
        ALTER TABLE gdelt_signals
        ADD CONSTRAINT fk_gdelt_signals_country
        FOREIGN KEY (country_code) REFERENCES countries(country_code) ON DELETE CASCADE;

        ALTER TABLE theme_aggregations_1h
        ADD CONSTRAINT fk_theme_agg_1h_country
        FOREIGN KEY (country_code) REFERENCES countries(country_code) ON DELETE CASCADE;

        RAISE NOTICE 'Foreign key constraints to countries table added successfully';
    ELSE
        RAISE NOTICE 'Countries table not found - foreign key constraints skipped';
    END IF;
END $$;


-- ============================================================================
-- 9. ENABLE TRIGRAM EXTENSION FOR ENTITY SEARCH
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

COMMENT ON EXTENSION pg_trgm IS 'Enable fuzzy text search for entity names';


-- ============================================================================
-- 10. STORAGE ESTIMATES
-- ============================================================================

-- Storage calculations for gdelt_signals table:
--
-- Per row estimate (average):
-- - id: 8 bytes
-- - gkg_record_id: 30 bytes
-- - timestamps (3): 24 bytes
-- - country fields: 120 bytes
-- - coordinates: 24 bytes
-- - tone fields (6): 48 bytes
-- - theme fields: 150 bytes
-- - derived fields: 20 bytes
-- - source fields: 300 bytes (variable)
-- - dedup fields: 100 bytes
-- - metadata: 16 bytes
-- - Row overhead: 24 bytes
-- TOTAL: ~500 bytes/row average
--
-- Daily volume: 1-2M signals/day
-- Daily storage: 500-1000 MB/day
-- Monthly storage: 15-30 GB/month (before partitioning/archival)
--
-- signal_themes table:
-- - ~8 themes per signal average
-- - ~100 bytes per row
-- - 8M-16M rows/day
-- - 800MB-1.6GB/day
--
-- theme_aggregations_1h:
-- - 10 countries x 100 themes x 24 hours = 24K rows/day
-- - ~200 bytes per row
-- - ~5MB/day (negligible)


-- ============================================================================
-- END OF MIGRATION
-- ============================================================================

-- Verify migration
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Migration 003_gdelt_signals_schema.sql completed successfully!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - gdelt_signals (core GDELT GKG records)';
    RAISE NOTICE '  - signal_themes (many-to-many theme relationships)';
    RAISE NOTICE '  - signal_entities (persons and organizations)';
    RAISE NOTICE '  - theme_aggregations_1h (hourly rollups)';
    RAISE NOTICE '';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  - bucket_15min() - Round to 15-minute bucket';
    RAISE NOTICE '  - bucket_1h() - Round to 1-hour bucket';
    RAISE NOTICE '  - sentiment_label() - Derive sentiment from tone';
    RAISE NOTICE '  - geographic_precision() - Derive precision from location type';
    RAISE NOTICE '';
    RAISE NOTICE 'Triggers created:';
    RAISE NOTICE '  - trigger_gdelt_derived_fields';
    RAISE NOTICE '';
    RAISE NOTICE 'Performance targets:';
    RAISE NOTICE '  - Query latency: < 100ms';
    RAISE NOTICE '  - Ingestion: 1-2M rows/day';
    RAISE NOTICE '  - Storage: ~500MB/day (signals table)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  - Run migration: python -m app.db.migrate';
    RAISE NOTICE '  - Implement GDELT parser to populate tables';
    RAISE NOTICE '  - Test with sample data';
    RAISE NOTICE '';
END $$;
