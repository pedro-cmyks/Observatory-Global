-- Processed historical surfaces synced from the local Atlas archive.
-- These tables intentionally store compact product-ready outputs, not raw
-- historical copies of signals_v2.

CREATE TABLE IF NOT EXISTS historical_processing_runs (
    run_id              UUID PRIMARY KEY,
    archive_root        TEXT NOT NULL,
    partition_from_ts   TIMESTAMPTZ NOT NULL,
    partition_to_ts     TIMESTAMPTZ NOT NULL,
    model_version       TEXT NOT NULL,
    processor_version   TEXT NOT NULL,
    status              TEXT NOT NULL,
    rows_read           BIGINT NOT NULL DEFAULT 0 CHECK (rows_read >= 0),
    rows_processed      BIGINT NOT NULL DEFAULT 0 CHECK (rows_processed >= 0),
    rows_failed         BIGINT NOT NULL DEFAULT 0 CHECK (rows_failed >= 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    error               TEXT,
    CONSTRAINT historical_processing_runs_status_valid
        CHECK (status IN ('started', 'completed', 'failed')),
    CONSTRAINT historical_processing_runs_window_valid
        CHECK (partition_to_ts > partition_from_ts)
);

CREATE TABLE IF NOT EXISTS historical_topic_country_daily (
    day                   DATE NOT NULL,
    topic_slug            TEXT NOT NULL,
    country_code          TEXT NOT NULL,
    source_family         TEXT NOT NULL,
    signal_class          TEXT NOT NULL,
    signal_count          BIGINT NOT NULL CHECK (signal_count >= 0),
    avg_sentiment         DOUBLE PRECISION,
    sentiment_coverage    DOUBLE PRECISION NOT NULL DEFAULT 0
        CHECK (sentiment_coverage >= 0 AND sentiment_coverage <= 1),
    topic_coverage        DOUBLE PRECISION NOT NULL DEFAULT 0
        CHECK (topic_coverage >= 0 AND topic_coverage <= 1),
    entity_coverage       DOUBLE PRECISION NOT NULL DEFAULT 0
        CHECK (entity_coverage >= 0 AND entity_coverage <= 1),
    local_voice_ratio     DOUBLE PRECISION
        CHECK (local_voice_ratio IS NULL OR (local_voice_ratio >= 0 AND local_voice_ratio <= 1)),
    source_diversity      DOUBLE PRECISION
        CHECK (source_diversity IS NULL OR source_diversity >= 0),
    evidence_sample_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_sample_count >= 0),
    model_version         TEXT NOT NULL,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (day, topic_slug, country_code, source_family, signal_class, model_version)
);

CREATE INDEX IF NOT EXISTS idx_hist_topic_country_daily_lookup
    ON historical_topic_country_daily (day DESC, country_code, topic_slug);

CREATE INDEX IF NOT EXISTS idx_hist_topic_country_daily_topic
    ON historical_topic_country_daily (topic_slug, day DESC, signal_count DESC);

CREATE INDEX IF NOT EXISTS idx_hist_topic_country_daily_country
    ON historical_topic_country_daily (country_code, day DESC, signal_count DESC);

CREATE TABLE IF NOT EXISTS historical_evidence_samples (
    sample_id             TEXT PRIMARY KEY,
    day                   DATE NOT NULL,
    topic_slug            TEXT NOT NULL,
    country_code          TEXT NOT NULL,
    source_family         TEXT NOT NULL,
    signal_class          TEXT NOT NULL,
    archive_relative_path TEXT NOT NULL,
    source_name           TEXT,
    source_url            TEXT,
    headline              TEXT,
    signal_timestamp      TIMESTAMPTZ,
    sentiment             DOUBLE PRECISION,
    confidence            DOUBLE PRECISION
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    selection_reason      TEXT NOT NULL,
    model_version         TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hist_evidence_lookup
    ON historical_evidence_samples (day DESC, country_code, topic_slug);

CREATE INDEX IF NOT EXISTS idx_hist_evidence_topic
    ON historical_evidence_samples (topic_slug, day DESC);

CREATE TABLE IF NOT EXISTS historical_archive_coverage (
    day                 DATE NOT NULL,
    archive_root        TEXT NOT NULL,
    rows_archived       BIGINT NOT NULL CHECK (rows_archived >= 0),
    rows_processed      BIGINT NOT NULL CHECK (rows_processed >= 0),
    sentiment_coverage  DOUBLE PRECISION NOT NULL
        CHECK (sentiment_coverage >= 0 AND sentiment_coverage <= 1),
    topic_coverage      DOUBLE PRECISION NOT NULL
        CHECK (topic_coverage >= 0 AND topic_coverage <= 1),
    entity_coverage     DOUBLE PRECISION NOT NULL
        CHECK (entity_coverage >= 0 AND entity_coverage <= 1),
    model_version       TEXT NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (day, archive_root, model_version)
);
