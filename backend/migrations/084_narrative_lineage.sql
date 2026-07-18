-- 084_narrative_lineage.sql
-- Narrative lineage census (2026-07-18): persist the MEASURED stitch between
-- live dynamic topics and the archive story layer (archive_story_units, mig
-- 069), plus the unit->unit edges that chain archive eras into lineages.
-- Producer: backend/scripts/narrative_lineage_census.py (OpenAI space only —
-- topic centroids are rebuilt from member headlines in the archive's own
-- embedding space; e5 never touches this table).
-- Loader:   backend/scripts/load_narrative_lineage.py (idempotent upsert).
-- Consumer: GET /api/v2/theme/{id}/lineage (narrative-lineage-v0).
--
-- ONE table, discriminated by `kind` (task call: keep it simple, additive):
--   topic_unit  live dynamic_topics id -> archive unit  (the stitch)
--   unit_unit   archive unit -> archive unit            (era chaining)
-- No FK to archive_story_units: units are append-only but re-loadable; the
-- census is the source of truth and re-emits the full edge set each run.
-- Reversible: DROP TABLE narrative_lineage; (nothing else references it).

CREATE TABLE IF NOT EXISTS narrative_lineage (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('topic_unit', 'unit_unit')),
    topic_id    BIGINT,            -- topic_unit rows: dynamic_topics.id
    src_unit_id BIGINT,            -- unit_unit rows: earlier archive unit
    unit_id     BIGINT NOT NULL,   -- archive_story_units.id (dst for unit_unit)
    sim         REAL NOT NULL,     -- measured cosine (OpenAI space)
    week        DATE,              -- ISO Monday of the (dst) unit's week
    src_week    DATE,              -- unit_unit only: ISO Monday of src week
    edge_kind   TEXT,              -- unit_unit only: intra|adjacent|gap-bridge
    method      TEXT NOT NULL,     -- census build + measured thresholds
    candidate   BOOLEAN NOT NULL DEFAULT FALSE,  -- near-threshold / low-confidence
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT narrative_lineage_shape CHECK (
        (kind = 'topic_unit' AND topic_id IS NOT NULL AND src_unit_id IS NULL)
        OR
        (kind = 'unit_unit' AND src_unit_id IS NOT NULL AND topic_id IS NULL)
    )
);

-- upsert identities (partial unique per kind)
CREATE UNIQUE INDEX IF NOT EXISTS ux_narrative_lineage_topic_unit
    ON narrative_lineage (topic_id, unit_id) WHERE kind = 'topic_unit';
CREATE UNIQUE INDEX IF NOT EXISTS ux_narrative_lineage_unit_unit
    ON narrative_lineage (src_unit_id, unit_id) WHERE kind = 'unit_unit';

-- serving lookups: topic -> stitch, unit -> component expansion (both ends)
CREATE INDEX IF NOT EXISTS idx_narrative_lineage_unit
    ON narrative_lineage (unit_id);
CREATE INDEX IF NOT EXISTS idx_narrative_lineage_src_unit
    ON narrative_lineage (src_unit_id) WHERE src_unit_id IS NOT NULL;

ALTER TABLE narrative_lineage ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS narrative_lineage_service_all ON narrative_lineage;
CREATE POLICY narrative_lineage_service_all ON narrative_lineage
    FOR ALL TO service_role USING (true) WITH CHECK (true);
