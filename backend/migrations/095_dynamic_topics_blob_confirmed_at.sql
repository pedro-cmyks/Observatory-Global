-- 095: blob-veto stamp (2026-08-03).
-- Gate-(c) census (docs/research/recall-229/2026-08-03-tf3b-gate-c-census.md)
-- measured the court's `entailed` stamp at ~70% precision as a serving
-- certificate: 28 judge-confirmable blob topics were certified AND promoted,
-- and the nightly overmerge sweep missed all 28 (its measured blind spots:
-- single-country + within-category fusions). The court alone cannot carry
-- promotion. This stamp composes a SECOND, independent veto:
--   - scripts/detect_overmerge.py stamps NOW() on every topic its DeepSeek
--     judge confirms as a fusion (active or candidate), and NULLs it on
--     topics it re-evaluates and finds clean;
--   - scripts/project_dynamic_topics.py refuses candidate->active promotion
--     while the stamp is FRESH (<7 days — staleness horizon so an old stamp
--     on a topic whose membership has since re-formed cannot block forever;
--     the nightly sweep re-stamps a still-fused topic, so a real blob never
--     goes stale).
-- Reversible: the column is inert until both scripts ship; NULL = never
-- confirmed (or confirmed clean on re-evaluation).
ALTER TABLE dynamic_topics
    ADD COLUMN IF NOT EXISTS blob_confirmed_at timestamptz;

COMMENT ON COLUMN dynamic_topics.blob_confirmed_at IS
    'Stamped NOW() by the overmerge confirmer (detect_overmerge --write) when '
    'its judge confirms this topic is a fusion of distinct stories; NULLed '
    'when the confirmer re-evaluates the topic and finds it clean. A topic '
    'with a fresh stamp (<7d) cannot promote candidate->active.';
