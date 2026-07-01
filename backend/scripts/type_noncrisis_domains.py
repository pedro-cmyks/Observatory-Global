"""R3.1 finish — open-domain category for the diverse non-crisis singletons.

The seed-anchor (crisis) + emergent-cluster (coherent non-crisis) passes leave ~123
diverse non-crisis stories with no category (they don't cluster). This gives each an
OPEN coarse non-crisis domain via DeepSeek so EVERY narrative carries a category (the
crisis-relevance-as-lens goal — nothing is a generic "narrative thread" fallback).
These are open domains, NOT crisis categories — a World Cup / obituary / market move is
a real narrative, categorized honestly. crisis_relevant stays false (the lens).

  python -m backend.scripts.type_noncrisis_domains --write
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

from backend.scripts.compute_category_typing import _DS_URL

# coarse OPEN non-crisis domains (a seed set; emergent super-categories already cover the
# clustered ones — this catches the diverse singletons). Not crisis, not a reject.
_DOMAINS = [
    "Sports", "Entertainment & Culture", "Business & Markets", "Crime & Justice",
    "Science & Technology", "Health & Lifestyle", "Local & Community", "Obituary & Tribute",
    "Weather & Nature", "Politics & Governance", "Accident & Incident", "Other",
]


async def _ds_domain(label: str, key: str) -> str:
    import httpx
    doms = "\n".join(f"- {d}" for d in _DOMAINS)
    prompt = (f"Give the best OPEN category for this (non-crisis) news story from the "
              f"list. STORY: \"{label}\"\nCATEGORIES:\n{doms}\nAnswer with ONLY the exact category.")
    async with httpx.AsyncClient() as c:
        r = await c.post(_DS_URL, json={"model": "deepseek-chat", "temperature": 0,
                         "messages": [{"role": "user", "content": prompt}]},
                         headers={"Authorization": f"Bearer {key}"}, timeout=30.0)
        r.raise_for_status()
        ans = r.json()["choices"][0]["message"]["content"].strip().strip('"')
    return ans if ans in _DOMAINS else "Other"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    db, key = os.environ.get("DATABASE_URL"), os.environ.get("DEEPSEEK_API_KEY", "")
    if not db:
        print("DATABASE_URL required", file=sys.stderr); sys.exit(2)
    conn = await asyncpg.connect(db)
    try:
        rows = await conn.fetch(
            "SELECT id, label FROM dynamic_topics WHERE state='active' AND is_umbrella=false "
            "AND crisis_relevant = false AND category IS NULL")
        print(f"{len(rows)} uncategorized non-crisis singletons")
        done = 0
        for r in rows:
            dom = await _ds_domain(r["label"] or "?", key) if key else "Other"
            if args.dry_run and done < 10:
                print(f"  {dom:22} <- {r['label'][:40]}")
            if args.write:
                await conn.execute("UPDATE dynamic_topics SET category=$2 WHERE id=$1", int(r["id"]), dom)
            done += 1
        print(f"{'wrote' if args.write else 'dry'} {done} open-domain categories")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
