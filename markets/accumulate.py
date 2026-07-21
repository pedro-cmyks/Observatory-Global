#!/usr/bin/env python3
"""L4 markets — combined daily accumulator (the #226 gate prerequisite).

Runs both forward accumulators, best-effort and independent (one failing never
blocks the other):
  1. prices        — Yahoo daily closes for the instrument universe (first run
                     backfills ~4mo; the genuinely-lost-otherwise capture).
  2. news intensity— per-category/country daily snapshot from the Atlas public API
                     (point-in-time by construction).

This is the ONE ship-now piece under #226 STOP: pure descriptive accumulation, no
claims, no UI, no engine touch. The event study (m0) and any relation surface stay
gated until the October re-run.

Run from the repo root:  python3 -m markets.accumulate
"""
from __future__ import annotations

import sys

from markets import accumulate_news_intensity, accumulate_prices, store


def main() -> int:
    rc_p = 1
    rc_n = 1
    try:
        rc_p = accumulate_prices.main()
    except SystemExit as e:
        rc_p = int(e.code or 0)
    except Exception as e:  # noqa: BLE001
        print(f"price accumulator crashed: {e}", file=sys.stderr)

    # accumulate_prices.main() parses argv; call the news one with a clean argv
    saved = sys.argv
    sys.argv = [saved[0]]
    try:
        rc_n = accumulate_news_intensity.main()
    except SystemExit as e:
        rc_n = int(e.code or 0)
    except Exception as e:  # noqa: BLE001
        print(f"news accumulator crashed: {e}", file=sys.stderr)
    finally:
        sys.argv = saved

    conn = store.connect()
    cov = store.coverage(conn)
    conn.close()
    print(f"\nACCUMULATOR SUMMARY @ {store.default_db_path()}\n"
          f"  prices: {cov['price_rows']} rows / {cov['price_symbols']} symbols "
          f"[{cov['price_span'][0]}..{cov['price_span'][1]}]  (rc={rc_p})\n"
          f"  news:   {cov['news_rows']} rows / {cov['news_days']} day(s) "
          f"[{cov['news_span'][0]}..{cov['news_span'][1]}]  (rc={rc_n})")
    # exit 0 if EITHER made progress — the price side is the load-bearing one
    return 0 if (rc_p == 0 or rc_n == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
