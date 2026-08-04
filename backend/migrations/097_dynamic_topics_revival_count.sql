-- 097: re-revival cap counter (2026-08-04).
-- (Task spec named this "mig 096"; 096 was already taken by
-- 096_label_status_too_broad.sql from the same #261 arc — numbered 097.)
--
-- Re-census fresh cohort (docs/research/recall-229/2026-08-04-recensus-
-- fresh-cohort.md) measured VETTED revivals at 33.3% real: the residual
-- revival tail is sticky old identities (sport churn "Spain World Cup
-- Victory", old wars "Khamenei Funeral Threats", service buckets "Analyst
-- Rating Reiterations") that re-match promiscuously forever and whose labels
-- DO entail their old-life receipts. Two levers ship together:
--   1. label_court.py scopes a revived candidate's trial to topic_members
--      rows with assigned_at > revived_at (post-revival receipts, withhold
--      when starved) — no schema change;
--   2. this column: revivals since the last CLEAN promotion.
--      - project_dynamic_topics.persist()'s atomic revival UPDATE increments
--        it (same single statement as the revived_at stamp + court-column
--        reset — never a second WAN statement);
--      - a clean candidate->active promotion through the court gate resets
--        it to 0;
--      - next_state refuses to revive a deprecated/retired topic once
--        revival_count >= 3 (REVIVAL_CAP, frozen) — hard-retired by
--        exhaustion; its signals fall to other candidates or found new
--        identities (the landing program's job).
-- Reversible/inert: only written under ATLAS_LIFECYCLE_TICK_V2 (the only
-- regime that revives-to-candidate); legacy never touches it. Revert:
--   UPDATE dynamic_topics SET revival_count = 0;  -- or DROP COLUMN.
ALTER TABLE dynamic_topics
    ADD COLUMN IF NOT EXISTS revival_count int NOT NULL DEFAULT 0;

COMMENT ON COLUMN dynamic_topics.revival_count IS
    'Re-revival cap (2026-08-04): revivals (deprecated/retired -> candidate '
    'under the v2 lifecycle clock) since the last clean candidate->active '
    'promotion, which resets it to 0. At >= 3 (REVIVAL_CAP) a re-matching '
    'deprecated/retired topic no longer revives — hard-retired by exhaustion.';
