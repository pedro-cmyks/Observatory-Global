-- Migration 012: Geo validation — source origin country
-- Run ONCE in Supabase SQL editor.
--
-- Why: GDELT attributes signals to the country an article MENTIONS, not where
-- the source outlet is based. A US TV station covering Iran gets country_code=IR.
-- This adds source_origin_country to track outlet home country, enabling
-- downstream filtering and data-quality warnings in CountryBrief.

BEGIN;

ALTER TABLE signals_v2
    ADD COLUMN IF NOT EXISTS source_origin_country CHAR(2) DEFAULT NULL;

-- Index for join queries: "signals about X from sources based in Y"
CREATE INDEX IF NOT EXISTS idx_signals_origin_country
    ON signals_v2 (source_origin_country, timestamp DESC)
    WHERE source_origin_country IS NOT NULL;

-- For the mismatch query: country_code != source_origin_country
CREATE INDEX IF NOT EXISTS idx_signals_geo_mismatch
    ON signals_v2 (country_code, source_origin_country, timestamp DESC)
    WHERE source_origin_country IS NOT NULL
      AND country_code IS DISTINCT FROM source_origin_country;

-- Backfill RSS/ReliefWeb signals that already have source_country embedded
-- in their attribution (source_family IN ('rss','ngo') sourced from known outlets).
-- GDELT signals left NULL — will be populated by the updated ingest going forward.
UPDATE signals_v2
SET source_origin_country = 'US'
WHERE source_family = 'gdelt'
  AND source_name ILIKE ANY (ARRAY[
      '%cnn%', '%fox news%', '%foxnews%', '%msnbc%', '%nbc news%',
      '%abc news%', '%cbs news%', '%npr%', '%pbs%', '%ap%',
      '%bloomberg%', '%reuters%', '%washington post%', '%new york times%',
      '%nytimes%', '%wsj%', '%wall street journal%', '%usa today%',
      '%politico%', '%axios%', '%the hill%', '%huffpost%', '%vox%',
      '%buzzfeed%', '%vice%', '%time%', '%newsweek%', '%the atlantic%',
      '%new yorker%', '%slate%', '%salon%', '%breitbart%', '%daily beast%',
      '%daily wire%', '%epoch times%', '%oann%', '%newsmax%'
  ])
  AND source_origin_country IS NULL;

DO $$
DECLARE
    total_count   BIGINT;
    filled_count  BIGINT;
BEGIN
    SELECT COUNT(*) INTO total_count FROM signals_v2;
    SELECT COUNT(*) INTO filled_count FROM signals_v2 WHERE source_origin_country IS NOT NULL;
    RAISE NOTICE 'Migration 012 complete: % / % signals have source_origin_country', filled_count, total_count;
END $$;

COMMIT;
