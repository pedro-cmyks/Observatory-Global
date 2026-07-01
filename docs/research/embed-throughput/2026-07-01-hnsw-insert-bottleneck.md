# Embed throughput — the HNSW-insert bottleneck (#241), measured

Date: 2026-07-01 · Method: controlled measurement on prod Supabase (isolated inserts +
index build). Feeds Paper 8 (coverage/recall throughput) + the #241 fix decision.

## Why this matters
Clustering (R1 recall) only sees EMBEDDED signals. The embed can't keep up with ingest,
so the recall ceiling is the embed throughput. Measured state:
- `signal_embeddings` = **276,609** rows; embed **~37,376/24h** (3 off-peak cron runs).
- Ingest ~150K+/24h (GDELT alone) → **backlog 442,015 un-embedded** signals (168h). Growing.

## Measurements (isolated, prod)
| operation | rate | note |
|---|---|---|
| raw INSERT (no index), 5000 vecs | 170 ms → **~29,400 rows/s** | pure write is trivial |
| raw INSERT (no index), 276K vecs | 12.2 s → **~22,600 rows/s** | server-side bulk |
| **HNSW incremental insert, 5K-row graph** | 13.8 s / 5000 → **~362 rows/s** | **~80× the raw cost** |
| **HNSW incremental insert, real 276K graph + WAN (embed cron)** | **<16 rows/s** | degrades with graph size + M1→Supabase WAN |
| HNSW index BUILD, parallel, 512MB mem | **FAILS** | `could not resize shared memory … No space left on device` — Supabase shmem cap |
| **HNSW index BUILD, single-threaded (`max_parallel_maintenance_workers=0`, 128MB)** | 50K in 41.3 s → **~1,210 rows/s → 276K in ~4 min** | dodges the shmem limit |

## Conclusion (measurement-backed)
1. **The bottleneck is HNSW graph maintenance per insert, not the write, not the embed,
   not WAN alone.** No-index insert is ~22–29K/s; the HNSW makes it ~16/s on the real graph
   — an ~80×+ tax that WORSENS as the graph grows (362/s @5K → <16/s @276K).
2. **The classic drop→bulk-insert→rebuild fix IS viable here** — but ONLY single-threaded:
   the parallel build hits Supabase's shared-memory cap; `max_parallel_maintenance_workers=0`
   builds 276K in ~4 min. So a bulk embed run can: drop the index → insert at ~22K/s →
   rebuild in ~4 min. That turns a 100K-signal run from ~1.7 h (at 16/s) into ~5 min.
3. Concurrency bump (already 4-way) helps at the margin (HNSW insert has graph-lock
   contention); it does NOT remove the 80× tax.
4. Embedding EVERYTHING is the deeper problem: ingest > any per-insert HNSW rate. Even the
   drop/rebuild wins per-run, but the steady state still needs **selective embedding**
   (#222/#164 stratified — skip roundup/syndication/junk) so the insert volume matches what
   HNSW can carry.

## Recommended fix (two levers, measured)
- **Lever 1 — drop/rebuild in the bulk embed cron (biggest per-run win).** In
  `embed_hot_corpus.py`, an opt-in bulk mode: `DROP INDEX idx_signal_embeddings_vec` →
  bulk-insert the run's batch at ~22K/s → `SET max_parallel_maintenance_workers=0; CREATE
  INDEX … hnsw …` (~4 min). Off-peak only; the semantic lane degrades to lexical during the
  rebuild (already its honest fallback). GUARD: verify the rebuild completes before the run
  exits; if it fails, the index is gone until the next build — so wrap it + alert.
- **Lever 2 — selective embedding (structural, #222/#164).** Don't embed obvious
  roundup/syndication/junk; embed the high-value subset. Reduces the insert volume at the
  root so the steady state stops falling behind.

DELICATE (drops the prod vector index to rebuild) — implement behind a flag, test on a
bench table, enable in the cron only after Pedro's review. The measurements above are the
justification (Paper-8 methodology: the coverage ceiling is an infra-throughput result,
not a clustering-quality one).
