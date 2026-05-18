"""
NLP Worker — standalone Fly process (issue #163).

Runs `run_nlp_enrichment()` in a loop, updating `nlp_progress` after every
iteration. Intended to run as its own Fly process group so memory peaks do
not collide with ingestion HTTP fetches.

Local smoke test:
    python -m enrichment.nlp_worker --limit 200 --once

Production (Fly):
    python -m enrichment.nlp_worker --limit 500
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import socket
import time
from datetime import datetime, timezone

import asyncpg

from enrichment.nlp_pipeline import run_nlp_enrichment

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [nlp_worker] %(levelname)s %(message)s")

WORKER_ID = os.getenv("NLP_WORKER_ID", socket.gethostname())
WORKER_INTERVAL_SECONDS = int(os.getenv("NLP_WORKER_INTERVAL_SECONDS", "120"))
WORKER_BATCH_LIMIT = int(os.getenv("NLP_WORKER_LIMIT", "500"))


# ── Progress helpers ─────────────────────────────────────────────────────────
async def _progress_metrics(conn: asyncpg.Connection) -> dict:
    """Compute lag + backlog totals against the production processed column."""
    row = await conn.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE nlp_processed_at IS NULL
                  AND created_at > NOW() - INTERVAL '24 hours'
            ) AS unprocessed_24h,
            COUNT(*) FILTER (WHERE nlp_processed_at IS NULL) AS unprocessed_total,
            MIN(created_at) FILTER (WHERE nlp_processed_at IS NULL) AS oldest_unprocessed_at
        FROM signals_v2
        """
    )
    oldest = row["oldest_unprocessed_at"]
    lag_minutes = None
    if oldest is not None:
        delta = datetime.now(timezone.utc) - oldest
        lag_minutes = int(delta.total_seconds() // 60)
    return {
        "unprocessed_24h": int(row["unprocessed_24h"] or 0),
        "unprocessed_total": int(row["unprocessed_total"] or 0),
        "oldest_unprocessed_at": oldest,
        "lag_minutes": lag_minutes,
    }


async def _checkpoint(
    conn: asyncpg.Connection,
    rows_processed: int,
    duration_seconds: float,
    last_error: str | None = None,
) -> None:
    metrics = await _progress_metrics(conn)
    await conn.execute(
        """
        INSERT INTO nlp_progress (
            worker_id, rows_processed_total, lag_minutes, oldest_unprocessed_at,
            unprocessed_24h, unprocessed_total, current_phase, last_run_at,
            last_run_duration_seconds, last_error
        )
        VALUES ($1, $2, $3, $4, $5, $6, 'idle', NOW(), $7, $8)
        ON CONFLICT (worker_id) DO UPDATE SET
            rows_processed_total = nlp_progress.rows_processed_total + EXCLUDED.rows_processed_total,
            lag_minutes = EXCLUDED.lag_minutes,
            oldest_unprocessed_at = EXCLUDED.oldest_unprocessed_at,
            unprocessed_24h = EXCLUDED.unprocessed_24h,
            unprocessed_total = EXCLUDED.unprocessed_total,
            current_phase = EXCLUDED.current_phase,
            last_run_at = EXCLUDED.last_run_at,
            last_run_duration_seconds = EXCLUDED.last_run_duration_seconds,
            last_error = EXCLUDED.last_error
        """,
        WORKER_ID,
        rows_processed,
        metrics["lag_minutes"],
        metrics["oldest_unprocessed_at"],
        metrics["unprocessed_24h"],
        metrics["unprocessed_total"],
        duration_seconds,
        last_error,
    )


async def _refresh_low_volume_view(conn: asyncpg.Connection) -> None:
    """Refresh the low_volume_countries materialised view used by the priority query."""
    try:
        await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY low_volume_countries")
    except Exception:
        # CONCURRENTLY requires a unique index AND prior data — fall back on first run.
        try:
            await conn.execute("REFRESH MATERIALIZED VIEW low_volume_countries")
        except Exception:
            logger.exception("low_volume_countries refresh failed — non-fatal")


# ── Main loop ────────────────────────────────────────────────────────────────
async def _one_cycle(limit: int) -> int:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")

    start = time.monotonic()
    rows_processed = 0
    last_error: str | None = None
    try:
        await run_nlp_enrichment(limit=limit)
        # run_nlp_enrichment does not return a count today; estimate via lag delta.
        # We treat one cycle as up to `limit` rows for the per-iteration metric.
        rows_processed = limit
    except Exception as exc:
        last_error = repr(exc)[:500]
        logger.exception("NLP worker cycle failed")

    duration = time.monotonic() - start

    conn = await asyncpg.connect(db_url)
    try:
        await _refresh_low_volume_view(conn)
        await _checkpoint(conn, rows_processed, duration, last_error)
    finally:
        await conn.close()

    logger.info(
        "Cycle done: rows~=%d duration=%.1fs error=%s",
        rows_processed, duration, "yes" if last_error else "no",
    )
    return rows_processed


async def main(limit: int, once: bool) -> None:
    logger.info(
        "NLP worker starting (worker_id=%s, limit=%d, interval=%ds, once=%s)",
        WORKER_ID, limit, WORKER_INTERVAL_SECONDS, once,
    )
    while True:
        try:
            await _one_cycle(limit)
        except Exception:
            logger.exception("Worker iteration crashed — sleeping before retry")
        if once:
            return
        await asyncio.sleep(WORKER_INTERVAL_SECONDS)


def _parse_args():
    parser = argparse.ArgumentParser(description="Atlas NLP standalone worker")
    parser.add_argument("--limit", type=int, default=WORKER_BATCH_LIMIT)
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(main(args.limit, args.once))
