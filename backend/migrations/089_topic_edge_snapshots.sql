-- 089_topic_edge_snapshots.sql
-- Track C1 — the edge-snapshot STORE (spec docs/superpowers/specs/
-- 2026-07-21-time-axis-versioned-relationships.md §6). Foundational substrate
-- for the time axis / versioned relationships feature: persist, once per pass,
-- the DERIVED kinship-edge set + the entity backbone, versioned against
-- churn-resistant anchors, so replay/diff (C2/C3, not built here) can read
-- them cheaply and separate real narrative change from substrate churn.
--
-- NUMBERING NOTE: 088 is reserved (unmerged) by the parallel markets branch
-- (`docs/superpowers/plans/2026-07-21-implementation-plan.md` B2) — using 089
-- here to avoid a collision when that branch merges.
--
-- Two tables:
--
-- 1. topic_edge_snapshots — the CURRENT direct kinship graph (spec §5a: "the
--    walk graph / kinship edges persisted with a timestamp each pass"), keyed
--    on the CHURN-RESISTANT anchor `dynamic_topics.identity_key` (NOT the
--    ephemeral numeric id / `dynamic-topic-<n>` — a retired topic resurrects
--    on centroid match under the SAME identity_key, spec §4). `topic_id_a/b`
--    are carried for reference/display only (the current `dynamic-topic-<n>`
--    at snapshot time), never the join key. `degree` is always 1 in this pass
--    (C1 persists only the DIRECT kNN graph, i.e. "hermano" edges per the
--    chains spec's kinship model); the multi-hop primo walk stays an
--    on-demand from-pins computation (`/api/v2/dossier/walk`) and is NOT
--    re-derived or stored here — the column stays wide enough (>=1) for a
--    future write path without a migration.
--
-- 2. entity_backbone_edges — the coarse, long-arc entity co-occurrence spine
--    (spec §4: "actors/places outlast threads... the months-long spine"),
--    RARITY-GATED over the temporal window (spec §7: "else Trump-<anything>
--    glues the whole backbone across all of time — #234, again"). Explicitly
--    co-occurrence, never asserted relationship (spec §7).
--
-- Both are populated by `backend/scripts/snapshot_topic_edges.py` (idempotent
-- upsert; re-running the same snapshot_at / window_end converges, never
-- duplicates). Additive + reversible; touches no existing serving path.
--
-- Rollback:
--   DROP TABLE IF EXISTS topic_edge_snapshots;
--   DROP TABLE IF EXISTS entity_backbone_edges;

CREATE TABLE IF NOT EXISTS topic_edge_snapshots (
    id             BIGSERIAL   PRIMARY KEY,
    snapshot_at    TIMESTAMPTZ NOT NULL,
    identity_key_a TEXT        NOT NULL,   -- canonicalized: identity_key_a <= identity_key_b
    identity_key_b TEXT        NOT NULL,
    topic_id_a     TEXT        NOT NULL,   -- e.g. 'dynamic-topic-31' — reference only
    topic_id_b     TEXT        NOT NULL,
    degree         INT         NOT NULL DEFAULT 1 CHECK (degree >= 1),
    -- Whitened cosine, NOT clamped to [0,1]: whitening deliberately
    -- de-compresses the anisotropic e5 cone (chains spec §2.2) so a
    -- genuinely weak/unrelated top-k pick can read as a low or negative
    -- value — that is the honest measurement, not an error.
    weight         REAL        NOT NULL CHECK (weight >= -1 AND weight <= 1),
    basis          TEXT        NOT NULL DEFAULT 'semantic'
                   CHECK (basis IN ('semantic', 'shared_country', 'shared_person',
                                     'text_mention', 'body_mention', 'co_occurrence')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT topic_edge_snapshots_unique
        UNIQUE (snapshot_at, identity_key_a, identity_key_b)
);

-- Point-in-time reads ("what did the graph look like at date X").
CREATE INDEX IF NOT EXISTS idx_topic_edge_snapshots_snapshot_at
    ON topic_edge_snapshots (snapshot_at);
-- Pair-history reads ("how has this relationship evolved over time") — the
-- C2/C3 replay/diff access pattern; snapshot_at trails so a range scan over
-- one pair's history is an index-only lookup.
CREATE INDEX IF NOT EXISTS idx_topic_edge_snapshots_identity_pair
    ON topic_edge_snapshots (identity_key_a, identity_key_b, snapshot_at);

CREATE TABLE IF NOT EXISTS entity_backbone_edges (
    id             BIGSERIAL   PRIMARY KEY,
    window_start   TIMESTAMPTZ NOT NULL,
    window_end     TIMESTAMPTZ NOT NULL,
    entity_a       TEXT        NOT NULL,   -- canonicalized: entity_a <= entity_b
    entity_b       TEXT        NOT NULL,
    cooccur_count  INT         NOT NULL CHECK (cooccur_count > 0),
    rarity_weight  REAL        NOT NULL CHECK (rarity_weight >= 0 AND rarity_weight <= 1),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT entity_backbone_edges_unique
        UNIQUE (window_end, entity_a, entity_b)
);

CREATE INDEX IF NOT EXISTS idx_entity_backbone_edges_window
    ON entity_backbone_edges (window_end);
CREATE INDEX IF NOT EXISTS idx_entity_backbone_edges_pair
    ON entity_backbone_edges (entity_a, entity_b);

-- Server-only tables (asyncpg via the API/scripts; never PostgREST). 082/086
-- lesson: Supabase default privileges grant ALL to anon+authenticated on new
-- tables — revoke, and enable RLS with no policies as defense-in-depth.
ALTER TABLE topic_edge_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_backbone_edges ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON topic_edge_snapshots FROM anon, authenticated;
REVOKE ALL ON entity_backbone_edges FROM anon, authenticated;
