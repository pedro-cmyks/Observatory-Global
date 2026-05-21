"""Process and optionally sync verified archive partitions by UTC day."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from scripts.archive_common import MANIFEST_FILE, iter_manifest_records
from scripts.historical_process_partition import MODEL_VERSION_DEFAULT, iter_jsonl_gzip
from scripts.historical_process_partition import build_daily_source_rows, build_daily_topic_country_rows
from scripts.historical_sync import load_artifact, load_source_artifact, upsert_rows, upsert_source_rows


@dataclass(frozen=True)
class BackfillDay:
    day: date
    input_path: Path
    output_path: Path
    manifest_rows: int
    should_process: bool
    should_sync: bool


def _day_from_path(path: Path) -> date:
    year: int | None = None
    month: int | None = None
    day: int | None = None
    for part in path.parts:
        if part.startswith("day="):
            day = int(part.split("=", 1)[1])
        elif part.startswith("month="):
            month = int(part.split("=", 1)[1])
        elif part.startswith("year="):
            year = int(part.split("=", 1)[1])
    if year is None or month is None or day is None:
        raise ValueError(f"Archive path does not include year/month/day partitions: {path}")
    return date(year, month, day)


def _parse_day(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def discover_backfill_days(
    *,
    archive_dir: Path,
    output_dir: Path,
    start_day: date | None = None,
    end_day: date | None = None,
    force_process: bool = False,
    sync_existing: bool = False,
) -> list[BackfillDay]:
    records = sorted(iter_manifest_records(archive_dir), key=lambda record: record.from_ts)
    days: list[BackfillDay] = []

    for record in records:
        relative_path = Path(record.relative_path)
        input_path = archive_dir / relative_path
        day = _day_from_path(relative_path)
        if start_day and day < start_day:
            continue
        if end_day and day > end_day:
            continue

        output_path = output_dir / f"{day.isoformat()}-topic-country.json"
        should_process = force_process or not output_path.exists()
        should_sync = sync_existing or should_process
        days.append(
            BackfillDay(
                day=day,
                input_path=input_path,
                output_path=output_path,
                manifest_rows=record.row_count,
                should_process=should_process,
                should_sync=should_sync,
            )
        )

    return days


def process_partition(day: BackfillDay, *, model_version: str) -> dict[str, Any]:
    rows = list(iter_jsonl_gzip(day.input_path))
    aggregate_rows = build_daily_topic_country_rows(rows, model_version=model_version)
    source_rows = build_daily_source_rows(rows, model_version=model_version)
    day.output_path.parent.mkdir(parents=True, exist_ok=True)
    day.output_path.write_text(
        json.dumps(
            {
                "input": str(day.input_path.resolve()),
                "model_version": model_version,
                "input_rows": len(rows),
                "manifest_rows": day.manifest_rows,
                "aggregate_rows": len(aggregate_rows),
                "source_aggregate_rows": len(source_rows),
                "rows": aggregate_rows,
                "source_rows": source_rows,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return {
        "day": day.day.isoformat(),
        "processed": True,
        "input_rows": len(rows),
        "manifest_rows": day.manifest_rows,
        "aggregate_rows": len(aggregate_rows),
        "source_aggregate_rows": len(source_rows),
        "output": str(day.output_path),
    }


async def sync_artifact(database_url: str, artifact_path: Path) -> dict[str, Any]:
    rows = load_artifact(artifact_path)
    source_rows = load_source_artifact(artifact_path)
    synced = await upsert_rows(database_url, rows)
    synced_source_rows = await upsert_source_rows(database_url, source_rows) if source_rows else 0
    return {
        "artifact": str(artifact_path),
        "synced_rows": synced,
        "synced_source_rows": synced_source_rows,
    }


async def run_backfill(args: argparse.Namespace) -> dict[str, Any]:
    archive_dir = Path(args.archive_dir).expanduser()
    output_dir = Path(args.output_dir)
    if not (archive_dir / MANIFEST_FILE).exists():
        raise SystemExit(f"Archive manifest not found: {archive_dir / MANIFEST_FILE}")

    days = discover_backfill_days(
        archive_dir=archive_dir,
        output_dir=output_dir,
        start_day=_parse_day(args.start_day),
        end_day=_parse_day(args.end_day),
        force_process=args.force_process,
        sync_existing=args.sync_existing,
    )
    if not days:
        return {"days": [], "processed_days": 0, "synced_days": 0, "dry_run": args.dry_run}

    database_url = args.database_url
    if args.execute_sync and not database_url:
        raise SystemExit("DATABASE_URL or --database-url is required with --execute-sync")

    results: list[dict[str, Any]] = []
    for day in days:
        result = {
            "day": day.day.isoformat(),
            "input": str(day.input_path),
            "output": str(day.output_path),
            "manifest_rows": day.manifest_rows,
            "should_process": day.should_process,
            "should_sync": day.should_sync,
        }
        if not args.dry_run and day.should_process:
            result.update(process_partition(day, model_version=args.model_version))
        elif not args.dry_run and day.output_path.exists():
            artifact = json.loads(day.output_path.read_text(encoding="utf-8"))
            result.update(
                {
                    "processed": False,
                    "input_rows": artifact.get("input_rows"),
                    "aggregate_rows": artifact.get("aggregate_rows"),
                    "source_aggregate_rows": artifact.get("source_aggregate_rows"),
                }
            )

        if not args.dry_run and args.execute_sync and day.should_sync:
            result.update(await sync_artifact(database_url, day.output_path))
        results.append(result)

    return {
        "archive_dir": str(archive_dir),
        "output_dir": str(output_dir),
        "dry_run": args.dry_run,
        "execute_sync": args.execute_sync,
        "days": results,
        "processed_days": sum(1 for item in results if item.get("processed")),
        "synced_days": sum(1 for item in results if item.get("synced_rows") is not None),
        "manifest_rows": sum(int(item.get("manifest_rows") or 0) for item in results),
        "aggregate_rows": sum(int(item.get("aggregate_rows") or 0) for item in results),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill processed historical Atlas days")
    parser.add_argument(
        "--archive-dir",
        default="/Users/pedro/AtlasArchive/cutovers/2026-05-20",
        help="Verified archive root containing manifest.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/research/processed-historical-sync",
        help="Directory for daily processed artifacts",
    )
    parser.add_argument("--start-day", help="Inclusive UTC day, e.g. 2026-05-03")
    parser.add_argument("--end-day", help="Inclusive UTC day, e.g. 2026-05-20")
    parser.add_argument("--model-version", default=MODEL_VERSION_DEFAULT)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-process", action="store_true")
    parser.add_argument("--sync-existing", action="store_true")
    parser.add_argument("--execute-sync", action="store_true")
    return parser.parse_args()


def main() -> None:
    result = asyncio.run(run_backfill(parse_args()))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
