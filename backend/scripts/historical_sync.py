"""Sync processed historical artifacts into compact Supabase tables.

Country-code correction layer (2026-07-30): artifact rows are derived from
the IMMUTABLE external archive, which still carries the pre-b7ab7def FIPS/ISO
bug (Lebanon stored as LS, Serbia as raw GEC RB, ...). The corrections in
docs/research/country-code-remap/country-code-corrections-v1.json are applied
HERE, at the write boundary, GDELT-lane rows only (source_family
'gdelt'/'unknown' — see app/services/country_corrections.py for the measured
scope). Rows that land on the same PK after correction (e.g. an ex-LS Lebanon
aggregate beside a genuine override-path LB row) are merged with the
documented merge policy. Without this layer any re-sync from the archive
would re-poison historical_topic_country_daily.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.country_corrections import (  # noqa: E402
    correct_country_code,
    merge_daily_rows,
)


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

SOURCE_UPSERT_SQL = """
INSERT INTO historical_source_daily (
    day, source_domain, source_family, signal_class, signal_count,
    avg_sentiment, sentiment_coverage, model_version, updated_at
)
VALUES (
    $1::date, $2, $3, $4, $5,
    $6, $7, $8, NOW()
)
ON CONFLICT (day, source_domain, source_family, signal_class, model_version)
DO UPDATE SET
    signal_count = EXCLUDED.signal_count,
    avg_sentiment = EXCLUDED.avg_sentiment,
    sentiment_coverage = EXCLUDED.sentiment_coverage,
    updated_at = NOW()
"""

REQUIRED_FIELDS = {
    "day",
    "topic_slug",
    "country_code",
    "source_family",
    "signal_class",
    "signal_count",
    "sentiment_coverage",
    "topic_coverage",
    "entity_coverage",
    "evidence_sample_count",
    "model_version",
}

SOURCE_REQUIRED_FIELDS = {
    "day",
    "source_domain",
    "source_family",
    "signal_class",
    "signal_count",
    "sentiment_coverage",
    "model_version",
}


def build_upsert_payload(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = []
    for row in rows:
        missing = REQUIRED_FIELDS - set(row)
        if missing:
            raise ValueError(f"Historical aggregate row missing fields: {sorted(missing)}")
        payload.append(dict(row))
    return payload


def build_source_upsert_payload(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = []
    for row in rows:
        missing = SOURCE_REQUIRED_FIELDS - set(row)
        if missing:
            raise ValueError(f"Historical source row missing fields: {sorted(missing)}")
        payload.append(dict(row))
    return payload


def coerce_day(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Unsupported historical aggregate day value: {value!r}")


def apply_country_corrections(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply the corrections-v1 single-hop remap at the write boundary.

    GDELT-lane rows only (correct_country_code scopes on source_family);
    artifact rows that collide on the upsert PK after correction are merged
    (merge_daily_rows policy) so the executemany upsert never has two rows
    racing for one PK. Aggregate rows carry no headline, so the LS bucket
    goes wholesale to LB (the ~375:1 Liechtenstein residue is documented in
    the corrections artifact).
    """
    merged: dict[tuple, dict[str, Any]] = {}
    order: list[tuple] = []
    for row in rows:
        row = dict(row)
        row["country_code"] = correct_country_code(
            row["country_code"], source_family=row.get("source_family")
        )
        key = (
            coerce_day(row["day"]).isoformat(),
            row["topic_slug"],
            row["country_code"],
            row["source_family"],
            row["signal_class"],
            row["model_version"],
        )
        if key in merged:
            merged[key] = merge_daily_rows(merged[key], row)
        else:
            merged[key] = row
            order.append(key)
    return [merged[k] for k in order]


def load_artifact(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"Artifact missing rows array: {path}")
    return apply_country_corrections(build_upsert_payload(rows))


def load_source_artifact(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("source_rows", [])
    if not isinstance(rows, list):
        raise ValueError(f"Artifact source_rows must be an array: {path}")
    return build_source_upsert_payload(rows)


async def upsert_rows(database_url: str, rows: list[dict[str, Any]], *, batch_size: int = 1000) -> int:
    conn = await asyncpg.connect(database_url)
    try:
        total = 0
        for offset in range(0, len(rows), batch_size):
            batch = rows[offset : offset + batch_size]
            await conn.executemany(
                UPSERT_SQL,
                [
                    (
                        coerce_day(row["day"]),
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
                        int(row["evidence_sample_count"]),
                        row["model_version"],
                    )
                    for row in batch
                ],
            )
            total += len(batch)
        return total
    finally:
        await conn.close()


async def upsert_source_rows(
    database_url: str,
    rows: list[dict[str, Any]],
    *,
    batch_size: int = 1000,
) -> int:
    conn = await asyncpg.connect(database_url)
    try:
        total = 0
        for offset in range(0, len(rows), batch_size):
            batch = rows[offset : offset + batch_size]
            await conn.executemany(
                SOURCE_UPSERT_SQL,
                [
                    (
                        coerce_day(row["day"]),
                        row["source_domain"],
                        row["source_family"],
                        row["signal_class"],
                        int(row["signal_count"]),
                        row.get("avg_sentiment"),
                        float(row["sentiment_coverage"]),
                        row["model_version"],
                    )
                    for row in batch
                ],
            )
            total += len(batch)
        return total
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync processed historical Atlas artifact")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = load_artifact(Path(args.artifact))
    source_rows = load_source_artifact(Path(args.artifact))
    if args.dry_run:
        print(
            json.dumps(
                {"dry_run": True, "rows": len(rows), "source_rows": len(source_rows)},
                sort_keys=True,
            )
        )
        return
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required unless --dry-run is set")
    synced = asyncio.run(upsert_rows(args.database_url, rows))
    synced_source_rows = asyncio.run(upsert_source_rows(args.database_url, source_rows))
    print(
        json.dumps(
            {"dry_run": False, "rows": synced, "source_rows": synced_source_rows},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
