-- Migration 069: archive_story_units — the archive's story layer, queryable.
--
-- Stage B (2026-07-05) clustered the full embedded archive (6.9M headlines,
-- May-03→Jul-04) into ~6.5K per-day story units. This table makes them
-- SERVABLE: the thread-level "click a past peak → that day's receipts"
-- (time-as-dimension spec, the last surface of the cycle) matches a topic
-- to its archive-era units by centroid and serves their sample headlines
-- with an honest FROM-THE-ARCHIVE tier.
--
-- Loader: backend/scripts/load_archive_units.py (reads the Ext jsonl).
-- ~6.5K rows × halfvec(1536) ≈ 20 MB; no vector index needed at this size
-- (seq scan of 6.5K rows is sub-ms territory).

CREATE TABLE IF NOT EXISTS archive_story_units (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    day         DATE NOT NULL,
    label       TEXT NOT NULL,            -- medoid headline of the cluster
    samples     JSONB NOT NULL,           -- up to 3 sample headlines
    n_signals   INT NOT NULL,
    cohesion    REAL,
    top_cc      TEXT[],                   -- top subject countries
    vec         halfvec(1536) NOT NULL,   -- OpenAI text-embedding-3-small
    UNIQUE (day, label)
);

CREATE INDEX IF NOT EXISTS idx_archive_story_units_day
    ON archive_story_units (day);

ALTER TABLE archive_story_units ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS archive_story_units_service_all ON archive_story_units;
CREATE POLICY archive_story_units_service_all ON archive_story_units
    FOR ALL TO service_role USING (true) WITH CHECK (true);
