#!/usr/bin/env python
"""Load Stage-B archive story units into archive_story_units (mig 069).

Idempotent (ON CONFLICT day,label DO NOTHING). Run from the M1 (reads the
external volume).

Usage:
  python backend/scripts/load_archive_units.py \
      [--units /Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl] [--write]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date

INSERT = """
    INSERT INTO archive_story_units
        (day, label, samples, n_signals, cohesion, top_cc, vec)
    VALUES ($1::date, $2, $3::jsonb, $4, $5, $6, $7::halfvec)
    ON CONFLICT (day, label) DO NOTHING
"""


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--units",
                    default="/Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    rows = []
    for line in open(args.units):
        d = json.loads(line)
        if not d.get("centroid"):
            continue
        rows.append((
            date.fromisoformat(d["day"]), d["label"][:300],
            json.dumps(d.get("samples") or [], ensure_ascii=False),
            int(d.get("n", 0)), float(d.get("cohesion") or 0),
            d.get("top_cc") or [],
            "[" + ",".join(f"{x:.5f}" for x in d["centroid"]) + "]",
        ))
    print(f"{len(rows)} units parsed", file=sys.stderr)
    if not args.write:
        print("dry-run (no writes)")
        return 0

    import asyncpg
    conn = await asyncpg.connect(os.environ["DATABASE_URL"],
                                 statement_cache_size=0)
    try:
        for i in range(0, len(rows), 500):
            await conn.executemany(INSERT, rows[i:i + 500])
            print(f"  {min(i + 500, len(rows))}/{len(rows)}", file=sys.stderr)
        n = await conn.fetchval("SELECT count(*) FROM archive_story_units")
        print(f"table now holds {n} units")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
