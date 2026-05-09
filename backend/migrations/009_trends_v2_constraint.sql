-- Migration 009: Add hour_bucket column + named constraint to trends_v2
-- Problem: ingest_trends.py uses ON CONFLICT ON CONSTRAINT
--   trends_v2_country_code_keyword_hour_bucket_key which did not exist.
-- The table had a per-exact-timestamp UNIQUE that never deduped within a cycle.
--
-- Fix: add a regular hour_bucket column (populated by INSERT, not generated —
-- GENERATED ALWAYS AS fails because date_trunc on timestamptz is not immutable),
-- then add the named UNIQUE constraint the ingest code expects.

BEGIN;

-- 1. Add hour_bucket column (nullable initially for safe migration)
ALTER TABLE trends_v2
    ADD COLUMN IF NOT EXISTS hour_bucket TIMESTAMPTZ;

-- 2. Backfill existing rows
UPDATE trends_v2
SET hour_bucket = date_trunc('hour', timestamp)
WHERE hour_bucket IS NULL;

-- 3. Drop old exact-timestamp unique constraint (superseded by hour_bucket one)
ALTER TABLE trends_v2
    DROP CONSTRAINT IF EXISTS trends_v2_country_code_keyword_timestamp_key;

-- 4. Add the named constraint ingest_trends.py expects
ALTER TABLE trends_v2
    DROP CONSTRAINT IF EXISTS trends_v2_country_code_keyword_hour_bucket_key;

ALTER TABLE trends_v2
    ADD CONSTRAINT trends_v2_country_code_keyword_hour_bucket_key
    UNIQUE (country_code, keyword, hour_bucket);

COMMIT;
