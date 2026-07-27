#!/usr/bin/env python3
"""Build the universe field artifact on the M1.

The heavy PCA + full-space neighbour build (MEASURED 75.5s on 2026-07-27:
2,603 nodes / 6,306 edges / 3.96 MB of JSON) runs here under the existing
heavy-job mutex, never in an HTTP request -- the Fly proxy closes the request
long before the build finishes, which is exactly why `/api/v2/universe` sat at
0% availability with a permanently dark UNIVERSE tab.

Dry-run is the default; `--execute` upserts one compact JSON artifact into
`universe_field_artifacts`, which the endpoint then simply reads.

Nothing is sampled or capped: the artifact holds every active non-umbrella
topic that carries a centroid (`meta.bounded` is False, and must be flipped if
that ever stops being true).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from typing import Any

import asyncpg

from app import db
from app.services.universe_field import (
    TIMELINE_DAYS,
    build_universe_payload,
    store_universe_artifact,
)


async def _run(*, execute: bool, days: int) -> dict[str, Any]:
    db.pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=1,
        max_size=2,
        # The build's own SET statement_timeout bounds the queries; the pool
        # timeout only needs to be wider than the measured build.
        command_timeout=600,
    )
    try:
        started = time.monotonic()
        payload = await build_universe_payload(days)
        build_seconds = time.monotonic() - started

        reason = payload.get("reason")
        meta = payload.get("meta") or {}
        nodes = payload.get("nodes") or []
        edges = payload.get("edges") or []
        encoded_bytes = len(json.dumps(payload))

        if reason:
            # An honest empty build (e.g. fewer than 3 active topics) must NOT
            # overwrite a real stored field with nothing. Serving keeps the
            # previous artifact; the run reports why it wrote nothing.
            return {
                "execute": execute,
                "stored": False,
                "reason": reason,
                "days": days,
                "build_seconds": round(build_seconds, 2),
            }

        if execute:
            await store_universe_artifact(
                payload, days=days, build_seconds=build_seconds,
            )
        return {
            "execute": execute,
            "stored": bool(execute),
            "reason": None,
            "days": days,
            "contract": payload.get("contract"),
            "build_seconds": round(build_seconds, 2),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "anchor_count": len(payload.get("anchors") or []),
            "payload_bytes": encoded_bytes,
            "payload_mb": round(encoded_bytes / 1e6, 2),
            "bounded": meta.get("bounded"),
        }
    finally:
        await db.pool.close()
        db.pool = None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute", action="store_true",
        help="upsert the compact universe artifact (default: dry run)",
    )
    parser.add_argument(
        "--days", type=int, default=TIMELINE_DAYS,
        help=f"timeline window to build (default {TIMELINE_DAYS})",
    )
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_run(execute=args.execute, days=args.days)), indent=2))


if __name__ == "__main__":
    main()
