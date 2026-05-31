-- Migration 046: emergent_clusters
--
-- Persistent storage for the emergent topic discovery layer (spec:
-- docs/superpowers/specs/2026-05-29-emergent-topic-discovery-design.md).
-- Each row is one cluster captured at a snapshot in time:
--   - raw HDBSCAN cluster (raw_signal_count, raw_sample_ids)
--   - precision-gate-filtered kept set (n_signals, sample_signal_ids,
--     gate_threshold, cohesion on kept)
--   - DeepSeek (and optionally 3-vendor) labeling (label, description,
--     vendor_agreement, vendor_labels)
--   - centroid + top countries for cross-snapshot continuity matching
--
-- Additive, reversible. RLS enabled with no policy: backend connects as
-- postgres superuser and bypasses RLS; anon/authenticated cannot read.

CREATE TABLE IF NOT EXISTS emergent_clusters (
    id                  BIGSERIAL PRIMARY KEY,
    snapshot_at         TIMESTAMPTZ NOT NULL,
    snapshot_window_h   INT          NOT NULL DEFAULT 24,
    cluster_id          INT          NOT NULL,                -- HDBSCAN local id within the snapshot
    label               TEXT         NOT NULL,
    description         TEXT,
    raw_signal_count    INT          NOT NULL,                -- HDBSCAN cluster size before precision filter
    n_signals           INT          NOT NULL,                -- kept after the >=90% precision filter
    gate_threshold      NUMERIC,                              -- logistic threshold used for this snapshot
    velocity            INT,                                  -- delta in n_signals vs prior matched snapshot
    cohesion            NUMERIC,                              -- mean pairwise cosine on the kept set
    top_country_codes   TEXT[]       NOT NULL DEFAULT '{}',
    sample_signal_ids   BIGINT[]     NOT NULL DEFAULT '{}',   -- top-K from kept set (display)
    raw_sample_ids      BIGINT[]     NOT NULL DEFAULT '{}',   -- top-K from full HDBSCAN cluster (audit)
    centroid_vec        REAL[],                               -- 768-dim e5-base centroid of the kept set
    vendor_agreement    TEXT         NOT NULL DEFAULT 'deepseek',
                                                              -- 'deepseek' | 'high' | 'moderate' | 'incoherent'
    vendor_labels       JSONB,                                -- {"deepseek": {...}, "claude": {...}, "gpt": {...}}
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Latest-snapshot reads dominate the API hot path.
CREATE INDEX IF NOT EXISTS idx_emergent_snapshot
    ON emergent_clusters (snapshot_at DESC);

-- Default product ranking: most accelerating clusters first.
CREATE INDEX IF NOT EXISTS idx_emergent_velocity
    ON emergent_clusters (snapshot_at DESC, velocity DESC NULLS LAST);

-- Continuity matching reads recent centroids; supports the dynamic_topics
-- lifecycle (Phase 6) that searches "what cluster from the last few
-- snapshots is this one a continuation of".
CREATE INDEX IF NOT EXISTS idx_emergent_recent_window
    ON emergent_clusters (snapshot_at DESC, snapshot_window_h);

ALTER TABLE emergent_clusters ENABLE ROW LEVEL SECURITY;
-- No policy: anon/authenticated have no SELECT/INSERT/UPDATE/DELETE access
-- through PostgREST. Backend connects as postgres superuser and bypasses
-- RLS by virtue of role (mirrors mig 030 lockdown convention).
