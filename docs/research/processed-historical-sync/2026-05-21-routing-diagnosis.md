# Processed Historical Routing Diagnosis — 2026-05-21

## Summary

The processed historical backfill is complete and queryable. The next failures are routing and grain mismatches, not storage.

Live compact history:

```text
table:                 historical_topic_country_daily
model_version:         atlas-hist-v1
days:                  2026-05-03 through partial 2026-05-20
represented signals:   2,128,070
compact rows:          22,711
countries:             236
topics:                11
```

The main issue: several `/app` endpoints still query hot raw `signals_v2` or old GDELT theme tables when the user asks for `1w`/`1m`. Since raw history has been pruned, those endpoints either reject the window, return partial hot data, or time out.

## Production Reproduction

Checked against `https://atlas-api-pedro.fly.dev` on 2026-05-21.

| Endpoint | Result | Diagnosis |
|---|---|---|
| `/api/v2/heat/countries?hours=168&limit=5` | HTTP 400 | Endpoint explicitly supports only `hours=24`. |
| `/api/v2/heatmap?hours=168` | HTTP 200, empty deprecated payload | Heatmap route is deprecated and not connected to processed history. |
| `/api/v2/country/CO?hours=168` | HTTP 200 | Works, but mixes long-window pre-agg stats with raw hot `signals_v2` themes/sources/persons. No coverage metadata. |
| `/api/v2/theme/armed-conflict-escalation?hours=168` | Curl timed out after 40s | Endpoint treats Atlas topic slug as a GDELT theme code and scans raw `signals_v2`; returns no useful data. |
| `/api/v2/anomalies/themes?hours=168&limit=5` | HTTP 200, empty list | Uses raw `signals_v2` current window and empty `theme_daily_v2`; not historical processed. |
| `/api/v2/briefing?hours=168` | HTTP 200, historical top themes | `top_themes` works from compact history, but `top_sources` is degraded. |

## Query Evidence

Measured with `EXPLAIN (ANALYZE, FORMAT JSON)` against Supabase.

Before maintenance:

| Query | Execution time |
|---|---:|
| Briefing `top_sources` 168h raw group-by | ~21.3s |
| Theme endpoint sample for Atlas slug | ~11.0s and 0 rows |
| Historical topic country aggregate | ~42ms |

Maintenance performed:

```sql
ANALYZE historical_topic_country_daily;
ANALYZE country_hourly_v2;
ANALYZE theme_country_hourly_v2;
```

After maintenance:

| Query | Execution time |
|---|---:|
| Briefing `top_sources` 168h raw group-by | ~10.3s |
| Theme endpoint sample for Atlas slug | ~15.1s and 0 rows |
| Historical topic country aggregate | ~42ms |

Interpretation:

- `ANALYZE` helped the raw source group-by but did not fix it. It remains above `BRIEFING_DB_TIMEOUT_SECONDS=8`.
- The theme endpoint is not just slow. It is wrong for Atlas slugs because it searches `'ARMED-CONFLICT-ESCALATION' = ANY(signals_v2.themes)`, but `signals_v2.themes` contains GDELT taxonomy codes, not Atlas topic slugs.
- The compact historical table is fast enough for product routing.

## Root Causes

### 1. Grain mismatch

`historical_topic_country_daily` is at this grain:

```text
day, topic_slug, country_code, source_family, signal_class, model_version
```

Some existing endpoints expect signal-level grain:

```text
timestamp, source_name, source_url, headline, persons, raw GDELT themes
```

Only aggregate views should route to compact history. Evidence samples need a separate table.

### 2. Atlas topic slug vs GDELT theme code confusion

`/api/v2/theme/{theme_code}` was originally built for GDELT theme codes. The new briefing exposes Atlas topic slugs such as `armed-conflict-escalation`, which do not exist in `signals_v2.themes`.

Long-window topic pages need to branch:

- Atlas topic slug + `hours > 24` -> `historical_topic_country_daily`.
- GDELT theme code + `hours > 24` -> `theme_country_hourly_v2` where appropriate.
- Signal samples -> hot-only until `historical_evidence_samples` is populated.

### 3. `top_sources` lacks a historical source-name aggregate

`historical_topic_country_daily` has `source_family`, not `source_name`. That is enough for voice lanes, but not enough to answer "top publishers".

The current briefing fallback groups hot `signals_v2` by `source_name` across 168h. After hot/cold prune this is both semantically partial and slow.

Resolution shipped 2026-05-21:

- Added `historical_source_daily` with daily `source_domain` / `source_family` / `signal_class` aggregates.
- Synced the verified cutover archive into `161,871` compact source aggregate rows representing `2,128,070` archived signals.
- Routed `/api/v2/briefing?hours>24` `top_sources` to `historical_source_daily`.
- Live query plan after `VACUUM`: ~40 ms, index-only scan, `Heap Fetches: 0`.

### 4. `theme_daily_v2` is empty

`/api/v2/anomalies/themes` joins against `theme_daily_v2`, but live stats show `theme_daily_v2` has 0 rows. The endpoint can return a valid empty payload while hiding that its baseline table has no data.

### 5. No reusable coverage envelope yet

Briefing has `historical_coverage`, but `/app` endpoints do not share a helper. Without one, every endpoint will reinvent hot/processed/missing logic differently.

## Endpoint Classification

### Ready for compact historical routing

These map naturally to daily aggregate grain:

- `/api/v2/heat/countries`
- `/api/v2/country/{code}` summary, topic list, source-family lanes
- `/api/v2/theme/{topic_slug}` summary, country breakdown, timeline by day
- `/api/v2/anomalies/themes` when reframed as processed-history volume change

### Needs separate aggregate before routing

- Briefing `top_sources`: needs `historical_source_daily` or similar.
- Country/source publisher lists: need source-name aggregate or evidence samples.

### Must stay hot-only for now

- Signal samples.
- Persons/entities.
- Raw headlines/evidence.
- Narrative details that require signal-level timelines.

## Recommended Fix Order

1. Add shared `processed_historical.py` helper and coverage metadata.
2. Route `/api/v2/heat/countries` for `hours > 24` from compact historical country totals. Keep the existing `country_heat_v2` 24h heat path unchanged.
3. Route `/api/v2/country/{code}` long-window summary and topics from compact history. Mark sources/persons as hot-only or omit them from historical coverage until source/evidence tables exist. Implemented on 2026-05-21: long windows now return country summary, processed topics, source-family/signal-class mix, optional evidence samples, and coverage metadata.
4. Route `/api/v2/theme/{topic_slug}` long-window Atlas topic pages from compact history. Add explicit `source="historical_topic_country_daily"` and `coverage`.
5. Fix `/api/v2/anomalies/themes` by using compact history for historical windows and returning a degraded/coverage reason when baseline is unavailable.
6. Add `historical_source_daily` for #194 so long-window top publishers do not scan raw `signals_v2`. Implemented on 2026-05-21: long-window briefing source rankings now use compact processed source aggregates and expose `top_sources_source`.

## Non-Fixes

- Do not raise DB timeouts to hide `top_sources` slowness.
- Do not rehydrate raw historical rows into Supabase.
- Do not route signal-level endpoints to compact history without evidence samples.
- Do not count Reddit/social commentary as publisher corroboration.

## Operational Note

`ANALYZE` was run on:

- `historical_topic_country_daily`
- `country_hourly_v2`
- `theme_country_hourly_v2`

This improved planner state but did not remove the need for routing changes.
