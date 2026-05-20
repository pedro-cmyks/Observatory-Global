# Atlas Hot/Cold Data Operating Model Design

Date: 2026-05-20  
Branch: `v3-intel-layer`  
Related issues: #188, #189, #184, #185, #164, #154, #157, #162, #167

## Problem

Atlas has enough raw data, but not enough normalized data.

The current production shape asks Supabase to do three jobs at once:

1. Serve the live product.
2. Store the historical raw archive.
3. Act as the workbench for large backfills, NLP retries, vocabulary mining, and topic experiments.

That is not sustainable. The live state on 2026-05-20 shows the mismatch:

- Total signals: approximately 2.26M.
- Unprocessed NLP backlog: approximately 2.09M.
- Unprocessed 24h window: approximately 179K.
- Ingest velocity is higher than transformer NLP throughput.
- Broad updates over millions of rows create Supabase IO pressure and statement timeouts.

The goal is not to keep every raw row forever in the hot database. The goal is to keep Atlas trustworthy, current, explainable, and fast while preserving the ability to reprocess historical evidence offline.

## Design Goal

Move Atlas from a single hot database model to a tiered data operating model:

- Supabase remains the live product database.
- Raw historical archives move to cheaper cold storage.
- Heavy backfills and model experiments run outside the hot path.
- A local worker can help process historical data, but the public app must never depend on the local machine being online.

## Non-Goals

- Do not replace Supabase as the operational database.
- Do not make the frontend read from Pedro's local machine.
- Do not migrate all historical data immediately.
- Do not run destructive full-table rewrites in production.
- Do not require a new paid cloud data warehouse before proving the simpler local/archive path.
- Do not add new cloud services for this transition. Use the current stack:
  Supabase, Fly.io, Vercel, Upstash, and Pedro's local machine/storage.

## Recommended Approach

Use a hybrid model:

1. **Hot Store: Supabase**
   - Keeps recent operational data, product-facing aggregates, and user-facing derived fields.
   - Optimized for `/brief`, `/app`, search, country panels, narrative threads, heat ranking, and workspace evidence lookup.

2. **Cold Archive: Local Storage First**
   - Keeps raw historical signals as append-only partitioned files.
   - Preferred format: compressed Parquet if tooling is available; otherwise JSONL `.zst` as a first step.
   - Partition by date and source family:
     - `archive/signals/year=2026/month=05/day=20/source_family=gdelt/...`
   - Must be queryable locally. The archive is not only backup; it is the
     historical research store.

3. **Offline Worker: Pedro's Local Machine**
   - Reads cold archive partitions.
   - Runs expensive NLP/topic/backfill experiments.
   - Writes only curated outputs back to Supabase:
     - `nlp_sentiment`
     - `nlp_confidence`
     - `nlp_method`
     - `nlp_model_version`
     - topic assignments
     - aggregate refresh inputs
   - Uses checkpoints so it can stop and resume without duplication.
   - Preferred operating window: early morning UTC-5, when interactive use is
     low and the machine can run heavier jobs without affecting product demos.

4. **Cloud Worker: Fly NLP Hot Lane**
   - Continues processing fresh/high-value rows.
   - Its job is same-day product quality, not historical drain.

## Data Tiers

### Tier 0: Ingest Buffer

Purpose: absorb incoming source data and prevent drops.

Location: Fly ingestion process + Supabase inserts.

Retention target: immediate to a few hours.

Rules:

- Ingest should never block on transformer NLP.
- Every signal gets basic provenance fields at insert:
  - `source_family`
  - `source_lang`
  - `geo_confidence`
  - `attribution_method`
  - `signal_class`
- Every signal should get a cheap fast-lane enrichment as close to ingest as possible.

### Tier 1: Hot Product Store

Purpose: serve Atlas quickly.

Location: Supabase.

Retention target:

- Raw row detail: 24h.
- Product aggregates: longer retention where useful.
- User-facing curated evidence: retained if pinned/exported or referenced by a durable product object.

Contains:

- Recent `signals_v2` rows.
- `country_hourly_v2`, `theme_hourly_v2`, `theme_country_hourly_v2`.
- `country_heat_v2`.
- `atlas_topics`, topic assignments, source mix, voice mix, correction tables.
- NLP and topic metadata for rows that remain hot.

Rules:

- Product routes should prefer aggregates over raw scans.
- Broad production updates must be batched.
- Raw rows older than 24h should be exported and verified before leaving the hot
  store. Aggregates and evidence pointers may remain much longer.
- Any new aggregate with sentiment must include:
  - raw GDELT sentiment aggregate,
  - NLP sentiment aggregate,
  - NLP coverage count,
  - explicit `sentiment_source` decision logic.

### Tier 2: Warm Index

Purpose: query recent history without keeping every raw field in hot tables.

Location: Supabase for product-facing rollups; local query index for archive exploration.

Retention target: 30d to 180d.

Contains:

- Deduplicated cluster metadata.
- Country/topic/source/day rollups.
- Searchable evidence pointers into the local archive.
- Source and voice mix history.

Rules:

- Store enough to answer product questions.
- Do not store every raw headline forever if it is already archived.

### Tier 3: Cold Archive

Purpose: preserve raw evidence and allow reprocessing.

Location: local disk first. No new cloud storage dependency in the first implementation.

Retention target: indefinite, bounded by storage budget.

Contains:

- Raw ingested signals.
- Provider payloads when legally/operationally safe.
- Exported partitions from Supabase before pruning.
- Model output snapshots for reproducibility.

Rules:

- Append-only.
- Partitioned by date/source.
- Checksummed.
- Rehydratable into Supabase in small batches if needed.
- Queryable via local scripts or an embedded analytical engine such as DuckDB
  over Parquet/JSONL partitions. Historical search should not require
  re-importing the full archive into Supabase.

## Processing Lanes

### Fast Lane

Target: all incoming rows.

Purpose: make today's data usable quickly.

Processing:

- Lexicon sentiment.
- Lightweight topic intelligence.
- Source classification.
- Country/source/voice attribution.
- Basic dedupe or cluster hint.

SLA:

- 90-100% of hot-window rows served by product routes should have Atlas-owned
  NLP enrichment within 24h. This may be fast-lane NLP rather than transformer
  NLP for every row.
- Stretch target: within 1h for rows that appear in `/brief` or top heat countries.

### Deep Lane

Target: selected/high-value rows.

Purpose: transformer-grade quality where it matters.

Priority:

1. Fresh hot-window rows.
2. Non-English/API/social rows.
3. High heat/surprise rows.
4. Low-volume countries.
5. User-touched evidence from search, workspace, and country/theme panels.
6. Stratified audit samples.

SLA:

- Deep NLP should not attempt full historical drain in the hot worker.
- It should keep the current product window improving continuously.

### Historical Lane

Target: cold archive partitions.

Purpose: offline reprocessing, model experiments, and backfills.

Location: local worker or detached batch runner.

Rules:

- Never competes with hot ingestion.
- Syncs curated deltas back to Supabase in batches.
- Has checkpoints by partition, model version, and row id.

## Local Worker Design

The local worker is useful, but only as an offline enrichment engine.

Preferred schedule:

- Early morning UTC-5.
- Runs after the previous UTC day has been archived and checksummed.
- Prioritizes historical partitions and model improvement work, not today's
  hot product window unless explicitly invoked for catch-up.

It may:

- Download/export cold partitions.
- Run NLP/topic models against historical data.
- Mine lexicons from transformer-tagged rows.
- Generate candidate updates.
- Push back bounded, idempotent updates.
- Serve local-only archive queries for the owner/research workflow.

It must not:

- Serve frontend traffic.
- Be required for `/brief` or `/app` to work.
- Hold the only copy of any operational hot data.
- Receive inbound public network traffic.
- Become a public API dependency.

Connectivity model:

- Outbound-only from local machine.
- Uses Supabase service credentials stored in local `.env`, never committed.
- Writes through batch scripts with checkpoint files.

Failure behavior:

- If local worker is offline: historical backfill pauses; product continues.
- If Supabase is unavailable: local worker queues output locally and retries later.
- If local output is bad: rollback by model version or batch id.

## Sync Protocol

Every local/offline job should produce:

- `job_id`
- `source_partition`
- `model_name`
- `model_version`
- `started_at`
- `completed_at`
- `rows_read`
- `rows_written`
- `checksum`
- `status`

Writes back to Supabase should be:

- Batched, default 500-1000 rows.
- Idempotent by `signal_id + model_version + output_type`.
- Timeout-bounded.
- Resume-safe.

Recommended table:

```sql
CREATE TABLE IF NOT EXISTS offline_enrichment_jobs (
  job_id TEXT PRIMARY KEY,
  source_partition TEXT NOT NULL,
  model_name TEXT NOT NULL,
  model_version TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  rows_read BIGINT DEFAULT 0,
  rows_written BIGINT DEFAULT 0,
  checksum TEXT,
  status TEXT NOT NULL,
  error TEXT
);
```

## Disconnection Protocols

### Local Worker Disconnects

Expected result:

- No user-facing outage.
- Historical processing pauses.
- Latest 24h continues on Fly/Supabase.
- Local archive queries may be unavailable until the machine is back online.

Recovery:

- Resume from local checkpoint.
- Compare job checkpoint against Supabase `offline_enrichment_jobs`.
- Continue next unfinished partition.

### Supabase IO Pressure

Expected result:

- Stop historical writes.
- Keep hot app queries and ingest alive.

Recovery:

- Pause local sync.
- Lower batch size.
- Resume during low-traffic window.
- Use indexes before any repeated update path.

### Fly NLP Worker Lag

Expected result:

- Fast lane still gives basic labels.
- Product marks low NLP coverage honestly.

Recovery:

- Raise `NLP_WORKER_LIMIT` only under #184 measurement plan.
- Add additional worker only after DB write pressure is understood.
- Do not let historical backlog consume hot lane.

### Archive Disk Unavailable

Expected result:

- App continues.
- Cold export pauses.
- Historical query from archive is degraded/unavailable.

Recovery:

- Re-export missing hot partitions before Supabase retention deletes them.
- Alert if archive lag approaches retention boundary.

## Storage Format

Preferred cold format:

- Parquet with ZSTD compression.
- Partitioned by date/source.
- Schema version embedded in metadata or path.
- Queryable through DuckDB or an equivalent local analytical reader.

Fallback format:

- JSONL compressed with ZSTD.
- Easier to inspect and recover manually.

Minimum fields:

- signal id
- source provider id or URL
- headline
- timestamp
- created_at
- country_code
- themes/raw topics
- source_name/source_url
- provenance fields
- raw sentiment
- NLP outputs if present
- model version fields

## Security

Local machine rules:

- `.env.local-worker` is gitignored.
- Service role credentials are never committed.
- Prefer least-privilege key or RPC endpoints for batch updates if practical.
- Logs must not print database URLs or API keys.
- Archive directory should be excluded from git and Time Machine noise if very large.

Public system rules:

- No inbound tunnel to the local machine.
- No frontend calls to local URLs.
- No dependency on local worker for live health.

## Archive Queryability

The cold archive must support owner/research queries without rehydrating all
data into Supabase.

Minimum query capabilities:

- Query by date range.
- Query by country.
- Query by source family or attribution method.
- Query by source name/domain.
- Query by topic/theme fields available in the archived rows.
- Query by NLP method/model version when archived outputs exist.

Implementation preference:

- Store archive partitions in Parquet if the local Python/DuckDB stack is
  available.
- Maintain a small local manifest file:
  - partition path,
  - min/max timestamp,
  - row count,
  - checksum,
  - schema version,
  - export job id.
- Provide a CLI like:
  - `python -m scripts.archive_query --country CO --from 2026-05-01 --to 2026-05-07`
  - `python -m scripts.archive_query --source-family social --limit 100`

The app can later expose historical archive search as an offline/admin tool,
but the public product should keep using Supabase hot data and aggregates.

## Phased Implementation

### Phase 0: Measurement and Guardrails

- Confirm current ingest/day, NLP/day, backlog slope.
- Add dashboard or script for:
  - hot unprocessed count,
  - NLP coverage by source/lang/country,
  - Fly worker duration/memory,
  - Supabase IO proxy metrics where available.

Exit criteria:

- We can see whether backlog is improving or worsening without manual SQL spelunking.
- We can measure whether hot-window product routes are serving 90-100% rows with
  Atlas-owned NLP enrichment.

### Phase 1: Same-Day SLA

- Define hot-window SLA in #188.
- Ensure every new signal gets fast-lane enrichment.
- Keep transformer worker focused on fresh/high-value rows.
- Product routes should prefer enriched rows or enriched aggregates and expose
  coverage honestly.

Exit criteria:

- 90-100% of rows served from the 24h hot window have at least fast-lane NLP.
- New data entering today becomes product-usable today, even if historical backlog remains.

### Phase 2: Safe Archive Export

- Export partitions older than 24h to local cold storage.
- Verify checksums and row counts.
- Keep Supabase untouched except for read/export.
- Build the local manifest and basic archive query CLI.

Exit criteria:

- We can prove raw history exists outside Supabase before pruning or moving historical raw rows.
- The archive is locally queryable by date/country/source without re-importing.

### Phase 3: Local Offline Worker

- Process one small historical partition locally.
- Write results to a staging table or batch file.
- Validate quality before touching production columns.

Exit criteria:

- One end-to-end offline enrichment job is reproducible and resumable.

### Phase 4: Controlled Sync Back

- Sync curated results in small batches.
- Track job ids.
- Update aggregates only after row-level write validation.

Exit criteria:

- Supabase receives useful historical enrichment without IO spikes.

### Phase 5: Retention Policy

- Decide what raw rows can leave hot storage.
- Keep aggregates and evidence pointers.
- Archive before pruning.

Exit criteria:

- Supabase hot data size stabilizes instead of growing indefinitely.

## Open Questions

1. What exact early-morning UTC-5 window should the local worker use?
2. Should the first archive format be Parquet immediately, or JSONL `.zst` first for easier inspection?
3. Which product routes count for the initial 90-100% served NLP target: `/brief` only, or `/brief` + `/app` country/theme/search panels?
4. Should historical archive queries be CLI-only first, or should we plan an owner-only UI later?

## Recommendation

Start with Phase 0 and Phase 1, then Phase 2 immediately after the SLA is measurable.

The immediate product pain is not historical completeness; it is that incoming data is under-processed. Make today's data healthy first. In parallel, design the archive export so future backfills do not require repeated full-table movement inside Supabase.

Use the local machine for early-morning offline enrichment, archive querying, and historical reprocessing. Do not use it for public live serving.
