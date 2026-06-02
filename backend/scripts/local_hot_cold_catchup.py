"""End-to-end local hot/cold catch-up runner for Atlas.

The runner keeps Supabase as the hot processed store and Pedro's machine as the
local archive/processed-history worker. It is deliberately conservative:

- dry-run by default;
- archive verification is mandatory before sync/prune;
- live prune requires an explicit irreversible-delete flag;
- overlapping UTC days are recomputed from all verified local archive roots so
  compact historical aggregates are not accidentally overwritten by a partial
  incremental archive.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import asyncpg

from scripts.archive_common import MANIFEST_FILE, ArchiveManifestRecord, iter_manifest_records, parse_timestamp
from scripts.archive_export import export_range
from scripts.archive_plan import build_plan
from scripts.archive_verify import verify_archive
from scripts.historical_process_partition import (
    MODEL_VERSION_DEFAULT,
    build_daily_source_rows,
    build_daily_topic_country_rows,
    iter_jsonl_gzip,
)
from scripts.historical_sync import upsert_rows, upsert_source_rows
from scripts.local_archive_worker import DEFAULT_END, DEFAULT_START, DEFAULT_TZ, is_inside_window, parse_clock
from scripts.nlp_sla_report import build_report
from scripts.prune_archived_signals import prune_archived


DEFAULT_ARCHIVE_ROOT = "/Users/pedro/AtlasArchive"
DEFAULT_OUTPUT_DIR = "docs/research/processed-historical-sync"
DEFAULT_APP_NAME = "atlas-api-pedro"
EXPORT_RETRY_ATTEMPTS = 3
EXPORT_RETRY_BASE_DELAY_SECONDS = 5.0


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArchiveRoot:
    path: Path
    records: tuple[ArchiveManifestRecord, ...]


def _utc_day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _record_window(record: ArchiveManifestRecord) -> tuple[datetime, datetime]:
    return parse_timestamp(record.from_ts), parse_timestamp(record.to_ts)


def _record_overlaps_day(record: ArchiveManifestRecord, day: date) -> bool:
    day_start, day_end = _utc_day_bounds(day)
    from_ts, to_ts = _record_window(record)
    return from_ts < day_end and to_ts > day_start


def days_touched_by_records(records: Iterable[ArchiveManifestRecord]) -> list[date]:
    days: set[date] = set()
    for record in records:
        from_ts, to_ts = _record_window(record)
        cursor = from_ts.date()
        last = (to_ts - timedelta(microseconds=1)).date()
        while cursor <= last:
            days.add(cursor)
            cursor = cursor + timedelta(days=1)
    return sorted(days)


def discover_archive_roots(
    archive_root: Path,
    *,
    include_roots: Iterable[Path] = (),
) -> list[ArchiveRoot]:
    """Discover verified archive roots that can contribute rows to a day recompute."""
    candidates: list[Path] = []
    for parent_name in ("cutovers", "incremental"):
        parent = archive_root / parent_name
        if parent.exists():
            candidates.extend(path for path in sorted(parent.iterdir()) if path.is_dir())
    candidates.extend(include_roots)

    seen: set[Path] = set()
    roots: list[ArchiveRoot] = []
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in seen or not (resolved / MANIFEST_FILE).exists():
            continue
        seen.add(resolved)
        records = tuple(
            record for record in iter_manifest_records(resolved) if record.kind == "signals_v2_export"
        )
        if records:
            roots.append(ArchiveRoot(path=resolved, records=records))
    return roots


def collect_rows_for_day(archive_roots: Iterable[ArchiveRoot], day: date) -> list[dict[str, Any]]:
    """Read all archived rows for a UTC day across archive roots, deduped by signal id."""
    rows_by_id: dict[str, dict[str, Any]] = {}
    anonymous_rows: list[dict[str, Any]] = []
    day_start, day_end = _utc_day_bounds(day)

    for root in archive_roots:
        for record in root.records:
            if not _record_overlaps_day(record, day):
                continue
            path = root.path / record.relative_path
            for row in iter_jsonl_gzip(path):
                ts_raw = row.get("timestamp") or row.get("created_at")
                if not ts_raw:
                    continue
                ts = parse_timestamp(str(ts_raw))
                if ts < day_start or ts >= day_end:
                    continue
                signal_id = row.get("id")
                if signal_id is None:
                    anonymous_rows.append(row)
                else:
                    rows_by_id[str(signal_id)] = row

    rows = list(rows_by_id.values()) + anonymous_rows
    return sorted(rows, key=lambda item: (str(item.get("timestamp") or ""), str(item.get("id") or "")))


async def process_and_sync_days(
    *,
    archive_roots: list[ArchiveRoot],
    days: list[date],
    output_dir: Path,
    model_version: str,
    database_url: str | None,
    execute_sync: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for day in days:
        rows = collect_rows_for_day(archive_roots, day)
        topic_rows = build_daily_topic_country_rows(rows, model_version=model_version)
        source_rows = build_daily_source_rows(rows, model_version=model_version)
        output_path = output_dir / f"{day.isoformat()}-topic-country.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "input": "combined-local-archive-roots",
                    "archive_roots": [str(root.path) for root in archive_roots],
                    "model_version": model_version,
                    "input_rows": len(rows),
                    "aggregate_rows": len(topic_rows),
                    "source_aggregate_rows": len(source_rows),
                    "rows": topic_rows,
                    "source_rows": source_rows,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        result: dict[str, Any] = {
            "day": day.isoformat(),
            "input_rows": len(rows),
            "aggregate_rows": len(topic_rows),
            "source_aggregate_rows": len(source_rows),
            "artifact": str(output_path),
            "synced": False,
        }
        if execute_sync:
            if not database_url:
                raise RuntimeError("DATABASE_URL or --database-url is required with --execute")
            result["synced_rows"] = await upsert_rows(database_url, topic_rows)
            result["synced_source_rows"] = await upsert_source_rows(database_url, source_rows)
            result["synced"] = True
        results.append(result)
    return results


async def vacuum_signals(database_url: str) -> None:
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute("VACUUM (ANALYZE) public.signals_v2")
    finally:
        await conn.close()


def _is_transient_export_error(exc: BaseException) -> bool:
    return isinstance(
        exc,
        (
            asyncpg.ConnectionDoesNotExistError,
            asyncpg.PostgresConnectionError,
            ConnectionResetError,
            OSError,
        ),
    )


async def _export_range_with_retries(
    *,
    archive_dir: Path,
    from_ts: datetime,
    to_ts: datetime,
    source_family: str | None,
    dry_run: bool,
    batch_size: int,
    attempts: int = EXPORT_RETRY_ATTEMPTS,
    base_delay_seconds: float = EXPORT_RETRY_BASE_DELAY_SECONDS,
    exporter=export_range,
    sleeper=asyncio.sleep,
) -> int:
    """Retry one archive export batch after transient DB connection loss."""
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await exporter(
                archive_dir=archive_dir,
                from_ts=from_ts,
                to_ts=to_ts,
                source_family=source_family,
                dry_run=dry_run,
                batch_size=batch_size,
            )
        except BaseException as exc:
            if not _is_transient_export_error(exc) or attempt >= attempts:
                raise
            last_exc = exc
            delay = base_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Transient archive export failure for %s -> %s (attempt %s/%s): %s; "
                "retrying in %.1fs",
                from_ts.isoformat(),
                to_ts.isoformat(),
                attempt,
                attempts,
                exc,
                delay,
            )
            await sleeper(delay)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Archive export retry loop exited unexpectedly")


def _new_incremental_dir(archive_root: Path, now: datetime, run_id: str | None) -> Path:
    suffix = run_id or uuid.uuid4().hex[:8]
    return archive_root / "incremental" / f"{now.date().isoformat()}-{suffix}"


async def run_catchup(args: argparse.Namespace) -> dict[str, Any]:
    database_url = args.database_url or os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")

    tz_name = args.timezone or os.getenv("LOCAL_WORKER_TIMEZONE") or DEFAULT_TZ
    now = datetime.now(ZoneInfo(tz_name))
    start = parse_clock(args.window_start or os.getenv("LOCAL_WORKER_WINDOW_START") or DEFAULT_START)
    end = parse_clock(args.window_end or os.getenv("LOCAL_WORKER_WINDOW_END") or DEFAULT_END)
    inside_window = is_inside_window(now, start, end)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.older_than_hours)
    plan = await build_plan(from_ts=None, to_ts=cutoff, max_days=args.max_days)
    planned_rows = int(plan["planned_rows"])

    should_run = inside_window or args.force or (
        args.allow_catch_up_outside_window and planned_rows >= args.min_catch_up_rows
    )
    result: dict[str, Any] = {
        "timezone": tz_name,
        "window": f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}",
        "inside_window": inside_window,
        "forced": bool(args.force),
        "allow_catch_up_outside_window": bool(args.allow_catch_up_outside_window),
        "execute": bool(args.execute),
        "execute_prune": bool(args.execute_prune),
        "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
        "plan": plan,
        "ran": False,
    }
    if not should_run:
        result["message"] = "Outside maintenance window and catch-up threshold not met."
        result["sla_report"] = await build_report(hours=args.sla_hours, limit=args.sla_limit)
        return result
    if planned_rows <= 0:
        result["message"] = "No rows older than the hot retention cutoff."
        result["sla_report"] = await build_report(hours=args.sla_hours, limit=args.sla_limit)
        return result

    result["ran"] = True
    if not args.execute:
        result["message"] = "Dry-run only. Use --execute to export and sync; add --execute-prune for live prune."
        result["sla_report"] = await build_report(hours=args.sla_hours, limit=args.sla_limit)
        return result

    archive_root = Path(args.archive_root).expanduser()
    incremental_dir = Path(args.archive_dir).expanduser() if args.archive_dir else _new_incremental_dir(
        archive_root,
        now,
        args.run_id,
    )
    exported_rows = 0
    exports = []
    for batch in plan["batches"]:
        if int(batch["row_count"]) <= 0:
            continue
        rows = await _export_range_with_retries(
            archive_dir=incremental_dir,
            from_ts=parse_timestamp(batch["from"]),
            to_ts=parse_timestamp(batch["to"]),
            source_family=None,
            dry_run=False,
            batch_size=args.batch_size,
        )
        exported_rows += rows
        exports.append({**batch, "exported_rows": rows})

    result["archive_dir"] = str(incremental_dir)
    result["exports"] = exports
    result["exported_rows"] = exported_rows
    if exported_rows != planned_rows:
        raise RuntimeError(f"Exported rows {exported_rows} did not match planned rows {planned_rows}")

    verification = verify_archive(incremental_dir)
    result["verification"] = verification
    if not verification.get("ok"):
        raise RuntimeError("Archive verification failed; refusing sync/prune")

    archive_roots = discover_archive_roots(archive_root, include_roots=[incremental_dir])
    affected_days = days_touched_by_records(iter_manifest_records(incremental_dir))
    result["affected_days"] = [day.isoformat() for day in affected_days]
    result["archive_roots"] = [str(root.path) for root in archive_roots]
    result["processed_days"] = await process_and_sync_days(
        archive_roots=archive_roots,
        days=affected_days,
        output_dir=Path(args.output_dir),
        model_version=args.model_version,
        database_url=database_url,
        execute_sync=True,
    )

    prune_dry_run = await prune_archived(
        archive_dir=incremental_dir,
        cutoff=cutoff,
        execute=False,
        max_rows=args.max_prune_rows,
    )
    result["prune_dry_run"] = prune_dry_run
    if args.execute_prune:
        if not args.i_understand_irreversible_delete:
            raise RuntimeError("Live prune requires --i-understand-irreversible-delete")
        if int(prune_dry_run["archive_rows"]) != exported_rows:
            raise RuntimeError("Prune archive rows do not match exported rows; refusing live prune")
        if int(prune_dry_run["db_candidate_rows"]) != exported_rows:
            raise RuntimeError("Prune DB candidate rows do not match exported rows; refusing live prune")
        result["prune"] = await prune_archived(
            archive_dir=incremental_dir,
            cutoff=cutoff,
            execute=True,
            max_rows=args.max_prune_rows,
        )
        if args.vacuum_after_prune:
            await vacuum_signals(database_url)
            result["vacuum_analyze_signals_v2"] = True
    else:
        result["message"] = "Export/sync completed; live prune skipped because --execute-prune was not set."

    result["sla_report"] = await build_report(hours=args.sla_hours, limit=args.sla_limit)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas local hot/cold catch-up orchestrator")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"))
    parser.add_argument("--archive-root", default=os.getenv("ATLAS_ARCHIVE_ROOT") or DEFAULT_ARCHIVE_ROOT)
    parser.add_argument("--archive-dir", default=None, help="Specific incremental archive output dir")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--older-than-hours", type=int, default=24)
    parser.add_argument("--max-days", type=int, default=None)
    parser.add_argument("--max-prune-rows", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--model-version", default=MODEL_VERSION_DEFAULT)
    parser.add_argument("--timezone", default=None)
    parser.add_argument("--window-start", default=None)
    parser.add_argument("--window-end", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-catch-up-outside-window", action="store_true")
    parser.add_argument("--min-catch-up-rows", type=int, default=1000)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--execute-prune", action="store_true")
    parser.add_argument("--i-understand-irreversible-delete", action="store_true")
    parser.add_argument("--no-vacuum-after-prune", dest="vacuum_after_prune", action="store_false")
    parser.add_argument("--sla-hours", type=int, default=24)
    parser.add_argument("--sla-limit", type=int, default=20)
    parser.set_defaults(vacuum_after_prune=True)
    return parser.parse_args()


def main() -> None:
    result = asyncio.run(run_catchup(parse_args()))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
