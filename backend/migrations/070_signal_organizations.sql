-- Migration 070: signals_v2.organizations — the WHO-orgs half of "which
-- entities are involved" (#251, J-audit 2026-07-02).
--
-- Surfaces answer WHO-people (persons) but signal-level ORG data never
-- existed — GKG's V2ENHANCEDORGANIZATIONS field was parsed away. This
-- mirrors the `persons` TEXT[] column so companies/agencies/armed-groups
-- flow per-signal into the subjects merge (classify_subject already types
-- ORG). Forward-only by design: backfill is optional (old GKG rows lose
-- nothing they had).

ALTER TABLE signals_v2
    ADD COLUMN IF NOT EXISTS organizations TEXT[] DEFAULT NULL;
