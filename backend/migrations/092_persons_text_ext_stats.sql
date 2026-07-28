-- 092: extended expression statistics for the persons-text trigram predicate.
-- ALREADY APPLIED to prod 2026-07-28 (this file is the versioned record).
--
-- MEASURED (docs/research/recall-229/2026-07-30-timeline-trgm-stats-followup.md):
-- the planner NEVER consults the mig-090 index's own expression statistics,
-- because idx_signals_v2_persons_text_trgm is a PARTIAL index (WHERE persons
-- IS NOT NULL) and examine_variable() skips partial-index stats — their sample
-- covers only the predicate subset. So every `... LIKE '%name%'` estimate fell
-- through to like_selectivity()'s pattern-shape heuristic: 0.2^len × 5, i.e.
-- EVERY 5-letter name ('trump', 'putin') estimated identically (1,617 rows vs
-- real 27,535 / 5,467), and at the 72h window the planner declined a BitmapAnd
-- with idx_signals_v2_timestamp it should have taken. Raising the INDEX column
-- statistics target was measured and REFUTED — the stats grew 10× and the
-- estimate did not move, because they are never read.
--
-- A CREATE STATISTICS object on the same expression is NOT partial, so the
-- planner does read it. Measured after ANALYZE: trump estimates 27,805,
-- putin 3,766, maduro 111 (three orders of magnitude of differentiation, was
-- uniform 1,617) and the 72h trump plan flips to
-- BitmapAnd(persons_trgm, timestamp): heap blocks 23,096 -> ~11,400,
-- execution 6.17s -> 2.7s (1 parallel worker) / 5.9s (serial, cold cache).
--
-- Serves every query spelled on the mig-090 expression: the person channels of
-- /api/v2/focus/{ref}/timeline (focus_timeline.py) and /search/thread's
-- persons branch (search.py).
--
-- NOTE: statistics objects populate on ANALYZE — run `ANALYZE signals_v2;`
-- after applying (takes ~1-2 min on the ~1M-row hot table; autovacuum
-- maintains it afterwards). Reversal: DROP STATISTICS stats_signals_v2_persons_text;

CREATE STATISTICS IF NOT EXISTS stats_signals_v2_persons_text
  ON (f_unaccent(lower(f_arr_text(persons))))
  FROM signals_v2;

-- 1000 MCVs / 1001 histogram bounds — the LIKE estimator matches the pattern
-- against these values, so resolution here is what differentiates a ubiquitous
-- name from a rare one. Sample cost: 300 × 1000 rows per ANALYZE, measured
-- ~60-110s on prod — acceptable for a nightly autovacuum cadence.
ALTER STATISTICS stats_signals_v2_persons_text SET STATISTICS 1000;

-- ANALYZE signals_v2;  -- required once, uncomment when running by hand
