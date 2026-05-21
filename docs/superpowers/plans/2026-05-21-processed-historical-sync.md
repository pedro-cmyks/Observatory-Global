# Processed Historical Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local historical processor that turns archived raw signals into compact processed Supabase tables for `1w`, `1m`, `3m`, and `record` product views while keeping Supabase lightweight.

**Architecture:** Supabase keeps hot raw rows and processed product surfaces only. The local archive remains the raw historical store. A local processor reads archive partitions, writes compact daily aggregates and evidence samples, and syncs those outputs to Supabase with explicit method/version/coverage metadata.

**Tech Stack:** Python 3.11, FastAPI, asyncpg, Supabase Postgres, local JSONL gzip archive, pytest, React/Vite frontend after backend APIs are available.

---

## File Map

Create:

- `backend/migrations/029_historical_processed_tables.sql`  
  Historical compact tables and indexes.

- `backend/scripts/historical_process_partition.py`  
  Reads local archive partitions and writes local JSON artifacts for processed aggregates.

- `backend/scripts/historical_sync.py`  
  Uploads processed aggregate artifacts to Supabase with idempotent upserts.

- `backend/scripts/historical_coverage_report.py`  
  Reports processed coverage by date, topic, country, source family, and model version.

- `backend/tests/test_historical_processing.py`  
  Unit tests for aggregate generation, evidence sampling, and idempotent payload shape.

- `docs/research/processed-historical-sync/`  
  Run outputs and coverage notes.

Modify:

- `backend/scripts/archive_common.py`  
  Add helpers for iterating archive rows by manifest record and partition path.

- `backend/app/routers/briefing.py`  
  Later task: route long windows to historical processed tables.

- `frontend-v2/src/pages/BriefNewspaper.tsx`  
  Later task: display historical coverage/source badges for long windows.

- `STATUS.md`, `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`  
  Keep operational handoff current.

## Phase 0: GitHub And Documentation Setup

- [x] **Step 1: Create tracking issues**

Create these GitHub issues:

```bash
gh issue create \
  --title "data(history): processed historical sync from local archive to Supabase" \
  --body "Build the local processor and sync path that turns /Users/pedro/AtlasArchive into compact processed Supabase historical tables. This follows #190 and implements docs/superpowers/specs/2026-05-21-processed-historical-sync-design.md." \
  --label "enhancement,backend"

gh issue create \
  --title "db(history): keep Supabase lightweight with processed-only historical tables" \
  --body "Add historical processed tables, coverage metadata, and guardrails so Supabase stores product-ready historical indexes and evidence samples, not full raw historical signals." \
  --label "enhancement,backend"

gh issue create \
  --title "feat(history): route 1w and 1m app windows to processed historical tables" \
  --body "Update API/frontend behavior so long windows use processed historical tables with coverage badges instead of scanning historical raw signals_v2 rows." \
  --label "enhancement,frontend,backend,ux"
```

- [x] **Step 2: Comment linkage on existing issues**

Comment on #164, #167, #171, #184, #185:

```text
Processed Historical Sync integration note:
Supabase should serve processed historical product surfaces, not raw historical rows. The local archive processor will handle backlog/historical processing and sync compact daily aggregates, topic/entity/narrative indexes, evidence samples, and coverage metadata back to Supabase. This narrows Fly's role to hot-window SLA and keeps Supabase lightweight.
Spec: docs/superpowers/specs/2026-05-21-processed-historical-sync-design.md
Plan: docs/superpowers/plans/2026-05-21-processed-historical-sync.md
```

## Phase 1: Supabase Historical Processed Schema

- [x] **Step 1: Add migration 029**

Create `backend/migrations/029_historical_processed_tables.sql`:

```sql
CREATE TABLE IF NOT EXISTS historical_processing_runs (
    run_id              UUID PRIMARY KEY,
    archive_root        TEXT NOT NULL,
    partition_from_ts   TIMESTAMPTZ NOT NULL,
    partition_to_ts     TIMESTAMPTZ NOT NULL,
    model_version       TEXT NOT NULL,
    processor_version   TEXT NOT NULL,
    status              TEXT NOT NULL,
    rows_read           BIGINT NOT NULL DEFAULT 0,
    rows_processed      BIGINT NOT NULL DEFAULT 0,
    rows_failed         BIGINT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    error               TEXT,
    CONSTRAINT historical_processing_runs_status_valid
        CHECK (status IN ('started', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS historical_topic_country_daily (
    day                   DATE NOT NULL,
    topic_slug            TEXT NOT NULL,
    country_code          TEXT NOT NULL,
    source_family         TEXT NOT NULL,
    signal_class          TEXT NOT NULL,
    signal_count          BIGINT NOT NULL,
    avg_sentiment         DOUBLE PRECISION,
    sentiment_coverage    DOUBLE PRECISION NOT NULL DEFAULT 0,
    topic_coverage        DOUBLE PRECISION NOT NULL DEFAULT 0,
    entity_coverage       DOUBLE PRECISION NOT NULL DEFAULT 0,
    local_voice_ratio     DOUBLE PRECISION,
    source_diversity      DOUBLE PRECISION,
    evidence_sample_count INTEGER NOT NULL DEFAULT 0,
    model_version         TEXT NOT NULL,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (day, topic_slug, country_code, source_family, signal_class, model_version)
);

CREATE INDEX IF NOT EXISTS idx_hist_topic_country_daily_lookup
    ON historical_topic_country_daily (day DESC, country_code, topic_slug);

CREATE INDEX IF NOT EXISTS idx_hist_topic_country_daily_topic
    ON historical_topic_country_daily (topic_slug, day DESC, signal_count DESC);

CREATE TABLE IF NOT EXISTS historical_evidence_samples (
    sample_id             TEXT PRIMARY KEY,
    day                   DATE NOT NULL,
    topic_slug            TEXT NOT NULL,
    country_code          TEXT NOT NULL,
    source_family         TEXT NOT NULL,
    signal_class          TEXT NOT NULL,
    archive_relative_path TEXT NOT NULL,
    source_name           TEXT,
    source_url            TEXT,
    headline              TEXT,
    signal_timestamp      TIMESTAMPTZ,
    sentiment             DOUBLE PRECISION,
    confidence            DOUBLE PRECISION,
    selection_reason      TEXT NOT NULL,
    model_version         TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hist_evidence_lookup
    ON historical_evidence_samples (day DESC, country_code, topic_slug);

CREATE TABLE IF NOT EXISTS historical_archive_coverage (
    day                 DATE NOT NULL,
    archive_root        TEXT NOT NULL,
    rows_archived       BIGINT NOT NULL,
    rows_processed      BIGINT NOT NULL,
    sentiment_coverage  DOUBLE PRECISION NOT NULL,
    topic_coverage      DOUBLE PRECISION NOT NULL,
    entity_coverage     DOUBLE PRECISION NOT NULL,
    model_version       TEXT NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (day, archive_root, model_version)
);
```

- [x] **Step 2: Add schema shape tests**

Create `backend/tests/test_historical_processing.py` with:

```python
from pathlib import Path


def test_migration_029_defines_processed_historical_tables():
    sql = Path("migrations/029_historical_processed_tables.sql").read_text()

    assert "historical_processing_runs" in sql
    assert "historical_topic_country_daily" in sql
    assert "historical_evidence_samples" in sql
    assert "historical_archive_coverage" in sql
    assert "PRIMARY KEY (day, topic_slug, country_code, source_family, signal_class, model_version)" in sql
    assert "archive_relative_path" in sql


def test_migration_029_does_not_create_raw_history_table():
    sql = Path("migrations/029_historical_processed_tables.sql").read_text().lower()

    assert "historical_signals_v2" not in sql
    assert "raw_payload" not in sql
```

- [x] **Step 3: Run tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_historical_processing.py -q
```

Expected: `2 passed`.

- [x] **Step 4: Apply migration**

Status 2026-05-21: Supabase MCP OAuth configured, migration applied through
Supabase MCP, and tables verified before live sync.

Apply via Supabase SQL editor or the configured Supabase MCP, not through Alembic.

Verify:

```sql
SELECT to_regclass('historical_topic_country_daily') IS NOT NULL AS ok;
```

Expected: `ok = true`.

- [x] **Step 5: Commit**

```bash
git add backend/migrations/029_historical_processed_tables.sql backend/tests/test_historical_processing.py
git commit -m "feat(data): add processed historical tables"
```

## Phase 2: Local Historical Processor

- [x] **Step 1: Add a pure aggregation function test**

Extend `backend/tests/test_historical_processing.py`:

```python
from scripts.historical_process_partition import build_daily_topic_country_rows


def test_build_daily_topic_country_rows_groups_processed_archive_rows():
    rows = [
        {
            "id": 1,
            "timestamp": "2026-05-19T03:00:00Z",
            "country_code": "CO",
            "source_family": "gdelt",
            "signal_class": "reporting",
            "headline": "Colombia energy grid outage",
            "themes": ["ENERGY"],
            "nlp_sentiment": -0.4,
            "nlp_confidence": 0.8,
            "nlp_persons": ["Example Person"],
        },
        {
            "id": 2,
            "timestamp": "2026-05-19T04:00:00Z",
            "country_code": "CO",
            "source_family": "gdelt",
            "signal_class": "reporting",
            "headline": "Colombia energy rationing",
            "themes": ["ENERGY"],
            "nlp_sentiment": -0.2,
            "nlp_confidence": 0.7,
            "nlp_persons": [],
        },
    ]

    output = build_daily_topic_country_rows(rows, model_version="atlas-hist-v1")

    assert len(output) == 1
    row = output[0]
    assert row["day"] == "2026-05-19"
    assert row["topic_slug"] == "energy-grid-instability"
    assert row["country_code"] == "CO"
    assert row["signal_count"] == 2
    assert row["sentiment_coverage"] == 1.0
    assert row["topic_coverage"] == 1.0
    assert row["entity_coverage"] == 0.5
    assert row["avg_sentiment"] == -0.3
```

- [x] **Step 2: Create processor script**

Create `backend/scripts/historical_process_partition.py`:

```python
from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOPIC_HINTS = {
    "ENERGY": "energy-grid-instability",
    "ENV_CLIMATECHANGE": "water-stress-drought",
    "PROTEST": "labor-strike-disruption",
    "ARMEDCONFLICT": "armed-conflict-escalation",
}


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def infer_topic_slug(row: dict[str, Any]) -> str:
    headline = (row.get("headline") or "").lower()
    themes = {str(t).upper() for t in row.get("themes") or []}
    if "energy" in headline or "grid" in headline or "blackout" in headline:
        return "energy-grid-instability"
    for theme, slug in TOPIC_HINTS.items():
        if theme in themes:
            return slug
    return "general-monitoring"


def build_daily_topic_country_rows(
    rows: list[dict[str, Any]],
    *,
    model_version: str,
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        ts_raw = row.get("timestamp") or row.get("created_at")
        if not ts_raw:
            continue
        day = _parse_ts(str(ts_raw)).date().isoformat()
        topic_slug = infer_topic_slug(row)
        country_code = (row.get("country_code") or "XX").upper()
        source_family = row.get("source_family") or "unknown"
        signal_class = row.get("signal_class") or "unknown"
        key = (day, topic_slug, country_code, source_family, signal_class)
        bucket = buckets.setdefault(
            key,
            {
                "day": day,
                "topic_slug": topic_slug,
                "country_code": country_code,
                "source_family": source_family,
                "signal_class": signal_class,
                "signal_count": 0,
                "sentiment_sum": 0.0,
                "sentiment_n": 0,
                "topic_n": 0,
                "entity_n": 0,
                "model_version": model_version,
            },
        )
        bucket["signal_count"] += 1
        if row.get("nlp_sentiment") is not None:
            bucket["sentiment_sum"] += float(row["nlp_sentiment"])
            bucket["sentiment_n"] += 1
        if topic_slug != "general-monitoring":
            bucket["topic_n"] += 1
        if row.get("nlp_persons"):
            bucket["entity_n"] += 1

    output = []
    for bucket in buckets.values():
        count = bucket["signal_count"]
        sentiment_n = bucket.pop("sentiment_n")
        sentiment_sum = bucket.pop("sentiment_sum")
        topic_n = bucket.pop("topic_n")
        entity_n = bucket.pop("entity_n")
        bucket["avg_sentiment"] = round(sentiment_sum / sentiment_n, 4) if sentiment_n else None
        bucket["sentiment_coverage"] = round(sentiment_n / count, 4)
        bucket["topic_coverage"] = round(topic_n / count, 4)
        bucket["entity_coverage"] = round(entity_n / count, 4)
        bucket["local_voice_ratio"] = None
        bucket["source_diversity"] = None
        bucket["evidence_sample_count"] = 0
        output.append(bucket)
    return sorted(output, key=lambda r: (r["day"], r["topic_slug"], r["country_code"]))


def iter_jsonl_gzip(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process local Atlas archive partition")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-version", default="atlas-hist-v1")
    args = parser.parse_args()

    rows = list(iter_jsonl_gzip(Path(args.input)))
    aggregate_rows = build_daily_topic_country_rows(rows, model_version=args.model_version)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"rows": aggregate_rows}, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"input_rows": len(rows), "aggregate_rows": len(aggregate_rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [x] **Step 3: Run targeted tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_historical_processing.py -q
```

Expected: `3 passed`.

- [x] **Step 4: Smoke process one archive partition**

Status 2026-05-21: processed
`/Users/pedro/AtlasArchive/cutovers/2026-05-20/signals/year=2026/month=05/day=19/source_family=mixed/part-11758c4c6f83.jsonl.gz`.
Result: `185,163` input rows -> `1,728` aggregate rows at
`docs/research/processed-historical-sync/2026-05-19-topic-country.json`.

Run:

```bash
cd backend
.venv/bin/python -m scripts.historical_process_partition \
  --input /Users/pedro/AtlasArchive/cutovers/2026-05-20/signals/year=2026/month=05/day=19/source_family=mixed/part-11758c4c6f83.jsonl.gz \
  --output docs/research/processed-historical-sync/2026-05-19-topic-country.json \
  --model-version atlas-hist-v1
```

Expected: JSON output with `input_rows` around `185163` and `aggregate_rows > 0`.

- [x] **Step 5: Commit**

```bash
git add backend/scripts/historical_process_partition.py backend/tests/test_historical_processing.py docs/research/processed-historical-sync/
git commit -m "feat(data): process archive partitions into historical aggregates"
```

## Phase 3: Idempotent Supabase Sync

- [x] **Step 1: Add sync payload test**

Extend `backend/tests/test_historical_processing.py`:

```python
from scripts.historical_sync import build_upsert_payload


def test_build_upsert_payload_preserves_primary_key_fields():
    rows = [{
        "day": "2026-05-19",
        "topic_slug": "energy-grid-instability",
        "country_code": "CO",
        "source_family": "gdelt",
        "signal_class": "reporting",
        "signal_count": 2,
        "avg_sentiment": -0.3,
        "sentiment_coverage": 1.0,
        "topic_coverage": 1.0,
        "entity_coverage": 0.5,
        "local_voice_ratio": None,
        "source_diversity": None,
        "evidence_sample_count": 0,
        "model_version": "atlas-hist-v1",
    }]

    payload = build_upsert_payload(rows)

    assert payload[0]["day"] == "2026-05-19"
    assert payload[0]["topic_slug"] == "energy-grid-instability"
    assert payload[0]["model_version"] == "atlas-hist-v1"
```

- [x] **Step 2: Create sync script**

Create `backend/scripts/historical_sync.py`:

```python
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import asyncpg


UPSERT_SQL = """
INSERT INTO historical_topic_country_daily (
    day, topic_slug, country_code, source_family, signal_class, signal_count,
    avg_sentiment, sentiment_coverage, topic_coverage, entity_coverage,
    local_voice_ratio, source_diversity, evidence_sample_count, model_version, updated_at
)
VALUES (
    $1::date, $2, $3, $4, $5, $6,
    $7, $8, $9, $10,
    $11, $12, $13, $14, NOW()
)
ON CONFLICT (day, topic_slug, country_code, source_family, signal_class, model_version)
DO UPDATE SET
    signal_count = EXCLUDED.signal_count,
    avg_sentiment = EXCLUDED.avg_sentiment,
    sentiment_coverage = EXCLUDED.sentiment_coverage,
    topic_coverage = EXCLUDED.topic_coverage,
    entity_coverage = EXCLUDED.entity_coverage,
    local_voice_ratio = EXCLUDED.local_voice_ratio,
    source_diversity = EXCLUDED.source_diversity,
    evidence_sample_count = EXCLUDED.evidence_sample_count,
    updated_at = NOW()
"""


def build_upsert_payload(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    required = {"day", "topic_slug", "country_code", "source_family", "signal_class", "model_version"}
    payload = []
    for row in rows:
        missing = required - set(row)
        if missing:
            raise ValueError(f"Historical aggregate row missing fields: {sorted(missing)}")
        payload.append(dict(row))
    return payload


async def sync_rows(rows: list[dict[str, Any]]) -> int:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("SET statement_timeout = 60000")
        payload = build_upsert_payload(rows)
        async with conn.transaction():
            for row in payload:
                await conn.execute(
                    UPSERT_SQL,
                    row["day"],
                    row["topic_slug"],
                    row["country_code"],
                    row["source_family"],
                    row["signal_class"],
                    int(row["signal_count"]),
                    row.get("avg_sentiment"),
                    float(row["sentiment_coverage"]),
                    float(row["topic_coverage"]),
                    float(row["entity_coverage"]),
                    row.get("local_voice_ratio"),
                    row.get("source_diversity"),
                    int(row.get("evidence_sample_count") or 0),
                    row["model_version"],
                )
        return len(payload)
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync processed historical aggregates to Supabase")
    parser.add_argument("--input", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = build_upsert_payload(data["rows"])
    if args.dry_run:
        print(json.dumps({"dry_run": True, "rows": len(rows)}, sort_keys=True))
        return
    inserted = asyncio.run(sync_rows(rows))
    print(json.dumps({"dry_run": False, "rows": inserted}, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [x] **Step 3: Run tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_historical_processing.py -q
```

Expected: `4 passed`.

- [x] **Step 4: Dry-run sync artifact**

Status 2026-05-21: dry-run accepted the processed artifact and reported
`{"dry_run": true, "rows": 1728}`.

Run:

```bash
cd backend
.venv/bin/python -m scripts.historical_sync \
  --artifact ../docs/research/processed-historical-sync/2026-05-19-topic-country.json \
  --dry-run
```

Expected: `{"dry_run": true, "rows": <positive number>}`.

- [x] **Step 5: Commit**

Status 2026-05-21: live sync completed using Fly runtime `DATABASE_URL`.
Result: `{"dry_run": false, "rows": 1728}`. Supabase verification for
`2026-05-19` / `atlas-hist-v1`: `1,728` rows and `185,163` summed
`signal_count`.

```bash
git add backend/scripts/historical_sync.py backend/tests/test_historical_processing.py
git commit -m "feat(data): sync processed historical aggregates"
```

## Phase 4: API Bridge For Long Windows

- [x] **Step 1: Add briefing shape test**

Create or extend `backend/tests/test_briefing_performance_shape.py`:

```python
from pathlib import Path


def test_briefing_long_windows_use_historical_processed_tables():
    source = Path("app/routers/briefing.py").read_text()

    assert "historical_topic_country_daily" in source
    assert "hours > 24" in source or "use_historical" in source
```

- [x] **Step 2: Add helper in briefing router**

Modify `backend/app/routers/briefing.py` with a helper:

```python
def _use_historical_processed(hours: int) -> bool:
    return hours > 24
```

- [x] **Step 3: Route long-window `top_themes` to historical table**

Status 2026-05-21: `top_themes_historical` uses
`historical_topic_country_daily` for `hours > 24`, filters by
`BRIEFING_HISTORICAL_MODEL_VERSION` (`atlas-hist-v1` default), and returns
coverage/source metadata.

In `get_briefing`, branch `top_themes`:

```python
if _use_historical_processed(hours):
    top_themes = await _fetch_section(conn, degraded_segments, "top_themes_historical", """
        SELECT topic_slug AS theme, SUM(signal_count)::bigint AS count
        FROM historical_topic_country_daily
        WHERE day >= (CURRENT_DATE - CEIL($1::numeric / 24)::int)
        GROUP BY topic_slug
        ORDER BY count DESC
        LIMIT 10
    """, hours)
else:
    top_themes = await _fetch_section(conn, degraded_segments, "top_themes", """
        SELECT theme, SUM(signal_count)::bigint as count
        FROM theme_hourly_v2
        WHERE hour > NOW() - ($1::int * INTERVAL '1 hour')
        GROUP BY theme ORDER BY count DESC LIMIT 10
    """, hours)
```

- [x] **Step 4: Run backend tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_briefing_performance_shape.py tests/test_historical_processing.py -q
```

Expected: all selected tests pass.

- [x] **Step 5: Commit**

```bash
git add backend/app/routers/briefing.py backend/tests/test_briefing_performance_shape.py
git commit -m "feat(api): serve long-window briefing from historical aggregates"
```

## Phase 5: Frontend Coverage Badge

- [x] **Step 1: Extend `BriefingData` type**

Modify `frontend-v2/src/pages/BriefNewspaper.tsx`:

```ts
type HistoricalCoverage = {
  source: 'hot' | 'historical_processed'
  sentimentCoverage?: number
  topicCoverage?: number
  modelVersion?: string
}
```

Add `historical_coverage?: HistoricalCoverage` to `BriefingData`.

- [x] **Step 2: Render long-window coverage note**

In the briefing header area, render:

```tsx
{data?.historical_coverage?.source === 'historical_processed' && (
  <div className="brief-coverage-note">
    Historical processed coverage
    {typeof data.historical_coverage.topicCoverage === 'number'
      ? ` ${(data.historical_coverage.topicCoverage * 100).toFixed(0)}%`
      : ''}
  </div>
)}
```

- [x] **Step 3: Add CSS**

Modify `frontend-v2/src/pages/BriefNewspaper.css`:

```css
.brief-coverage-note {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 6px;
  color: var(--muted);
  font-size: 12px;
}
```

- [x] **Step 4: Build frontend**

Run:

```bash
cd frontend-v2
npm run build
```

Expected: Vite build passes.

- [x] **Step 5: Commit**

```bash
git add frontend-v2/src/pages/BriefNewspaper.tsx frontend-v2/src/pages/BriefNewspaper.css
git commit -m "feat(frontend): show historical processed coverage"
```

## Phase 6: Operations And Supabase Budget Guardrails

- [x] **Step 1: Add coverage report script**

Create `backend/scripts/historical_coverage_report.py`:

```python
from __future__ import annotations

import argparse
import asyncio
import json
import os

import asyncpg


REPORT_SQL = """
SELECT
    MIN(day)::text AS first_day,
    MAX(day)::text AS last_day,
    COUNT(*)::bigint AS aggregate_rows,
    SUM(signal_count)::bigint AS represented_signals,
    AVG(sentiment_coverage)::float AS avg_sentiment_coverage,
    AVG(topic_coverage)::float AS avg_topic_coverage,
    AVG(entity_coverage)::float AS avg_entity_coverage,
    COUNT(DISTINCT model_version)::int AS model_versions
FROM historical_topic_country_daily
"""


async def build_report() -> dict:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")
    conn = await asyncpg.connect(db_url)
    try:
        row = await conn.fetchrow(REPORT_SQL)
        return {k: (float(v) if isinstance(v, float) else v) for k, v in dict(row).items()}
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Report processed historical coverage")
    parser.parse_args()
    print(json.dumps(asyncio.run(build_report()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Document operating cadence**

Update `docs/superpowers/plans/2026-05-20-hot-cold-data-operating-model.md` with:

```text
Nightly cadence:
1. Verify local archive manifest.
2. Process yesterday's cold partition locally.
3. Sync compact historical aggregates/evidence samples to Supabase.
4. Run historical coverage report.
5. Keep Supabase raw retention at the hot-window policy.
```

- [x] **Step 3: Commit**

```bash
git add backend/scripts/historical_coverage_report.py docs/superpowers/plans/2026-05-20-hot-cold-data-operating-model.md
git commit -m "docs(data): add historical sync operating cadence"
```

## Verification Checklist

- [x] `cd backend && .venv/bin/python -m pytest tests/test_historical_processing.py -q`
- [x] `cd backend && .venv/bin/python -m pytest tests/test_briefing_performance_shape.py -q`
- [x] `cd frontend-v2 && npm run build`
- [x] Local archive still verifies:

```bash
cd backend
.venv/bin/python -m scripts.archive_verify \
  --archive-dir /Users/pedro/AtlasArchive/cutovers/2026-05-20
```

- [x] Supabase row budget check after sync:

Status 2026-05-21: `historical_coverage_report` against Supabase returned
`1,728` aggregate rows, `185,163` represented signals, `226` countries, and
`11` topics for the current historical processed baseline.

Updated 2026-05-21 after full cutover backfill: `historical_coverage_report`
against Supabase returned `22,711` aggregate rows, `2,128,070` represented
signals, `236` countries, `11` topics, average topic coverage `0.8052`,
average NLP sentiment coverage `0.1695`, and average entity coverage `0.5564`.
This exactly matches the verified local archive row count.

```sql
SELECT COUNT(*) FROM historical_topic_country_daily;
SELECT COUNT(*) FROM historical_evidence_samples;
SELECT COUNT(*) FROM signals_v2;
```

## Rollout Order

1. Schema and local processor.
2. One-day local processing dry run.
3. Sync one day to Supabase.
4. Read from API for `1w` top themes only.
5. Add frontend coverage badge.
6. Expand to country/topic/source/entity historical surfaces.
7. Revisit Fly worker size only after hot SLA is stable for 48h.

## Full Cutover Backfill — 2026-05-21

Added `backend/scripts/historical_backfill.py` to make the backfill repeatable
and idempotent. It discovers verified manifest records, writes missing daily
artifacts, and can sync existing artifacts with `--sync-existing --execute-sync`.

Commands used:

```bash
cd backend

.venv/bin/python -m scripts.historical_backfill \
  --archive-dir /Users/pedro/AtlasArchive/cutovers/2026-05-20 \
  --output-dir ../docs/research/processed-historical-sync \
  --start-day 2026-05-03 \
  --end-day 2026-05-20

DATABASE_URL="$DB_URL" .venv/bin/python -m scripts.historical_backfill \
  --archive-dir /Users/pedro/AtlasArchive/cutovers/2026-05-20 \
  --output-dir ../docs/research/processed-historical-sync \
  --start-day 2026-05-03 \
  --end-day 2026-05-20 \
  --sync-existing \
  --execute-sync
```

Result:

```text
days synced:         18
manifest rows:       2,128,070
aggregate rows:      22,711
first day:           2026-05-03
last day:            2026-05-20
model_version:       atlas-hist-v1
```

Production smoke after sync:

```text
/api/v2/briefing?hours=168
top_themes_source: historical_topic_country_daily
historical_coverage.source: historical_processed
historical_coverage.sentimentCoverage: 0.148
degraded_segments: ["top_sources"]
```

`top_sources` degradation is tracked separately in #194.

## Self-Review

- The plan avoids rehydrating raw historical rows into Supabase.
- The first API bridge is intentionally narrow: long-window briefing top themes.
- Local processing starts with daily aggregates, not hourly or per-row sync.
- Evidence samples are modeled separately so raw archive remains the source of truth.
- Fly worker sizing remains tied to hot SLA, not historical backlog.
