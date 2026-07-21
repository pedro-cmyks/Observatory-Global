#!/usr/bin/env python3
"""L4 markets — the PRICE accumulator (the genuinely-lost-otherwise capture).

Yahoo's free chart API only serves a rolling ~4-month window, so every day not
captured ages out FOREVER. This is the piece that must start NOW (design §6): the
first run backfills the full ~4mo window; each subsequent daily run appends the new
close. Prices are DESCRIPTIVE (level + trend); nothing here is a claim, a forecast,
a direction, or a trade signal.

Separate-consumer rule: hits Yahoo's public chart API only; writes the markets-side
sqlite store (markets/store.py), never Atlas's DB.

Usage:
  python3 markets/accumulate_prices.py [--range 4mo] [--db PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import date

from markets import store
from markets.instruments import all_symbols, symbol_labels


def fetch_yahoo_daily(symbol: str, rng: str = "4mo") -> dict[str, float]:
    """date(ISO) -> close. Mirrors m0_event_study.yahoo_daily (public chart API,
    honest retry/backoff)."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.request.quote(symbol)}?range={rng}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read())
            res = d["chart"]["result"][0]
            closes: dict[str, float] = {}
            ts = res.get("timestamp") or []
            quote = res["indicators"]["quote"][0]["close"]
            for t, c in zip(ts, quote):
                if c is not None:
                    closes[date.fromtimestamp(t).isoformat()] = float(c)
            return closes
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                print(f"  ! {symbol}: give up ({e})", file=sys.stderr)
                return {}
            time.sleep(3 * (attempt + 1))
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", default="4mo",
                    help="Yahoo range window (first run captures the whole thing)")
    ap.add_argument("--db", default=None, help="override ATLAS_MARKETS_DB")
    args = ap.parse_args()

    db_path = None if args.db is None else __import__("pathlib").Path(args.db)
    conn = store.connect(db_path)
    labels = symbol_labels()
    symbols = all_symbols()
    print(f"price accumulator: {len(symbols)} symbols → {store.default_db_path() if db_path is None else db_path}",
          file=sys.stderr)

    ok = 0
    for sym in symbols:
        closes = fetch_yahoo_daily(sym, args.range)
        if not closes:
            continue
        store.upsert_prices(conn, sym, closes, source="yahoo")
        lo, hi = min(closes), max(closes)
        lab = labels.get(sym, (sym, "?"))[0]
        print(f"  {sym:10s} {len(closes):4d} closes {lo}..{hi}  ({lab})",
              file=sys.stderr)
        ok += 1
        time.sleep(1)  # gentle on the public API

    cov = store.coverage(conn)
    conn.close()
    print(f"done: {ok}/{len(symbols)} symbols fetched; store now holds "
          f"{cov['price_rows']} price rows across {cov['price_symbols']} symbols "
          f"({cov['price_span'][0]}..{cov['price_span'][1]})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
