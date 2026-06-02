-- Migration 049: dynamic_topics.noise_rate (Phase 6, Sub-A quality gate)
--
-- Per-topic mean evidence-role noise fraction from the local student
-- (2026-06-02-evidence-role-student-v1). The robust quality gate that
-- replaces the brittle label-regex roundup heuristic: a grab-bag topic has
-- a high noise-role membership. Promotion to `active` requires noise_rate
-- below a threshold. Additive, nullable (null = not yet scored).

ALTER TABLE dynamic_topics ADD COLUMN IF NOT EXISTS noise_rate NUMERIC;
