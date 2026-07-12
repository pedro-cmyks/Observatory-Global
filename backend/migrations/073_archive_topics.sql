-- 073_archive_topics.sql
-- Archive Intelligence Tier (spec 2026-07-10): one LIGHT row per historical
-- topic. Centroids are REAL[] (OpenAI text-embedding-3-small, 1536d) with NO
-- vector index — at thousands of rows a scan+cosine answers in <100ms, and a
-- second HNSW competing for the Micro's ~1GB RAM is the exact failure mode
-- measured on 2026-07-08/10 (36h thrashing rebuild). Per-story detail and the
-- 42GB of vectors stay on the external disk (parquet + shards).

CREATE TABLE IF NOT EXISTS archive_topics (
    id               BIGSERIAL PRIMARY KEY,
    label            TEXT NOT NULL,
    category         TEXT,
    crisis_relevant  BOOLEAN,
    country_code     CHAR(2),
    period_start     DATE NOT NULL,
    period_end       DATE NOT NULL,
    n_stories        INT NOT NULL CHECK (n_stories > 0),
    n_signals        INT,
    centroid_vec     REAL[] NOT NULL,
    top_sources      JSONB,
    sample_story_ids TEXT[],
    build_id         TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT archive_topics_period_valid CHECK (period_end >= period_start)
);

CREATE INDEX IF NOT EXISTS idx_archive_topics_period
    ON archive_topics (period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_archive_topics_country
    ON archive_topics (country_code, period_start);
CREATE INDEX IF NOT EXISTS idx_archive_topics_build
    ON archive_topics (build_id);

ALTER TABLE archive_topics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS archive_topics_read ON archive_topics;
CREATE POLICY archive_topics_read ON archive_topics FOR SELECT USING (true);
