# Trigram-stats follow-up: the registered fix REFUTED, the root cause found, the real fix shipped

**Date:** 2026-07-28 (follow-up to `2026-07-30-timeline-no-index-verdict.md`, same arc)
**Applied to prod:** `ALTER INDEX … SET STATISTICS 1000` (tested, refuted, **reverted**) →
`CREATE STATISTICS stats_signals_v2_persons_text` (works, **kept**, mig 092 records it)
**Postgres:** 17.6 · `signals_v2` ≈ 1.01M rows, ~all with `persons IS NOT NULL`

## Registered experiment: index statistics target — REFUTED

The 07-30 verdict's recorded fix was `ALTER INDEX idx_signals_v2_persons_text_trgm
ALTER COLUMN 1 SET STATISTICS 1000; ANALYZE signals_v2;`. Applied and measured:

| | before (target 100) | after (target 1000) |
|---|---|---|
| index stats present | 39 MCVs / 101 hist bounds | 1000 MCVs / 1001 hist bounds |
| trump estimate (LIKE alone) | 1,611 | **1,617** |
| putin estimate | 1,611 | **1,617** |
| 72h trump plan | Bitmap Heap + Filter | **unchanged** |

10× stats resolution moved the estimate by 0.4% (reltuples drift) and left the two
names **identical**. Reverted (`SET STATISTICS -1`, re-ANALYZEd; index stats back at
default 100/101).

## Root cause: partial-index stats are never consulted

Two independent confirmations:

1. **The stats can't matter.** `idx_signals_v2_persons_text_trgm` is a **partial**
   index (`WHERE persons IS NOT NULL`). Postgres's `examine_variable()` skips
   expression statistics from partial indexes — their ANALYZE sample covers only the
   predicate's subset, so they'd bias whole-table estimates. The index's pg_stats row
   exists (ANALYZE writes it) but the planner never reads it, at any target.
2. **The arithmetic names the actual estimator.** 1,617 / 1,011,571 rows = 0.0016 =
   **0.2⁵ × 5** — `like_selectivity()`'s pattern-shape heuristic exactly
   (`FIXED_CHAR_SEL`^5 literal chars × `FULL_WILDCARD_SEL`). The estimate is a pure
   function of the pattern's **length**: every 5-letter name gets 1,617. This is the
   07-30 artifact's "length-based fallback", now mechanically identified.

So the 72h BitmapAnd was declined because the planner thought `%trump%` matches 1,617
rows — cheap enough to fetch straight — when it really matches 27,535.

## The fix that works: a non-partial statistics object on the same expression

```sql
CREATE STATISTICS stats_signals_v2_persons_text
  ON (f_unaccent(lower(f_arr_text(persons)))) FROM signals_v2;
ALTER STATISTICS stats_signals_v2_persons_text SET STATISTICS 1000;
ANALYZE signals_v2;  -- ~60-110s measured
```

A `CREATE STATISTICS` object is not partial, so `examine_variable()` does read it and
the LIKE estimator matches the pattern against its 1000 MCVs + 1001 histogram bounds.

**Estimates (LIKE condition alone, real count in parens):**

| needle | before | after ext-stats |
|---|---|---|
| trump | 1,611 | **27,805** (27,535) |
| putin | 1,611 | **3,766** (5,467) |
| maduro | — | **111** |

Three orders of magnitude of differentiation where there was none.

**Plans + timings (person-channel ch1 query shape from `focus_timeline.py`):**

| query | before plan | before time | after plan | after time |
|---|---|---|---|---|
| trump 72h | Bitmap Heap + Filter, 23,096 heap blocks | 6.17s | **BitmapAnd(trgm, timestamp)**, ~11,400 heap blocks | **2.72s** (1 worker) / 5.95s (serial, cold) |
| trump 24h | BitmapAnd (already) | 596ms | BitmapAnd, unchanged shape | 133ms (warm) |
| trump 168h | Bitmap Heap + Filter | 6.3-8.2s | same shape, now **parallel** (honest 15K-row estimate) | 4.12s |
| putin 72h | same misestimate, plan happened to be fine | ~0.3-1.4s | plain Bitmap Heap (correctly — 2.5K rows) | 1.16-1.37s |

## Honest residuals

- **trump 72h straddles the 3s channel budget, it does not clear it.** The plan is
  now right; the residual is heap I/O under Supabase buffer pressure — even
  back-to-back runs re-read ~10K blocks (`shared read` stays high, `written>0` =
  eviction). 2.72s when a parallel worker launches, ~6s serial when none does.
  Roughly a 2× improvement, not a category change.
- **168h stays over budget (4.1s)** — as the 07-30 verdict said, no plan fixes a
  window that is ~94% of the corpus. The parallel plan (a side effect of the honest
  row estimate) did pull it down from 6.3-8.2s.
- Timings are cache-regime-dependent; treat the before/after **plan shapes and
  estimates** as the durable result, the wall clocks as one day's observation.
- The ext-stats object also serves `/search/thread`'s persons branch (same mig-090
  expression). Its ANALYZE cost: 300K-row sample, ~60-110s, absorbed by autovacuum.

## Verdict

The registered fix (index stats target) is **refuted and reverted** — not "1000 wasn't
enough" but *cannot work*: partial-index statistics are invisible to the planner.
The same-class replacement (extended expression statistics) is **measured working and
kept**: estimator differentiates names, 72h BitmapAnd fires, 24h/putin unregressed,
mig 092 versions the object. Seventh measured verdict of the arc.
