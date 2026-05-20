# Hot/Cold Data Operating Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for inline execution, or `superpowers:subagent-driven-development` if the user explicitly asks for parallel workers. Execute tasks one at a time and update checkboxes as work lands.

## Goal

Make Atlas serve a 24-hour product window with 90-100% Atlas-owned enrichment while keeping historical data queryable outside Supabase. No new cloud services: use the current stack only.

## Recommendation

Use a split operating model:

- **Hot store:** Supabase keeps the last 24 hours plus aggregate tables needed by the app. This is the fast product surface.
- **Cold archive:** Pedro's local machine stores historical raw/enriched signals in a queryable archive. The local archive is allowed to be slower, bigger, and cheaper.
- **Local work window:** 00:00-06:00 America/Bogota for export, archive compaction, historical queries, and optional backfills. This avoids competing with daytime development and product checks.
- **SLA definition:** 90-100% of product-served hot-window rows must have Atlas-owned enrichment. That can be transformer, lexicon/topic intelligence, source classification, or explicit low-confidence neutral fallback. The UI/API must expose the method honestly.

Supabase and the local archive hold overlapping information briefly, but they do not have the same job. Supabase answers live product questions; the archive answers historical and audit questions.

## Constraints

- No S3, BigQuery, Snowflake, new queues, or new hosted databases.
- Do not make ingestion wait on transformer NLP.
- Do not delete historical data until archive export has a manifest and verification count.
- Avoid adding heavy dependencies to the Fly runtime unless they are proven necessary.
- Keep archive tooling runnable with the Python standard library first; add optional DuckDB/Parquet support later if local dependencies are available.

## Phase 1 - Archive Foundation

- [x] Add local archive environment variables to `backend/.env.example`.
- [x] Add archive writer/query helpers using JSONL gzip partitions and a manifest.
- [x] Add a CLI that exports explicit date ranges from `signals_v2` to the local archive.
- [x] Add a CLI that queries the local archive by time range, country, source family, source name, and limit.
- [x] Add unit tests for partition naming, manifest writing, and archive filtering.
- [x] Document example commands in this plan.

## Phase 2 - NLP SLA Measurement

- [x] Add a lightweight SLA report CLI for the last 24 hours.
- [x] Report total hot rows, Atlas-owned enriched rows, transformer rows, fast-lane rows, raw rows, and coverage percent.
- [x] Group gaps by source family, source language, and country so we know where the backlog hurts product first.
- [x] Add tests for SLA math on synthetic rows.

## Phase 3 - Fast-Lane Enrichment

- [ ] Ensure every newly ingested hot row receives `signal_class` and topic intelligence quickly.
- [ ] For sentiment, use transformer when available; use lexicon when matched; use explicit neutral low-confidence fallback when no sentiment evidence exists.
- [ ] Store method fields so downstream product can distinguish `transformer`, `lexicon`, and `fast_neutral`.
- [ ] Keep transformer NLP for higher-value/prioritized rows, not as the only path to "processed".

## Phase 4 - Local Night Worker

- [x] Add a local one-shot worker script that only runs inside 00:00-06:00 America/Bogota unless `--force` is passed.
- [x] Worker sequence: SLA report, export explicit cold partition, verify manifest count via exporter, then optional archive query smoke test.
- [ ] Add a launchd-compatible command snippet, but do not require launchd for manual use.
- [ ] Keep database deletes manual until archive verification is trusted.

## Phase 5 - Retention Cutover

- [ ] Run archive export for a small date range and verify counts.
- [ ] Run archive export for all rows older than 24 hours in date-sized batches.
- [ ] Only after verification, add a prune script for archived raw rows older than 24 hours.
- [ ] Keep product aggregate tables and correction tables in Supabase even when raw rows age out.

## Example Commands

```bash
cd backend

# Inspect current hot-window enrichment.
python -m scripts.nlp_sla_report --hours 24

# Export one UTC day to local archive.
python -m scripts.archive_export \
  --archive-dir "$ATLAS_ARCHIVE_DIR" \
  --from 2026-05-19T00:00:00Z \
  --to 2026-05-20T00:00:00Z \
  --dry-run

# Query archived rows locally.
python -m scripts.archive_query \
  --archive-dir "$ATLAS_ARCHIVE_DIR" \
  --country CO \
  --source-family social \
  --limit 25
```

## Acceptance Criteria

- Archive files are queryable locally without connecting to Supabase.
- Archive manifest records row count, time range, checksum, and export metadata.
- No destructive prune runs unless the matching archive manifest exists.
- Hot-window enrichment report can prove whether Atlas is at 90-100% served coverage.
- The implementation references GitHub issues `#188` and `#189`.
