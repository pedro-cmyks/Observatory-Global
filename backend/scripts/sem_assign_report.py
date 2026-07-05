#!/usr/bin/env python
"""Semantic-lane ledger: per-topic candidate counts + gate keep-rates per lane.

The spec's honesty requirement: every consumer can distinguish lanes
(method='embedding', model_version='sem-assign-v0'), and this report reconciles what each lane added and how
the gate graded it. Read it after the first live pass and periodically.

Usage: python backend/scripts/sem_assign_report.py [--window-hours 48]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

REPORT_SQL = """
    SELECT t.slug, a.method, a.model_version,
           count(*) AS n,
           count(*) FILTER (WHERE a.gate_score IS NOT NULL) AS scored,
           count(*) FILTER (WHERE a.gate_kept) AS kept,
           round(avg(a.confidence)::numeric, 3) AS avg_conf
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    WHERE ($1::real = 0 OR a.assigned_at > NOW() - ($1::real * INTERVAL '1 hour'))
      AND a.method IN ('lexicon', 'embedding')
    GROUP BY t.slug, a.method, a.model_version
    ORDER BY t.slug, a.method
"""


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-hours", type=float, default=48.0)
    args = ap.parse_args()

    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        rows = await conn.fetch(REPORT_SQL, args.window_hours)
    finally:
        await conn.close()

    by_slug: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_slug.setdefault(r["slug"], {})[r["method"]] = {
            "n": r["n"], "scored": r["scored"], "kept": r["kept"],
            "avg_conf": float(r["avg_conf"]) if r["avg_conf"] is not None else None,
        }

    print(f"window={args.window_hours}h")
    print(f"{'topic':42s} {'lex n/scored/kept':>20s} {'sem n/scored/kept':>20s}")
    tot = {"lexicon": [0, 0, 0], "embedding": [0, 0, 0]}
    for slug in sorted(by_slug):
        cells = []
        for m in ("lexicon", "embedding"):
            e = by_slug[slug].get(m)
            if e:
                cells.append(f"{e['n']}/{e['scored']}/{e['kept']}")
                tot[m][0] += e["n"]; tot[m][1] += e["scored"]; tot[m][2] += e["kept"]
            else:
                cells.append("—")
        print(f"{slug:42s} {cells[0]:>20s} {cells[1]:>20s}")
    print(f"{'TOTAL':42s} "
          f"{'/'.join(map(str, tot['lexicon'])):>20s} "
          f"{'/'.join(map(str, tot['embedding'])):>20s}")
    keep = {m: (v[2] / v[1] if v[1] else None) for m, v in tot.items()}
    print(json.dumps({"keep_rate": {m: (round(k, 3) if k is not None else None)
                                    for m, k in keep.items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
