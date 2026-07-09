-- 074_dynamic_topics_is_junk.sql
-- Useful-coverage quality gate (2026-07-09, docs/state/2026-07-09-useful-coverage-gate.md).
--
-- The clustering recall fix (9d1b04e7) lifted story coverage 0.04% -> ~40% but
-- admitted junk grab-bags as active anchors: multi-source gravity wells
-- ("Full list of Welsh beaches" 2021 members, "Celebrity Emotional Statements"
-- 1456, "Mixed: Economic and Regional Updates" 1203) that vacuum loosely-related
-- signals via the >=0.82 assign threshold and eat ~30% of assigned coverage.
--
-- is_junk = a CONTENT-based quality flag (not a label regex): set by
-- scripts/flag_junk_topics.py from the R3.1 category typer + listicle labels +
-- few-source feed-dump signature (scripts/topic_junk.py). It is read by
--   - build_unified_topics._load_centroids  -> junk topics stop anchoring (coverage reclaim)
--   - project_dynamic_topics promotion       -> junk topics never promote / are demoted (serving)
-- so the useful coverage (non-junk members / signals) climbs while the junk
-- gravity wells release their vacuumed signals back to real stories.
--
-- Fully reversible: UPDATE dynamic_topics SET is_junk=false, junk_reason=NULL;
-- (build/project honor a kill-switch too — see ATLAS_UNIFIED_EXCLUDE_JUNK).

ALTER TABLE dynamic_topics
  ADD COLUMN IF NOT EXISTS is_junk boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS junk_reason text;

-- Partial index: the anchor-load + promotion queries filter on is_junk IS NOT TRUE
-- across the active/candidate population; a partial index on the junk minority
-- keeps the exclusion cheap without bloating the hot path.
CREATE INDEX IF NOT EXISTS idx_dynamic_topics_is_junk
  ON dynamic_topics (id) WHERE is_junk;
