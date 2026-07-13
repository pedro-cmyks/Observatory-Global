# ANN index recovery — measured HNSW to IVFFlat cutover

**Date:** 2026-07-13  
**Scope:** `signal_embeddings.vec` (`halfvec(768)`) on the shared 1 GB Supabase
instance.  
**Issue:** GitHub #241.

## Decision

Atlas now uses an IVFFlat cosine index for the hot semantic corpus. This is a
measured operating decision, not a claim that IVFFlat is universally superior
to HNSW. On this database, the HNSW graph could not be built or maintained
inside the available memory/I/O envelope without starving serving.

Migration `076_signal_embeddings_ivfflat.sql` makes the cutover idempotent. The
local writer rebuilds the same index after retention/bulk maintenance, and the
serving semantic lanes set `ivfflat.probes = 20` on their database connection.

## Failure evidence

| Trial | Observation |
|---|---|
| existing HNSW writes | 256 inserts exceeded 120 seconds and blocked the writer |
| HNSW `m=16` build | stopped progressing at 35,759 / 62,394 blocks (57.3%); backend became uninterruptible |
| HNSW `m=8` | spilled after 201,417 tuples; post-spill progress projected tens of minutes |
| HNSW `m=4` | spilled after 214,302 tuples |

Reducing `m` moved the spill point only modestly. The 768-dimensional vector
payload and graph-build working set, not only graph-link count, dominate this
instance. Project restart was required to clear the uninterruptible build; no
product or archive rows were deleted.

## IVFFlat construction

The corpus contained 326,762 rows at build time. Atlas used 327 lists, following
the pgvector sub-million rule of approximately `rows / 1000`. K-means completed
in about 12 seconds and the whole build in about 105 seconds. After concurrent
ingest, the live table held 327,274 rows; table and index were each about 513 MB.

The installed definition is:

```sql
CREATE INDEX idx_signal_embeddings_vec
ON public.signal_embeddings
USING ivfflat (vec halfvec_cosine_ops)
WITH (lists = '327');
```

## Retrieval benchmark

Twenty deterministic, dispersed queries were compared with exact cosine search
on the same corpus. Query plans confirmed `Index Scan using
idx_signal_embeddings_vec`.

| probes | mean recall@10 | minimum | p10 | mean latency |
|---:|---:|---:|---:|---:|
| 5 | 0.915 | 0.60 | — | 107.64 ms |
| 10 | 0.955 | 0.60 | 0.80 | 111.36 ms |
| **20** | **1.000** | **1.00** | **1.00** | **130.97 ms** |

At probes 20, maximum observed ANN latency was 203.08 ms. Warm exact scans were
generally 150–300 ms; the first cold exact scan took 3.5–3.7 seconds. Atlas
therefore fixes a probe floor of 20 for the current index/list count. This must
be re-benchmarked if corpus size or list count changes materially.

## Write-path benchmark

A transaction inserted 256 real missing signal IDs using an existing vector and
then rolled back. The insert took 172.429 ms (about 1,485 rows/s); network
`BEGIN` and `ROLLBACK` each contributed roughly 101 ms. This isolates index
maintenance from durable data mutation and contrasts with the HNSW write timeout.

## Operational contract

- recurring retention remains bounded; no semantic meaning is discarded to fit
  a visual limit;
- the writer owns ANN restoration in an outer `finally`;
- migration and writer converge on one IVFFlat definition;
- both signal and thread-member ANN search prepare probes 20 explicitly;
- the heavy-job mutex remains required because serving and batch still share one
  database;
- #241 should close only after a recurring embed cycle completes with fresh
  `topic_members`, movement, and publication artifacts, not merely after an
  index exists.

