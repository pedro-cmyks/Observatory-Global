-- Migration 048: dynamic_topics lifecycle (Phase 6, Sub-A)
--
-- Self-curating topic taxonomy sourced from the emergent layer. A
-- dynamic_topic is a stable cross-snapshot identity (validated in
-- docs/research/topic-quality/2026-06-02-emergent-topic-identity.md):
-- emergent_clusters from different snapshots that are the same topic
-- (centroid cosine >= 0.85) collapse into one row whose centroid is the
-- running mean of its members.
--
-- State machine (driven by quality signals, not persistence alone):
--   candidate  -> active      : persists >= 2 snapshots AND cohesive AND
--                               enough volume AND not a roundup artifact
--   active     -> deprecated  : no new member cluster for K snapshots
--   deprecated -> retired     : stale for a further M snapshots
--   deprecated -> active      : re-emerges with a new member cluster
--
-- Runs in SHADOW: not read by any product surface yet. The projection
-- writer (project_dynamic_topics.py) is the only writer. Additive,
-- reversible. RLS enabled with no policy (mirrors mig 046 lockdown).

CREATE TABLE IF NOT EXISTS dynamic_topics (
    id                BIGSERIAL PRIMARY KEY,
    identity_key      TEXT        NOT NULL UNIQUE,        -- stable human-ish key
    state             TEXT        NOT NULL DEFAULT 'candidate'
                                  CHECK (state IN ('candidate', 'active', 'deprecated', 'retired')),
    label             TEXT        NOT NULL,               -- representative label
    centroid_vec      REAL[],                             -- running-mean e5 centroid (for matching)
    first_seen        TIMESTAMPTZ NOT NULL,
    last_seen         TIMESTAMPTZ NOT NULL,
    n_snapshots       INT         NOT NULL DEFAULT 1,     -- distinct snapshots seen
    agg_n_signals     INT         NOT NULL DEFAULT 0,     -- summed kept signals across members
    mean_cohesion     NUMERIC,                            -- mean member cohesion
    is_roundup        BOOLEAN     NOT NULL DEFAULT FALSE, -- generic "roundup/mixed" artifact
    snapshots_since_seen INT      NOT NULL DEFAULT 0,     -- staleness counter for deprecate/retire
    last_state_change TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dynamic_topic_members (
    dynamic_topic_id    BIGINT      NOT NULL REFERENCES dynamic_topics(id) ON DELETE CASCADE,
    emergent_cluster_id BIGINT      NOT NULL REFERENCES emergent_clusters(id) ON DELETE CASCADE,
    snapshot_at         TIMESTAMPTZ NOT NULL,
    match_score         NUMERIC,                          -- centroid cosine at link time
    added_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (dynamic_topic_id, emergent_cluster_id)
);

-- Product/lifecycle reads: active topics by recency.
CREATE INDEX IF NOT EXISTS idx_dynamic_topics_state
    ON dynamic_topics (state, last_seen DESC);

-- Staleness sweep.
CREATE INDEX IF NOT EXISTS idx_dynamic_topics_last_seen
    ON dynamic_topics (last_seen DESC);

-- Member lookups both directions.
CREATE INDEX IF NOT EXISTS idx_dynamic_topic_members_topic
    ON dynamic_topic_members (dynamic_topic_id);
CREATE INDEX IF NOT EXISTS idx_dynamic_topic_members_cluster
    ON dynamic_topic_members (emergent_cluster_id);

ALTER TABLE dynamic_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic_topic_members ENABLE ROW LEVEL SECURITY;
-- No policy: anon/authenticated have no access through PostgREST. The
-- backend connects as postgres superuser and bypasses RLS by role.
