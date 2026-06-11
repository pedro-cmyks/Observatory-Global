-- Migration 054: signal_embeddings (Phase 1.5b deliverable 2, #223)
--
-- Persisted e5 embeddings for the deduped hot corpus, enabling full-corpus
-- semantic retrieval in research plans (Pipeline Funnel Principle: gates
-- decide what Atlas volunteers, not what it can find when asked).
--
-- Sizing decision (measured 2026-06-11, see #223): halfvec fp16 over fp32 —
-- ~1.7GB data + ~1GB HNSW at ~1.1M rows (7d retention) vs 10GB current DB.
-- Near-lossless for cosine ranking.
--
-- Writer: local M1 worker (scripts/embed_hot_corpus.py) — incremental,
-- embeds deduped hot-window headlines with the snapshot-identical pooling,
-- sweeps rows older than the retention window. Fly never writes this table.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS signal_embeddings (
    signal_id    BIGINT PRIMARY KEY REFERENCES signals_v2(id) ON DELETE CASCADE,
    embedded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    model        TEXT NOT NULL DEFAULT 'multilingual-e5-base',
    vec          halfvec(768) NOT NULL
);

-- ANN search: cosine over fp16 vectors.
CREATE INDEX IF NOT EXISTS idx_signal_embeddings_vec
    ON signal_embeddings USING hnsw (vec halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Retention sweep scans by age.
CREATE INDEX IF NOT EXISTS idx_signal_embeddings_embedded_at
    ON signal_embeddings (embedded_at);

ALTER TABLE signal_embeddings ENABLE ROW LEVEL SECURITY;
-- No public policies on purpose: service role only.
