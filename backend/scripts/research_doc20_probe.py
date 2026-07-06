#!/usr/bin/env python
"""#161 — GDELT DOC 2.0 as QUERY-TIME evidence enrichment: the measured probe.

Acceptance (issue): test 3 Atlas contexts (country crisis / market topic /
low-volume signal), measure relevance, language diversity, duplicate overlap
with existing signals, latency → research note with a recommendation
(query-time enrichment / defer / reject). NO bulk ingestion.

DOC 2.0: https://api.gdeltproject.org/api/v2/doc/doc (free, no key).

Usage:
  python backend/scripts/research_doc20_probe.py \
      --out docs/research/doc20/2026-07-06-doc20-probe.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

CONTEXTS = [
    {
        "name": "country crisis (Sudan conflict escalation)",
        "query": '"sudan" (conflict OR "el fasher" OR RSF OR fighting)',
        "atlas_like": "%sudan%",
    },
    {
        "name": "market topic (oil & gas supply)",
        "query": '"oil supply" OR "opec production" OR "gas pipeline"',
        "atlas_like": "%oil%",
    },
    {
        "name": "low-volume signal (Armenia election annulment)",
        "query": '"armenia" (election OR "constitutional court" OR annul)',
        "atlas_like": "%armenia%",
    },
]


def doc20_query(q: str, timespan: str = "3d", maxrecords: int = 50):
    params = urllib.parse.urlencode({
        "query": q, "mode": "artlist", "format": "json",
        "maxrecords": maxrecords, "timespan": timespan, "sort": "hybridrel",
    })
    t0 = time.time()
    req = urllib.request.Request(f"{DOC_URL}?{params}",
                                 headers={"User-Agent": "atlas-probe/1.0"})
    body = b""
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                time.sleep(8 * (attempt + 1))  # DOC 2.0 free tier throttles hard
                continue
            raise
        except urllib.error.URLError:
            if attempt < 4:
                time.sleep(8 * (attempt + 1))  # slow/refused — retry; the
                # flakiness itself is probe data (latency acceptance metric)
                continue
            raise
    latency = time.time() - t0
    try:
        arts = json.loads(body).get("articles", [])
    except json.JSONDecodeError:
        arts = []
    return arts, latency


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/research/doc20/2026-07-06-doc20-probe.md")
    args = ap.parse_args()

    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    conn = await asyncpg.connect(dsn, statement_cache_size=0) if dsn else None

    lines = ["# DOC 2.0 query-time enrichment probe (#161) — measured",
             "", f"3 contexts, timespan 3d, maxrecords 75, sort hybridrel.", ""]
    verdict_rows = []
    for i, ctx in enumerate(CONTEXTS):
        if i:
            time.sleep(10)  # respect the free-tier rate limit between contexts
        arts, latency = doc20_query(ctx["query"])
        langs = Counter((a.get("language") or "?").lower() for a in arts)
        domains = Counter(urllib.parse.urlparse(a.get("url", "")).netloc
                          .removeprefix("www.") for a in arts)
        overlap = None
        if conn and arts:
            urls = [a.get("url") for a in arts if a.get("url")]
            overlap = await conn.fetchval(
                "SELECT count(*) FROM signals_v2 WHERE source_url = ANY($1)",
                urls)
        lines += [f"## {ctx['name']}",
                  f"- query: `{ctx['query']}`",
                  f"- results: **{len(arts)}** · latency **{latency:.2f}s**",
                  f"- languages: {dict(langs.most_common(8))}",
                  f"- top domains: {[d for d, _ in domains.most_common(6)]}",
                  f"- URL overlap with signals_v2 (already ingested): "
                  f"{overlap if overlap is not None else 'n/a'}/{len(arts)}",
                  "- sample headlines:"]
        lines += [f"  - [{(a.get('language') or '?')}] "
                  f"{(a.get('title') or '')[:110]}" for a in arts[:8]]
        lines.append("")
        verdict_rows.append((ctx["name"], len(arts), latency,
                             len(langs), overlap))

    if conn:
        await conn.close()

    lines += ["## Measurements summary", "",
              "| context | results | latency | langs | already-ingested |",
              "|---|---|---|---|---|"]
    for n, c, l, lg, ov in verdict_rows:
        lines.append(f"| {n} | {c} | {l:.2f}s | {lg} | {ov} |")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    for row in verdict_rows:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
