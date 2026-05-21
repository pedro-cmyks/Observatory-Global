# Processed Historical Routing — Design Spec

**Date**: 2026-05-21
**Author**: Claude (orchestrator) + Pedro
**Tracking issue**: #193
**Related spec**: [`2026-05-21-processed-historical-sync-design.md`](./2026-05-21-processed-historical-sync-design.md)
**Status**: Draft pending user approval

## Context

Issue #193 asks to route `/app` long-window queries (`1w`, `1m`) to the processed historical tables introduced in #191/#192, instead of failing silently when the hot store does not cover the requested window.

Current state:

- Hot store (`signals_v2` on Fly Postgres) is pruned to a 24h SLA. Floor after the May 20 cutover is `2026-05-20T03:33:29Z`. Roughly 259k rows present.
- Cold archive lives on Pedro's local disk at `/Users/pedro/AtlasArchive/cutovers/2026-05-20`. 2.1M verified raw rows covering `2026-05-03` → `2026-05-20T03:33Z`.
- Processed historical table `historical_topic_country_daily` already exists (migration 029). The first artifact is loaded for `2026-05-19` only — 1,728 aggregate rows representing 185,163 signals across 11 atlas topics and 226 countries.
- `/api/v2/briefing` already routes `hours > 24` to `historical_topic_country_daily` (PR #144 follow-up). `/app` endpoints do not.

Without #193, the analyst surface in `/app` is silently capped to 24h — users see empty heatmaps and topic detail pages for any window longer than a day. The product framing is "narrative intelligence console", not "live monitor", so this gap is a credibility hit.

## Goals

1. `/app` endpoints that map naturally to the `(topic, country, day)` grain serve windows longer than the hot floor by querying `historical_topic_country_daily` and merging with hot data.
2. The API response makes coverage explicit so the frontend can show partial-coverage badges instead of pretending to return a full window.
3. Routing logic lives in one place and is unit-testable, not duplicated across endpoints.
4. The cutover boundary (`HOT_STORE_FLOOR`) is config-driven, not hardcoded into every endpoint.
5. The backfill that fills in `2026-05-03` → `2026-05-19` runs once, deterministically, with verifiable output.

## Non-goals

- Endpoints that need signal-level grain (`/narratives`, `/signals`, `/concept/{slug}`, `/source/.../profile`, `/flows`) are out of scope for this spec. They keep their current hot-only behavior. A follow-up spec will tackle signal-level historical evidence sampling.
- Auto-backfill triggered by missing coverage ("self-healing archive") is out of scope. Sketched as option D in the brainstorm; revisit in a separate spec.
- Pre-aggregated weekly/monthly rollup tables (`historical_topic_country_weekly` etc.) are out of scope. Filed as the follow-up issue suggested in the brainstorm. The daily table is sufficient to validate routing first.
- Frontend ranking changes (replacing volume-rank with heat-rank, etc.) are unrelated and out of scope.

## Design decisions (brainstorm record)

| # | Dimension | Choice | Notes |
|---|-----------|--------|-------|
| 1 | Routing strategy | Coverage-aware union + degraded badge | Query hot + processed, merge per-day, expose source ranges and missing windows in response. |
| 2 | Backfill scope | Full archive 2026-05-03 → 2026-05-19 (17 days) | Sequential daily processing; option to parallelize via `--workers 3` later. |
| 3 | API response shape | Source ranges + quality metrics | 3 keys (`hot`, `processed`, `missing`) plus `partial_coverage` and `coverage_pct`. Scales to any window size. |
| 4 | Overlap handling | Boundary-aware split via `HOT_STORE_FLOOR` config | Pre-floor → processed, post-floor → hot, no day duplicated across sources. |
| 5 | Endpoint scope | Quintet (`/heatmap`, `/heat/countries`, `/country/{code}`, `/theme/{code}`, `/anomalies/themes`) + centralized helper | Sub-endpoints (`/theme/{code}/drift`, `/spikes`, `/insight`) stay hot-only for now. |

## Architecture

```text
┌──────────────────────────────────────────────────────────┐
│  /api/v2/<endpoint>?hours=N                               │
│                  │                                        │
│                  ▼                                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │  app/services/processed_historical.py             │   │
│  │                                                    │   │
│  │  query_topic_country_window(hours, *, topic=,     │   │
│  │                             country=, now=)        │   │
│  │    1. compute_window_bounds(hours, now)            │   │
│  │    2. split_at_floor(HOT_STORE_FLOOR)              │   │
│  │    3. query_hot(signals_v2, post_floor)            │   │
│  │    4. query_processed(historical_*, pre_floor)     │   │
│  │    5. merge_results(hot_rows, processed_rows)      │   │
│  │    6. build_coverage_meta(...)                     │   │
│  │  → (rows, CoverageMeta)                            │   │
│  └──────────────────────────────────────────────────┘   │
│                  │                                        │
│                  ▼                                        │
│  endpoint applies its own shaping over `rows`             │
│  attaches `coverage` from CoverageMeta to response        │
└──────────────────────────────────────────────────────────┘
```

The helper is the only place that knows about `HOT_STORE_FLOOR`, the two underlying tables, or how to split a window. Endpoints stay agnostic — they see a flat list of `(topic, country, day, signal_count, avg_sentiment, ...)` rows plus a coverage envelope.

## Components

### `app/services/processed_historical.py` (new)

```python
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone


@dataclass
class CoverageMeta:
    hot: dict | None
    processed: dict | None
    missing: list[dict] = field(default_factory=list)
    partial_coverage: bool = False
    coverage_pct: float = 1.0


async def query_topic_country_window(
    hours: int,
    *,
    topic_code: str | None = None,
    country_code: str | None = None,
    now: datetime | None = None,
) -> tuple[list[dict], CoverageMeta]:
    """Unified window query across hot + processed historical.

    Returns aggregated rows at (topic_code, country_code, day) grain
    plus a coverage envelope describing where each part of the window
    came from.
    """
```

Internal helpers (private to this module):

- `_compute_window_bounds(hours, now) -> (window_from, window_to)` — UTC bounds.
- `_split_at_floor(window_from, window_to, floor) -> (pre_floor_range, post_floor_range)` — either may be `None` if the window is fully on one side.
- `_query_hot(window_from, window_to, *, topic, country)` — hits `signals_v2`, aggregates to `(topic, country, day)` grain on the fly, joins `atlas_topics`/`signal_topic_assignments`.
- `_query_processed(window_from, window_to, *, topic, country)` — hits `historical_topic_country_daily` directly.
- `_build_coverage_meta(hot_rows, processed_rows, window_from, window_to, floor)` — see formulas below.

### `app/config.py` (edit)

Add:

```python
HOT_STORE_FLOOR = os.getenv("HOT_STORE_FLOOR", "2026-05-20T03:33:29Z")
PROCESSED_COVERAGE_WARN_THRESHOLD = float(os.getenv("PROCESSED_COVERAGE_WARN_THRESHOLD", "0.80"))
```

Both are read once on import and exported as constants. `HOT_STORE_FLOOR` is parsed via `datetime.fromisoformat` after rewriting the trailing `Z` to `+00:00` (Python < 3.11 compat), and re-exported as a tz-aware `datetime` in UTC.

### `backend/app/routers/*.py` (edit, 5 files)

Each of the quintet endpoints adopts the pattern:

```python
@router.get("/api/v2/heatmap")
async def heatmap(hours: int = 24, topic: str | None = None, country: str | None = None):
    if hours <= 24:
        return await _heatmap_hot(hours, topic=topic, country=country)

    rows, coverage = await query_topic_country_window(
        hours,
        topic_code=topic,
        country_code=country,
    )
    aggregated = _aggregate_for_heatmap(rows)
    return {
        "countries": aggregated,
        "coverage": asdict(coverage),
        "partial_coverage": coverage.partial_coverage,
    }
```

Per-endpoint shaping (`_aggregate_for_heatmap`, etc.) lives in the same router file. Endpoints that already have a `theme_country_hourly_v2` fast-path for `hours <= 24` keep that fast-path unchanged.

### `frontend-v2/src/components/CoverageBadge.tsx` (new)

Shared badge component. Props: `coverage: CoverageMeta`. Render rules:

- `coverage.partial_coverage === true` → orange pill, label "Cobertura parcial · faltan N días", `data-tip` lists missing ranges.
- `coverage.processed && coverage.hot` → grey pill, label "Compuesto: hot + processed".
- `coverage.processed && !coverage.hot` → blue pill, label "Processed historical".
- `coverage.hot && !coverage.processed` → no badge (default live state).

CSS lives in `CoverageBadge.css`, no Tailwind.

### Frontend consumers (edit)

- `App.tsx` / heatmap container → reads `coverage` from `/heatmap` response, passes to `CoverageBadge` near the map header.
- `CountryBrief.tsx` → renders badge near the country title when `hours > 24`.
- `ThemeDetail.tsx` → renders badge near the topic title when `hours > 24`.
- `AnomalyPanel.tsx` → renders badge if `anomalies_themes.coverage.partial_coverage`.

## Data flow

1. User changes time window to `1w` (`hours=168`).
2. Frontend sends `GET /api/v2/heatmap?hours=168`.
3. Router calls `query_topic_country_window(168)`.
4. Helper computes window `[now - 168h, now]`.
5. `HOT_STORE_FLOOR = 2026-05-20T03:33:29Z`. Split:
   - `pre_floor = [now - 168h, 2026-05-20T03:33Z]`
   - `post_floor = [2026-05-20T03:33Z, now]`
6. `_query_processed` selects from `historical_topic_country_daily` where `day BETWEEN pre_floor.from::date AND pre_floor.to::date`.
7. `_query_hot` aggregates `signals_v2` to `(topic, country, day)` grain for the post-floor range.
8. `_merge_results` concatenates the two row lists. No de-dup needed because the split is exclusive — `day < floor::date` goes to processed, `day >= floor::date` goes to hot.
9. `_build_coverage_meta` produces the envelope (see formulas below).
10. Endpoint shapes rows into `countries` and returns response.

## Coverage meta formulas

```python
def _build_coverage_meta(hot_rows, processed_rows, window_from, window_to, floor):
    expected_days = (window_to.date() - window_from.date()).days + 1

    hot_meta = None
    if hot_rows:
        hot_meta = {
            "from": max(window_from, floor).isoformat(),
            "to": window_to.isoformat(),
            "row_count": sum(r["signal_count"] for r in hot_rows),
        }

    processed_meta = None
    if processed_rows:
        processed_to = min(window_to, floor)
        processed_meta = {
            "from": window_from.isoformat(),
            "to": processed_to.isoformat(),
            "signal_count": sum(r["signal_count"] for r in processed_rows),
            "topic_count": len({r["topic_code"] for r in processed_rows}),
        }

    covered_days = {r["day"] for r in hot_rows} | {r["day"] for r in processed_rows}
    coverage_pct = len(covered_days) / expected_days if expected_days else 1.0

    missing = _compute_gap_ranges(window_from, window_to, covered_days)
    partial = bool(missing) or coverage_pct < PROCESSED_COVERAGE_WARN_THRESHOLD

    return CoverageMeta(hot_meta, processed_meta, missing, partial, round(coverage_pct, 3))
```

`_compute_gap_ranges` walks the expected day list, collapses consecutive missing days into a single range, and tags each with `reason="not_yet_processed"` (only reason supported in v1; the field is future-proofing for `archive_corrupted`, `processing_failed`, etc.).

## API response shape (full)

```json
{
  "countries": [
    {"country_code": "CO", "signal_count": 12450, "avg_sentiment": -0.32, ...}
  ],
  "coverage": {
    "hot": {
      "from": "2026-05-20T03:33:29Z",
      "to": "2026-05-21T11:20:00Z",
      "row_count": 259360
    },
    "processed": {
      "from": "2026-05-14T00:00:00Z",
      "to": "2026-05-20T03:33:29Z",
      "signal_count": 1240333,
      "topic_count": 30
    },
    "missing": [],
    "partial_coverage": false,
    "coverage_pct": 1.0
  },
  "partial_coverage": false
}
```

`partial_coverage` is duplicated at the top level for convenience — frontend can read it without descending into `coverage`. The nested `coverage` object is the source of truth.

## Backfill plan

The processed table currently holds 2026-05-19 only. Backfill the remaining 16 days from the verified archive.

1. **Loop** over `2026-05-03` → `2026-05-19` inclusive (skip 05-19, already loaded).
2. For each day: `python backend/scripts/historical_process_partition.py --date YYYY-MM-DD`. Output JSON goes to `docs/research/processed-historical-sync/YYYY-MM-DD-topic-country.json`.
3. Sync to Supabase: `python backend/scripts/historical_sync.py --date YYYY-MM-DD --execute`. Uses upsert key `(topic_code, country_code, day, atlas_version)`.
4. After each day: `python backend/scripts/historical_coverage_report.py --date YYYY-MM-DD` confirms row count matches expectations.
5. Final smoke: `historical_coverage_report.py` (no `--date`) lists every day with row counts and signal totals. Expect 17 rows, summing to ~2.1M signals.

Wall-clock estimate: ~25 minutes sequential at ~90 seconds per day average (varies by signal volume). Parallel `--workers 3` reduces to ~9 minutes if processor is concurrency-safe — confirmed later, not blocking.

Idempotency: `historical_sync.py --execute` is upsert-based, safe to re-run. Bad day can be reprocessed without manual cleanup.

## Operational guardrails

- **Cutover floor is config-driven**. If a future cutover changes the floor, update `HOT_STORE_FLOOR` env var on Fly (and re-run backfill up to the new floor). No code change required.
- **Day-boundary timezone**: `historical_topic_country_daily.day` is UTC date. `signals_v2.published_at` is UTC timestamp. Helper aggregates hot to UTC date to match. Frontend rendering of day labels uses user's local timezone — explicit `ts_utc → local` conversion in `CoverageBadge` tooltip.
- **Cache**: processed queries are cacheable for 24h (the row set does not change once a day is processed). Hot queries cache 15 min. Helper output cache uses the shorter TTL (15 min) to be safe across the boundary.
- **`historical_topic_country_daily` index**: migration 029 created the table; a `(topic_code, country_code, day)` btree index is added in a small migration `032_historical_topic_country_daily_index.sql` if `EXPLAIN` shows seq scans on the quintet endpoints.

## Testing strategy

### Unit (`backend/tests/test_processed_historical.py`, new)

1. `test_window_bounds_short_window` — `hours=24, now=fixed` → `(now-24h, now)`.
2. `test_window_bounds_long_window` — `hours=720` → `(now-30d, now)`.
3. `test_split_at_floor_window_fully_before_floor` — returns `(window, None)`.
4. `test_split_at_floor_window_fully_after_floor` — returns `(None, window)`.
5. `test_split_at_floor_window_straddles_floor` — splits cleanly at floor.
6. `test_coverage_meta_full_processed_full_hot` — `partial_coverage = false`.
7. `test_coverage_meta_missing_middle_days` — `missing` lists the gap, `partial_coverage = true`.
8. `test_coverage_pct_below_threshold` — `partial_coverage = true` even with no explicit missing ranges if pct < 0.80.
9. `test_gap_range_collapsing` — three consecutive missing days collapse to a single range.

### Integration (`backend/tests/test_processed_historical_endpoints.py`, new)

For each of the 5 quintet endpoints:

1. `hours=24` returns existing hot-only shape (no `coverage` key, regression guard).
2. `hours=168` returns `coverage` populated, rows include processed days.
3. `hours=720` with truncated processed coverage returns `partial_coverage=true` with non-empty `missing`.

Fixtures use a fake `signals_v2` table and a fake `historical_topic_country_daily` table populated in `conftest.py`.

### Smoke (live Fly, post-deploy)

1. `curl https://atlas-api-pedro.fly.dev/api/v2/heatmap?hours=24` → no `coverage` key (or `coverage` reflects hot-only).
2. `curl ...heatmap?hours=168` → `coverage.processed` covers `2026-05-14` → `2026-05-20T03:33Z`, `coverage.hot` covers `2026-05-20T03:33Z` → now, `partial_coverage=false`.
3. `curl ...heatmap?hours=720` (30d) → `partial_coverage=true`, `missing` lists pre-2026-05-03 days.
4. Same three calls against `/heat/countries`, `/country/CO`, `/theme/disease-outbreak`, `/anomalies/themes`.

## Risks and mitigations

1. **Processed table missing index** — first long-window queries may hit seq scans. Mitigation: monitor query latency post-deploy, add migration 032 if needed.
2. **Day-boundary timezone mismatches** — user perceives missing days due to local vs UTC confusion. Mitigation: tooltip text explicitly says "UTC" for ranges in the coverage badge.
3. **Schema drift** between archive and processed table — processor adds new columns later, sync breaks. Mitigation: `historical_sync.py` already uses `ON CONFLICT ... DO UPDATE SET <enumerated columns>`; document the column list in `029_historical_processed_tables.sql` header.
4. **Cache key collision** — `/heatmap?hours=24` and `/heatmap?hours=168` already have distinct cache keys; new `coverage` payload changes shape but not key. Mitigation: bump cache version constant or namespace (`v_processed_routing_1`).
5. **Frontend coverage badge over-flagging** — `partial_coverage = true` for any pct < 0.80 may show false negatives if the user picks an unusual window. Mitigation: badge copy is informational, not alarming ("Cobertura parcial" not "Datos faltantes").

## Files touched

**New (backend):**

- `backend/app/services/processed_historical.py`
- `backend/tests/test_processed_historical.py`
- `backend/tests/test_processed_historical_endpoints.py`

**New (frontend):**

- `frontend-v2/src/components/CoverageBadge.tsx`
- `frontend-v2/src/components/CoverageBadge.css`

**Edit (backend):**

- `backend/app/config.py` (add `HOT_STORE_FLOOR`, `PROCESSED_COVERAGE_WARN_THRESHOLD`)
- `backend/app/routers/heatmap.py` (or wherever `/api/v2/heatmap` lives)
- `backend/app/routers/heat.py` (`/api/v2/heat/countries`)
- `backend/app/routers/country.py` (`/api/v2/country/{code}`)
- `backend/app/routers/theme.py` (`/api/v2/theme/{code}` only — not sub-endpoints)
- `backend/app/routers/anomalies.py` (`/api/v2/anomalies/themes`)

**Edit (frontend):**

- `frontend-v2/src/App.tsx`
- `frontend-v2/src/components/CountryBrief.tsx`
- `frontend-v2/src/components/ThemeDetail.tsx`
- `frontend-v2/src/components/AnomalyPanel.tsx`

**Optional (post-deploy):**

- `backend/migrations/032_historical_topic_country_daily_index.sql` (only if `EXPLAIN` shows seq scans)

## Definition of done

- [ ] All 16 missing archive days processed and synced. `historical_coverage_report.py` shows 17 days, ~2.1M signals.
- [ ] `processed_historical.py` exists with unit tests covering 9 cases listed above.
- [ ] Quintet of endpoints serves windows > 24h with `coverage` envelope. Hot-only path for `hours <= 24` regression-tested.
- [ ] `CoverageBadge` renders correctly across the four states (partial, composite, processed-only, hot-only).
- [ ] Live smoke against Fly returns expected coverage envelopes for `hours=24`, `hours=168`, `hours=720`.
- [ ] Backend tests pass (target: 275+ passed, 6 skipped — up from the current 271/6).
- [ ] Frontend `npm run build` passes.
- [ ] `CLAUDE.md` "Current Session Context" updated with the routing summary and the new `HOT_STORE_FLOOR` operational rule.
- [ ] Commits pushed to `v3-intel-layer`, Fly auto-deploys, Vercel auto-deploys.
- [ ] Issue #193 closed with link to the merged commits and the live smoke transcripts.

## Open questions

None for v1. Auto-backfill (option D from the brainstorm), weekly rollup table, and signal-level historical evidence are filed as separate follow-ups.
