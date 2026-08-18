-- 102_dynamic_topic_subject_coherence.sql
--
-- The grab-bag coherence measurement, STORED, so LIVE /threads rows can carry
-- the mark (#257 serving half). Until now `measure_subject_geography_coherence`
-- (contract atlas-subject-coherence-v1, app/services/subject_geography.py) ran
-- only at seal time (investigation_graph.py -> package.gaps
-- `subject_geography_grab_bag:<label>`), so the live Brief and console could
-- not mark a mixed-geography story until the nightly publication — the payload
-- hole lib/cardWarnings.ts documents.
--
-- MEASURED before choosing this lane (2026-08-18, bench over 40 rows x 24
-- receipts, multilingual headlines): running the measurement inline in
-- `assemble_dynamic_thread` adds ~3.4 ms/row — the full _COUNTRY_PATTERNS +
-- _NATIVE_COUNTRY_PATTERNS regex tables per headline, uncached — i.e. ~137 ms
-- median (~427 ms p95) on a 40-row list, ~2.7x the 50 ms serving budget. So
-- the compute leaves the request path, exactly like migs 091/098/101:
--
--     backend/scripts/compute_subject_coherence.py --execute  (off-request)
--         -> dynamic_topic_subject_coherence   (one JSONB result per topic)
--             -> /threads: one guarded ANY($1) PK read per list
--                (thread_intelligence._fetch_subject_coherence_map), serving
--                `subject_geography_grab_bag: true|false|null` per row.
--
-- A topic without a stored row serves null — honest absence, never
-- false-by-default. Serving guards on to_regclass, so this migration being
-- unapplied degrades to all-null (the mig-087 crash class, avoided by
-- construction).
--
-- Server-only via asyncpg; no Supabase client key touches it. RLS enabled
-- with no policies = deny-all for client roles (082-style, house rule).
--
-- Reversible: DROP TABLE dynamic_topic_subject_coherence;

CREATE TABLE IF NOT EXISTS dynamic_topic_subject_coherence (
    -- dynamic_topics.id (BIGSERIAL). No FK: topics are pruned/re-founded by
    -- their own lifecycle and a stale row here is inert (never joined once
    -- the id stops serving); the compute pass refreshes/deletes as receipts
    -- move.
    topic_id    BIGINT PRIMARY KEY,
    -- The full atlas-subject-coherence-v1 result (status, grab_bag,
    -- significant_countries, cooccurrence, reason_codes) — glass-box, not
    -- just the bool the row serves.
    result      JSONB NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE dynamic_topic_subject_coherence IS
    'Stored atlas-subject-coherence-v1 measurement per dynamic topic '
    '(scripts/compute_subject_coherence.py). Serving reads it pure '
    '(thread_intelligence._fetch_subject_coherence_map) to mark live '
    '/threads rows subject_geography_grab_bag; inline compute measured '
    '~137 ms per 40-row list (2026-08-18), over the 50 ms budget.';

ALTER TABLE dynamic_topic_subject_coherence ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON dynamic_topic_subject_coherence FROM anon;
REVOKE ALL ON dynamic_topic_subject_coherence FROM authenticated;
