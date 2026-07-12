#!/usr/bin/env python3
"""Precompute the universe-v0 payload into the universe_snapshot table.

The `/api/v2/universe` live rebuild is ~11s warm / >20s cold over ~500 active
topics (5 topic_members×signals_v2 joins + numpy SVD + full-space neighbor
matrix) — past the frontend's 20s abort, so a cold cache miss renders the
"Universe data unavailable" empty state. This script builds the payload out of
band so the endpoint just reads a JSONB row.

Run from the M1 cron alongside the other snapshot jobs (see
scripts/run-universe-snapshot.sh). The endpoint ALSO self-heals via a
non-blocking write-through rebuild, so this cron is a warm-keeper, not a
single point of failure.

Usage (from the backend/ directory, so `app` is importable):
  /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.build_universe_snapshot [--days 30]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg


async def _main(days: int) -> int:
    # Import the fastapi-free service module (not the router) so this runs in
    # the ML venv, which has numpy/asyncpg but no fastapi.
    from app import db
    from app.services import universe_build

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2

    db.pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
    try:
        payload = await universe_build.store_universe_snapshot(days)
        n = len(payload.get("nodes") or [])
        if n < 3:
            print(f"universe build produced {n} nodes (reason="
                  f"{payload.get('reason')}) — NOT persisted", file=sys.stderr)
            return 1
        print(f"universe_snapshot days={days} built: {n} nodes, "
              f"{len(payload.get('edges') or [])} edges")
        return 0
    finally:
        await db.pool.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the universe_snapshot payload")
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()
    return asyncio.run(_main(args.days))


if __name__ == "__main__":
    raise SystemExit(main())
