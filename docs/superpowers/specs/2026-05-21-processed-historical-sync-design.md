# Atlas Processed Historical Sync Design

Date: 2026-05-21  
Branch: `v3-intel-layer`  
Related issues: #164, #167, #171, #184, #185, #190

## Decision

Supabase should be the product-serving database for processed data, not the
long-term raw archive.

After the hot/cold cutover, Atlas has two distinct responsibilities:

- Keep recent ingestion and same-day processing reliable.
- Convert historical archive partitions into compact processed product surfaces.

The raw archive lives locally. Supabase keeps only what the application needs to
serve historical analysis quickly: processed aggregates, topic/entity/narrative
indexes, quality metadata, and small evidence samples.

## Current State

The cutover in #190 moved `2,128,070` historical `signals_v2` rows into the local
archive and pruned them from Supabase after exact manifest verification.

Current verified shape after the prune:

- Local archive: `/Users/pedro/AtlasArchive/cutovers/2026-05-20`.
- Archive rows: `2,128,070`.
- Exact `signals_v2` count after prune: `259,360`.
- `nlp_progress.unprocessed_total`: `241,002`.
- Fly health: healthy.
- `/health.total_signals` now represents aggregate historical volume from
  `country_hourly_v2`, not raw hot-store rows.

The next problem is not storage. The next problem is making historical data
processed, queryable, and visible in the app without re-inflating Supabase.

## Goals

1. Keep Supabase lightweight.
2. Keep all product-served data processed or explicitly labeled as low-confidence.
3. Process historical archive partitions locally, where storage and compute are cheaper.
4. Sync compact processed outputs back to Supabase.
5. Let the app serve `1w`, `1m`, `3m`, and eventually `record` views from processed
   historical tables.
6. Preserve raw evidence for audit and request-time retrieval without making raw
   historical rows the normal product path.

## Non-Goals

- Do not make the public app depend on Pedro's computer being online.
- Do not rehydrate all raw historical rows into Supabase.
- Do not add a new cloud service for the first implementation.
- Do not run all historical transformer NLP on Fly.
- Do not make every old raw row individually visible in the normal UI.
- Do not overwrite source taxonomies such as raw GDELT `themes`; normalize them
  into Atlas-owned topic layers.

## Product Principle

Everything Supabase serves to the product should be processed enough to explain.

For every product-facing historical value, Atlas should know:

- source window,
- method,
- model or rule version,
- processing coverage,
- confidence where applicable,
- representative evidence pointers.

Raw historical data remains available, but it is an audit and reprocessing layer,
not the ordinary app-serving layer.

## Data Tiers

### Tier 0: Hot Raw Buffer

Location: Supabase `signals_v2`.

Retention target: `24h`, with small operational slack if needed.

Purpose:

- absorb new ingests,
- deduplicate,
- classify provenance and `signal_class`,
- run fast-lane NLP/topic enrichment,
- provide immediate evidence for today's app.

Rules:

- Ingest must not wait on transformer NLP.
- Every row should get fast-lane processing as soon as possible.
- Rows that are not deeply processed inside the hot window are archived and
  later handled by the local processor.

### Tier 1: Hot Processed Store

Location: Supabase.

Purpose:

- serve the live product window,
- power `/brief`, `/app`, heat, search, country detail, narrative threads,
- expose honest method/coverage metadata.

Contains:

- recent processed `signals_v2`,
- `country_hourly_v2`,
- `theme_hourly_v2`,
- `theme_country_hourly_v2`,
- `country_heat_v2`,
- `atlas_topics`,
- recent `signal_topic_assignments`,
- source/voice/provenance fields.

Rules:

- Routes should prefer aggregates when the query window is larger than the hot
  raw window.
- Raw scans over `signals_v2` should be bounded to hot windows unless the endpoint
  is explicitly an evidence request.

### Tier 2: Historical Processed Index

Location: Supabase, compact tables only.

Purpose:

- serve `1w`, `1m`, `3m`, and `record` analysis,
- provide processed trends without raw-row bloat,
- expose coverage and quality metadata.

Recommended tables:

- `historical_country_daily`
- `historical_topic_country_daily`
- `historical_source_daily`
- `historical_entity_daily`
- `historical_narrative_daily`
- `historical_evidence_samples`
- `historical_processing_runs`
- `historical_archive_coverage`

These tables should be append/upsert oriented and keyed by day, country, topic,
source family, model version, and processing method.

### Tier 3: Local Raw Archive

Location: `/Users/pedro/AtlasArchive`.

Purpose:

- retain complete raw evidence,
- support reprocessing and audits,
- allow local historical queries,
- produce processed sync artifacts.

Rules:

- append-only,
- partitioned,
- checksummed,
- locally queryable,
- not required for the public app to work.

## Processing Lanes

### Fly Hot Lane

Fly handles same-day reliability.

Responsibilities:

- ingest,
- fast-lane sentiment/topic/source classification,
- transformer NLP for prioritized hot rows,
- hot aggregates,
- health and backlog telemetry.

The Fly `nlp_worker` should stay sized for the hot lane while the backlog is still
large. Once the local processor is stable and the hot SLA is proven, machine size
can be tested downward.

### Local Historical Lane

The local processor handles archived partitions after the hot window.

Responsibilities:

- read local archive partitions,
- run historical NLP/topic/entity passes,
- generate daily processed aggregates,
- generate evidence samples,
- generate coverage reports,
- sync compact outputs to Supabase.

The local lane should run in the early morning UTC-5 maintenance window and should
checkpoint every partition/model run.

### Evidence Request Lane

Raw evidence retrieval is allowed, but not as the default historical experience.

Examples:

- owner asks to inspect raw rows for a topic/date/country,
- dossier export needs underlying articles,
- audit wants to reproduce an aggregate.

This can be served locally or through a staged export, but the standard app views
should use processed tables.

## Supabase Lightweight Contract

Supabase may store:

- hot raw rows for operational ingestion,
- processed aggregates,
- topic/entity/narrative indexes,
- small evidence samples,
- processing run metadata,
- correction and learning tables.

Supabase should not store:

- all historical raw rows,
- duplicated historical headlines at full granularity,
- full provider payloads for old rows,
- one row per old raw signal unless that row is a curated evidence sample,
- large all-table backfill state that can be rebuilt from the archive.

## Historical Table Sketch

### `historical_processing_runs`

Tracks model/version/checkpoint state.

Fields:

- `run_id`
- `archive_root`
- `partition_from_ts`
- `partition_to_ts`
- `model_version`
- `processor_version`
- `status`
- `rows_read`
- `rows_processed`
- `rows_failed`
- `created_at`
- `completed_at`
- `error`

### `historical_topic_country_daily`

Primary table for app historical topic/country views.

Fields:

- `day`
- `topic_id`
- `country_code`
- `source_family`
- `signal_class`
- `signal_count`
- `avg_sentiment`
- `sentiment_coverage`
- `topic_coverage`
- `entity_coverage`
- `local_voice_ratio`
- `source_diversity`
- `evidence_sample_count`
- `model_version`
- `updated_at`

### `historical_evidence_samples`

Small representative evidence set, not full raw storage.

Fields:

- `sample_id`
- `day`
- `topic_id`
- `country_code`
- `source_family`
- `signal_class`
- `archive_relative_path`
- `source_name`
- `source_url`
- `headline`
- `timestamp`
- `sentiment`
- `confidence`
- `selection_reason`
- `model_version`

## App Behavior

For `<=24h`:

- query hot processed data,
- use `signals_v2` only where evidence cards need fresh raw detail.

For `>24h`:

- query historical processed tables,
- show coverage badges,
- show representative evidence samples,
- avoid raw scans.

For raw evidence:

- use an explicit action such as "Request raw evidence" or "Open archive evidence",
- clearly indicate whether data is local/archive-derived.

## Coverage Target

Product-served historical data should reach 90-100% processed coverage at the
aggregate level. This does not require transformer NLP on every raw row.

Acceptable method mix:

- transformer for high-value and representative samples,
- lexicon/corpus-mined fast lane for broad sentiment coverage,
- Atlas topic lexicon/embedding/zero-shot for normalized topics,
- explicit `fast_neutral` or low-confidence labels where the system lacks signal.

The UI should display method and coverage honestly.

## Issue Mapping

- #164: old full-backfill thinking becomes local/historical lane, not hot DB pressure.
- #167: Atlas Topic Intelligence is the normalized topic layer for both GDELT and non-GDELT.
- #171: topic lexicon backfill should target hot/incremental and historical compact outputs.
- #184: Fly worker sizing applies to hot SLA only, not full historical processing.
- #185: corpus-mined lexicons are the bridge from transformer samples to broad local coverage.
- #190: raw retention cutover is complete; this design defines how to make the archive useful.

## Open Risks

1. Historical processed tables can still grow too large if keyed too granularly.
   Mitigation: start daily, not hourly, and keep evidence samples small.

2. Local processor may produce model outputs that drift from Fly hot processing.
   Mitigation: store `model_version`, `processor_version`, and method fields.

3. App routes may accidentally fall back to raw `signals_v2` for long windows.
   Mitigation: add route shape tests that assert long windows use historical tables.

4. Supabase aggregate count can confuse users after raw prune.
   Mitigation: expose separate metrics: `hot_raw_rows`, `historical_processed_rows`,
   and `aggregate_signal_volume`.

## Acceptance Criteria

- A local processor can read a verified archive partition and produce processed
  aggregate artifacts.
- Supabase receives compact historical outputs, not raw historical rows.
- App routes for `1w` and `1m` can serve trend/country/topic views without scanning
  old `signals_v2` rows.
- Every historical endpoint exposes processing coverage and method metadata.
- Raw evidence remains available through explicit sample or archive request flows.
