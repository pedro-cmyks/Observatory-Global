# PostgreSQL Database Schema Design
## Flow Analysis, Narrative Evolution, and Stance Tracking

**Date**: 2025-01-13
**Status**: Design Document - Ready for Implementation
**Target**: Iteration 2 - Minimum Viable Schema
**Related**: ADR-0002 (Heat Formula), 001_create_trends_archive.sql

---

## Table of Contents
1. [Core Entities](#1-core-entities)
2. [Complete SQL Schema](#2-complete-sql-schema)
3. [ER Diagram](#3-er-diagram)
4. [Retention Policy](#4-retention-policy)
5. [Query Examples](#5-query-examples)
6. [Storage Requirements](#6-storage-requirements)
7. [Migration Plan](#7-migration-plan)
8. [Performance Optimization](#8-performance-optimization)

---

## 1. Core Entities

### Entity Overview

```
┌─────────────┐
│  Countries  │ (reference/static)
└─────────────┘
       │
       ├─────────────────────┐
       │                     │
┌──────▼───────┐      ┌─────▼──────┐
│   Topics     │      │  Hotspots  │ (time-series)
└──────┬───────┘      └────────────┘
       │
       │
┌──────▼────────────┐
│ Topic_Snapshots   │ (time-series, most granular)
└──────┬────────────┘
       │
       │
┌──────▼────────┐
│    Flows      │ (time-series, relationships)
└───────────────┘
       │
       │
┌──────▼──────────┐
│ Stance_History  │ (time-series, narrative evolution)
└─────────────────┘
```

### Entity Descriptions

1. **Countries** (Static Reference)
   - ISO country codes, metadata, coordinates
   - ~250 rows, rarely changes

2. **Topics** (Master Table)
   - Unique topics across all time and countries
   - Normalized labels with aliases/synonyms
   - ~10K-100K rows (grows slowly)

3. **Topic_Snapshots** (Time-Series Core)
   - Most granular: (topic, country, timestamp)
   - Sample headlines, counts, confidence scores
   - Partitioned by date for performance
   - ~5K-50K rows/day depending on countries monitored

4. **Hotspots** (Aggregated Time-Series)
   - Country-level intensity at given timestamp
   - Pre-computed for faster visualization
   - ~100-500 rows/day (fewer countries have high intensity)

5. **Flows** (Relationships Time-Series)
   - Detected information flows between country pairs
   - Heat score, similarity, time delta
   - ~50-500 rows/day (depends on threshold)

6. **Stance_History** (Narrative Evolution)
   - Tracks sentiment/stance changes over time
   - Enables "narrative drift" detection
   - ~1K-10K rows/day (tracks subset of important topics)

---

## 2. Complete SQL Schema

### Migration File: `002_comprehensive_flow_schema.sql`

```sql
-- ============================================================================
-- Observatory Global - Comprehensive Flow Analysis Schema
-- Migration: 002_comprehensive_flow_schema.sql
-- Purpose: Support flow analysis, narrative evolution, and stance tracking
-- Author: Database Design Agent
-- Date: 2025-01-13
-- ============================================================================

-- Enable UUID extension for better distributed IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable PostGIS for future geo-queries (optional but recommended)
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

-- Indexes (will be created on each partition)
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

-- Current week partition
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
-- 10. GRANTS (Least Privilege)
-- ============================================================================

-- Application user (read-write on most tables)
-- CREATE USER observatory_app WITH PASSWORD 'CHANGE_ME';

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO observatory_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO observatory_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO observatory_app;

-- Read-only user (for analytics/BI tools)
-- CREATE USER observatory_readonly WITH PASSWORD 'CHANGE_ME';

GRANT SELECT ON ALL TABLES IN SCHEMA public TO observatory_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO observatory_readonly;


-- ============================================================================
-- 11. INDEXES FOR FULL-TEXT SEARCH (Optional)
-- ============================================================================

-- Add full-text search capabilities (future enhancement)
-- ALTER TABLE topics ADD COLUMN searchable_text tsvector;
-- CREATE INDEX idx_topics_fulltext ON topics USING GIN(searchable_text);


-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
```

---

## 3. ER Diagram

### Text-Based Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         STATIC REFERENCE LAYER                          │
└─────────────────────────────────────────────────────────────────────────┘

    ┌────────────────────┐
    │     COUNTRIES      │
    ├────────────────────┤
    │ PK country_code    │
    │    country_name    │
    │    region          │
    │    latitude        │
    │    longitude       │
    │    population      │
    │    is_active       │
    └─────────┬──────────┘
              │
              │ (1)
              │
┌─────────────┴─────────────────────────────────────────────────────────┐
│                                                                         │
│                                                                         │
┌─────────────────────────────────────────────────────────────────────────┐
│                        TOPIC MASTER LAYER                               │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────┐
    │       TOPICS        │
    ├─────────────────────┤
    │ PK topic_id (UUID)  │
    │    normalized_label │
    │    aliases[]        │
    │    category         │
    │    keywords[]       │
    │    first_seen_at    │
    │    last_seen_at     │
    └──────────┬──────────┘
               │
               │ (1)
               │
┌──────────────┴────────────────────────────────────────────────────────┐
│                                                                         │
│                                                                         │
┌─────────────────────────────────────────────────────────────────────────┐
│                      TIME-SERIES DATA LAYER                             │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────┐
    │   TOPIC_SNAPSHOTS        │ ◄────── PARTITIONED by snapshot_time
    ├──────────────────────────┤
    │ PK snapshot_id (UUID)    │
    │ FK topic_id              │
    │ FK country_code          │
    │    snapshot_time    ◄────┐
    │    count                 │
    │    volume_score          │
    │    velocity_score        │
    │    confidence            │
    │    sources (JSONB)       │
    │    sample_titles[]       │
    │    avg_sentiment         │
    │    stance_label          │
    └──────────┬───────────────┘
               │
               │ (1)
               │
               │ Aggregates into ───────┐
               │                        │
               │                        │
    ┌──────────▼──────────┐   ┌────────▼────────┐
    │     HOTSPOTS        │   │   FLOWS         │
    ├─────────────────────┤   ├─────────────────┤
    │ PK hotspot_id       │   │ PK flow_id      │
    │ FK country_code     │   │ FK from_country │
    │    snapshot_time    │   │ FK to_country   │
    │    intensity        │   │    from_time    │
    │    topic_count      │   │    to_time      │
    │    top_topics       │   │    heat         │
    │    (JSONB)          │   │    similarity   │
    └─────────────────────┘   │    time_delta   │
                              │    shared_topics│
                              │    (JSONB)      │
                              └─────────────────┘

               │
               │ Feeds into
               │
    ┌──────────▼──────────────┐
    │   STANCE_HISTORY        │
    ├─────────────────────────┤
    │ PK stance_id            │
    │ FK topic_id             │
    │ FK country_code         │
    │    snapshot_time        │
    │    stance_label         │
    │    sentiment_score      │
    │    previous_stance      │
    │    stance_changed       │
    │    drift_magnitude      │
    │    sample_quotes[]      │
    └─────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE CACHING LAYER                            │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐      ┌──────────────────────┐
    │ MV_RECENT_HOTSPOTS      │      │ MV_ACTIVE_FLOWS      │
    │ (Materialized View)     │      │ (Materialized View)  │
    │ Refresh every 15 min    │      │ Refresh every 15 min │
    └─────────────────────────┘      └──────────────────────┘
```

### Cardinality Summary

| Relationship | Type | Cardinality |
|-------------|------|-------------|
| Countries → Topic_Snapshots | 1:N | One country has many snapshots |
| Topics → Topic_Snapshots | 1:N | One topic appears in many snapshots |
| Topic_Snapshots → Hotspots | N:1 | Many snapshots aggregate to one hotspot |
| Topic_Snapshots → Flows | N:M | Snapshots from two countries create a flow |
| Topics → Stance_History | 1:N | One topic has multiple stance records |
| Countries → Stance_History | 1:N | One country has many stance records |

---

## 4. Retention Policy

### Retention Strategy: Hybrid (Hot/Warm/Cold)

#### Tier 1: Hot Storage (PostgreSQL)
**Duration**: Last 30 days
**Performance**: Optimized indexes, recent partitions
**Use Case**: Real-time queries, API responses

- **topic_snapshots**: Full granularity (every 15 min)
- **hotspots**: All records
- **flows**: All detected flows (heat >= 0.5)
- **stance_history**: All records

**Storage**: ~10-50 GB/month (depends on countries monitored)

#### Tier 2: Warm Storage (PostgreSQL Archived)
**Duration**: 30-90 days
**Performance**: Older partitions, less frequent access
**Use Case**: Historical analysis, trend reports

- **topic_snapshots**: Aggregated to hourly (reduce by 4x)
- **hotspots**: Keep as-is (already aggregated)
- **flows**: Keep high-heat flows only (heat >= 0.7)
- **stance_history**: Keep stance changes only

**Aggregation Query** (run nightly):
```sql
-- Aggregate 15-min snapshots to hourly (for data 30-90 days old)
INSERT INTO topic_snapshots (topic_id, country_code, snapshot_time, count, ...)
SELECT
    topic_id,
    country_code,
    DATE_TRUNC('hour', snapshot_time) AS snapshot_time,
    SUM(count) AS count,
    AVG(volume_score) AS volume_score,
    AVG(velocity_score) AS velocity_score,
    AVG(confidence) AS confidence,
    JSONB_AGG(DISTINCT sources) AS sources,
    ARRAY_AGG(DISTINCT unnest(sample_titles)) AS sample_titles,
    AVG(avg_sentiment) AS avg_sentiment,
    MODE() WITHIN GROUP (ORDER BY stance_label) AS stance_label
FROM topic_snapshots
WHERE snapshot_time BETWEEN NOW() - INTERVAL '90 days' AND NOW() - INTERVAL '30 days'
GROUP BY topic_id, country_code, DATE_TRUNC('hour', snapshot_time);

-- Then delete original 15-min snapshots
DELETE FROM topic_snapshots
WHERE snapshot_time BETWEEN NOW() - INTERVAL '90 days' AND NOW() - INTERVAL '30 days'
  AND snapshot_time != DATE_TRUNC('hour', snapshot_time);
```

**Storage**: ~5-15 GB (4x reduction from aggregation)

#### Tier 3: Cold Storage (S3 or Archive)
**Duration**: 90+ days
**Performance**: Slow, bulk exports only
**Use Case**: Research, compliance, long-term trends

- **topic_snapshots**: Aggregated to daily
- **hotspots**: Weekly averages
- **flows**: Monthly summaries (top 100 flows/month)
- **stance_history**: Major drift events only (drift_magnitude > 0.5)

**Export Format**: Parquet files on S3, partitioned by month

**Export Query** (run monthly):
```bash
# PostgreSQL to Parquet via pg_dump + pandas
COPY (
    SELECT * FROM topic_snapshots
    WHERE snapshot_time BETWEEN '2024-12-01' AND '2024-12-31'
) TO STDOUT WITH (FORMAT csv, HEADER) | \
python export_to_parquet.py --output s3://observatory-archive/snapshots/2024-12/
```

**Storage**: S3 Standard-IA or Glacier (~$1-5/month)

#### Tier 4: Forever Delete
**Duration**: After 1 year
**Rationale**:

- GDPR/compliance: Most jurisdictions allow 1-year retention for analytics
- Diminishing value: >1 year old micro-trends lose relevance
- Cost: Storage costs grow linearly

**What to keep forever**:
- Aggregated monthly summaries (for historical comparison)
- Major events (user-flagged or high-impact flows)
- Topics master table (never delete, only archive old topics)

### Summary Table

| Data Type | Hot (0-30d) | Warm (30-90d) | Cold (90d-1y) | Delete |
|-----------|-------------|---------------|---------------|--------|
| **topic_snapshots** | 15-min | Hourly | Daily | Yes |
| **hotspots** | All | All | Weekly | Yes |
| **flows** | heat>=0.5 | heat>=0.7 | Top 100/mo | Yes |
| **stance_history** | All | Changes only | drift>0.5 | Yes |
| **topics** | All | All | All | Never |
| **countries** | All | All | All | Never |

### Automation Plan

```sql
-- Create cron job (via pg_cron extension)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Daily: Aggregate old snapshots (runs at 2 AM UTC)
SELECT cron.schedule(
    'aggregate-old-snapshots',
    '0 2 * * *',
    $$
    -- Aggregate 15-min to hourly (30-90 days old)
    SELECT aggregate_old_snapshots();
    $$
);

-- Weekly: Export to cold storage (runs Sunday 3 AM UTC)
SELECT cron.schedule(
    'export-to-cold-storage',
    '0 3 * * 0',
    $$
    -- Export data >90 days old
    SELECT export_to_cold_storage();
    $$
);

-- Monthly: Purge old data (runs 1st of month, 4 AM UTC)
SELECT cron.schedule(
    'purge-old-data',
    '0 4 1 * *',
    $$
    -- Delete data >1 year old
    DELETE FROM topic_snapshots WHERE snapshot_time < NOW() - INTERVAL '1 year';
    DELETE FROM hotspots WHERE snapshot_time < NOW() - INTERVAL '1 year';
    DELETE FROM flows WHERE detected_at < NOW() - INTERVAL '1 year';
    DELETE FROM stance_history WHERE snapshot_time < NOW() - INTERVAL '1 year';
    $$
);
```

### Rationale

**Why 30-day hot tier?**
- Matches typical news cycle (most users care about last month)
- Keeps queries fast (<500ms) without over-indexing
- Reasonable storage cost (~$50-100/month for 10-50GB on managed PostgreSQL)

**Why not keep everything forever?**
- Cost: Storage + IOPS costs scale linearly with data volume
- Performance: Queries slow down with billions of rows
- Value: 6-month-old micro-trends rarely queried
- Compliance: GDPR permits reasonable retention windows

**Why aggregate instead of delete?**
- Preserves long-term trends for historical comparison
- Reduces storage by 4-10x while keeping insights
- Allows "zoom out" queries (daily/weekly/monthly trends)

---

## 5. Query Examples

### Query 1: Get All Topics for Country at Time T

```sql
-- Get topics for US at 2025-01-13 10:00:00
SELECT
    t.normalized_label,
    ts.count,
    ts.velocity_score,
    ts.confidence,
    ts.sample_titles,
    ts.stance_label
FROM topic_snapshots ts
JOIN topics t ON ts.topic_id = t.topic_id
WHERE ts.country_code = 'US'
  AND ts.snapshot_time = '2025-01-13 10:00:00'
ORDER BY ts.count DESC
LIMIT 50;
```

**Indexes Used**: `idx_topic_snapshots_country`, `idx_topic_snapshots_time`
**Expected Performance**: <50ms (partition pruning + indexed scan)

### Query 2: Track Topic X Across Countries Over Time

```sql
-- Track "election fraud" across countries (last 7 days)
SELECT
    ts.country_code,
    c.country_name,
    ts.snapshot_time,
    ts.count,
    ts.velocity_score,
    ts.stance_label,
    ts.avg_sentiment
FROM topic_snapshots ts
JOIN topics t ON ts.topic_id = t.topic_id
JOIN countries c ON ts.country_code = c.country_code
WHERE t.normalized_label = 'election fraud'
  AND ts.snapshot_time >= NOW() - INTERVAL '7 days'
ORDER BY ts.snapshot_time DESC, ts.count DESC;
```

**Indexes Used**: `idx_topics_label`, `idx_topic_snapshots_topic_country_time`
**Expected Performance**: <200ms (indexed lookup + time range scan)

### Query 3: Calculate Flow Intensity Between Countries

```sql
-- Get flows from US in last 24 hours
SELECT
    f.to_country,
    ct.country_name AS destination,
    f.heat,
    f.similarity_score,
    f.time_delta_hours,
    f.shared_topics->0->>'label' AS top_shared_topic,
    f.from_time,
    f.to_time
FROM flows f
JOIN countries ct ON f.to_country = ct.country_code
WHERE f.from_country = 'US'
  AND f.detected_at >= NOW() - INTERVAL '24 hours'
  AND f.heat >= 0.5
ORDER BY f.heat DESC
LIMIT 20;
```

**Indexes Used**: `idx_flows_from_country_time`, `idx_flows_heat`
**Expected Performance**: <100ms (materialized view cached)

### Query 4: Detect Narrative Drift (Stance Changes)

```sql
-- Find topics where stance changed significantly (last 30 days)
SELECT
    t.normalized_label,
    sh.country_code,
    c.country_name,
    sh.previous_stance,
    sh.stance_label AS current_stance,
    sh.drift_magnitude,
    sh.snapshot_time,
    sh.sample_quotes[1] AS example_quote
FROM stance_history sh
JOIN topics t ON sh.topic_id = t.topic_id
JOIN countries c ON sh.country_code = c.country_code
WHERE sh.stance_changed = true
  AND sh.drift_magnitude >= 0.5
  AND sh.snapshot_time >= NOW() - INTERVAL '30 days'
ORDER BY sh.drift_magnitude DESC, sh.snapshot_time DESC
LIMIT 50;
```

**Indexes Used**: `idx_stance_changed`, `idx_stance_drift`
**Expected Performance**: <150ms (indexed on stance_changed and drift_magnitude)

### Query 5: Time-Series for Visualization (Hotspots Over Time)

```sql
-- Get intensity time-series for visualization (last 7 days, hourly)
SELECT
    h.snapshot_time,
    h.country_code,
    c.country_name,
    h.intensity,
    h.topic_count,
    h.top_topics->0->>'label' AS top_topic
FROM hotspots h
JOIN countries c ON h.country_code = c.country_code
WHERE h.snapshot_time >= NOW() - INTERVAL '7 days'
  AND h.intensity >= 0.3
ORDER BY h.snapshot_time ASC, h.intensity DESC;
```

**Indexes Used**: `idx_hotspots_time`, `idx_hotspots_intensity`
**Expected Performance**: <200ms (time range scan + filtering)

### Query 6: Aggregate Weekly Trend (Data Pipeline Health)

```sql
-- Weekly summary: topics per country, average intensity
SELECT
    DATE_TRUNC('week', snapshot_time) AS week,
    country_code,
    COUNT(DISTINCT topic_id) AS unique_topics,
    AVG(count) AS avg_topic_count,
    MAX(count) AS peak_topic_count
FROM topic_snapshots
WHERE snapshot_time >= NOW() - INTERVAL '90 days'
GROUP BY DATE_TRUNC('week', snapshot_time), country_code
ORDER BY week DESC, unique_topics DESC;
```

**Indexes Used**: `idx_topic_snapshots_country_time`, partial partition scan
**Expected Performance**: <1s (aggregating 90 days of data)

### Query 7: Find Similar Topics (Semantic Search)

```sql
-- Find topics similar to "climate change" using keyword overlap
SELECT
    t.normalized_label,
    t.category,
    t.aliases,
    t.total_appearance_count,
    t.last_seen_at
FROM topics t
WHERE t.keywords && ARRAY['climate', 'warming', 'environment']  -- Array overlap
   OR t.normalized_label ILIKE '%climate%'
ORDER BY t.total_appearance_count DESC
LIMIT 20;
```

**Indexes Used**: `idx_topics_keywords` (GIN index on array)
**Expected Performance**: <50ms (GIN index for fast array search)

### Query 8: Top Flows By Region (Geo-Aggregation)

```sql
-- Top flows by region (last 24 hours)
SELECT
    cf.region AS source_region,
    ct.region AS destination_region,
    COUNT(*) AS flow_count,
    AVG(f.heat) AS avg_heat,
    MAX(f.heat) AS max_heat,
    JSONB_AGG(
        JSONB_BUILD_OBJECT(
            'from', f.from_country,
            'to', f.to_country,
            'heat', f.heat
        ) ORDER BY f.heat DESC
    ) AS top_flows
FROM flows f
JOIN countries cf ON f.from_country = cf.country_code
JOIN countries ct ON f.to_country = ct.country_code
WHERE f.detected_at >= NOW() - INTERVAL '24 hours'
  AND f.heat >= 0.6
GROUP BY cf.region, ct.region
HAVING COUNT(*) >= 3
ORDER BY avg_heat DESC;
```

**Indexes Used**: `idx_flows_detected_at`, `idx_flows_heat`, `idx_countries_region`
**Expected Performance**: <300ms (aggregation on filtered set)

---

## 6. Storage Requirements

### Assumptions

- **Countries Monitored**: 10 (Iteration 2) → 50 (Iteration 3)
- **Snapshots**: Every 15 minutes = 96/day
- **Topics per Country**: ~30-50 per snapshot
- **Flow Threshold**: heat >= 0.5 (filters ~70% of potential flows)

### Per-Table Estimates

#### Topic_Snapshots (Most Voluminous)

**Per Row**:
- UUIDs (32 bytes × 2) = 64 bytes
- Integers (4 bytes × 4) = 16 bytes
- Decimals (8 bytes × 6) = 48 bytes
- Timestamps (8 bytes × 2) = 16 bytes
- Text arrays (~200 bytes avg) = 200 bytes
- JSONB sources (~50 bytes) = 50 bytes
- **Total per row**: ~400 bytes

**Per Day**:
- 10 countries × 96 snapshots × 40 topics = **38,400 rows/day**
- 38,400 rows × 400 bytes = **15.4 MB/day** (uncompressed)
- With PostgreSQL compression (~50%): **~8 MB/day**

**Per Month**: 8 MB × 30 = **240 MB/month**

**Per Year**: 240 MB × 12 = **2.9 GB/year** (hot + warm)

**At 50 Countries** (Iteration 3): 2.9 GB × 5 = **14.5 GB/year**

#### Hotspots

**Per Row**: ~300 bytes (smaller, aggregated)

**Per Day**: 10 countries × 96 snapshots = **960 rows/day** = 288 KB/day

**Per Month**: 288 KB × 30 = **8.6 MB/month**

**Per Year**: 103 MB/year → **515 MB/year** (50 countries)

#### Flows

**Per Row**: ~500 bytes (includes JSONB shared_topics)

**Per Day**:
- Country pairs: C(10, 2) = 45 pairs
- Snapshots: 96/day
- Filters: ~70% filtered by threshold
- 45 pairs × 96 × 0.3 = **1,296 rows/day**
- 1,296 × 500 bytes = **648 KB/day**

**Per Month**: 648 KB × 30 = **19.4 MB/month**

**Per Year**: 233 MB/year → **5.8 GB/year** (50 countries, C(50,2) = 1225 pairs)

#### Stance_History

**Per Row**: ~350 bytes

**Per Day**: 10 countries × 20 tracked topics × 96 snapshots × 0.1 (sampled) = **1,920 rows/day** = 672 KB/day

**Per Month**: 672 KB × 30 = **20 MB/month**

**Per Year**: 240 MB/year → **1.2 GB/year** (50 countries)

#### Topics (Master Table)

**Per Row**: ~500 bytes (includes aliases, keywords)

**Total**: ~10,000-100,000 unique topics over lifetime = **5-50 MB total** (static after initial growth)

#### Countries (Reference Table)

**Total**: ~250 countries × 300 bytes = **75 KB** (static)

### Total Storage Summary (10 Countries, Hot Tier Only)

| Table | Per Day | Per Month | Per Year |
|-------|---------|-----------|----------|
| **topic_snapshots** | 8 MB | 240 MB | 2.9 GB |
| **hotspots** | 288 KB | 8.6 MB | 103 MB |
| **flows** | 648 KB | 19.4 MB | 233 MB |
| **stance_history** | 672 KB | 20 MB | 240 MB |
| **topics** | - | - | 50 MB |
| **countries** | - | - | 75 KB |
| **Indexes** (50% overhead) | 4.7 MB | 144 MB | 1.8 GB |
| **Total** | **14 MB/day** | **430 MB/month** | **5.3 GB/year** |

**With Warm Tier** (30-90 days, hourly aggregation): +1.5 GB

**Total Year 1** (Hot + Warm): **~6.8 GB**

### Scaling to 50 Countries

| Tier | 10 Countries | 50 Countries |
|------|--------------|--------------|
| **Hot (30 days)** | 430 MB | 2.2 GB |
| **Warm (60 days)** | 500 MB | 2.5 GB |
| **Cold (275 days)** | 1.2 GB | 6 GB |
| **Total Year 1** | **2.1 GB** | **10.7 GB** |
| **Annual Growth** | +5.3 GB/year | +27 GB/year |

### Cost Estimates (AWS RDS PostgreSQL)

| Instance | Storage | IOPS | Cost/Month |
|----------|---------|------|------------|
| **db.t3.medium** (2 vCPU, 4 GB RAM) | 20 GB | 3000 | ~$60 |
| **db.t3.large** (2 vCPU, 8 GB RAM) | 50 GB | 3000 | ~$110 |
| **db.m5.large** (2 vCPU, 8 GB RAM) | 50 GB | 12000 | ~$180 |

**Recommendation for Iteration 2**: db.t3.medium with 20 GB storage (~$60/month)

---

## 7. Migration Plan

### Phase 1: Initial Setup (Week 1)

**Goal**: Enable basic persistence without disrupting current in-memory system

#### Step 1.1: Enable PostgreSQL in Docker

```bash
# Uncomment PostgreSQL service in docker-compose.yml
cd infra
nano docker-compose.yml  # Uncomment lines 20-35

# Create .env file with database credentials
cat >> .env << EOF
POSTGRES_DB=observatory
POSTGRES_USER=observatory
POSTGRES_PASSWORD=$(openssl rand -base64 32)
EOF

# Start database
docker compose up -d postgres

# Verify health
docker compose exec postgres pg_isready -U observatory
```

#### Step 1.2: Run Migrations

```bash
# Create migration runner (Python script)
# backend/app/db/migrate.py

cat > backend/app/db/migrate.py << 'EOF'
"""Database migration runner."""
import os
import psycopg2
from pathlib import Path

def run_migrations():
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        database=os.getenv('POSTGRES_DB', 'observatory'),
        user=os.getenv('POSTGRES_USER', 'observatory'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

    migrations_dir = Path(__file__).parent / 'migrations'
    migration_files = sorted(migrations_dir.glob('*.sql'))

    for migration_file in migration_files:
        print(f"Running migration: {migration_file.name}")
        with open(migration_file) as f:
            sql = f.read()
            with conn.cursor() as cur:
                cur.execute(sql)
        conn.commit()
        print(f"✓ {migration_file.name} completed")

    conn.close()
    print("All migrations completed successfully!")

if __name__ == '__main__':
    run_migrations()
EOF

# Run migrations
python backend/app/db/migrate.py
```

#### Step 1.3: Create Database Connection Pool

```python
# backend/app/db/connection.py

from psycopg2.pool import SimpleConnectionPool
from app.core.config import settings

# Connection pool (reuse connections)
db_pool = SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    host=settings.POSTGRES_HOST,
    port=settings.POSTGRES_PORT,
    database=settings.POSTGRES_DB,
    user=settings.POSTGRES_USER,
    password=settings.POSTGRES_PASSWORD
)

def get_db_connection():
    """Get a connection from the pool."""
    return db_pool.getconn()

def release_db_connection(conn):
    """Release connection back to pool."""
    db_pool.putconn(conn)
```

### Phase 2: Backfill Historical Data (Week 2)

**Goal**: Populate database with current in-memory data (if any exists in Redis)

#### Step 2.1: Export Current Trends from Redis

```python
# backend/app/scripts/backfill_from_redis.py

import redis
import json
from datetime import datetime
from app.db.connection import get_db_connection, release_db_connection

def backfill_trends():
    """Export trends from Redis to PostgreSQL."""
    r = redis.Redis(host='redis', port=6379, db=0)
    conn = get_db_connection()
    cur = conn.cursor()

    # Get all trend keys
    trend_keys = r.keys('trends:*')

    for key in trend_keys:
        # Parse key: "trends:US:2025-01-13T10:00:00"
        _, country, timestamp = key.decode().split(':')
        data = json.loads(r.get(key))

        # Insert topics into topic_snapshots
        for topic in data['topics']:
            # First, upsert into topics table
            cur.execute("""
                INSERT INTO topics (normalized_label, first_seen_at, last_seen_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (normalized_label) DO UPDATE
                SET last_seen_at = EXCLUDED.last_seen_at
                RETURNING topic_id
            """, (topic['label'], timestamp, timestamp))

            topic_id = cur.fetchone()[0]

            # Insert snapshot
            cur.execute("""
                INSERT INTO topic_snapshots
                (topic_id, country_code, snapshot_time, count, confidence, sources, sample_titles)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                topic_id,
                country,
                timestamp,
                topic['count'],
                topic['confidence'],
                json.dumps(topic['sources']),
                topic['sample_titles']
            ))

    conn.commit()
    cur.close()
    release_db_connection(conn)
    print(f"Backfilled {len(trend_keys)} snapshots from Redis")

if __name__ == '__main__':
    backfill_trends()
```

### Phase 3: Incremental Updates (Week 3)

**Goal**: Write new data to both Redis (for speed) and PostgreSQL (for persistence)

#### Step 3.1: Modify Trends API to Write to DB

```python
# backend/app/api/v1/trends.py (add persistence)

from app.db.connection import get_db_connection, release_db_connection

@router.get("/{country}", response_model=TrendsResponse)
async def get_trends(country: str = Path(..., regex="^[A-Z]{2}$")):
    # ... existing code to fetch trends ...

    # NEW: Persist to database (async background task)
    background_tasks.add_task(persist_trends_to_db, country, trends_response)

    return trends_response

def persist_trends_to_db(country: str, data: TrendsResponse):
    """Background task: persist trends to PostgreSQL."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        for topic in data.topics:
            # Upsert topic
            cur.execute("""
                INSERT INTO topics (normalized_label, first_seen_at, last_seen_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (normalized_label) DO UPDATE
                SET last_seen_at = EXCLUDED.last_seen_at,
                    total_appearance_count = topics.total_appearance_count + 1
                RETURNING topic_id
            """, (topic.label, data.generated_at, data.generated_at))

            topic_id = cur.fetchone()[0]

            # Insert snapshot
            cur.execute("""
                INSERT INTO topic_snapshots
                (topic_id, country_code, snapshot_time, count, confidence, sources, sample_titles)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                topic_id,
                country,
                data.generated_at,
                topic.count,
                topic.confidence,
                json.dumps(topic.sources),
                topic.sample_titles
            ))

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to persist trends: {e}")
    finally:
        cur.close()
        release_db_connection(conn)
```

#### Step 3.2: Modify Flows API to Write to DB

```python
# backend/app/api/v1/flows.py (add persistence)

@router.get("", response_model=FlowsResponse)
async def get_flows(...):
    # ... existing flow detection ...

    # NEW: Persist flows and hotspots
    background_tasks.add_task(persist_flows_to_db, hotspots, flows)

    return response

def persist_flows_to_db(hotspots: List[Hotspot], flows: List[Flow]):
    """Persist computed flows to database."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Insert hotspots
        for hotspot in hotspots:
            cur.execute("""
                INSERT INTO hotspots
                (country_code, snapshot_time, intensity, topic_count, top_topics)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (country_code, snapshot_time) DO UPDATE
                SET intensity = EXCLUDED.intensity,
                    topic_count = EXCLUDED.topic_count,
                    top_topics = EXCLUDED.top_topics
            """, (
                hotspot.country,
                datetime.now(),
                hotspot.intensity,
                hotspot.topic_count,
                json.dumps([t.dict() for t in hotspot.top_topics])
            ))

        # Insert flows
        for flow in flows:
            cur.execute("""
                INSERT INTO flows
                (from_country, to_country, from_time, to_time, heat,
                 similarity_score, time_delta_hours, shared_topics)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                flow.from_country,
                flow.to_country,
                datetime.now(),  # Simplified: use current time
                datetime.now() + timedelta(hours=flow.time_delta_hours),
                flow.heat,
                flow.similarity_score,
                flow.time_delta_hours,
                json.dumps(flow.shared_topics)
            ))

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to persist flows: {e}")
    finally:
        cur.close()
        release_db_connection(conn)
```

### Phase 4: Read from Database (Week 4)

**Goal**: Switch API queries to read from PostgreSQL (with Redis caching)

#### Step 4.1: Implement Read-Through Cache Pattern

```python
# backend/app/services/trends_repository.py

from datetime import datetime, timedelta
from typing import List, Optional
import redis
import json
from app.db.connection import get_db_connection, release_db_connection

class TrendsRepository:
    """Repository for trends data (PostgreSQL + Redis cache)."""

    def __init__(self):
        self.redis = redis.Redis(host='redis', port=6379, db=0)
        self.cache_ttl = 900  # 15 minutes

    def get_trends(self, country: str, timestamp: Optional[datetime] = None) -> List[Topic]:
        """Get trends for country at given time (or latest)."""
        timestamp = timestamp or datetime.now()
        cache_key = f"trends:{country}:{timestamp.isoformat()}"

        # Check cache
        cached = self.redis.get(cache_key)
        if cached:
            return [Topic(**t) for t in json.loads(cached)]

        # Query database
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    t.topic_id,
                    t.normalized_label,
                    ts.count,
                    ts.sample_titles,
                    ts.sources,
                    ts.confidence
                FROM topic_snapshots ts
                JOIN topics t ON ts.topic_id = t.topic_id
                WHERE ts.country_code = %s
                  AND ts.snapshot_time <= %s
                ORDER BY ts.snapshot_time DESC, ts.count DESC
                LIMIT 50
            """, (country, timestamp))

            rows = cur.fetchall()
            topics = [
                Topic(
                    id=str(row[0]),
                    label=row[1],
                    count=row[2],
                    sample_titles=row[3] or [],
                    sources=row[4] or [],
                    confidence=row[5]
                )
                for row in rows
            ]

            # Cache result
            self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps([t.dict() for t in topics])
            )

            return topics
        finally:
            cur.close()
            release_db_connection(conn)
```

### Phase 5: Monitoring & Optimization (Week 5)

#### Step 5.1: Add Database Health Monitoring

```python
# backend/app/api/v1/health.py (enhance)

@router.get("/db")
async def database_health():
    """Check database health and performance."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Check connection
        cur.execute("SELECT 1")

        # Check table sizes
        cur.execute("""
            SELECT
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """)
        table_sizes = cur.fetchall()

        # Check row counts
        cur.execute("""
            SELECT
                'topic_snapshots' AS table,
                COUNT(*) AS rows
            FROM topic_snapshots
            UNION ALL
            SELECT 'flows', COUNT(*) FROM flows
            UNION ALL
            SELECT 'hotspots', COUNT(*) FROM hotspots
        """)
        row_counts = cur.fetchall()

        return {
            "status": "healthy",
            "table_sizes": dict(table_sizes),
            "row_counts": dict(row_counts),
            "timestamp": datetime.now()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now()
        }
    finally:
        cur.close()
        release_db_connection(conn)
```

#### Step 5.2: Set Up Slow Query Logging

```sql
-- Enable slow query logging (queries >1s)
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';
SELECT pg_reload_conf();

-- Create pg_stat_statements extension for query analytics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slowest queries
SELECT
    query,
    calls,
    mean_exec_time,
    max_exec_time,
    total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### Migration Timeline Summary

| Week | Phase | Deliverables |
|------|-------|--------------|
| **Week 1** | Initial Setup | PostgreSQL running, migrations executed, connection pool ready |
| **Week 2** | Backfill | Historical data from Redis → PostgreSQL (if available) |
| **Week 3** | Incremental Writes | API writes to both Redis + PostgreSQL (dual-write pattern) |
| **Week 4** | Read Migration | API reads from PostgreSQL (with Redis cache), validate correctness |
| **Week 5** | Monitoring | Health checks, slow query logging, performance tuning |

**Total Migration Time**: 5 weeks (parallel with Iteration 2 feature development)

---

## 8. Performance Optimization

### Indexing Strategy

#### Primary Indexes (Already in Schema)
- **B-tree indexes**: Fast equality/range queries on timestamps, foreign keys
- **GIN indexes**: Fast array/JSONB searches (sources, keywords, shared_topics)
- **Composite indexes**: Optimize common query patterns (country + time + count)

#### Partial Indexes (Add if Needed)
```sql
-- Index only active countries
CREATE INDEX idx_countries_active_only
ON countries(country_code)
WHERE is_active = true;

-- Index only recent hotspots (last 30 days)
CREATE INDEX idx_hotspots_recent
ON hotspots(snapshot_time, intensity DESC)
WHERE snapshot_time >= NOW() - INTERVAL '30 days';

-- Index only high-heat flows
CREATE INDEX idx_flows_high_heat
ON flows(heat DESC, detected_at DESC)
WHERE heat >= 0.7;
```

### Query Optimization Techniques

#### 1. Partition Pruning
- Queries with `WHERE snapshot_time BETWEEN X AND Y` automatically skip irrelevant partitions
- Reduces scan size by 90%+ for recent queries

#### 2. Materialized Views
- Pre-compute common aggregations (recent hotspots, active flows)
- Refresh every 15 minutes via cron job:
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_recent_hotspots;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_active_flows;
```

#### 3. Connection Pooling
- Reuse database connections instead of opening new ones
- Reduces connection overhead from ~50ms to <1ms

#### 4. JSONB Indexing
```sql
-- Index specific JSONB keys for faster queries
CREATE INDEX idx_top_topics_label
ON hotspots USING GIN ((top_topics->'label'));

CREATE INDEX idx_shared_topics_label
ON flows USING GIN ((shared_topics->'label'));
```

#### 5. EXPLAIN ANALYZE Monitoring
```sql
-- Before optimizing, always check query plan
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM topic_snapshots
WHERE country_code = 'US'
  AND snapshot_time >= NOW() - INTERVAL '7 days';

-- Look for:
-- - Seq Scan → BAD (add index)
-- - Index Scan → GOOD
-- - Bitmap Heap Scan → OK (for low-selectivity queries)
```

### Caching Strategy

```
┌─────────────────────────────────────────────────┐
│             Request Flow                        │
└─────────────────────────────────────────────────┘

Client Request
      │
      ▼
┌─────────────┐
│ Redis Cache │ ◄── 15-min TTL
└──────┬──────┘
       │ Cache Miss
       ▼
┌──────────────────┐
│ Materialized View│ ◄── Refreshed every 15 min
└──────┬───────────┘
       │ View Miss (rare)
       ▼
┌──────────────────┐
│ Base Tables      │ ◄── Partitioned, indexed
│ (PostgreSQL)     │
└──────────────────┘
```

**Hit Rates**:
- Redis: 80-90% (most API requests)
- Materialized View: 95-99% (when Redis misses)
- Base Tables: 1-5% (only for historical queries)

### Database Configuration Tuning

```sql
-- Recommended PostgreSQL settings (postgresql.conf)

-- Memory
shared_buffers = '1GB'  -- 25% of RAM
effective_cache_size = '3GB'  -- 75% of RAM
work_mem = '16MB'  -- Per sort/hash operation
maintenance_work_mem = '256MB'  -- For VACUUM, CREATE INDEX

-- Connections
max_connections = 100
superuser_reserved_connections = 3

-- Query Planner
random_page_cost = 1.1  -- SSD (default 4.0 is for HDD)
effective_io_concurrency = 200  -- SSD

-- Write-Ahead Log
wal_buffers = '16MB'
checkpoint_timeout = '15min'
checkpoint_completion_target = 0.9

-- Autovacuum (keep tables clean)
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = '1min'
```

### Monitoring Queries

```sql
-- 1. Table bloat (should run VACUUM if >20% bloat)
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    n_dead_tup,
    n_live_tup,
    ROUND(n_dead_tup * 100.0 / NULLIF(n_live_tup, 0), 2) AS bloat_percent
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- 2. Index usage (unused indexes waste space/write performance)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- 3. Cache hit ratio (should be >95%)
SELECT
    SUM(heap_blks_read) AS heap_read,
    SUM(heap_blks_hit) AS heap_hit,
    ROUND(SUM(heap_blks_hit) * 100.0 / NULLIF(SUM(heap_blks_hit + heap_blks_read), 0), 2) AS cache_hit_ratio
FROM pg_statio_user_tables;
```

### Expected Performance Targets

| Query Type | Target Latency | Method |
|-----------|----------------|--------|
| **Get trends for country** | <50ms | Redis cache (hit) |
| **Get recent hotspots** | <100ms | Materialized view |
| **Calculate flows (10 countries)** | <2s | In-memory compute, then cache |
| **Detect stance changes** | <200ms | Indexed scan on stance_history |
| **Historical time-series (7 days)** | <500ms | Partition pruning + indexes |
| **Aggregate weekly trends** | <3s | Partition-wise aggregation |

---

## Summary

### Key Design Decisions

1. **Partitioning**: Weekly partitions for `topic_snapshots` balances query performance with maintenance overhead
2. **Materialized Views**: Pre-compute expensive aggregations (hotspots, flows) for sub-100ms API responses
3. **Hybrid Storage**: Hot (30d) → Warm (90d) → Cold (1y) maximizes performance while controlling costs
4. **JSONB for Flexibility**: Store arrays/objects (sources, top_topics) as JSONB for schema evolution
5. **Triggers**: Auto-update `topics` table and detect stance drift without application logic
6. **UUID Primary Keys**: Future-proof for distributed systems and sharding

### Next Steps

1. **Week 1**: Create migration file `002_comprehensive_flow_schema.sql` from schema above
2. **Week 2**: Run migration on dev environment, test with sample data
3. **Week 3**: Implement repository layer (read/write abstractions)
4. **Week 4**: Modify API endpoints to persist data
5. **Week 5**: Monitor performance, tune queries, validate retention policy

### Future Enhancements (Iteration 3+)

- **PostGIS**: Geo-spatial queries (find flows within 1000km radius)
- **Full-Text Search**: `tsvector` columns for semantic topic search
- **TimescaleDB**: Hypertables for automatic partitioning and compression
- **pgvector**: Store BERT embeddings for semantic similarity (stance tracking)
- **Replication**: Multi-region read replicas for global scale
- **Sharding**: Partition by region (Americas, Europe, Asia) for 100+ countries

---

**Document Status**: Ready for Implementation
**Approved By**: Pending Review
**Last Updated**: 2025-01-13
