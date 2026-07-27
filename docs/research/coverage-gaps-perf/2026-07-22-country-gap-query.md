# Country coverage-gap query: 31–113s → 33–55ms

**Date:** 2026-07-22 · **Scope:** `_COUNTRY_GAPS_SQL` (`app/services/country_edition.py`;
canonical `COUNTRY_GAPS_SQL` in `app/services/coverage_gaps.py` on the
under-the-radar-gaps branch) · **Migration:** `090_coverage_gap_indexes.sql`
(applied to prod 2026-07-22) · **Status:** shipped, payload proven identical

Everything below is measured against production data, not inferred.

---

## 1. The problem, measured

| Lane | Before |
|---|---|
| Global coverage-gap query | 12.8s cold / 0.10s warm |
| **Country** coverage-gap query | **31s / 63s / 70s** across three consecutive local runs |
| `GET /api/v2/country-edition?cc=US` (Fly) | **113s** |

The new L2 "Under the Radar" dock lens bounds itself at a 10s wall clock / 8s
query timeout — correctly, since a 113s query pinning 1 of only 10 pool
connections is a self-inflicted DoS. So the country lane rendered an honest
"could not be measured" instead of the gaps. The bound was right; the query was
wrong. `country_edition.py` runs the same SQL with **no** timeout, so it simply
waited 113s — a pre-existing production problem, not a regression from the new
work.

### Substrate

| | rows | heap | indexes |
|---|---|---|---|
| `signals_v2` | 1,064,557 (7-day retention) | 1146 MB | 1814 MB |
| `signal_topic_assignments` | 91,425 (**12,526 in the 24h window**) | 38 MB | 40 MB |

`shared_buffers` = **256 MB**, `effective_cache_size` = 768 MB, heap cache hit
ratio 80%. The working set is ~12× the buffer cache — this is *why* the query
"does not warm". `random_page_cost` = **1.1** (tuned for local SSD) while a
random read on this storage measured **~5.6 ms**; the planner therefore treats
heap-touching plans as nearly free, which drives the bad plan choices below.

### Baseline `EXPLAIN (ANALYZE, BUFFERS)`

```
Nested Loop  (actual time=3.322..1565.082 rows=1182 loops=2)
  ->  Parallel Seq Scan on signal_topic_assignments a   (rows=6263, Rows Removed by Filter: 39450)
        Buffers: shared hit=979 read=3910
  ->  Index Scan using signals_v2_pkey on signals_v2 s  (actual time=0.216..0.216 rows=0 loops=12526)
        Filter: (country_code = 'US'), Rows Removed by Filter: 1
        Buffers: shared hit=45931 read=5431
```

Two independent structural defects, not one:

1. **`signal_topic_assignments` has no index on `assigned_at`** → the window
   predicate seq-scans all 91k rows on every call, global lane included.
2. **12,526 random PK probes into a 1.1 GB heap**, each fetching a row only to
   discard it (`rows=0`, `Rows Removed by Filter: 1`). At ~5.6 ms cold that is
   ~37s (the run above is partly warm at 1.6s; cold it is the 31–70s measured).

---

## 2. Candidates tried, and what each measured

### (b) Composite index on `signals_v2 (country_code, timestamp)` — already existed
`idx_signals_v2_country_time (country_code, timestamp DESC)` was **already
present** and the planner still refused it. Forcing the country-driven direction
(`enable_nestloop=off`) was **far worse: 137s, read=73,419** — it scans all
146k US signals *with* heap fetches. The planner was right; the cost is touching
the `signals_v2` heap **at all**, in either direction. So the fix is not "join
the other way" — it is "never touch the heap".

### (b′) Covering index — the actual lever
`signals_v2` is 89.4% all-visible (autovacuumed same day), so index-only scans
are viable. `(id) INCLUDE (country_code)` turns each probe into an Index Only
Scan: **probe cost 0.216ms → 0.010ms, heap fetches 12,526 → 1,234** (exactly the
~10% predicted by the all-visible ratio). US: 1,597ms → **230ms**.

Plus `(assigned_at) INCLUDE (signal_id, topic_id, gate_kept, gate_score)` on
`signal_topic_assignments` — kills defect 1. The 146ms seq scan becomes a
**4ms** index-only scan.

**Column order is load-bearing.** The country-leading variant
`(country_code, id)` was also built and measured, and it is **worse**: it lures
the planner into driving from the country side, scanning ~50k index entries with
~5,700 heap fetches. Cold: **IN 14.9s, GB 12.6s**. Forcing the id-driven plan for
the same GB query gave **31.8ms** with 1,570 heap fetches and `read=65`. The
index was dropped again; migration 090 documents "do not re-add".

The id-driven plan's cost is proportional to the **assignment window** (~12.5k,
constant) rather than to the country's signal volume (up to 146k) — the right
invariant for a global product.

### (a) Country+time predicate on `signals_v2` — rejected on correctness
Adding `s.timestamp > NOW() - …` would let `(country_code, timestamp)` serve the
filter, but `a.assigned_at` and `s.timestamp` are different clocks: an assignment
made inside the window can reference an older signal. It is not provably
result-preserving, so it was not pursued.

### The residual: plan instability for small countries
With the indexes alone, 10 of 12 countries ran at a flat ~31ms, but **CO took
10,248ms** — the planner switched to `Bitmap Heap Scan on signals_v2` for smaller
countries (6,156 rows scattered across the 1.1 GB heap = 6,156 cold random
reads). `EXISTS` did **not** fix it (PG rewrites it into a hash semi-join and
picks the same bitmap scan).

**Fix: a correlated scalar subquery**, which the planner *cannot* pull up into a
join, pinning the one good plan:

```sql
AND (SELECT s.country_code FROM signals_v2 s WHERE s.id = a.signal_id) = $2
```

Same index-only probe for **every** country, 0.002ms × 12,862 loops.
CO: 10,248ms → **35.5ms**.

---

## 3. Equivalence proof (not eyeballed)

`signals_v2.id` is the primary key, so the original join matched **at most one**
row per assignment and projected **no** column of `s` — i.e. it was already a
semi-join. The subquery reproduces every branch:

| case | original join | scalar subquery |
|---|---|---|
| signal in country `$2` | row kept | value = `$2` → kept |
| signal in another country | filtered out | value ≠ `$2` → excluded |
| **no matching signal** (retention deletes signals; assignments linger) | inner join drops it | returns NULL → `NULL = $2` → excluded |
| `country_code IS NULL` | `NULL = $2` → excluded | NULL → excluded |
| duplicate signals | impossible (PK) | impossible (PK) |

Empirically, two independent checks:

1. **Exhaustive, all countries at once.** `HAVING` / `ORDER BY` / `LIMIT` are
   textually identical in both forms, so if the grouped aggregates match, the
   payload matches. A symmetric-difference `EXCEPT` over
   `(country, slug, label, raw, verified, scored)` for the full 24h window
   returned **0 rows**.
2. **End-to-end payload diff**, full query including `HAVING`/`ORDER`/`LIMIT`,
   15 countries (US CO TR IN BR GB FR DE RU UA VE NG PK ID MX):
   **all IDENTICAL, 0 diffs.**

Also verified under **bound parameters** (asyncpg binds `$1/$2/$3`; all EXPLAINs
above used literals). A `PREPARE`d statement executed 7× — past the point where
PostgreSQL may switch to a generic plan — kept the same Index Only Scan at
33–172ms. The plan does not degrade when the statement is cached.

---

## 4. After

Server-side execution time, 24h window, prod data:

| Country | Before | After (warm) |
|---|---|---|
| US | 31–70s (113s in prod) | **32 ms** |
| CO | 10,248 ms | **36 ms** |
| IN | 14,866 ms | **42 ms** |
| GB | 12,608 ms | **41 ms** |
| VE | 1,820 ms | **36 ms** |
| TR / BR / FR / DE / RU / UA / NG | 3.7–7.5s | **31–57 ms** |

**Bonus — the global lane** (untouched SQL) also benefits from the `assigned_at`
index, since it had the same seq scan: **12.8s cold / 0.10s warm → 12.2 ms**.

Cost: 32 MB + 5.3 MB, against `signals_v2`'s existing 1814 MB of indexes.

Tests: `tests/test_country_edition.py` **12 passed**. The other branch's
`tests/test_coverage_gaps.py` asserts `sql == COUNTRY_GAPS_SQL` (identity against
the constant, not a literal), so changing the constant does not break it.

---

## 5. Honest residual: the cold call

Steady state is 33–55ms, but a **fully cold** call is still slow. Measured via
asyncpg on a fresh connection: US **53.9s** once, and 11.8s on another run, while
every subsequent country in the same pass ran at ~120ms.

This is not a plan regression (§3 confirms plan stability) — it is
`shared_buffers` = 256 MB against a ~3 GB working set. The 12,149 probes touch
essentially every leaf page of the 32 MB index (~4k pages) plus ~1.2k heap pages;
cold at ~5 ms/page that is tens of seconds. Every country probes the *same* 12.8k
assignment ids, so the first call warms the pages and the rest ride free.

**So the 8s timeout can still fire on the first call after an eviction.** The
shipped fix removes ~99.9% of the steady-state cost and is strictly safe, but it
does not make the working set cache-resident. That is what §6 is for.

---

## 6. (c) Denormalizing `country_code` onto `signal_topic_assignments` — measured, recommended as follow-up

Measured on a real scratch table (`91,761` rows, built from the join, indexed
`(assigned_at) INCLUDE (country_code, topic_id, gate_kept, gate_score)`, then
dropped):

| | buffers touched | time |
|---|---|---|
| Shipped (scalar subquery + indexes) | **39,233** | 33–55 ms |
| Denormalized | **~850** (max `read=90`) | **5–7 ms** |

Total object size **12 MB** — it fits in the 256 MB cache and *stays* there,
which is precisely the failure mode §5 describes. That is a 46× reduction in
buffers touched and a further ~7× on warm latency, and it removes `signals_v2`
from the query entirely.

**Worth it — but it is a separate change, not a drop-in**, because:

- it needs a writer contract: every producer of `signal_topic_assignments` must
  populate `country_code`;
- it introduces a real staleness hazard. `signals_v2.country_code` **is**
  corrected retroactively in this codebase (the geo-mistag title-only fix +
  71-row backfill, the 1,419 `RP→PH`/`CG→CD` FIPS backfill). A denormalized copy
  would silently diverge from the join-based truth unless refreshed.

Recommendation: ship §2 now (done — zero schema change, provably identical
payload), and treat denormalization as the follow-up that closes the cold-call
gap, with a defined backfill/refresh story.

Cheaper mitigations if the cold call proves to bite in practice: `pg_prewarm` is
**available but not installed** (v1.2) and could warm `idx_signals_v2_id_country`
after a restart; and `random_page_cost = 1.1` badly misdescribes this storage
(~5.6 ms random reads) — raising it would stop the planner preferring
heap-touching plans in general, but that is a global setting and needs its own
measured change.

---

## 7. Where the change landed

The fix is in the canonical `app/services/coverage_gaps.py::COUNTRY_GAPS_SQL` —
the ONE definition shared by `GET /api/v2/country-edition` (via
`services/country_edition.py`) and `GET /api/v2/attention/coverage-gaps` (via
`routers/attention_threads.py`). Both surfaces get the fix from the single
constant; neither call site changed.

Sequencing note: this work was measured against the pre-refactor tree, where the
SQL still lived inline as `_COUNTRY_GAPS_SQL` in `country_edition.py`. The
under-the-radar-gaps refactor merged to `v3-intel-layer` first, so the change was
re-applied to the canonical constant before landing. The SQL text is identical
either way — only its home moved.

`GLOBAL_GAPS_SQL` needs **no** change (it never touches `signals_v2`) and gets
the 12.8s → 12.2ms win for free from the `assigned_at` index.

## 8. NOT FIXED — `EXTENDED_RECEIPTS_SQL` is now the binding constraint

Measured end-to-end through the real service path (`fetch_coverage_gaps`,
`timeout=8.0`, prod, on the merged tree) — i.e. what the dock lens actually calls:

| cc | full service path | of which gaps query |
|---|---|---|
| US | **TimeoutError at 8,002 ms** | 33–55 ms |
| CO | **TimeoutError at 8,593 ms** | 36 ms |
| IN | 19,291 ms (5 gaps, 9 receipts) | 42 ms |
| GB | 11,001 ms (6 gaps, 10 receipts) | 41 ms |
| NG | 10,812 ms (6 gaps, 15 receipts) | ~40 ms |
| TR / BR / VE | 7,555 / 3,327 / 4,153 ms | 31–57 ms |
| **global** | **635 ms** | 12 ms |

The gaps query is no longer the problem — **the receipts lookup is**. Two
distinct causes, both real:

1. **Serial per-slug heap I/O.** `EXTENDED_RECEIPTS_SQL` projects real heap
   columns (`headline`, `source_name`, `source_url`), so index-only cannot apply.
   Measured for `fuel-subsidy-unrest`: `Index Scan on signals_v2 … rows=1
   loops=31` at **13 ms per row** = ~400 ms for one slug, and
   `fetch_extended_receipts_by_slug` loops **serially over up to 6 slugs**.
2. **The cold primary query still can exceed 8s** (§5). US/CO failing at exactly
   the timeout is the primary gaps query on a cold connection — it is
   deliberately *not* wrapped in try/except (callers must distinguish "no gaps"
   from "query failed"), so it propagates.

Note the shape: the global lane is 635 ms because global gaps have few slugs;
the country lane fans out to 6.

Levers, in order of value (none applied here — each is a real change, not a
tweak, and this pass was scoped to the gaps query):

- **Batch the 6 per-slug queries into one.** One round trip instead of six, and
  it lets the planner use a bitmap heap scan — which *sorts* page access instead
  of issuing ~200 independent random probes. Requires reworking
  `fetch_extended_receipts_by_slug`'s deliberate per-slug error isolation (the
  "delight lesson" guard), so it needs its own review.
- **Denormalization (§6)** removes cause 2 outright.
- Shrinking `LIMIT 40` is **not** safe: `pick_extended_receipts` needs the pool
  to dedupe syndicated copies by headline and drop junk *before* taking K=3, so a
  smaller pool can change the selected receipts.

Until one of those lands, a country focus can still exceed the 10s wall clock —
the honest "could not be measured" state may still appear for large countries,
now driven by receipts rather than by the gaps query.

### Unrelated finding
`idx_signals_v2_persons_text_trgm` is **INVALID** (`pg_index.indisvalid = false`)
— a leftover from a failed `CREATE INDEX CONCURRENTLY`. It is unusable for reads
but still maintained on every write. Pre-existing, not touched here; worth a
`DROP INDEX CONCURRENTLY`.
