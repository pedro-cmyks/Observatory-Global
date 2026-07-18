-- 085_temporal_signature.sql
-- Temporal signature (Lane C, 2026-07-18): the lineage speaks for EVERY
-- thread, not just the giants. Classifies each ACTIVE dynamic topic's shape
-- in time from the narrative_lineage edges (mig 084) + its own hot span:
--   new          no ancestor archive units matched — genuinely first coverage
--                since the archive begins (May), only asserted when the
--                census actually attempted the topic (coverage >= member
--                floor; below-floor topics stay NULL — absence over guess)
--   continuous   one unbroken weekly chain (default; not a badge)
--   recurrent    >=3 active eras (went quiet >=2 weeks and returned, twice+)
--   resurrected  exactly one >=2-week quiet gap, then returned (currently
--                active); dead-lineage-descendant folds here by construction
-- Umbrellas inherit the majority signature of their active children.
--
-- Producer: backend/scripts/temporal_signature.py (nightly, after the
-- lineage census+load in run-scoped-snapshot.sh; re-writes active topics,
-- NULLs the unclassifiable — a stale signature never outlives its lineage).
-- signature_meta: {eras, gap_weeks, first_seen_week, returned_week, ...}.
--
-- Additive + reversible:
--   ALTER TABLE dynamic_topics DROP COLUMN temporal_signature,
--                              DROP COLUMN signature_meta;

ALTER TABLE dynamic_topics
    ADD COLUMN IF NOT EXISTS temporal_signature TEXT,
    ADD COLUMN IF NOT EXISTS signature_meta JSONB;

-- serving reads it via existing per-id lookups; no new index needed (the
-- column rides along _DYNAMIC_TOPICS_SELECT / detail SQL).
