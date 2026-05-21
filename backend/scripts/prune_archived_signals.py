"""Prune signals_v2 rows only for verified local archive manifest ranges.

This script defaults to dry-run. Live deletion requires both --execute and the
explicit --i-understand-irreversible-delete flag.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import asyncpg

from scripts.archive_common import iter_manifest_records, parse_timestamp
from scripts.archive_verify import verify_archive


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [archive-prune] %(levelname)s %(message)s")

BATCH_SIZE = 25_000

COUNT_RANGE_SQL = """
SELECT COUNT(*)::bigint
FROM signals_v2
WHERE timestamp >= $1
  AND timestamp < $2
"""

DELETE_RANGE_SQL = """
WITH victims AS (
    SELECT id
    FROM signals_v2
    WHERE timestamp >= $1
      AND timestamp < $2
    ORDER BY timestamp, id
    LIMIT $3
)
DELETE FROM signals_v2 WHERE id IN (SELECT id FROM victims)
"""


def covered_manifest_ranges(archive_dir: Path, cutoff: datetime) -> list[dict[str, Any]]:
    records = list(iter_manifest_records(archive_dir))
    ranges = []
    for record in records:
        if record.kind != "signals_v2_export":
            continue
        from_ts = parse_timestamp(record.from_ts)
        to_ts = parse_timestamp(record.to_ts)
        if to_ts > cutoff:
            continue
        ranges.append(
            {
                "from_ts": from_ts,
                "to_ts": to_ts,
                "source_family": record.source_family,
                "row_count": record.row_count,
                "relative_path": record.relative_path,
            }
        )
    return sorted(ranges, key=lambda item: (item["from_ts"], item["to_ts"], item["relative_path"]))


async def prune_archived(
    *,
    archive_dir: Path,
    cutoff: datetime,
    execute: bool,
    max_rows: int | None,
) -> dict[str, Any]:
    verification = verify_archive(archive_dir)
    if not verification["ok"]:
        return {
            "ok": False,
            "executed": False,
            "error": "archive_verification_failed",
            "verification": verification,
        }

    ranges = covered_manifest_ranges(archive_dir, cutoff)
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")

    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("SET statement_timeout = 60000")
        planned = []
        total_candidates = 0
        for item in ranges:
            candidate_count = int(await conn.fetchval(COUNT_RANGE_SQL, item["from_ts"], item["to_ts"]) or 0)
            total_candidates += candidate_count
            planned.append(
                {
                    "from": item["from_ts"].isoformat().replace("+00:00", "Z"),
                    "to": item["to_ts"].isoformat().replace("+00:00", "Z"),
                    "archive_rows": int(item["row_count"]),
                    "db_candidate_rows": candidate_count,
                    "relative_path": item["relative_path"],
                }
            )

        result: dict[str, Any] = {
            "ok": True,
            "executed": execute,
            "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
            "archive_dir": str(archive_dir),
            "range_count": len(ranges),
            "archive_rows": sum(int(item["row_count"]) for item in ranges),
            "db_candidate_rows": total_candidates,
            "max_rows": max_rows,
            "planned_ranges": planned[:50],
            "note": (
                "Only rows inside verified manifest ranges with to_ts <= cutoff are eligible. "
                "Product aggregate/correction/topic/NLP audit tables are not touched."
            ),
        }
        if not execute:
            return result

        deleted_total = 0
        started = time.monotonic()
        for item in ranges:
            while True:
                if max_rows is not None and deleted_total >= max_rows:
                    break
                batch_limit = BATCH_SIZE
                if max_rows is not None:
                    batch_limit = min(batch_limit, max_rows - deleted_total)
                tag = await conn.execute(DELETE_RANGE_SQL, item["from_ts"], item["to_ts"], batch_limit)
                batch_deleted = int(tag.split()[-1])
                if batch_deleted == 0:
                    break
                deleted_total += batch_deleted
                logger.info(
                    "Deleted batch=%s total=%s range=%s..%s",
                    f"{batch_deleted:,}",
                    f"{deleted_total:,}",
                    item["from_ts"].isoformat(),
                    item["to_ts"].isoformat(),
                )
            if max_rows is not None and deleted_total >= max_rows:
                break
        result["deleted_rows"] = deleted_total
        result["elapsed_seconds"] = round(time.monotonic() - started, 2)
        return result
    finally:
        await conn.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prune signals_v2 rows covered by verified archive")
    parser.add_argument("--archive-dir", default=os.environ.get("ATLAS_ARCHIVE_DIR"))
    parser.add_argument("--older-than-hours", type=int, default=24)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--i-understand-irreversible-delete", action="store_true")
    parser.add_argument("--max-rows", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.archive_dir:
        raise SystemExit("ATLAS_ARCHIVE_DIR or --archive-dir is required")
    if args.execute and not args.i_understand_irreversible_delete:
        raise SystemExit("Live prune requires --i-understand-irreversible-delete")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.older_than_hours)
    result = asyncio.run(
        prune_archived(
            archive_dir=Path(args.archive_dir).expanduser(),
            cutoff=cutoff,
            execute=bool(args.execute),
            max_rows=args.max_rows,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
