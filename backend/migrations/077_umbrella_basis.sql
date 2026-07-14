-- 077 — umbrella provenance: how each umbrella was grouped.
--
-- Umbrellas can now be formed by more than one grouper: the semantic
-- complete-linkage over centroids (the R2 default), or the LLM same-event judge
-- (gap-2, docs/specs/2026-07-14-gap2-event-umbrella-design.md) which reconnects
-- event fragments the centroid cut misses (US-Iran strikes / Hormuz / Bahrain
-- drone). This records WHICH grouper formed a given umbrella so serving / A-B /
-- audit can distinguish them. Additive + nullable — no existing row changes; the
-- eclipse contract columns (category/crisis_relevant/parent_id/etc.) are untouched.
--
-- Reversible: ALTER TABLE dynamic_topics DROP COLUMN umbrella_basis;
ALTER TABLE dynamic_topics
    ADD COLUMN IF NOT EXISTS umbrella_basis TEXT;

COMMENT ON COLUMN dynamic_topics.umbrella_basis IS
    'How this umbrella was grouped: semantic-complete-linkage | llm-same-event-v1 | shared-actor. NULL for non-umbrella rows.';
