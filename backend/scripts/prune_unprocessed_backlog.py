"""
Prune unprocessed signals older than the NLP backfill window (ADR-0004).

Deletes rows in `signals_v2` where:
  - nlp_processed_at IS NULL  (never scored by transformer pipeline)
  - nlp_method IS NULL        (never scored by lexicon either)
  - created_at < NOW() - INTERVAL '<WINDOW_DAYS> days'

Runs in batches of 50K to avoid long-running transactions on a live table.

Safety:
  --dry-run prints expected counts without deleting.
  --max-rows caps total deletions in a single invocation.
  --window-days overrides the default 15-day boundary.

Usage:
    python -m scripts.prune_unprocessed_backlog --dry-run
    python -m scripts.prune_unprocessed_backlog --max-rows 2000000
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time

import asyncpg

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [prune] %(levelname)s %(message)s")

DEFAULT_WINDOW_DAYS = 15
BATCH_SIZE = 50_000


COUNT_SQL = """
SELECT COUNT(*) AS expected
FROM signals_v2
WHERE nlp_processed_at IS NULL
  AND nlp_method IS NULL
  AND created_at < NOW() - ($1 || ' days')::INTERVAL
"""


SAMPLE_BREAKDOWN_SQL = """
SELECT source_family, COUNT(*) AS n
FROM signals_v2
WHERE nlp_processed_at IS NULL
  AND nlp_method IS NULL
  AND created_at < NOW() - ($1 || ' days')::INTERVAL
GROUP BY source_family
ORDER BY n DESC
LIMIT 20
"""


DELETE_BATCH_SQL = """
WITH victims AS (
    SELECT id
    FROM signals_v2
    WHERE nlp_processed_at IS NULL
      AND nlp_method IS NULL
      AND created_at < NOW() - ($1 || ' days')::INTERVAL
    ORDER BY created_at
    LIMIT $2
)
DELETE FROM signals_v2 WHERE id IN (SELECT id FROM victims)
"""


async def _run(window_days: int, dry_run: bool, max_rows: int | None) -> None:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")
    conn = await asyncpg.connect(db_url)
    try:
        expected = await conn.fetchval(COUNT_SQL, str(window_days))
        breakdown = await conn.fetch(SAMPLE_BREAKDOWN_SQL, str(window_days))

        logger.info("Window: > %d days old", window_days)
        logger.info("Expected delete count: %s rows", f"{expected:,}")
        logger.info("Top source_family breakdown:")
        for row in breakdown:
            family = row["source_family"] or "(null)"
            logger.info("  %-20s %s", family, f"{row['n']:,}")

        if dry_run:
            logger.info("Dry-run mode — no deletes performed.")
            return

        if expected == 0:
            logger.info("Nothing to delete.")
            return

        deleted_total = 0
        cap = max_rows if max_rows is not None else expected
        started = time.monotonic()

        while deleted_total < cap:
            batch_limit = min(BATCH_SIZE, cap - deleted_total)
            tag = await conn.execute(DELETE_BATCH_SQL, str(window_days), batch_limit)
            # tag like 'DELETE 50000'
            batch_deleted = int(tag.split()[-1])
            if batch_deleted == 0:
                break
            deleted_total += batch_deleted
            elapsed = time.monotonic() - started
            rate = deleted_total / max(elapsed, 1)
            logger.info(
                "Batch deleted=%s total=%s rate=%.0f rows/s elapsed=%.1fs",
                f"{batch_deleted:,}", f"{deleted_total:,}", rate, elapsed,
            )

        logger.info("Done. Total deleted: %s rows in %.1fs", f"{deleted_total:,}", time.monotonic() - started)
    finally:
        await conn.close()


def _parse_args():
    parser = argparse.ArgumentParser(description="Atlas — prune unprocessed signal backlog (ADR-0004)")
    parser.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-rows", type=int, default=None)
    return parser.parse_args()


def main():
    args = _parse_args()
    asyncio.run(_run(args.window_days, args.dry_run, args.max_rows))


if __name__ == "__main__":
    main()
