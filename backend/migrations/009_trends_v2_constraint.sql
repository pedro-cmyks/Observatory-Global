-- Migration 009: Add hour_bucket generated column + named unique constraint to trends_v2
-- Needed by ingest_trends.py which uses:
--   ON CONFLICT ON CONSTRAINT trends_v2_country_code_keyword_hour_bucket_key
-- PostgreSQL cannot add a named UNIQUE constraint on an expression directly,
-- so we add a GENERATED ALWAYS AS stored column and constrain that.

BEGIN;

-- Add generated hour_bucket column (if absent)
ALTER TABLE trends_v2
    ADD COLUMN IF NOT EXISTS hour_bucket TIMESTAMPTZ
    GENERATED ALWAYS AS (date_trunc('hour', timestamp)) STORED;

-- Add the named UNIQUE constraint the ingest code expects
ALTER TABLE trends_v2
    DROP CONSTRAINT IF EXISTS trends_v2_country_code_keyword_hour_bucket_key;

ALTER TABLE trends_v2
    ADD CONSTRAINT trends_v2_country_code_keyword_hour_bucket_key
    UNIQUE (country_code, keyword, hour_bucket);

COMMIT;
