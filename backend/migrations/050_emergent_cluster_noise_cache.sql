-- Migration 050: emergent_clusters.role_noise_rate (Phase 6 cost control)
--
-- Per-cluster evidence-role noise fraction, computed ONCE by the local
-- student (e5 + logistic, $0 API) and cached here. The dynamic_topics
-- incremental writer scores only clusters where this is NULL, so noise is
-- never recomputed and AI/API cost does not grow with each cron run.
-- Additive, nullable.

ALTER TABLE emergent_clusters ADD COLUMN IF NOT EXISTS role_noise_rate NUMERIC;
