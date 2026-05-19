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

from enrichment.nlp_pipeline import (
    cleanup_drained_sample_queue,
    refresh_stratified_sample,
    run_nlp_enrichment,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [nlp_worker] %(levelname)s %(message)s")

WORKER_ID = os.getenv("NLP_WORKER_ID", socket.gethostname())
WORKER_INTERVAL_SECONDS = int(os.getenv("NLP_WORKER_INTERVAL_SECONDS", "120"))
WORKER_BATCH_LIMIT = int(os.getenv("NLP_WORKER_LIMIT", "500"))
# Refresh the stratified nlp_sample_queue every N worker cycles (~6h at 120s interval).
# Set to 0 to disable this expensive refresh and run it out-of-band.
SAMPLE_REFRESH_EVERY_N_CYCLES = int(os.getenv("NLP_SAMPLE_REFRESH_EVERY", "180"))
LOW_VOLUME_REFRESH_TIMEOUT_SECONDS = int(os.getenv("NLP_LOW_VOLUME_REFRESH_TIMEOUT_SECONDS", "20"))


# ── Progress helpers ─────────────────────────────────────────────────────────
async def _progress_metrics(conn: asyncpg.Connection, rows_processed: int) -> dict:
    """Compute cheap backlog metrics without full-table scans on signals_v2."""
    previous = await conn.fetchrow(
        """
        SELECT unprocessed_24h, unprocessed_total, oldest_unprocessed_at
        FROM nlp_progress
        ORDER BY last_run_at DESC NULLS LAST
        LIMIT 1
        """
    )

    unprocessed_24h = int(previous["unprocessed_24h"] or 0) if previous else 0
    unprocessed_total = int(previous["unprocessed_total"] or 0) if previous else 0
    oldest = previous["oldest_unprocessed_at"] if previous else None

    if previous:
        unprocessed_24h = max(0, unprocessed_24h - rows_processed)
        unprocessed_total = max(0, unprocessed_total - rows_processed)

    try:
        recent = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM signals_v2
            WHERE nlp_processed_at IS NULL
              AND created_at > NOW() - INTERVAL '24 hours'
            """,
            timeout=5,
        )
        unprocessed_24h = int(recent or 0)
    except Exception:
        logger.warning("NLP progress recent-count query timed out — using previous estimate")

    try:
        oldest = await conn.fetchval(
            """
            SELECT created_at
            FROM signals_v2
            WHERE nlp_processed_at IS NULL
            ORDER BY created_at ASC
            LIMIT 1
            """,
            timeout=5,
        ) or oldest
    except Exception:
        logger.warning("NLP progress oldest-row query timed out — using previous estimate")

    lag_minutes = None
    if oldest is not None:
        delta = datetime.now(timezone.utc) - oldest
        lag_minutes = int(delta.total_seconds() // 60)
    return {
        "unprocessed_24h": unprocessed_24h,
        "unprocessed_total": unprocessed_total,
        "oldest_unprocessed_at": oldest,
        "lag_minutes": lag_minutes,
    }


async def _checkpoint(
    conn: asyncpg.Connection,
    rows_processed: int,
    duration_seconds: float,
    last_error: str | None = None,
) -> None:
    metrics = await _progress_metrics(conn, rows_processed)
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


async def _refresh_low_volume_view(db_url: str) -> None:
    """Refresh the low_volume_countries materialised view used by the priority query."""
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY low_volume_countries")
    except Exception:
        # CONCURRENTLY requires a unique index AND prior data — fall back on first run.
        try:
            await conn.execute("REFRESH MATERIALIZED VIEW low_volume_countries")
        except Exception:
            logger.exception("low_volume_countries refresh failed — non-fatal")
    finally:
        await conn.close()


def _should_refresh_stratified_sample(cycle_idx: int) -> bool:
    return SAMPLE_REFRESH_EVERY_N_CYCLES > 0 and cycle_idx % SAMPLE_REFRESH_EVERY_N_CYCLES == 0


# ── Main loop ────────────────────────────────────────────────────────────────
async def _maintenance(conn: asyncpg.Connection, cycle_idx: int) -> None:
    """Per-cycle maintenance: drain cleanup + periodic stratified refresh."""
    try:
        drained = await cleanup_drained_sample_queue(conn)
        if drained:
            logger.info("Drained %d completed ids from nlp_sample_queue", drained)
    except Exception:
        logger.exception("sample queue cleanup failed — non-fatal")

    if _should_refresh_stratified_sample(cycle_idx):
        try:
            inserted = await refresh_stratified_sample(conn)
            logger.info("Stratified sample refresh enqueued %d new ids", inserted)
        except Exception:
            logger.exception("stratified sample refresh failed — non-fatal")


async def _one_cycle(limit: int, cycle_idx: int) -> int:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")

    start = time.monotonic()
    rows_processed = 0
    last_error: str | None = None
    try:
        await run_nlp_enrichment(limit=limit)
        # run_nlp_enrichment does not return a count today; treat one cycle as
        # up to `limit` rows for the per-iteration metric. Real counts come from
        # the lag delta the checkpoint computes.
        rows_processed = limit
    except Exception as exc:
        last_error = repr(exc)[:500]
        logger.exception("NLP worker cycle failed")

    duration = time.monotonic() - start

    conn = await asyncpg.connect(db_url)
    try:
        await _checkpoint(conn, rows_processed, duration, last_error)
    finally:
        await conn.close()

    maintenance_conn = await asyncpg.connect(db_url)
    try:
        if _should_refresh_stratified_sample(cycle_idx):
            try:
                await asyncio.wait_for(
                    _refresh_low_volume_view(db_url),
                    timeout=LOW_VOLUME_REFRESH_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "low_volume_countries refresh exceeded %ss — skipping this cycle",
                    LOW_VOLUME_REFRESH_TIMEOUT_SECONDS,
                )
        await _maintenance(maintenance_conn, cycle_idx)
    finally:
        await maintenance_conn.close()

    logger.info(
        "Cycle %d done: rows~=%d duration=%.1fs error=%s",
        cycle_idx, rows_processed, duration, "yes" if last_error else "no",
    )
    return rows_processed


async def main(limit: int, once: bool) -> None:
    logger.info(
        "NLP worker starting (worker_id=%s, limit=%d, interval=%ds, sample_refresh_every=%d, once=%s)",
        WORKER_ID, limit, WORKER_INTERVAL_SECONDS, SAMPLE_REFRESH_EVERY_N_CYCLES, once,
    )
    cycle = 0
    while True:
        cycle += 1
        try:
            await _one_cycle(limit, cycle)
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
