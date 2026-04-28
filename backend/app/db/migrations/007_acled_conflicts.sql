-- ============================================================================
-- Observatory Global - ACLED Conflict Data Integration
-- Migration: 007_acled_conflicts.sql
-- Purpose: Store conflict events from the Armed Conflict Location & Event Data Project
-- ============================================================================

CREATE TABLE IF NOT EXISTS acled_conflicts_v2 (
    event_id_cnty VARCHAR(50) PRIMARY KEY, -- Unique alphanumeric ACLED ID
    event_date DATE NOT NULL,
    year INTEGER,
    
    -- Event Types
    event_type VARCHAR(100),
    sub_event_type VARCHAR(100),
    
    -- Actors
    actor1 VARCHAR(255),
    assoc_actor_1 VARCHAR(255),
    inter1 SMALLINT,
    actor2 VARCHAR(255),
    assoc_actor_2 VARCHAR(255),
    inter2 SMALLINT,
    interaction SMALLINT,
    
    -- Location
    region VARCHAR(100),
    country VARCHAR(100),
    admin1 VARCHAR(100),
    admin2 VARCHAR(100),
    admin3 VARCHAR(100),
    location VARCHAR(255),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(10, 6),
    geo_precision SMALLINT,
    
    -- Details
    source VARCHAR(255),
    source_scale VARCHAR(50),
    notes TEXT,
    fatalities INTEGER,
    
    -- System metadata
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_acled_date
    ON acled_conflicts_v2(event_date DESC);

CREATE INDEX idx_acled_country_date
    ON acled_conflicts_v2(country, event_date DESC);

CREATE INDEX idx_acled_type_date
    ON acled_conflicts_v2(event_type, event_date DESC);

COMMENT ON TABLE acled_conflicts_v2 IS 'ACLED Armed Conflict Location & Event Data';

DO $$
BEGIN
    RAISE NOTICE 'Migration 007_acled_conflicts.sql completed successfully!';
END $$;
