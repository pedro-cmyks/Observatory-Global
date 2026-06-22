#!/usr/bin/env python3
"""Self-coverage gap report — does each country have its OWN press in Atlas?

The diversity question is not only "how many languages" but "who gets to speak
about whom." A country has self-coverage when its OWN outlets
(source_origin_country == country_code) cover it — not when foreigners, even
foreigners writing in the local language (BBC Persian), do.

This read-only report ranks subject countries by their domestic share of
ATTRIBUTABLE coverage (signals whose outlet origin we know). Countries at ~0%
are the work-list for the source-research project: find and add a domestic
outlet so they stop being narrated only from outside.

Caveats it prints honestly:
- GDELT carries no outlet origin → large `unattributed`; ratios are over the
  attributable slice only.
- GDELT subject codes are partly FIPS (RP=Philippines) while our feed origins
  are ISO2; a few FIPS-only subjects show false 0% until subject codes are
  normalized. Flagged, not silently dropped.

Usage:
    .venv/bin/python -m scripts.self_coverage_report [--days 14] [--min 40]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "")

SQL = """
WITH base AS (
  SELECT country_code, source_origin_country
  FROM signals_v2
  WHERE timestamp > now() - ($1::int * interval '1 day')
    AND country_code IS NOT NULL AND country_code <> 'XX'
    AND source_origin_country IS NOT NULL
)
SELECT country_code AS subject,
       count(*) AS attributable,
       count(*) FILTER (WHERE source_origin_country = country_code) AS domestic
FROM base
GROUP BY country_code
HAVING count(*) >= $2
ORDER BY (count(*) FILTER (WHERE source_origin_country = country_code))::float
         / count(*) ASC, attributable DESC
"""


async def report(days: int, min_n: int) -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(SQL, days, min_n)
    finally:
        await conn.close()
    out = []
    for r in rows:
        att, dom = int(r["attributable"]), int(r["domestic"])
        out.append({
            "subject": r["subject"],
            "attributable": att,
            "domestic": dom,
            "domestic_pct": round(100 * dom / att, 1) if att else 0.0,
        })
    zero = [r for r in out if r["domestic"] == 0]
    return {
        "days": days, "min_signals": min_n,
        "countries": out,
        "zero_self_coverage": [r["subject"] for r in zero],
        "n_countries": len(out),
        "n_zero": len(zero),
    }


def _print(rep: dict) -> None:
    print(f"\n=== Self-coverage report — last {rep['days']}d "
          f"(>= {rep['min_signals']} attributable signals) ===")
    print(f"{rep['n_countries']} countries measured; "
          f"{rep['n_zero']} have ZERO domestic voice.\n")
    print(f"{'subj':<5} {'attrib':>7} {'domestic':>9} {'self%':>6}")
    for r in rep["countries"]:
        flag = "  <-- no own press" if r["domestic"] == 0 else ""
        print(f"{r['subject']:<5} {r['attributable']:>7} "
              f"{r['domestic']:>9} {r['domestic_pct']:>5}%{flag}")
    print(f"\nZERO self-coverage (work-list): "
          f"{', '.join(rep['zero_self_coverage'])}\n")


async def main() -> None:
    ap = argparse.ArgumentParser(description="Self-coverage gap report")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--min", type=int, default=40)
    ap.add_argument("--json-out", type=str, default=None)
    args = ap.parse_args()
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL not set")
    rep = await report(args.days, args.min)
    _print(rep)
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(rep, f, indent=2)
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    asyncio.run(main())
