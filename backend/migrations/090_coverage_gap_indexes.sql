-- Coverage-gap query perf (measured 2026-07-22).
--
-- The COUNTRY-scoped coverage-gap query measured 31s/63s/70s locally and 113s
-- in production (GET /api/v2/country-edition?cc=US). EXPLAIN (ANALYZE, BUFFERS)
-- showed two structural problems, both fixed here:
--
--   1. signal_topic_assignments had NO index on assigned_at, so the window
--      predicate drove a Parallel Seq Scan over the whole table (91k rows,
--      4,889 buffers) on EVERY call -- global lane included.
--
--   2. The country join probed signals_v2 by primary key once per windowed
--      assignment (12,526 loops). Each probe fetched a heap row from a 1.1 GB
--      table only to discard it (`Rows Removed by Filter: 1`) -- 12,526 cold
--      random reads at ~5.6 ms each = ~37s of the wall clock.
--
-- Fix (2) is a COVERING index: with country_code carried in the index payload,
-- the probe becomes an Index Only Scan and never touches the signals_v2 heap
-- except for the ~10% of pages not yet all-visible (measured: 12,526 heap
-- fetches -> 1,234). Probe cost fell 0.216ms -> 0.010ms.
--
-- NOTE the column order: (id) INCLUDE (country_code), NOT (country_code, id).
-- The country-leading variant was built and MEASURED, and it is WORSE: it lures
-- the planner into driving from the country side, scanning ~50k index entries
-- with ~5,700 heap fetches (IN 14.9s / GB 12.6s cold) instead of the 12.5k cheap
-- probes the id-leading index serves. It was dropped again. Do not re-add it.
--
-- Measured effect (24h window, prod data):
--   country lane  US 31-70s -> 32ms   CO 10,248ms -> 36ms   (warm 17-65ms)
--   global lane   12.8s cold / 0.10s warm -> 12.2ms         (from index 1 alone)
-- Cost: 32 MB + 5.3 MB against signals_v2's existing 1,814 MB of indexes.
--
-- Already applied to production 2026-07-22 via CREATE INDEX CONCURRENTLY.
-- Both are additive and reversible (DROP INDEX CONCURRENTLY <name>).
-- Full write-up: docs/research/coverage-gaps-perf/2026-07-22-country-gap-query.md

-- 1. Kills the seq scan of signal_topic_assignments. Covering, so the windowed
--    read is an Index Only Scan (12,862 rows in ~4ms).
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sta_assigned_at_cover
    ON signal_topic_assignments (assigned_at)
    INCLUDE (signal_id, topic_id, gate_kept, gate_score);

-- 2. Makes the country filter answerable WITHOUT touching the signals_v2 heap.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_id_country
    ON signals_v2 (id)
    INCLUDE (country_code);
