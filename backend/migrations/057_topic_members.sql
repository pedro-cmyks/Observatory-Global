-- Unified Engine F0.1 (spec docs/specs/2026-06-29-atlas-unified-engine.md §2).
-- ONE typed-membership table every construction path writes to; serving reads it
-- filtered by `role`. Construct = unify, serve = separate. `engine_version`
-- distinguishes the v1-compat ETL projection from the future unified-v2 output so
-- the hybrid A/B can compare them over the same window without one corrupting the
-- other. Additive — does not touch existing serving until F0.3.
CREATE TABLE IF NOT EXISTS topic_members (
    signal_id      BIGINT      NOT NULL REFERENCES signals_v2(id) ON DELETE CASCADE,
    topic_id       TEXT        NOT NULL,            -- atlas slug or 'dynamic-topic-<n>'
    role           TEXT        NOT NULL CHECK (role IN
                       ('evidence','discussion','mood','movement')),
    source_family  TEXT,                            -- press|social|ngo|gov|event
    basis          TEXT        NOT NULL CHECK (basis IN
                       ('semantic','lexical','theme','co_occurrence')),
    confidence     REAL,
    gate_kept      BOOLEAN,                         -- evidence only: cleared the gate
    engine_version TEXT        NOT NULL,            -- 'v1-compat' | 'unified-v2'
    assigned_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (signal_id, topic_id, role, engine_version)
);
CREATE INDEX IF NOT EXISTS idx_topic_members_topic
    ON topic_members (topic_id, role, engine_version);
CREATE INDEX IF NOT EXISTS idx_topic_members_signal
    ON topic_members (signal_id);
-- Serving filters by the active engine_version + role; partial index keeps the
-- hot evidence read fast.
CREATE INDEX IF NOT EXISTS idx_topic_members_evidence
    ON topic_members (topic_id) WHERE role = 'evidence';
ALTER TABLE topic_members ENABLE ROW LEVEL SECURITY;
