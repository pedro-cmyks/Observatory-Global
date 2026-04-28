-- ============================================================================
-- Observatory Global - GDELT Events Integration
-- Migration: 006_gdelt_events.sql
-- Purpose: Store structured geopolitical events (CAMEO format) from GDELT
-- ============================================================================

CREATE TABLE IF NOT EXISTS events_v2 (
    global_event_id BIGINT PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Actor 1 (Source)
    actor1_code VARCHAR(50),
    actor1_name VARCHAR(255),
    actor1_country_code VARCHAR(3),
    
    -- Actor 2 (Target)
    actor2_code VARCHAR(50),
    actor2_name VARCHAR(255),
    actor2_country_code VARCHAR(3),
    
    -- Event Action
    is_root_event BOOLEAN,
    event_code VARCHAR(10) NOT NULL,        -- CAMEO Event Code
    event_root_code VARCHAR(10),            -- CAMEO Root Code
    quad_class SMALLINT,                    -- 1=Verbal Coop, 2=Material Coop, 3=Verbal Conflict, 4=Material Conflict
    goldstein_scale DECIMAL(5,2),           -- Theoretical impact (-10 to +10)
    
    -- Location (Action Geo)
    action_country_code VARCHAR(2),         -- ISO-2
    action_location_name VARCHAR(255),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(10, 6),
    
    -- Metadata
    num_mentions INTEGER,
    num_sources INTEGER,
    num_articles INTEGER,
    avg_tone DECIMAL(5,2),
    source_url TEXT,
    
    -- Processed Fields
    theme_inferred VARCHAR(100),            -- Best-effort mapping to our Themes
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_events_v2_ts
    ON events_v2(timestamp DESC);

CREATE INDEX idx_events_v2_action_country_ts
    ON events_v2(action_country_code, timestamp DESC);

CREATE INDEX idx_events_v2_actor1_ts
    ON events_v2(actor1_country_code, timestamp DESC);

CREATE INDEX idx_events_v2_actor2_ts
    ON events_v2(actor2_country_code, timestamp DESC);

CREATE INDEX idx_events_v2_quad_ts
    ON events_v2(quad_class, timestamp DESC);

COMMENT ON TABLE events_v2 IS 'GDELT Events table (structured geopolitical actions based on CAMEO coding)';

DO $$
BEGIN
    RAISE NOTICE 'Migration 006_gdelt_events.sql completed successfully!';
END $$;
