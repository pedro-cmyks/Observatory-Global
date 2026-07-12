# Archive Intelligence Tier — full-history processing, light on the database

**Date:** 2026-07-10 · **Status:** SPEC (Pedro-approved design, pending implementation)
**Owner constraint (Pedro, verbatim intent):** "todo el cómputo en mi computador,
y liviano en su base" — process ALL historical data (May-03 → today, beyond the
7-day hot window), but NEVER upload per-story embeddings/detail to Supabase and
NEVER grow the paid instance.

## 1. Why now / evidence

- The hot tier only serves 7 days; the external archive holds 10.5M+ rows and
  **42GB of OpenAI text-embedding-3-small vectors ALREADY COMPUTED on disk**
  (`/Volumes/Ext/Atlas/Embeddings/openai-3-small`, ~6.94M vectors, 166 shards).
  The heavy compute is already paid — what's missing is clustering/typing over it
  and a light serving layer.
- The database CANNOT hold the heavy form. Measured 2026-07-08/10 on the Supabase
  Micro (~1GB RAM, `shared_buffers` 256MB): a mere 253K-row halfvec HNSW rebuild
  **thrashed to disk for 36 hours** (`maintenance_work_mem` ceiling; see
  `docs/state/2026-07-08-embedding-throughput-fix.md`). 6.94M vectors ≈ 11GB+
  — impossible on this instance, and upgrading is ruled out by cost.
- Existing archive surfaces already prove the light pattern works:
  `archive_story_units` (mig 069), `historical_topic_country_daily`,
  `historical_evidence_samples` (60K samples), `/deep-history`, `/map/replay`,
  `/evidence/day`. This tier completes them with TOPICS + SEARCH.

## 2. Architecture — three layers, one golden rule

**Golden rule: heavy data (vectors, per-story detail) never leaves the external
disk. Supabase receives only topics + aggregates + samples (MB, not GB). The hot
7-day tier is untouched.**

```
EXTERNAL DISK (M1)                M1 (offline compute)              SUPABASE (light)
──────────────────                ─────────────────────             ─────────────────
OpenAI shards 42GB    ──read──►  archive_cluster_offline.py  ──►  archive_topics (thousands of rows:
archive_story_units              · window-at-a-time, resumable      label, category, centroid, dates,
                                 · scoped clustering (R1 pattern)   country, sizes, source mix)
per-story assignments ◄──write── · DeepSeek category typing   ──►  historical_topic_country_daily (exists)
(parquet + DuckDB, STAYS)        · centroids + daily aggregates ──► historical_evidence_samples (exists)
                                 · evidence samples (≤5/topic-day)
```

Serving (Fly API): query → embed with OpenAI (cheap, Fly-side) → cosine against
the few thousand `archive_topics.centroid_vec` rows → topic + aggregates +
samples. No new infra, no HNSW.

## 3. Components

### 3.1 Supabase — migration 073 (the only new table)

```sql
CREATE TABLE archive_topics (
    id               BIGSERIAL PRIMARY KEY,
    label            TEXT NOT NULL,
    category         TEXT,                 -- living taxonomy (same as typer)
    crisis_relevant  BOOLEAN,
    country_code     CHAR(2),              -- cluster scope (NULL = global pass)
    period_start     DATE NOT NULL,
    period_end       DATE NOT NULL,
    n_stories        INT NOT NULL,
    n_signals        INT,
    centroid_vec     REAL[] NOT NULL,      -- OpenAI 3-small 1536d; NO HNSW index
    top_sources      JSONB,                -- light sample for voice-mix framing
    sample_story_ids TEXT[],               -- pointers into the disk parquet
    build_id         TEXT NOT NULL,        -- run/checkpoint version
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_archive_topics_period  ON archive_topics (period_start, period_end);
CREATE INDEX idx_archive_topics_country ON archive_topics (country_code, period_start);
```

- Expected volume: ~2-5K rows → centroids ≈ 15-30MB total.
- `centroid_vec` is `REAL[]` **without** a vector index — at thousands of rows a
  scan + cosine (Python or SQL) answers in <100ms; a second HNSW competing for
  the Micro's RAM is exactly the failure mode we just measured.
- `historical_topic_country_daily` and `historical_evidence_samples` are REUSED:
  the builder appends rows for archive topics (keyed by `build_id`), same
  contracts the existing surfaces already read.

### 3.2 External disk — per-story detail (parquet + DuckDB)

```
/Volumes/Ext/Atlas/ArchiveTopics/
  assignments/month=YYYY-MM/part-*.parquet   -- story_id, topic_id, sim, country, date
  checkpoints/build-<id>.json                -- windows completed; resumable
```

- Parquet partitioned by month; DuckDB queries it locally (6.9M rows, seconds).
- When a surface someday needs the exact member stories of an archive topic, a
  local script extracts them and uploads only that sample — never the bulk.

### 3.3 M1 compute — `backend/scripts/archive_cluster_offline.py`

Nightly/mindful (taskpolicy -b, mlvenv), NEVER during working hours. Per window
(1 week, walking backward from the hot boundary to May-03):

1. Load that window's vectors + story metadata from the OpenAI shards on disk.
2. Scoped clustering per country/period (reuse the R1 scoped-pass machinery) +
   a global pass for cross-country stories.
3. DeepSeek types each topic against the LIVING taxonomy (cents per window;
   honest reject / free-category exactly like the hot typer).
4. Write to Supabase: one `archive_topics` row per topic (with centroid), daily
   aggregate rows, ≤5 evidence samples per topic-day (distinct-source, with URL).
5. Write per-story assignments to the month's parquet partition.
6. Checkpoint the window in `checkpoints/build-<id>.json` → a killed run resumes
   at the next window; re-running a completed window is idempotent (build_id
   upsert semantics: delete-and-replace that window's rows).

Uses the archive robot findings (2026-07-05): intra≥0.80 same-story guard,
token-dominance event-level guard, junk filters — the miner exists, this reuses
its lessons over the already-embedded corpus.

### 3.4 Fly API — `GET /api/v2/archive/search`

- `?q=<text>&country=CC&from=YYYY-MM-DD&to=YYYY-MM-DD` (all optional but q).
- Embeds the query with OpenAI text-embedding-3-small (~$0.00002/query; the gate
  cutover already runs OpenAI Fly-side).
- Cosine against `archive_topics.centroid_vec` (optionally filtered by
  country/date), top-K with a measured similarity floor (calibrated from the
  2026-07-05 `calibrate_openai_headline_tau.py` artifact: junk p50 0.542 / p95
  0.725 — floor starts at ~0.30 topic-level, re-measured at build time).
- Response contract `archive-search-v0`: topics + their daily series
  (`historical_topic_country_daily`) + evidence samples + honest empty state
  ("archive covers May-03→X; no coverage for that range").
- Tier labeling: everything served from this endpoint is marked
  `tier: "archive"` (same honest-tier convention as `/deep-history` and
  `/evidence/day`).

## 4. What this explicitly does NOT do

- No per-story rows in Supabase (6.9M assignments stay in parquet).
- No archive vectors in Supabase (42GB stay on disk).
- No HNSW for the archive (centroid scan is enough at this scale).
- No change to the hot 7-day pipeline, `signal_embeddings`, `dynamic_topics`,
  or any live serving path.
- No instance upgrade; DB stabilizes ~5GB on the current plan.
- No cross-space vector math: hot = e5, archive = OpenAI. The two tiers never
  compare vectors directly; they meet only at the surface level (labels,
  categories, countries, dates).

## 5. Database discipline (standing rules, born from the 2026-07-08/10 incident)

1. `signal_embeddings` stays capped ~200K rows (~5-6 days) — a 253K HNSW rebuild
   already exceeds the Micro's RAM.
2. NEVER `--bulk-reindex` in cron; live-index incremental inserts only.
3. New archive data enters ONLY as topic/aggregate/sample rows.
4. Any future vector column at >100K rows on this instance requires an explicit
   sizing check (`rows × dims × 2 bytes` vs `maintenance_work_mem`) before an
   index is even attempted.

## 6. Verification / acceptance

- **Build:** one window (e.g. first week of June) processed end-to-end on the M1
  → `archive_topics` rows exist with sane labels/categories; parquet partition
  written; checkpoint recorded; re-run of the same window is idempotent.
- **Serve:** `archive/search?q=iran water protests` returns June topics with
  daily series + evidence URLs; a query outside coverage returns the honest
  empty state. Espriella-class check: a Colombia-election query over the full
  archive range surfaces the topic beyond the 7-day hot window.
- **Weight:** `pg_total_relation_size('archive_topics')` stays in the tens of MB
  after full backfill; DB total stays under ~5.5GB.
- **No hot regression:** `/threads`, `/briefing`, research-plan smoke unchanged
  after migration + endpoint deploy.

## 7. Open items deferred (not in this build)

- Frontend surface for archive search (the endpoint contract comes first; UI
  slots into SearchBar/deep-history in a later pass).
- Umbrella folding of archive topics across windows (same event spanning weeks →
  one canonical row): run `assemble_constellation.py` logic over archive_topics
  in a second pass.
- PERU-style near-dup assembly on the archive (mechanical once topics exist).
