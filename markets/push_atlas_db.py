#!/usr/bin/env python3
"""L4 markets — push the thin DESCRIPTIVE price snapshot to Atlas DB (market_series).

The ONE allowed crossing (design §6): markets/ is a separate consumer, but a thin
descriptive price table lands in Atlas's DB so the product surface (#151, the Brief
strip / dock tab) can read it. This pushes ONLY last_close + last_close_at + a 30d
spark per symbol — never history, never a signal. Runs on M1 after the accumulator
(has DATABASE_URL); env-gated so the pure-consumer accumulator stays credential-clean
by default.

Usage:
  ATLAS_MARKETS_PUSH=1 DATABASE_URL=... python markets/push_atlas_db.py
  # or --emit-sql to print idempotent UPDATEs (apply via any client)
"""
from __future__ import annotations

import argparse
import os
import sys

from markets import store


def latest_snapshots(conn, spark_days: int = 30) -> list[dict]:
    """Per symbol: latest close/date + the trailing `spark_days` closes (oldest→newest)."""
    syms = [r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM market_price_daily").fetchall()]
    out = []
    for sym in syms:
        rows = conn.execute(
            "SELECT date, close FROM market_price_daily WHERE symbol=? "
            "ORDER BY date DESC LIMIT ?", (sym, spark_days)).fetchall()
        if not rows:
            continue
        rows = rows[::-1]  # oldest → newest for the spark
        last_date, last_close = rows[-1]
        out.append({"symbol": sym, "last_close": last_close,
                    "last_close_at": last_date,
                    "spark_30d": [c for _, c in rows]})
    return out


def _emit_sql(snaps: list[dict]) -> str:
    lines = []
    for s in snaps:
        arr = "ARRAY[" + ",".join(repr(round(float(c), 6)) for c in s["spark_30d"]) + "]::numeric[]"
        sym = s["symbol"].replace("'", "''")
        lines.append(
            f"UPDATE market_series SET last_close={float(s['last_close'])}, "
            f"last_close_at='{s['last_close_at']}', spark_30d={arr}, updated_at=now() "
            f"WHERE symbol='{sym}';")
    return "\n".join(lines)


async def _push_asyncpg(dsn: str, snaps: list[dict]) -> int:
    import asyncpg
    conn = await asyncpg.connect(dsn)
    try:
        n = 0
        for s in snaps:
            await conn.execute(
                "UPDATE market_series SET last_close=$2, last_close_at=$3::date, "
                "spark_30d=$4::numeric[], updated_at=now() WHERE symbol=$1",
                s["symbol"], float(s["last_close"]), s["last_close_at"],
                [float(c) for c in s["spark_30d"]])
            n += 1
        return n
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="sqlite store path override")
    ap.add_argument("--emit-sql", action="store_true",
                    help="print UPDATE statements instead of connecting")
    args = ap.parse_args()

    conn = store.connect(None if args.db is None else __import__("pathlib").Path(args.db))
    snaps = latest_snapshots(conn)
    conn.close()
    if not snaps:
        print("no price rows in the store — run accumulate_prices first", file=sys.stderr)
        return 1

    if args.emit_sql:
        print(_emit_sql(snaps))
        return 0

    if not os.environ.get("ATLAS_MARKETS_PUSH"):
        print("push disabled (set ATLAS_MARKETS_PUSH=1 to write Atlas DB); "
              "use --emit-sql to preview", file=sys.stderr)
        return 1
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1
    import asyncio
    n = asyncio.run(_push_asyncpg(dsn, snaps))
    print(f"pushed {n} symbols to market_series")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
