"""Export Supabase hot/cold signals into the local Atlas archive.

Usage:
    python -m scripts.archive_export --archive-dir "$ATLAS_ARCHIVE_DIR" \
      --from 2026-05-19T00:00:00Z --to 2026-05-20T00:00:00Z --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import asyncpg

from scripts.archive_common import (
    ARCHIVE_VERSION,
    ArchiveManifestRecord,
    append_manifest,
    normalize_row,
    parse_timestamp,
    partition_path,
)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [archive-export] %(levelname)s %(message)s")


EXPORT_COLUMNS = (
    "id",
    "timestamp",
    "created_at",
    "country_code",
    "source_name",
    "source_url",
    "headline",
    "themes",
    "persons",
    "sentiment",
    "source_family",
    "source_lang",
    "geo_confidence",
    "attribution_method",
    "is_state_media",
    "signal_class",
    "nlp_sentiment",
    "nlp_confidence",
    "nlp_framing",
    "nlp_persons",
    "nlp_processed_at",
    "nlp_method",
)


COUNT_SQL = """
SELECT COUNT(*) AS n
FROM signals_v2
WHERE timestamp >= $1
  AND timestamp < $2
  AND ($3::text IS NULL OR source_family = $3)
"""


FETCH_SQL = f"""
SELECT {", ".join(EXPORT_COLUMNS)}
FROM signals_v2
WHERE timestamp >= $1
  AND timestamp < $2
  AND ($3::text IS NULL OR source_family = $3)
ORDER BY timestamp ASC, id ASC
"""


async def export_range(
    *,
    archive_dir: Path,
    from_ts: datetime,
    to_ts: datetime,
    source_family: str | None,
    dry_run: bool,
    batch_size: int,
) -> int:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")

    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("SET statement_timeout = 30000")
        expected = int(await conn.fetchval(COUNT_SQL, from_ts, to_ts, source_family) or 0)
        logger.info(
            "Range %s -> %s source_family=%s expected=%s",
            from_ts.isoformat(),
            to_ts.isoformat(),
            source_family or "mixed",
            f"{expected:,}",
        )
        if dry_run:
            logger.info("Dry-run mode; no archive file written.")
            return expected

        job_id = uuid4().hex[:12]
        output_path = partition_path(archive_dir, from_ts, source_family, job_id)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        count = 0
        async with conn.transaction():
            rows = conn.cursor(FETCH_SQL, from_ts, to_ts, source_family, prefetch=batch_size)
            with gzip.open(output_path, "wt", encoding="utf-8") as handle:
                async for row in rows:
                    line = json.dumps(
                        normalize_row(row),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    digest.update(line.encode("utf-8"))
                    digest.update(b"\n")
                    handle.write(line)
                    handle.write("\n")
                    count += 1
        byte_count = output_path.stat().st_size

        relative = output_path.relative_to(archive_dir)
        append_manifest(
            archive_dir,
            ArchiveManifestRecord(
                archive_version=ARCHIVE_VERSION,
                kind="signals_v2_export",
                created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                from_ts=from_ts.isoformat().replace("+00:00", "Z"),
                to_ts=to_ts.isoformat().replace("+00:00", "Z"),
                source_family=source_family or "mixed",
                row_count=count,
                relative_path=str(relative),
                sha256=digest.hexdigest(),
                bytes=byte_count,
                command=" ".join(sys.argv),
            ),
        )
        logger.info("Wrote %s rows to %s", f"{count:,}", output_path)
        if count != expected:
            logger.warning("Expected %s rows but wrote %s rows", f"{expected:,}", f"{count:,}")
        return count
    finally:
        await conn.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas local archive exporter")
    parser.add_argument("--archive-dir", default=os.environ.get("ATLAS_ARCHIVE_DIR"))
    parser.add_argument("--from", dest="from_ts", required=True, help="Inclusive ISO timestamp")
    parser.add_argument("--to", dest="to_ts", required=True, help="Exclusive ISO timestamp")
    parser.add_argument("--source-family", default=None)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.archive_dir:
        raise SystemExit("ATLAS_ARCHIVE_DIR or --archive-dir is required")
    from_ts = parse_timestamp(args.from_ts)
    to_ts = parse_timestamp(args.to_ts)
    if to_ts <= from_ts:
        raise SystemExit("--to must be later than --from")
    asyncio.run(
        export_range(
            archive_dir=Path(args.archive_dir).expanduser(),
            from_ts=from_ts,
            to_ts=to_ts,
            source_family=args.source_family,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
    )


if __name__ == "__main__":
    main()
