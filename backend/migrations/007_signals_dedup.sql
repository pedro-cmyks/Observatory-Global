-- Migration 007: Deduplicate signals_v2 and add unique constraint on source_url
-- Run ONCE on the live database.
--
-- Why: ON CONFLICT DO NOTHING had no unique target, so every GDELT re-crawl of
-- the same article created a duplicate row. This inflates counts and wastes disk.
--
-- Strategy: keep the row with the lowest id per source_url (first insert wins),
-- then add a unique index so future inserts deduplicate automatically.

BEGIN;

-- Step 1: Remove duplicate rows, keeping the oldest insert per URL.
-- Only runs if there are duplicates; safe to run on clean DB.
DELETE FROM signals_v2
WHERE id NOT IN (
    SELECT MIN(id)
    FROM signals_v2
    WHERE source_url IS NOT NULL
    GROUP BY source_url
);

-- Step 2: Add unique index on source_url (NULLs are excluded from unique indexes
-- in PostgreSQL, so rows without a URL can still duplicate — acceptable).
CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_v2_source_url_unique
    ON signals_v2 (source_url)
    WHERE source_url IS NOT NULL;

COMMIT;
