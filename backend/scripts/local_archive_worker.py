"""Local Atlas archive worker for the 00:00-06:00 UTC-5 maintenance window."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.archive_common import parse_timestamp
from scripts.archive_export import export_range
from scripts.nlp_sla_report import build_report


DEFAULT_TZ = "America/Bogota"
DEFAULT_START = "00:00"
DEFAULT_END = "06:00"


def parse_clock(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(hour=int(hour), minute=int(minute))


def is_inside_window(now: datetime, start: time, end: time) -> bool:
    current = now.timetz().replace(tzinfo=None)
    if start <= end:
        return start <= current < end
    return current >= start or current < end


async def run_worker(args: argparse.Namespace) -> dict:
    tz_name = args.timezone or os.environ.get("LOCAL_WORKER_TIMEZONE") or DEFAULT_TZ
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    start = parse_clock(args.window_start or os.environ.get("LOCAL_WORKER_WINDOW_START") or DEFAULT_START)
    end = parse_clock(args.window_end or os.environ.get("LOCAL_WORKER_WINDOW_END") or DEFAULT_END)
    inside = is_inside_window(now, start, end)

    result = {
        "timezone": tz_name,
        "window": f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}",
        "inside_window": inside,
        "forced": bool(args.force),
        "ran": False,
    }
    if not inside and not args.force:
        result["message"] = "Outside maintenance window; use --force for a manual run."
        return result

    result["ran"] = True
    result["sla_report"] = await build_report(hours=args.hours, limit=args.limit)

    if args.export_from and args.export_to:
        archive_dir = args.archive_dir or os.environ.get("ATLAS_ARCHIVE_DIR")
        if not archive_dir:
            raise RuntimeError("ATLAS_ARCHIVE_DIR or --archive-dir is required for export")
        exported = await export_range(
            archive_dir=Path(archive_dir).expanduser(),
            from_ts=parse_timestamp(args.export_from),
            to_ts=parse_timestamp(args.export_to),
            source_family=args.source_family,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
        result["export"] = {
            "from": args.export_from,
            "to": args.export_to,
            "source_family": args.source_family or "mixed",
            "dry_run": bool(args.dry_run),
            "rows": exported,
        }
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas local hot/cold archive worker")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--timezone", default=None)
    parser.add_argument("--window-start", default=None)
    parser.add_argument("--window-end", default=None)
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--archive-dir", default=None)
    parser.add_argument("--export-from", default=None)
    parser.add_argument("--export-to", default=None)
    parser.add_argument("--source-family", default=None)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    result = asyncio.run(run_worker(_parse_args()))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
