-- Migration 068: atlas_topics.origin — the category corpus stops being
-- hand-frozen (Pedro 2026-07-04: "ese corpus no es fijo en piedra").
--
-- 'seed'  = the candidate-v2 ensemble set (2026-06-29, human-reviewed)
-- 'auto'  = grown by backend/scripts/grow_atlas_categories.py from the
--           R3.1 typer's free-form categories (anchored-emergent growth,
--           the mechanism the R3 spec promised but never built)
--
-- Auto categories are born lexicon-less (semantic/typing lens only); the
-- gate covers them as gold accumulates. Seeds are never auto-modified.

ALTER TABLE atlas_topics ADD COLUMN IF NOT EXISTS origin TEXT NOT NULL DEFAULT 'seed';
