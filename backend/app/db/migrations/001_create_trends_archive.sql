-- Migration: Create trends_archive table
-- Purpose: Store historical trending topics for flow detection and analysis
-- Author: Backend Flow Agent
-- Date: 2025-01-12

-- Create trends_archive table
CREATE TABLE IF NOT EXISTS trends_archive (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    country VARCHAR(2) NOT NULL,
    topic_label VARCHAR(500) NOT NULL,
    count INTEGER NOT NULL DEFAULT 0 CHECK (count >= 0),
    confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    sources JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_trends_archive_country_timestamp
    ON trends_archive(country, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_trends_archive_timestamp
    ON trends_archive(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_trends_archive_topic_label
    ON trends_archive(topic_label);

-- Add comment to table
COMMENT ON TABLE trends_archive IS 'Historical archive of trending topics for flow detection and time-series analysis';

-- Add column comments
COMMENT ON COLUMN trends_archive.timestamp IS 'Timestamp when the topic was trending';
COMMENT ON COLUMN trends_archive.country IS 'ISO 3166-1 alpha-2 country code';
COMMENT ON COLUMN trends_archive.topic_label IS 'Topic label or title';
COMMENT ON COLUMN trends_archive.count IS 'Topic frequency/popularity count';
COMMENT ON COLUMN trends_archive.confidence IS 'Confidence score for topic extraction [0.0, 1.0]';
COMMENT ON COLUMN trends_archive.sources IS 'JSON array of data sources (e.g., ["gdelt", "trends", "wikipedia"])';
COMMENT ON COLUMN trends_archive.created_at IS 'Timestamp when record was inserted';
