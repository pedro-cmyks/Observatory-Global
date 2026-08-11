#!/usr/bin/env python3
"""Warm the country doors on the M1 (council R4 N26).

`GET /api/v2/country-edition?cc=CO` returned 503 db_busy on cold open ON THE
DAY COLOMBIA WAS THE STORY. Re-measured from production the same day:

    cc=CO -> HTTP 503 after 110.8s
    cc=JP -> HTTP 503 after  21.7s
    cc=US -> HTTP 503 after  19.2s

The door's dominant cost is the scoped-children query, MEASURED from the M1
against prod at 12.2-23.1s per country (CO 23.1 / US 14.0 / JP 12.9 / GR 12.7 /
PY 12.2 / AI 8.6). Inside an HTTP request that is a coin flip against the 15s
budget; the 120s Redis layer never helped because nothing ever succeeded, so it
never filled.

So the composition happens HERE — off the request path, under the nightly
heavy-job mutex — and lands one compact JSONB row per door in
`country_edition_artifacts` (mig 098). The endpoint reads that row.

    dry run (default):  python -m scripts.build_country_editions
    write:              python -m scripts.build_country_editions --execute

WHICH DOORS (see country_edition.BUILD_* for the measurement behind each):
  * the top-50 countries of the 24h field — 88.9% of all signals; past there
    the curve is flat (+2.8pp for the next ten) and each ten costs ~3.5 min,
  * plus any country spiking against its OWN baseline with enough mass to
    compose an edition (>=150 signals and >=1.5x its daily baseline) — the N26
    case: the country that is the story without being big.

BOUNDED BY CONSTRUCTION: countries are built in selection order (head first),
a wall-clock budget stops the run cleanly, and one country's failure never ends
the run — 40 warm doors beat none. Every skipped/failed door is NAMED in the
receipt, never silently dropped.
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
from app.services.country_edition import (
    BUILD_ANOMALY_MIN_VOLUME,
    BUILD_ANOMALY_RATIO,
    BUILD_COUNTRY_CAP,
    BUILD_TOP_N,
    artifact_row_fields,
    fetch_country_edition,
    fetch_selection_inputs,
    select_build_countries,
    store_country_edition_artifact,
)

# The build's per-query budget. The serving default (15s) is sized for an HTTP
# request; this caller has no reader waiting and the query it needs measures up
# to 23s on a busy night, so it raises the floor via `query_timeout`. Only ever
# widens — see app/services/thread_intelligence.query_timeout.
DEFAULT_QUERY_TIMEOUT_S = 120

# Wall clock for the whole run. MEASURED 2026-08-11 from the M1: 65s per door
# sequential (CO 65.7 / JP 61.8 / US 67.5) — the scoped query is only ~20s of
# that; the rest is per-topic round-trips over the WAN. At concurrency 3 the
# same doors cost 28.3s each of wall clock (6 doors in 169.9s), so today's
# ~66-door selection lands near 31 min and 40 min leaves real headroom for a
# slower night. When a night is slower STILL, the run stops ON the budget with
# the head already warm, and every skipped door is named in the receipt.
DEFAULT_MAX_SECONDS = 2400

# Doors composed in parallel. This overlaps LATENCY, not work: most of a door's
# 65s is round-trip time on per-topic fetches, not database CPU. Kept low
# because the step shares the nightly mutex with the rest of the chain and the
# Supabase instance is the same one whose pressure caused N26 in the first
# place.
DEFAULT_CONCURRENCY = 3


async def _run(
    *,
    execute: bool,
    hours: int,
    top_n: int,
    cap: int,
    explicit: list[str],
    max_seconds: float,
    concurrency: int,
) -> dict[str, Any]:
    db.pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=1,
        # One connection per in-flight door plus one for the selection reads.
        max_size=max(2, concurrency + 1),
        # Wider than any single door's compose; the per-query timeouts inside
        # fetch_threads are the real bound.
        command_timeout=600,
    )
    try:
        volume_rows, heat_rows = await fetch_selection_inputs(hours=hours)
        selected = select_build_countries(
            volume_rows, heat_rows, top_n=top_n, explicit=explicit, cap=cap,
        )

        started = time.monotonic()
        built: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        gate = asyncio.Semaphore(max(1, concurrency))

        async def _door(item: dict[str, Any]) -> None:
            cc = item["country_code"]
            async with gate:
                if time.monotonic() - started > max_seconds:
                    # Named, not dropped: a truncated night must be legible.
                    skipped.append({**item, "reason": "budget_exhausted"})
                    return
                t0 = time.monotonic()
                try:
                    # enqueue=False: the enqueue's known-domain gate MEASURED
                    # 2-3.5 min per door under load (statement timeout on a
                    # 48h signals_v2 scan) and the browser enqueues
                    # `pending_urls` itself. See fetch_country_edition.
                    payload = await fetch_country_edition(
                        cc, hours=hours, enqueue=False,
                    )
                    # Refuses a payload the N17 guard never touched, BEFORE any
                    # write — an artifact with no slot_guard block would serve
                    # a door whose exclusions are invisible.
                    fields = artifact_row_fields(payload)
                    seconds = time.monotonic() - t0
                    if execute:
                        await store_country_edition_artifact(
                            payload,
                            country_code=cc,
                            hours=hours,
                            build_seconds=seconds,
                            selection_reason=item["selection_reason"],
                        )
                    built.append({
                        **item,
                        "threads": fields["thread_count"],
                        "slot_guard_excluded": fields["slot_guard_excluded"],
                        "receipts": payload["article_enrichment"]["yield"]["attempted"],
                        "enrichment_ok": payload["article_enrichment"]["yield"]["ok"],
                        "seconds": round(seconds, 2),
                        "stored": bool(execute),
                    })
                except Exception as exc:  # noqa: BLE001 — one door, not the night
                    failures.append({
                        **item,
                        "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                        "seconds": round(time.monotonic() - t0, 2),
                    })

        # Selection order is preserved by the gather: the semaphore admits
        # doors in the order they were scheduled, so a budget-truncated run
        # still leaves the HEAD warm.
        await asyncio.gather(*(_door(item) for item in selected))

        total_seconds = time.monotonic() - started
        return {
            "execute": execute,
            "hours": hours,
            "concurrency": concurrency,
            "selection": {
                "top_n": top_n,
                "cap": cap,
                "explicit": explicit,
                "anomaly_min_volume": BUILD_ANOMALY_MIN_VOLUME,
                "anomaly_ratio": BUILD_ANOMALY_RATIO,
                "selected": len(selected),
                "by_reason": {
                    reason: sum(
                        1 for s in selected if s["selection_reason"] == reason
                    )
                    for reason in sorted({s["selection_reason"] for s in selected})
                },
            },
            "built": len(built),
            "failed": len(failures),
            "skipped": len(skipped),
            "total_seconds": round(total_seconds, 1),
            "seconds_per_door": (
                round(total_seconds / len(built), 2) if built else None
            ),
            "budget_exhausted": bool(skipped),
            "doors": built,
            "failures": failures,
            "skipped_doors": skipped,
        }
    finally:
        await db.pool.close()
        db.pool = None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute", action="store_true",
        help="upsert the country-edition artifacts (default: dry run)",
    )
    parser.add_argument("--hours", type=int, default=24,
                        help="edition window (the door's own parameter)")
    parser.add_argument("--top-n", type=int, default=BUILD_TOP_N,
                        help=f"volume-lane depth (default {BUILD_TOP_N}, measured)")
    parser.add_argument("--cap", type=int, default=BUILD_COUNTRY_CAP,
                        help=f"hard ceiling on doors per run (default {BUILD_COUNTRY_CAP})")
    parser.add_argument("--countries", default="",
                        help="comma-separated codes to build first, whatever the lanes say")
    parser.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS,
                        help=f"wall-clock budget (default {DEFAULT_MAX_SECONDS})")
    parser.add_argument("--query-timeout", type=float, default=DEFAULT_QUERY_TIMEOUT_S,
                        help="per-query budget for the build path (never narrows serving)")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                        help=(f"doors composed in parallel (default {DEFAULT_CONCURRENCY}); "
                              "overlaps WAN round-trips, does not add database work"))
    args = parser.parse_args()

    # Off-request callers only: raises the floor inside fetch_threads.
    os.environ.setdefault("ATLAS_THREADS_QUERY_TIMEOUT_S", str(args.query_timeout))

    explicit = [c.strip().upper() for c in args.countries.split(",") if c.strip()]
    print(json.dumps(asyncio.run(_run(
        execute=args.execute,
        hours=args.hours,
        top_n=args.top_n,
        cap=args.cap,
        explicit=explicit,
        max_seconds=args.max_seconds,
        concurrency=args.concurrency,
    )), indent=2))


if __name__ == "__main__":
    main()
