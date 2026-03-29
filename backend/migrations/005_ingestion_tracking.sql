-- Ingestion tracking tables for gap detection and backfill

-- Track ingestion runs
CREATE TABLE IF NOT EXISTS ingest_watermark (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL DEFAULT 'gdelt_gkg',
    last_successful_timestamp TIMESTAMP,
    last_file_id VARCHAR(255),
    last_run_at TIMESTAMP DEFAULT NOW(),
    records_processed INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'idle',  -- idle, running, failed, completed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_watermark_source ON ingest_watermark(source_type);

-- Track individual file processing for backfill
CREATE TABLE IF NOT EXISTS ingest_file_log (
    id SERIAL PRIMARY KEY,
    file_url VARCHAR(500) NOT NULL,
    file_timestamp TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed, skipped
    records_count INTEGER,
    error_message TEXT,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(file_url)
);

CREATE INDEX IF NOT EXISTS idx_file_log_status ON ingest_file_log(status);

-- Insert initial watermark
INSERT INTO ingest_watermark (source_type, status) 
VALUES ('gdelt_gkg', 'idle')
ON CONFLICT DO NOTHING;
