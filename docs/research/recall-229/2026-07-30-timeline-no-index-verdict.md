# Ubiquitous-name timeline residual: NO INDEX FIXES IT — measured verdict

**Date:** 2026-07-30 · read-only prod measurement · nothing applied, no migration written
**Context:** the person-timeline fix (`b040fddc`) left an honest residual: `trump`
(26-27K rows, ~23K heap blocks) still exceeds the 3s channel budget at 168h. The
recorded follow-up hypothesis was "a composite index that lets the planner BitmapAnd
persons with timestamp". **That hypothesis is refuted.**

## The evidence

| needle | window | plan | heap blocks | time |
|---|---|---|---|---|
| trump | 24h | **BitmapAnd(persons_trgm, timestamp)** — already fires TODAY | 4,211 | **596ms** |
| trump | 72h | Bitmap Heap + Filter (BitmapAnd declined) | 23,096 | 6.17s |
| trump | 168h | Bitmap Heap + Filter | ~23,127 | 6.3-8.2s |
| putin | 168h | same shape | 4,980 | 341ms |

1. **BitmapAnd already happens** with zero schema changes — `idx_signals_v2_timestamp`
   exists and combines with the trigram index at 24h. A "composite" of a GIN trigram
   expression and a btree range is not a buildable object anyway; BitmapAnd IS the
   mechanism for combining them.
2. **At 168h there is nothing to exploit:** the hot table spans ~179h, so a 168h window
   is ~94% of the corpus — the timestamp predicate has ~0 selectivity and the planner
   correctly declines the second bitmap. The cost is the lossy trigram recheck: ~23K
   heap blocks, mandatory, no index shape changes it.

## Real bug found in passing (72h)
At 72h (~40% of the span — genuinely selective) the planner still picks the bad plan
because the trigram LIKE selectivity estimator gives `trump` and `putin` an IDENTICAL
1,611-row estimate (real: 27,450 vs 5,438) — a length-based fallback, not per-value
stats. Fix if that window matters: `ALTER INDEX idx_signals_v2_persons_text_trgm ALTER
COLUMN 1 SET STATISTICS <n>; ANALYZE signals_v2;` — **a statistics fix, not an index.**
Does not help 168h regardless.

## Honest alternatives for 168h (neither implemented)
1. **Bounded partial aggregation:** cap the scan (`ORDER BY timestamp DESC LIMIT
   ~10-15k`) before bucketing; label the channel `partial` — a lower bound for
   high-volume names, honestly stated. Same pattern as `_CANDIDATE_POOL_LIMIT`.
2. **`person_daily_mentions` rollup** (durable): a periodic job mirroring
   `country_hourly_v2`'s relationship to the country channel — O(few rows) for any
   name at any window. Bigger build; the right long-term answer if person timelines
   become load-bearing.

Sixth measured verdict of the arc; the follow-up recorded in `b040fddc` should not be
built as written.
