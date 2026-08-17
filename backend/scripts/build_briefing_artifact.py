#!/usr/bin/env python3
"""Precompute the /api/v2/briefing payload (mig 101) — off the request path.

Profiled 2026-08-17 (docs/research/perf/2026-08-17-briefing-profile.md): the
live fill runs ~19 sections 100% serially on one connection, costs 15-18s, a
real reader eats it on every 900s TTL expiry, and two sections
(`theme_country`, `top_sources`) degrade on EVERY fill under their 1.5s
budget — the request that pays the fill freezes ITS failures into the cached
payload for everyone after it (the fill-lottery).

This builder has no reader waiting, so it:

  * takes FULL section budgets (8s for the two fast-lane sections, 15s —
    the connection's statement_timeout — for the rest),
  * RETRIES once when the run degrades, and publishes the run with FEWER
    degraded sections (a tie goes to the second: a fresher measurement of
    the same failure),
  * upserts ONE jsonable-encoded row into `briefing_artifacts` that the
    handler serves on a Redis miss while it is <=75 minutes old.

It does NOT duplicate the assembly: it calls the router's own
`get_briefing(hours, profile=True)` — profile bypasses Redis on read AND
write (and outside uvicorn `app.state` has no redis anyway), and hands back
`meta_profile.sections_total_ms` as the honest build cost.

    dry run (default):  python -m scripts.build_briefing_artifact
    write:              python -m scripts.build_briefing_artifact --execute

Runs on backend/.venv (fastapi lives there; the mlvenv does not have it).
Cron: Step 6 of scripts/run-atlas-topic-classifier.sh (30-min cadence,
kill-switch ATLAS_BRIEFING_ARTIFACT=off).
"""
from __future__ import annotations

import os

# Section budgets, widened BEFORE the router import reads them (they are
# module-level constants in app.routers.briefing). setdefault so an operator's
# explicit env still wins. Serving defaults are untouched: 1.5s / 8s remain
# the request-path budgets.
os.environ.setdefault("BRIEFING_OPTIONAL_DB_TIMEOUT_SECONDS", "8")
os.environ.setdefault("BRIEFING_DB_TIMEOUT_SECONDS", "15")

import argparse  # noqa: E402
import asyncio  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import socket  # noqa: E402
import time  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from typing import Any  # noqa: E402

import asyncpg  # noqa: E402
from fastapi.encoders import jsonable_encoder  # noqa: E402

from app import db  # noqa: E402
from app.routers.briefing import get_briefing  # noqa: E402

logger = logging.getLogger("build_briefing_artifact")

_UPSERT_SQL = """
    INSERT INTO briefing_artifacts
        (window_hours, payload, generated_at, build_ms, degraded_segments,
         builder, updated_at)
    VALUES ($1, $2::jsonb, $3, $4, $5, $6, now())
    ON CONFLICT (window_hours) DO UPDATE SET
        payload = EXCLUDED.payload,
        generated_at = EXCLUDED.generated_at,
        build_ms = EXCLUDED.build_ms,
        degraded_segments = EXCLUDED.degraded_segments,
        builder = EXCLUDED.builder,
        updated_at = now()
"""


def pick_publish(first: dict[str, Any], second: dict[str, Any] | None) -> dict[str, Any]:
    """The honest-retry rule: publish the run with FEWER degraded sections.

    A tie goes to the SECOND run — same failure count, fresher data. With no
    second run (the first came back clean) the first is the publication.
    """
    if second is None:
        return first
    if len(first["degraded_segments"]) < len(second["degraded_segments"]):
        return first
    return second


async def _build_once(hours: int) -> dict[str, Any]:
    """One full live assembly through the router's own code path."""
    payload = await get_briefing(hours=hours, profile=True)
    meta = payload.pop("meta_profile", None) or {}
    return {
        "payload": payload,
        "build_ms": meta.get("sections_total_ms"),
        "degraded_segments": list(payload.get("degraded_segments") or []),
    }


async def _run(*, execute: bool, hours: int) -> dict[str, Any]:
    db.pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=1,
        max_size=2,
        # Wider than any single section budget; the per-query timeouts inside
        # get_briefing (and its SET statement_timeout = 15000) are the bound.
        command_timeout=60,
    )
    try:
        t0 = time.monotonic()
        first = await _build_once(hours)
        logger.info(
            "run 1: build_ms=%s degraded=%s",
            first["build_ms"], first["degraded_segments"],
        )
        second = None
        if first["degraded_segments"]:
            # Honest retry: a degraded run may be contention, not truth —
            # measure again before freezing degradations into the artifact.
            second = await _build_once(hours)
            logger.info(
                "run 2 (retry): build_ms=%s degraded=%s",
                second["build_ms"], second["degraded_segments"],
            )
        chosen = pick_publish(first, second)
        generated_at = datetime.now(timezone.utc)
        payload = chosen["payload"]
        # Stamped BEFORE the upsert so the stored row already carries its
        # provenance — the handler serves the payload as-is.
        payload["served_from"] = "artifact"
        payload["artifact_generated_at"] = generated_at.isoformat()

        if execute:
            async with db.pool.acquire() as conn:
                await conn.execute(
                    _UPSERT_SQL,
                    int(hours),
                    # jsonable_encoder = the EXACT transform FastAPI applies
                    # to a fresh response (Decimal->float, datetime->iso), so
                    # artifact-serve == live-serve parity holds byte-for-byte.
                    json.dumps(jsonable_encoder(payload)),
                    generated_at,
                    (float(chosen["build_ms"])
                     if chosen["build_ms"] is not None else None),
                    chosen["degraded_segments"],
                    f"build_briefing_artifact@{socket.gethostname()}",
                )

        return {
            "execute": execute,
            "hours": hours,
            "generated_at": generated_at.isoformat(),
            "wall_seconds": round(time.monotonic() - t0, 1),
            "runs": [
                {"build_ms": r["build_ms"], "degraded": r["degraded_segments"]}
                for r in ([first] + ([second] if second else []))
            ],
            "retried": second is not None,
            "published": {
                "build_ms": chosen["build_ms"],
                "degraded_segments": chosen["degraded_segments"],
                "which_run": (
                    1 if chosen is first else 2
                ),
            },
            "stored": bool(execute),
        }
    finally:
        await db.pool.close()
        db.pool = None


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute", action="store_true",
        help="upsert the briefing artifact (default: dry run)",
    )
    parser.add_argument("--hours", type=int, default=24,
                        help="briefing window (default 24 — the reader's door)")
    args = parser.parse_args()
    print(json.dumps(
        asyncio.run(_run(execute=args.execute, hours=args.hours)), indent=2,
    ))


if __name__ == "__main__":
    main()
