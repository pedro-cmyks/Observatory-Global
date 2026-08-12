-- The seal's status stops being an unreachable binary (T3.2, policy a+b).
--
-- 075 constrained status to ('ready','degraded'). `ready` required UNANIMOUS
-- per-story-node attribution across 12 story nodes while per-node coverage
-- runs ~50% (#184 NER throughput, #238 subject geography), so 0.5^12 made the
-- pass rate ~0 and all 25 sealed editions carried 'degraded' — the Brief fell
-- to live threads and the seal's Pareto selection never reached a reader.
-- Status is now GRADED from the measured readiness fractions:
--
--   sealed_full    every required dimension at or above the full bar (0.55)
--   sealed_partial at or above the partial bar (0.40), or evidence incomplete
--   sealed_thin    below the partial bar, or a dimension with nothing measured
--
-- Bars are the tertiles of the pooled who+where histogram over the 21
-- non-empty sealed editions, each placed in an adjacent EMPTY interval so a
-- one-node wobble cannot flip a grade. See app/services/edition_status.py and
-- docs/research/brief-daily/2026-08-12-m0-measurement.md (addendum §D).
--
-- The legacy values stay ADMITTED: 25 rows were sealed under the old binary
-- and are remapped read-side (normalize_stored_status), never rewritten here —
-- a backfill would assert a grade nobody measured at seal time.
-- Reversible: restore the 075 CHECK (no stored row uses a graded value yet).

ALTER TABLE atlas_daily_editions
    DROP CONSTRAINT IF EXISTS atlas_daily_editions_status_check;

ALTER TABLE atlas_daily_editions
    ADD CONSTRAINT atlas_daily_editions_status_check
    CHECK (status IN (
        'sealed_full', 'sealed_partial', 'sealed_thin',
        -- pre-2026-08-12 rows, never emitted again
        'ready', 'degraded'
    ));

COMMENT ON COLUMN atlas_daily_editions.status IS
    'Graded seal (atlas-edition-status-v1): sealed_full|sealed_partial|sealed_thin from measured readiness fractions; ready|degraded are legacy pre-graded rows. Reasons ride completion.status_reasons. Never a night-voiding marker — that is SEAL_FAILED in the reliability ledger.';
