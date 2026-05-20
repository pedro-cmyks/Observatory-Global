-- Migration 008: Add source provenance fields to signals_v2
-- Run ONCE in Supabase SQL editor.
--
-- Why: Before activating new sources (RSS, ReliefWeb) every signal needs
-- identity fields so analysts can distinguish Reuters wire from iHeart
-- entertainment or Iranian state media from independent outlets.
-- Without this, all signals are identity-less regardless of origin.

BEGIN;

ALTER TABLE signals_v2
    ADD COLUMN IF NOT EXISTS source_family      VARCHAR(20)  DEFAULT 'gdelt',
    ADD COLUMN IF NOT EXISTS source_lang        CHAR(2)      DEFAULT 'en',
    ADD COLUMN IF NOT EXISTS geo_confidence     FLOAT        DEFAULT 0.85,
    ADD COLUMN IF NOT EXISTS attribution_method VARCHAR(30)  DEFAULT 'gdelt_gkg',
    ADD COLUMN IF NOT EXISTS is_state_media     BOOLEAN      DEFAULT FALSE;

-- source_family values: gdelt | gdelt_translated | rss | ngo | wire | state | independent | unknown
-- attribution_method values: gdelt_gkg | gdelt_gkg_translated | reliefweb_api | rss_feed

-- Index for filtering by source family (used by source framing UI, #77)
CREATE INDEX IF NOT EXISTS idx_signals_source_family
    ON signals_v2 (source_family)
    WHERE source_family IS NOT NULL;

-- Index for low-confidence geo signals (used by anomaly validation)
CREATE INDEX IF NOT EXISTS idx_signals_low_geo_confidence
    ON signals_v2 (country_code, timestamp DESC)
    WHERE geo_confidence < 0.7;

-- Index for state media filter
CREATE INDEX IF NOT EXISTS idx_signals_state_media
    ON signals_v2 (is_state_media, timestamp DESC)
    WHERE is_state_media = TRUE;

-- Backfill: mark all existing signals as coming from GDELT English
UPDATE signals_v2
SET
    source_family      = 'gdelt',
    source_lang        = 'en',
    geo_confidence     = 0.85,
    attribution_method = 'gdelt_gkg',
    is_state_media     = FALSE
WHERE source_family IS NULL OR source_family = 'gdelt';

-- Verify
DO $$
DECLARE
    total_count   BIGINT;
    tagged_count  BIGINT;
BEGIN
    SELECT COUNT(*) INTO total_count  FROM signals_v2;
    SELECT COUNT(*) INTO tagged_count FROM signals_v2 WHERE source_family IS NOT NULL;
    RAISE NOTICE 'Migration 008 complete: % / % signals tagged with provenance', tagged_count, total_count;
END $$;

COMMIT;
