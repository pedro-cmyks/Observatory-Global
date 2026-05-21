"""Plan cold archive export batches from Supabase without writing files."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg

from scripts.archive_common import parse_timestamp


PLAN_SQL = """
WITH bounds AS (
    SELECT
        $1::timestamptz AS from_ts,
        $2::timestamptz AS to_ts
),
daily AS (
    SELECT
        date_trunc('day', timestamp) AS day,
        COUNT(*)::bigint AS row_count,
        COUNT(*) FILTER (WHERE nlp_method IS NOT NULL OR nlp_processed_at IS NOT NULL)::bigint
            AS atlas_owned_rows,
        COUNT(*) FILTER (WHERE signal_class IS NOT NULL)::bigint AS classified_rows,
        COUNT(DISTINCT COALESCE(source_family, 'unknown'))::int AS source_family_count
    FROM signals_v2, bounds
    WHERE timestamp >= bounds.from_ts
      AND timestamp < bounds.to_ts
    GROUP BY 1
)
SELECT *
FROM daily
ORDER BY day ASC
"""


BOUNDS_SQL = """
SELECT
    MIN(timestamp) AS oldest_ts,
    MAX(timestamp) AS newest_ts,
    COUNT(*)::bigint AS rows
FROM signals_v2
WHERE timestamp < $1::timestamptz
"""


async def build_plan(
    *,
    from_ts: datetime | None,
    to_ts: datetime,
    max_days: int | None,
) -> dict[str, Any]:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("SET statement_timeout = 60000")
        bounds = dict(await conn.fetchrow(BOUNDS_SQL, to_ts))
        oldest = bounds["oldest_ts"]
        effective_from = from_ts or oldest
        if effective_from is None:
            effective_from = to_ts
        effective_from = effective_from.astimezone(timezone.utc)
        effective_to = to_ts.astimezone(timezone.utc)
        if max_days is not None:
            effective_to = min(effective_to, effective_from + timedelta(days=max_days))

        rows = await conn.fetch(PLAN_SQL, effective_from, effective_to)
        batches = []
        for row in rows:
            day = row["day"].astimezone(timezone.utc)
            batch_from = max(day, effective_from)
            batch_to = min(day + timedelta(days=1), effective_to)
            batches.append(
                {
                    "from": batch_from.isoformat().replace("+00:00", "Z"),
                    "to": batch_to.isoformat().replace("+00:00", "Z"),
                    "row_count": int(row["row_count"] or 0),
                    "atlas_owned_rows": int(row["atlas_owned_rows"] or 0),
                    "classified_rows": int(row["classified_rows"] or 0),
                    "source_family_count": int(row["source_family_count"] or 0),
                }
            )
        return {
            "cutoff": effective_to.isoformat().replace("+00:00", "Z"),
            "from": effective_from.isoformat().replace("+00:00", "Z"),
            "to": effective_to.isoformat().replace("+00:00", "Z"),
            "source": "signals_v2.timestamp",
            "total_candidate_rows_before_cutoff": int(bounds["rows"] or 0),
            "oldest_ts": (
                oldest.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                if oldest
                else None
            ),
            "newest_ts_before_cutoff": (
                bounds["newest_ts"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                if bounds["newest_ts"]
                else None
            ),
            "planned_rows": sum(batch["row_count"] for batch in batches),
            "batch_count": len(batches),
            "batches": batches,
        }
    finally:
        await conn.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan Atlas cold archive export batches")
    parser.add_argument("--from", dest="from_ts", default=None, help="Inclusive ISO timestamp")
    parser.add_argument("--to", dest="to_ts", default=None, help="Exclusive ISO timestamp")
    parser.add_argument("--older-than-hours", type=int, default=24)
    parser.add_argument("--max-days", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    to_ts = (
        parse_timestamp(args.to_ts)
        if args.to_ts
        else datetime.now(timezone.utc) - timedelta(hours=args.older_than_hours)
    )
    from_ts = parse_timestamp(args.from_ts) if args.from_ts else None
    result = asyncio.run(build_plan(from_ts=from_ts, to_ts=to_ts, max_days=args.max_days))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
