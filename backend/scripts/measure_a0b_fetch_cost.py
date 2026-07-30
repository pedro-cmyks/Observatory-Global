"""A0b condition C5 — the serving cost of an M x LIMIT dynamic-threads fetch.

Read-only. Two independent measures, because they answer different questions:

  1. SERVER-SIDE (`EXPLAIN (ANALYZE, BUFFERS)` on the real `_DYNAMIC_TOPICS_SQL`
     and on `_EMERGENT_SAMPLE_SIGNALS_SQL`) — Postgres execution time, free of
     this laptop's WAN latency. This is the number that transfers to prod.
  2. WALL-CLOCK of the shipped `_fetch_dynamic_threads_with_conn` at each depth,
     interleaved so cache warmth is shared across arms. WAN-inflated from a
     laptop; reported as an upper bound and as the shape of the cost curve
     (the endpoint issues ONE sample-signal query PER SERVED ROW, so wall clock
     grows with M even where SQL time does not).

Timeouts are DATA, not failures: the shipped code caps the topic query at 15s
and each sample query at 8s, and a breach is a new degradation class, so they
are recorded per attempt instead of aborting the run.

    set -a; source ~/AtlasLocalWorker/.env; set +a
    backend/.venv/bin/python backend/scripts/measure_a0b_fetch_cost.py \
        --page 40 --mults 2,3,4 --reps 3 --out <json>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg  # noqa: E402

from app.services.thread_intelligence import (  # noqa: E402
    _DYNAMIC_TOPICS_SQL,
    _EMERGENT_SAMPLE_SIGNALS_SQL,
    _fetch_dynamic_threads_with_conn,
)


async def explain(conn: Any, sql: str, *args: Any) -> dict[str, Any]:
    rows = await conn.fetch(
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, *args, timeout=180,
    )
    plan = json.loads(rows[0][0])[0]
    return {
        "execution_ms": round(plan.get("Execution Time", 0.0), 1),
        "planning_ms": round(plan.get("Planning Time", 0.0), 1),
        "rows_out": plan["Plan"].get("Actual Rows"),
    }


async def main_async(page: int, mults: tuple[int, ...], reps: int) -> dict[str, Any]:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute("SET default_transaction_read_only = on")
    assert await conn.fetchval("SHOW default_transaction_read_only") == "on"
    depths = [page] + [page * m for m in mults]
    out: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "page": page, "mults": list(mults), "reps": reps,
        "shipped_timeouts_s": {"topic_sql": 15, "sample_signals": 8},
        "server_side": {}, "wall_clock": {},
    }
    try:
        # ---- 1. server-side ------------------------------------------------
        for d in depths:
            out["server_side"][str(d)] = {
                "topic_sql": await explain(conn, _DYNAMIC_TOPICS_SQL, 24, d),
            }
            print(f"  explain depth={d}: "
                  f"{out['server_side'][str(d)]['topic_sql']}", file=sys.stderr)
        # one sample-signal query, server-side, for the per-row unit cost
        rows = await conn.fetch(_DYNAMIC_TOPICS_SQL, 24, page, timeout=60)
        unit = []
        for r in rows[:8]:
            ids = list(r["sample_signal_ids"] or [])
            if ids:
                unit.append(await explain(conn, _EMERGENT_SAMPLE_SIGNALS_SQL, ids))
        out["server_side"]["sample_signals_unit"] = {
            "n": len(unit),
            "execution_ms_median": round(
                statistics.median([u["execution_ms"] for u in unit]), 1) if unit else None,
            "execution_ms_max": max((u["execution_ms"] for u in unit), default=None),
            "samples": unit,
        }
        # ---- 2. wall clock -------------------------------------------------
        timings: dict[int, list[float | None]] = {d: [] for d in depths}
        rowcounts: dict[int, int] = {}
        for _ in range(reps):
            for d in depths:
                t0 = time.perf_counter()
                try:
                    served = await _fetch_dynamic_threads_with_conn(
                        conn, hours=24, limit=d, country_code=None)
                    timings[d].append(time.perf_counter() - t0)
                    rowcounts[d] = len(served)
                except (TimeoutError, asyncio.TimeoutError):
                    timings[d].append(None)   # a shipped-timeout breach
                    print(f"  TIMEOUT at depth={d}", file=sys.stderr)
                print(f"  wall depth={d}: {timings[d][-1]}", file=sys.stderr)
        for d in depths:
            vals = [v for v in timings[d] if v is not None]
            s = sorted(vals)
            out["wall_clock"][str(d)] = {
                "rows_fetched": rowcounts.get(d),
                "timeouts": sum(1 for v in timings[d] if v is None),
                "attempts": len(timings[d]),
                "p50_s": round(s[len(s) // 2], 2) if s else None,
                "max_s": round(s[-1], 2) if s else None,
                "min_s": round(s[0], 2) if s else None,
                "samples_s": [None if v is None else round(v, 2) for v in timings[d]],
            }
    finally:
        await conn.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--page", type=int, default=40)
    ap.add_argument("--mults", default="2,3,4")
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()
    payload = asyncio.run(main_async(
        args.page, tuple(int(x) for x in args.mults.split(",")), args.reps))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str))
    print(f"wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
