-- ============================================================================
-- Observatory Global - Comprehensive Flow Analysis Schema
-- Migration: 002_comprehensive_flow_schema.sql
-- Purpose: Support flow analysis, narrative evolution, and stance tracking
-- Author: Database Design Agent
-- Date: 2025-01-13
-- Related: ADR-0002 (Heat Formula), docs/database-schema-design.md
-- ============================================================================

-- Enable UUID extension for better distributed IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable PostGIS for future geo-queries (optional but recommended)
-- Uncomment if you want geo-spatial features in Iteration 3+
-- CREATE EXTENSION IF NOT EXISTS postgis;


-- ============================================================================
-- 1. REFERENCE TABLES (Static/Slowly Changing)
-- ============================================================================

-- Countries reference table
CREATE TABLE IF NOT EXISTS countries (
    country_code VARCHAR(2) PRIMARY KEY,
    country_name VARCHAR(100) NOT NULL,
    region VARCHAR(50),  -- e.g., 'South America', 'Europe', 'Asia'
    subregion VARCHAR(50),  -- e.g., 'Southern Europe', 'Western Asia'
    latitude DECIMAL(10, 8),  -- For map visualization
    longitude DECIMAL(11, 8),
    population BIGINT,  -- For normalizing topic counts
    languages JSONB,  -- ['en', 'es'], for future translation features
    timezone VARCHAR(50),
    is_active BOOLEAN DEFAULT true,  -- Monitor this country?
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_countries_region ON countries(region);
CREATE INDEX idx_countries_active ON countries(is_active) WHERE is_active = true;

-- Comments
COMMENT ON TABLE countries IS 'Reference table for country metadata and geo-coordinates';
COMMENT ON COLUMN countries.is_active IS 'Set to false to exclude from monitoring without deleting historical data';


-- ============================================================================
-- 2. TOPICS MASTER TABLE (Slowly Growing)
-- ============================================================================

-- Topics master table (normalized, deduplicated)
CREATE TABLE IF NOT EXISTS topics (
    topic_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    normalized_label VARCHAR(500) NOT NULL UNIQUE,  -- Canonical form
    aliases TEXT[],  -- Alternative phrasings: ['election fraud', 'voter fraud', 'electoral irregularities']
    category VARCHAR(100),  -- e.g., 'politics', 'economics', 'health', 'environment'
    keywords TEXT[],  -- For search and matching: ['election', 'fraud', 'vote']
    first_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    total_appearance_count INTEGER DEFAULT 0,  -- How many times seen across all snapshots
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_topics_label ON topics(normalized_label);
CREATE INDEX idx_topics_category ON topics(category);
CREATE INDEX idx_topics_last_seen ON topics(last_seen_at DESC);
CREATE INDEX idx_topics_aliases ON topics USING GIN(aliases);  -- For array searches
CREATE INDEX idx_topics_keywords ON topics USING GIN(keywords);  -- For full-text search

-- Comments
COMMENT ON TABLE topics IS 'Master table of all unique topics with normalized labels and aliases';
COMMENT ON COLUMN topics.normalized_label IS 'Canonical topic name used for deduplication';
COMMENT ON COLUMN topics.aliases IS 'Array of alternative phrasings for fuzzy matching';


-- ============================================================================
-- 3. TOPIC SNAPSHOTS (Time-Series Core - PARTITIONED)
-- ============================================================================

-- Topic snapshots (most granular time-series data)
CREATE TABLE IF NOT EXISTS topic_snapshots (
    snapshot_id UUID DEFAULT uuid_generate_v4(),
    topic_id UUID NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    country_code VARCHAR(2) NOT NULL REFERENCES countries(country_code) ON DELETE CASCADE,
    snapshot_time TIMESTAMP NOT NULL,  -- When this topic was observed

    -- Volume metrics
    count INTEGER NOT NULL DEFAULT 0 CHECK (count >= 0),  -- Raw frequency/popularity
    volume_score DECIMAL(3, 2) CHECK (volume_score >= 0 AND volume_score <= 1),  -- Normalized [0,1]

    -- Velocity metrics (how fast it's rising)
    velocity_score DECIMAL(3, 2) CHECK (velocity_score >= 0 AND velocity_score <= 1),
    delta_count INTEGER DEFAULT 0,  -- Change since last snapshot (+/-)
    growth_rate DECIMAL(5, 2),  -- Percentage growth since last snapshot

    -- Confidence and source
    confidence DECIMAL(3, 2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    sources JSONB NOT NULL DEFAULT '[]'::jsonb,  -- ['gdelt', 'google_trends', 'wikipedia']

    -- Sample content
    sample_titles TEXT[],  -- Up to 5 sample headlines
    sample_urls TEXT[],  -- Corresponding URLs

    -- Stance/sentiment (for narrative tracking)
    avg_sentiment DECIMAL(3, 2),  -- [-1, 1]: negative to positive
    stance_label VARCHAR(50),  -- e.g., 'pro', 'anti', 'neutral', 'mixed'

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),

    -- Composite primary key (partition key + unique identifier)
    PRIMARY KEY (snapshot_time, snapshot_id)

) PARTITION BY RANGE (snapshot_time);

-- Indexes (will be created on each partition automatically)
CREATE INDEX idx_topic_snapshots_topic ON topic_snapshots(topic_id, snapshot_time DESC);
CREATE INDEX idx_topic_snapshots_country ON topic_snapshots(country_code, snapshot_time DESC);
CREATE INDEX idx_topic_snapshots_time ON topic_snapshots(snapshot_time DESC);
CREATE INDEX idx_topic_snapshots_count ON topic_snapshots(count DESC);
CREATE INDEX idx_topic_snapshots_sources ON topic_snapshots USING GIN(sources);

-- Composite indexes for common queries
CREATE INDEX idx_topic_snapshots_country_time_count ON topic_snapshots(country_code, snapshot_time DESC, count DESC);
CREATE INDEX idx_topic_snapshots_topic_country_time ON topic_snapshots(topic_id, country_code, snapshot_time DESC);

-- Comments
COMMENT ON TABLE topic_snapshots IS 'Time-series data of topic appearances by country (partitioned by date)';
COMMENT ON COLUMN topic_snapshots.velocity_score IS 'Rate of change: how fast this topic is growing [0,1]';
COMMENT ON COLUMN topic_snapshots.stance_label IS 'Stance/position: pro, anti, neutral, mixed';


-- ============================================================================
-- 4. HOTSPOTS (Aggregated Time-Series)
-- ============================================================================

-- Hotspots (country-level intensity at specific times)
CREATE TABLE IF NOT EXISTS hotspots (
    hotspot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    country_code VARCHAR(2) NOT NULL REFERENCES countries(country_code) ON DELETE CASCADE,
    snapshot_time TIMESTAMP NOT NULL,

    -- Intensity calculation (matches flow_detector.py)
    intensity DECIMAL(3, 2) NOT NULL CHECK (intensity >= 0 AND intensity <= 1),
    volume_component DECIMAL(3, 2),  -- Contribution from volume
    velocity_component DECIMAL(3, 2),  -- Contribution from velocity
    confidence_component DECIMAL(3, 2),  -- Contribution from confidence

    -- Aggregated metrics
    topic_count INTEGER NOT NULL DEFAULT 0,  -- Total topics contributing
    total_article_count INTEGER DEFAULT 0,  -- Sum of all topic counts
    avg_confidence DECIMAL(3, 2),

    -- Top topics (denormalized for performance)
    top_topics JSONB,  -- [{"topic_id": "...", "label": "...", "count": 45}, ...]

    -- Metadata
    calculation_method VARCHAR(50) DEFAULT 'weighted_average',  -- For versioning
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(country_code, snapshot_time)
);

-- Indexes
CREATE INDEX idx_hotspots_country_time ON hotspots(country_code, snapshot_time DESC);
CREATE INDEX idx_hotspots_time ON hotspots(snapshot_time DESC);
CREATE INDEX idx_hotspots_intensity ON hotspots(intensity DESC);
CREATE INDEX idx_hotspots_top_topics ON hotspots USING GIN(top_topics);

-- Comments
COMMENT ON TABLE hotspots IS 'Pre-computed country-level intensity scores for visualization';
COMMENT ON COLUMN hotspots.intensity IS 'Weighted score: volume(0.4) + velocity(0.3) + confidence(0.3)';
COMMENT ON COLUMN hotspots.top_topics IS 'Denormalized top 5 topics for fast API responses';


-- ============================================================================
-- 5. FLOWS (Information Flow Relationships)
-- ============================================================================

-- Flows (detected information flows between countries)
CREATE TABLE IF NOT EXISTS flows (
    flow_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_country VARCHAR(2) NOT NULL REFERENCES countries(country_code) ON DELETE CASCADE,
    to_country VARCHAR(2) NOT NULL REFERENCES countries(country_code) ON DELETE CASCADE,

    -- Temporal data
    from_time TIMESTAMP NOT NULL,  -- When topic appeared in source country
    to_time TIMESTAMP NOT NULL,  -- When topic appeared in destination country
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),  -- When flow was calculated

    -- Heat calculation (matches ADR-0002)
    heat DECIMAL(3, 2) NOT NULL CHECK (heat >= 0 AND heat <= 1),
    similarity_score DECIMAL(3, 2) NOT NULL CHECK (similarity_score >= 0 AND similarity_score <= 1),
    time_delta_hours DECIMAL(8, 2) NOT NULL CHECK (time_delta_hours >= 0),
    time_decay_factor DECIMAL(4, 3),  -- exp(-Δt / halflife)

    -- Shared content
    shared_topics JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{"topic_id": "...", "label": "...", "similarity": 0.87}, ...]
    shared_keywords TEXT[],

    -- Flow metadata
    flow_direction_confidence VARCHAR(20) DEFAULT 'medium',  -- 'high', 'medium', 'low'
    halflife_used DECIMAL(4, 1) DEFAULT 6.0,  -- Halflife parameter used (hours)

    -- Constraints
    CHECK (from_country != to_country),  -- No self-loops
    CHECK (to_time >= from_time)  -- Destination must be after or simultaneous with source
);

-- Indexes
CREATE INDEX idx_flows_countries ON flows(from_country, to_country);
CREATE INDEX idx_flows_heat ON flows(heat DESC);
CREATE INDEX idx_flows_detected_at ON flows(detected_at DESC);
CREATE INDEX idx_flows_time_range ON flows(from_time, to_time);
CREATE INDEX idx_flows_shared_topics ON flows USING GIN(shared_topics);

-- Composite indexes for common queries
CREATE INDEX idx_flows_from_country_time ON flows(from_country, from_time DESC);
CREATE INDEX idx_flows_to_country_time ON flows(to_country, to_time DESC);

-- Comments
COMMENT ON TABLE flows IS 'Detected information flows between country pairs (heat = similarity × time_decay)';
COMMENT ON COLUMN flows.heat IS 'Combined score: similarity × exp(-Δt/6h) [0,1]';
COMMENT ON COLUMN flows.flow_direction_confidence IS 'Confidence that direction is correct (not just correlation)';


-- ============================================================================
-- 6. STANCE HISTORY (Narrative Evolution Tracking)
-- ============================================================================

-- Stance history (tracks how positions change over time)
CREATE TABLE IF NOT EXISTS stance_history (
    stance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic_id UUID NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    country_code VARCHAR(2) NOT NULL REFERENCES countries(country_code) ON DELETE CASCADE,
    snapshot_time TIMESTAMP NOT NULL,

    -- Stance/sentiment data
    stance_label VARCHAR(50) NOT NULL,  -- 'pro', 'anti', 'neutral', 'mixed', 'uncertain'
    sentiment_score DECIMAL(3, 2) CHECK (sentiment_score >= -1 AND sentiment_score <= 1),  -- [-1, 1]
    confidence DECIMAL(3, 2) CHECK (confidence >= 0 AND confidence <= 1),

    -- Change detection
    previous_stance VARCHAR(50),  -- For drift detection
    stance_changed BOOLEAN DEFAULT false,
    drift_magnitude DECIMAL(3, 2),  -- How much stance changed [0,1]

    -- Supporting evidence
    sample_quotes TEXT[],  -- Representative quotes showing stance
    sample_sources TEXT[],  -- URLs of supporting articles

    -- Context
    article_count INTEGER DEFAULT 0,  -- How many articles inform this stance
    sources JSONB DEFAULT '[]'::jsonb,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(topic_id, country_code, snapshot_time)
);

-- Indexes
CREATE INDEX idx_stance_topic_country_time ON stance_history(topic_id, country_code, snapshot_time DESC);
CREATE INDEX idx_stance_country_time ON stance_history(country_code, snapshot_time DESC);
CREATE INDEX idx_stance_label ON stance_history(stance_label);
CREATE INDEX idx_stance_changed ON stance_history(stance_changed) WHERE stance_changed = true;
CREATE INDEX idx_stance_drift ON stance_history(drift_magnitude DESC) WHERE drift_magnitude > 0.3;

-- Comments
COMMENT ON TABLE stance_history IS 'Tracks stance/sentiment evolution for narrative drift analysis';
COMMENT ON COLUMN stance_history.stance_label IS 'Position: pro, anti, neutral, mixed, uncertain';
COMMENT ON COLUMN stance_history.drift_magnitude IS 'Magnitude of stance change from previous [0,1]';


-- ============================================================================
-- 7. PARTITIONING STRATEGY (Topic Snapshots)
-- ============================================================================

-- Create partitions for topic_snapshots (weekly partitions for Iteration 2)
-- Automate this with a cron job or pg_partman extension

-- Current week partition (2025 Week 3)
CREATE TABLE IF NOT EXISTS topic_snapshots_2025_w03
    PARTITION OF topic_snapshots
    FOR VALUES FROM ('2025-01-13') TO ('2025-01-20');

-- Next 4 weeks (manual for now, automate in Iteration 3)
CREATE TABLE IF NOT EXISTS topic_snapshots_2025_w04
    PARTITION OF topic_snapshots
    FOR VALUES FROM ('2025-01-20') TO ('2025-01-27');

CREATE TABLE IF NOT EXISTS topic_snapshots_2025_w05
    PARTITION OF topic_snapshots
    FOR VALUES FROM ('2025-01-27') TO ('2025-02-03');

CREATE TABLE IF NOT EXISTS topic_snapshots_2025_w06
    PARTITION OF topic_snapshots
    FOR VALUES FROM ('2025-02-03') TO ('2025-02-10');

CREATE TABLE IF NOT EXISTS topic_snapshots_2025_w07
    PARTITION OF topic_snapshots
    FOR VALUES FROM ('2025-02-10') TO ('2025-02-17');

-- Default partition for out-of-range data
CREATE TABLE IF NOT EXISTS topic_snapshots_default
    PARTITION OF topic_snapshots DEFAULT;

COMMENT ON TABLE topic_snapshots_2025_w03 IS 'Partition for week 2025-W03 (Jan 13-19)';


-- ============================================================================
-- 8. MATERIALIZED VIEWS (For Performance)
-- ============================================================================

-- Recent hotspots (last 24 hours)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_recent_hotspots AS
SELECT
    h.*,
    c.country_name,
    c.region
FROM hotspots h
JOIN countries c ON h.country_code = c.country_code
WHERE h.snapshot_time >= NOW() - INTERVAL '24 hours'
ORDER BY h.intensity DESC;

CREATE UNIQUE INDEX idx_mv_recent_hotspots_id ON mv_recent_hotspots(hotspot_id);
CREATE INDEX idx_mv_recent_hotspots_intensity ON mv_recent_hotspots(intensity DESC);

COMMENT ON MATERIALIZED VIEW mv_recent_hotspots IS 'Cached recent hotspots (refresh every 15 min)';


-- Active flows (last 24 hours, heat >= 0.5)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_active_flows AS
SELECT
    f.*,
    cf.country_name AS from_country_name,
    ct.country_name AS to_country_name
FROM flows f
JOIN countries cf ON f.from_country = cf.country_code
JOIN countries ct ON f.to_country = ct.country_code
WHERE f.detected_at >= NOW() - INTERVAL '24 hours'
  AND f.heat >= 0.5
ORDER BY f.heat DESC;

CREATE UNIQUE INDEX idx_mv_active_flows_id ON mv_active_flows(flow_id);
CREATE INDEX idx_mv_active_flows_heat ON mv_active_flows(heat DESC);

COMMENT ON MATERIALIZED VIEW mv_active_flows IS 'Cached active flows above threshold (refresh every 15 min)';


-- ============================================================================
-- 9. FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function: Update topic last_seen_at when snapshot inserted
CREATE OR REPLACE FUNCTION update_topic_last_seen()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE topics
    SET
        last_seen_at = NEW.snapshot_time,
        total_appearance_count = total_appearance_count + 1,
        updated_at = NOW()
    WHERE topic_id = NEW.topic_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Fire on topic_snapshots insert
CREATE TRIGGER trigger_update_topic_last_seen
    AFTER INSERT ON topic_snapshots
    FOR EACH ROW
    EXECUTE FUNCTION update_topic_last_seen();

COMMENT ON FUNCTION update_topic_last_seen IS 'Automatically update topics table when snapshot inserted';


-- Function: Detect stance changes
CREATE OR REPLACE FUNCTION detect_stance_change()
RETURNS TRIGGER AS $$
DECLARE
    prev_stance VARCHAR(50);
BEGIN
    -- Get previous stance for this topic/country
    SELECT stance_label INTO prev_stance
    FROM stance_history
    WHERE topic_id = NEW.topic_id
      AND country_code = NEW.country_code
      AND snapshot_time < NEW.snapshot_time
    ORDER BY snapshot_time DESC
    LIMIT 1;

    -- Set previous_stance and calculate drift
    IF prev_stance IS NOT NULL THEN
        NEW.previous_stance := prev_stance;
        NEW.stance_changed := (NEW.stance_label != prev_stance);

        -- Calculate drift magnitude (simplified: 1 if complete reversal, 0 if no change)
        IF NEW.stance_label = 'pro' AND prev_stance = 'anti' THEN
            NEW.drift_magnitude := 1.0;
        ELSIF NEW.stance_label = 'anti' AND prev_stance = 'pro' THEN
            NEW.drift_magnitude := 1.0;
        ELSIF NEW.stance_label = 'neutral' AND prev_stance IN ('pro', 'anti') THEN
            NEW.drift_magnitude := 0.5;
        ELSIF NEW.stance_label IN ('pro', 'anti') AND prev_stance = 'neutral' THEN
            NEW.drift_magnitude := 0.5;
        ELSIF NEW.stance_changed THEN
            NEW.drift_magnitude := 0.3;
        ELSE
            NEW.drift_magnitude := 0.0;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Fire on stance_history insert
CREATE TRIGGER trigger_detect_stance_change
    BEFORE INSERT ON stance_history
    FOR EACH ROW
    EXECUTE FUNCTION detect_stance_change();

COMMENT ON FUNCTION detect_stance_change IS 'Automatically detect and quantify stance changes (narrative drift)';


-- ============================================================================
-- 10. SEED DATA (Initial Countries)
-- ============================================================================

-- Insert initial monitored countries (Iteration 2 target: 10 countries)
INSERT INTO countries (country_code, country_name, region, subregion, latitude, longitude, population, languages, timezone, is_active)
VALUES
    ('US', 'United States', 'Americas', 'Northern America', 37.0902, -95.7129, 331000000, '["en"]', 'America/New_York', true),
    ('CO', 'Colombia', 'Americas', 'South America', 4.5709, -74.2973, 51000000, '["es"]', 'America/Bogota', true),
    ('BR', 'Brazil', 'Americas', 'South America', -14.2350, -51.9253, 213000000, '["pt"]', 'America/Sao_Paulo', true),
    ('MX', 'Mexico', 'Americas', 'Central America', 23.6345, -102.5528, 129000000, '["es"]', 'America/Mexico_City', true),
    ('AR', 'Argentina', 'Americas', 'South America', -38.4161, -63.6167, 45000000, '["es"]', 'America/Argentina/Buenos_Aires', true),
    ('GB', 'United Kingdom', 'Europe', 'Northern Europe', 55.3781, -3.4360, 68000000, '["en"]', 'Europe/London', true),
    ('FR', 'France', 'Europe', 'Western Europe', 46.2276, 2.2137, 67000000, '["fr"]', 'Europe/Paris', true),
    ('DE', 'Germany', 'Europe', 'Western Europe', 51.1657, 10.4515, 83000000, '["de"]', 'Europe/Berlin', true),
    ('ES', 'Spain', 'Europe', 'Southern Europe', 40.4637, -3.7492, 47000000, '["es"]', 'Europe/Madrid', true),
    ('IT', 'Italy', 'Europe', 'Southern Europe', 41.8719, 12.5674, 60000000, '["it"]', 'Europe/Rome', true)
ON CONFLICT (country_code) DO NOTHING;

COMMENT ON TABLE countries IS 'Seeded with 10 initial countries for Iteration 2';


-- ============================================================================
-- 11. PERFORMANCE MONITORING QUERIES (Helper Views)
-- ============================================================================

-- View: Table sizes
CREATE OR REPLACE VIEW v_table_sizes AS
SELECT
    schemaname AS schema,
    tablename AS table_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS data_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

COMMENT ON VIEW v_table_sizes IS 'Helper view to monitor table and index sizes';


-- View: Row counts
CREATE OR REPLACE VIEW v_row_counts AS
SELECT
    'countries' AS table_name,
    (SELECT COUNT(*) FROM countries) AS row_count
UNION ALL
SELECT 'topics', (SELECT COUNT(*) FROM topics)
UNION ALL
SELECT 'topic_snapshots', (SELECT COUNT(*) FROM topic_snapshots)
UNION ALL
SELECT 'hotspots', (SELECT COUNT(*) FROM hotspots)
UNION ALL
SELECT 'flows', (SELECT COUNT(*) FROM flows)
UNION ALL
SELECT 'stance_history', (SELECT COUNT(*) FROM stance_history);

COMMENT ON VIEW v_row_counts IS 'Helper view to quickly check row counts';


-- ============================================================================
-- END OF MIGRATION
-- ============================================================================

-- Verify migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 002_comprehensive_flow_schema.sql completed successfully!';
    RAISE NOTICE 'Tables created: countries, topics, topic_snapshots, hotspots, flows, stance_history';
    RAISE NOTICE 'Materialized views: mv_recent_hotspots, mv_active_flows';
    RAISE NOTICE 'Triggers: update_topic_last_seen, detect_stance_change';
    RAISE NOTICE 'Next steps: Run backfill script, test API persistence, monitor performance';
END $$;
