# Embedding throughput fix — 2026-07-08

Branch `v3-intel-layer`. File: `backend/scripts/embed_hot_corpus.py`
(executed copy synced to `~/AtlasLocalWorker/backend/scripts/`).

## Symptom

The embedding substrate was starved: **161K signals ingested/24h → only ~1,025
embedded (0.6%)** → clustering saw a stale corpus → ~30 active dynamic stories
(0.04% of signals). Concrete proof: the Colombia "espriella" election story had
537 signals in 30d but only 97 (18%) embedded, so 82% of a real story could not
cluster.

The M1 `com.atlas.embed-hot-corpus` cron logged, **every run, non-fatally**:

```
asyncpg.exceptions.QueryCanceledError: canceling statement due to statement timeout
[embed-hot-corpus] embed step failed/timed out (non-fatal); continuing to attach/ETL/build
```

The runner is `|| echo ... (non-fatal)`, so the pipeline kept building
`topic_members` on the STALE embedding corpus while `signal_embeddings` never
refreshed — and shrank under the 7-day retention `DELETE`.

## Root cause (measured, two layers)

The Supabase **session-mode pooler** (host `...pooler.supabase.com:5432`) runs
under a role default `statement_timeout = 2min` (verified: `SHOW
statement_timeout` → `2min`).

1. **The `_pending_rows` megasort.** The old query did ONE `DISTINCT ON
   (s.headline) … ORDER BY s.headline` dedup over the whole 168h window
   (~700K rows; there is **no btree on `headline`**, only trigram GIN). Under
   cron-time DB load that text megasort exceeded 2min → killed → 0 pending → 0
   embedded. (With the timeout lifted it actually returns in ~7s — the cap was
   the killer, not the cost.)

2. **The HNSW inserts.** Even when the select survived, the writes into the
   HNSW-indexed `signal_embeddings` over the M1↔Supabase WAN are slow; a 256-row
   batch legitimately runs **>124s** and was guillotined at 2min. A few batches
   squeaked through before the cap → the 1,025 we observed.

3. **Why the first "fix" didn't take.** Setting `statement_timeout = 0` via the
   asyncpg pool `init` callback works on first connect, but asyncpg runs
   `RESET ALL` when a connection is **released** back to the pool → the SET is
   wiped and a reused write connection reverts to 2min. Instrumentation caught it
   exactly:

   ```
   DIAG: cancel after 124s on 256 rows; conn timeout=2min
   ```

## Fix

`backend/scripts/embed_hot_corpus.py`:

1. **Lift the timeout reliably.**
   - Main (dedicated, non-pooled) connection: `SET statement_timeout = 0` once
     after connect — it persists (never released/reset).
   - Pooled write connections: `SET LOCAL statement_timeout = 0` **inside a
     per-write transaction** (`_insert`). `SET LOCAL` is transaction-scoped, so
     it is re-applied fresh on every write and is immune to the pool's
     `RESET ALL`.

2. **Time-chunk the pending select, newest-first.** `_pending_rows` now walks
   the window in 12h slices from now backward, `DISTINCT ON (headline)` per
   slice, dedup across slices in Python (`seen`), and STOPS once `max_n` newest
   distinct headlines are collected. Each sort is bounded (~50K rows / ~8s); the
   backlog tail never has to sort. Recency-priority means the served window
   embeds first (the espriella lever).

3. **FK-race guard.** Retention can delete a signal between select and insert
   (`ForeignKeyViolationError` abends the whole batch). The INSERT now carries
   `WHERE EXISTS (SELECT 1 FROM signals_v2 s WHERE s.id = t.id)` to drop
   just-deleted ids in-statement, and `_write` catches the rare remaining race,
   refilters to still-present ids, and retries once.

4. Concurrent writes (4-way pool) unchanged.

## Verification (before → after)

| Metric | Before | After |
|---|---|---|
| Distinct-headline coverage, 24h | ~0.6% (near-zero distinct) | **52.0%** (65,887 / 126,732) |
| `emb_24h` (signals with an embedding, 24h) | 1,025 | **67,008** |
| `signal_embeddings` total | 187,323 | 253,306 |
| espriella distinct-headline coverage (168h) | 18% (97 sig) | **32.3%** (167 / 517) |

- Bounded live-index run (3000 rows, batch 256): **EXIT 0, no timeout** (was
  dying at 2min before) → the `SET LOCAL` fix confirmed.
- Catch-up run (`--bulk-reindex`, 60K budget): embedded **56,576 of 58,619**
  pending distinct headlines. It STOPPED at the recency budget, not on error —
  24h alone holds 126K distinct headlines, more than one 60K run can cover.

## Throughput measured (the real story)

| Path | Rate | Note |
|---|---|---|
| Live HNSW index, 4-way writes, over WAN | **~9/s** | 60K → ~107 min; the WAN+HNSW insert wall |
| `--bulk-reindex` (drop index → insert → rebuild) | **~36/s insert** | but the HNSW **rebuild was the trap** — see below |

### The rebuild trap: `maintenance_work_mem`

The script's rebuild step ran `SET maintenance_work_mem = '256MB'`. On the 253K ×
768 halfvec table (~371MB of raw vectors) that is **too small** → pgvector builds
the HNSW graph **on disk**, thrashing: measured `wait_event = DataFileRead`,
`tuples_done` advancing at **~4 tuples/min** → a projected **~3.5 DAYS** to
finish. The old "~4min/276K" comment was wrong for this instance.

Fix: cancel the stuck build (`pg_cancel_backend`), rebuild with
`maintenance_work_mem = '384MB'` (just over the 371MB working set; the instance
is small — `shared_buffers = 256MB`, so 384MB is the safe ceiling, higher risks
OOM). Result: **in-memory build, `wait_event = null`, ~1,255 tuples/s → whole
253K index in ~3-4 min.** A ~1000× speedup from one GUC.

**Action item:** bump the `maintenance_work_mem` in the script's `--bulk-reindex`
rebuild batch from `'256MB'` to `'384MB'` (or gate it on instance size) before
that path is ever used again.

**Key finding:** `--bulk-reindex` shifts the per-row WAN HNSW cost into a
server-side rebuild, which is only cheap with adequate `maintenance_work_mem`. So:

- **One-time backlog catch-up:** `--bulk-reindex` is the right tool (used today).
- **Steady-state cron:** `--bulk-reindex` is **NOT** viable 3×/day — the index
  would be down for hours each run. Keep the **live-index incremental path**
  (now reliable thanks to the timeout fix) and run it more frequently / longer.
  At ~9/s the ~126K distinct headlines/day take ~3.9h/day of mindful compute
  with **no index drop**.

## Should embedding move? (task item 4)

The bottleneck is the **INSERT into HNSW over the M1↔Supabase WAN**, not the
embed compute. Two consequences:

- **OpenAI embedding API does NOT help** — it changes where vectors are computed,
  but the slow step is the WAN write into Supabase, which remains.
- **A Fly-side embedder WOULD help** — co-located with Supabase (both AWS
  us-east), the per-row HNSW insert loses the WAN round-trip → live-index inserts
  get fast, no drop/rebuild needed. This is the real structural fix if the M1
  path can't sustain keep-up. Deferred (Fly shared CPU embed is slow; needs its
  own machine) — logged here as the recommendation.

## Follow-ups

- **Cron budget vs volume:** 24h ≈ 126K distinct headlines; the cron's
  `ATLAS_EMBED_MAX_SIGNALS=60000` × 3/day = 180K/day capacity, sufficient IF each
  run keeps up. Do **not** enable `--bulk-reindex` in the cron (rebuild cost).
- **espriella** and other multi-day stories climb over successive runs (recency
  window + 7-day retention); a single run can't backfill a 7-day story while the
  whole firehose competes for the budget.
- Structural: Fly-side embedder (kills the WAN insert cost) — the durable
  keep-up answer.
