#!/usr/bin/env python3
"""On-demand data refresh for the local, single-user Atlas.

Nothing ingests on a schedule any more. This brings the database from
"whenever it was last refreshed" up to now, in one pass:

  1. GDELT catch-up — GDELT keeps every 15-minute GKG file at a predictable
     URL, so the gap since the last ingested bucket is replayed file by file
     (English + translingual lanes). Idempotent: signals_v2 dedups on source_url.
  2. One cycle of every other source (RSS, NewsData, ReliefWeb, forums,
     disasters, Wikipedia, Trends, …). These are NOT replayable — a feed only
     carries its recent items — so a long gap loses whatever scrolled off.
  3. Hourly aggregates recomputed over the whole gap, matviews refreshed.
  4. Lexicon topic assignments over the gap, and the briefing artifact.

What this does NOT do: embeddings, clustering, labels, the sealed daily
edition. Story threads (dynamic topics) stay as of the last deep run.

Usage (from backend/, with the API venv):
    python -m scripts.local_refresh                 # catch up, at most 36h back
    python -m scripts.local_refresh --max-hours 72
    python -m scripts.local_refresh --gdelt-step 1  # every 15-minute file, not one per hour
    python -m scripts.local_refresh --skip-sources  # GDELT + aggregates only
    python -m scripts.local_refresh --dry-run       # show the gap, change nothing
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.ingest_v2 import (  # noqa: E402
    GDELT_LAST_UPDATE_URL,
    download_and_parse_gkg,
    fetch_latest_gdelt_url,
    insert_signals,
    refresh_theme_aggregates,
    update_countries,
)

GDELT_BASE = "http://data.gdeltproject.org/gdeltv2"
SLOT = timedelta(minutes=15)
SLOTS_PER_BATCH = 6        # 12 files in memory at a time
DOWNLOAD_CONCURRENCY = 4
SOURCE_TIMEOUT_S = 180


def log(msg: str) -> None:
    print(msg, flush=True)


def floor_slot(ts: datetime) -> datetime:
    ts = ts.astimezone(timezone.utc)
    return ts.replace(minute=ts.minute - ts.minute % 15, second=0, microsecond=0)


def slot_from_url(url: str) -> datetime:
    stamp = url.rsplit("/", 1)[-1].split(".", 1)[0]
    return datetime.strptime(stamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def plan_slots(last: datetime, latest: datetime, max_hours: int,
               step: int = 1) -> tuple[list[datetime], float]:
    """Slots to replay, oldest first, and the hours left un-replayed (the hole)
    when the gap is longer than max_hours.

    `step` thins the replay to every Nth 15-minute file, counted back from the
    latest one so the newest file is always included. step=1 replays them all.
    """
    start = floor_slot(last) + SLOT
    floor = latest - timedelta(hours=max_hours) + SLOT
    hole_hours = 0.0
    if start < floor:
        hole_hours = (floor - start).total_seconds() / 3600
        start = floor
    slots = []
    cur = latest
    while cur >= start:
        slots.append(cur)
        cur -= SLOT * step
    slots.reverse()
    return slots, hole_hours


async def gdelt_catch_up(pool: asyncpg.Pool, slots: list[datetime]) -> tuple[int, int, int]:
    """Returns (parsed, inserted, files_empty)."""
    sem = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)

    async def fetch(slot: datetime, lane: str) -> list[dict]:
        stamp = slot.strftime("%Y%m%d%H%M%S")
        if lane == "en":
            url, lang = f"{GDELT_BASE}/{stamp}.gkg.csv.zip", "en"
        else:
            url, lang = f"{GDELT_BASE}/{stamp}.translation.gkg.csv.zip", "xx"
        async with sem:
            try:
                return await download_and_parse_gkg(url, source_lang=lang)
            except Exception as exc:  # one bad file must not sink the catch-up
                log(f"      {stamp} {lane}: {type(exc).__name__}: {exc}")
                return []

    parsed = inserted = empty = 0
    for i in range(0, len(slots), SLOTS_PER_BATCH):
        batch = slots[i:i + SLOTS_PER_BATCH]
        results = await asyncio.gather(
            *[fetch(s, lane) for s in batch for lane in ("en", "tr")]
        )
        for signals in results:
            if not signals:
                empty += 1
                continue
            parsed += len(signals)
            inserted += await insert_signals(pool, signals)
        done = min(i + SLOTS_PER_BATCH, len(slots))
        log(f"      {done}/{len(slots)} slots · {inserted:,} new signals")
    return parsed, inserted, empty


async def run_sources(gap_hours: int) -> list[tuple[str, str, float]]:
    """One cycle of every non-replayable source, concurrently, each time-boxed."""

    async def disasters():
        from app.services.ingest_disasters import ingest_disasters
        return await ingest_disasters(hours=max(24, gap_hours))

    def lazy(module: str, fn: str):
        async def run():
            mod = __import__(f"app.services.{module}", fromlist=[fn])
            return await getattr(mod, fn)()
        return run

    sources = [
        ("rss", lazy("ingest_rss", "run_rss_ingestion")),
        ("newsdata", lazy("ingest_newsdata", "run_newsdata_ingestion")),
        ("reliefweb", lazy("ingest_reliefweb", "run_reliefweb_ingestion")),
        ("lemmy", lazy("ingest_lemmy", "run_lemmy_ingestion")),
        ("bluesky", lazy("ingest_bluesky", "run_bluesky_ingestion")),
        ("reddit", lazy("ingest_reddit", "run_reddit_ingestion")),
        ("mediastack", lazy("ingest_mediastack", "run_mediastack_ingestion")),
        ("newsapi", lazy("ingest_newsapi", "run_newsapi_ingestion")),
        ("events", lazy("ingest_events", "run_events_ingestion")),
        ("disasters", disasters),
        ("wikipedia", lazy("ingest_wiki", "run_wiki_ingestion")),
        ("trends", lazy("ingest_trends", "run_trends_ingestion")),
    ]

    async def one(name, fn):
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(fn(), timeout=SOURCE_TIMEOUT_S)
            status = "ok"
        except asyncio.TimeoutError:
            status = f"timeout after {SOURCE_TIMEOUT_S}s (partial)"
        except Exception as exc:
            status = f"failed: {type(exc).__name__}: {str(exc)[:80]}"
        return name, status, time.monotonic() - t0

    return list(await asyncio.gather(*[one(n, f) for n, f in sources]))


async def refresh_matviews(db_url: str) -> list[tuple[str, str]]:
    out = []
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("SET statement_timeout = 0")
        for view in ("country_hourly_v2", "country_heat_v2"):
            try:
                try:
                    await conn.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}")
                except Exception:
                    await conn.execute(f"REFRESH MATERIALIZED VIEW {view}")
                out.append((view, "ok"))
            except Exception as exc:
                out.append((view, f"failed: {exc}"))
    finally:
        await conn.close()
    return out


def run_module(module: str, *args: str) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=BACKEND_DIR, capture_output=True, text=True,
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
    return proc.returncode == 0, tail[0][-110:]


async def source_counts(pool: asyncpg.Pool, since: datetime) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT source_family, count(*) AS n FROM signals_v2 "
            "WHERE created_at >= $1 GROUP BY 1 ORDER BY 2 DESC", since)


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--max-hours", type=int, default=36,
                    help="Replay at most this many hours of GDELT (default 36). "
                         "A longer gap leaves a hole, reported, never hidden.")
    ap.add_argument("--gdelt-step", type=int, default=4,
                    help="Replay every Nth 15-minute GDELT file (default 4 = one per "
                         "hour). 1 replays every file: ~3,600 signals per file, several "
                         "times what the old 15-minute loop ever ingested.")
    ap.add_argument("--skip-sources", action="store_true",
                    help="Skip the non-GDELT sources (RSS, forums, trends, …).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report the gap and the plan; change nothing.")
    args = ap.parse_args()

    # The ingest modules log every feed; keep the terminal to the step summary.
    logging.disable(logging.WARNING)

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        log("local_refresh: DATABASE_URL is not set")
        return 2

    started = datetime.now(timezone.utc)
    t_all = time.monotonic()
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            last = await conn.fetchval(
                "SELECT max(timestamp) FROM signals_v2 WHERE source_family = 'gdelt'")
        latest_url = await fetch_latest_gdelt_url(GDELT_LAST_UPDATE_URL)
        if not latest_url:
            log("local_refresh: GDELT is unreachable — nothing refreshed")
            return 1
        latest = slot_from_url(latest_url)
        last = last or (latest - timedelta(hours=args.max_hours))
        gap_h = max(0.0, (latest - floor_slot(last)).total_seconds() / 3600)
        slots, hole_h = plan_slots(last, latest, args.max_hours, max(1, args.gdelt_step))

        log(f"  gap        last GDELT bucket {floor_slot(last):%Y-%m-%d %H:%M} UTC → "
            f"latest {latest:%Y-%m-%d %H:%M} UTC  ({gap_h:.1f}h, {len(slots)} files, "
            f"1 of every {max(1, args.gdelt_step)})")
        if hole_h > 0:
            log(f"  HOLE       {hole_h:.1f}h older than --max-hours {args.max_hours} "
                f"will NOT be replayed (re-run with a larger --max-hours to fill it)")
        if args.dry_run:
            log("  dry run — nothing changed")
            return 0

        # 1. GDELT
        t0 = time.monotonic()
        if slots:
            parsed, inserted, empty = await gdelt_catch_up(pool, slots)
            log(f"  gdelt      {inserted:,} new / {parsed:,} parsed · "
                f"{empty} empty or missing files · {time.monotonic() - t0:.0f}s")
        else:
            inserted = 0
            log("  gdelt      already current")
        if slots and inserted == 0 and empty == 2 * len(slots):
            log("local_refresh: every GDELT file failed — stopping before aggregates")
            return 1

        # 2. Everything else, one cycle
        if not args.skip_sources:
            t0 = time.monotonic()
            for name, status, secs in await run_sources(math.ceil(gap_h)):
                log(f"  {name:<10} {status} · {secs:.0f}s")
            log(f"  sources    done · {time.monotonic() - t0:.0f}s wall")

        # 3. Aggregates over the whole gap (+2h of overlap, as the loop always had)
        t0 = time.monotonic()
        window = min(args.max_hours, math.ceil(gap_h)) + 2
        try:
            await update_countries(pool)
        except Exception as exc:
            log(f"  countries  failed (non-fatal): {exc}")
        await refresh_theme_aggregates(pool, window_hours=window)
        for view, status in await refresh_matviews(db_url):
            log(f"  matview    {view}: {status}")
        log(f"  aggregates {window}h window · {time.monotonic() - t0:.0f}s")

        # 4. Lexicon assignments + briefing artifact
        t0 = time.monotonic()
        ok, tail = run_module("scripts.backfill_lexicon_topics", "--window-hours", str(window))
        log(f"  lexicon    {'ok' if ok else 'FAILED'} · {tail} · {time.monotonic() - t0:.0f}s")
        t0 = time.monotonic()
        ok, tail = run_module("scripts.build_briefing_artifact", "--execute")
        log(f"  briefing   {'ok' if ok else 'FAILED'} · {tail} · {time.monotonic() - t0:.0f}s")

        counts = await source_counts(pool, started)
        total = sum(r["n"] for r in counts)
        by = ", ".join(f"{r['source_family']} {r['n']:,}" for r in counts) or "nothing new"
        log(f"  total      {total:,} new signals ({by}) · {time.monotonic() - t_all:.0f}s")
        log("  note       story threads are NOT rebuilt by this step "
            "(no embeddings/clustering) — they stay as of the last deep run")
        return 0
    finally:
        await pool.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
