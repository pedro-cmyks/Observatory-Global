"""System-wide scoped-recall estimate (#229 R0 → the decisive number).

The per-country probe proved scoping lifts recall ~13–15× on US + CN. This answers
the question that justifies R1: **if we scoped EVERY country, what does SYSTEM
recall become** (vs today's 5.6% of embedded / <1% per country)? Loops ALL
countries with >= --min-embedded signals, scoped-clusters each (leaf mcs=5 ms=2),
aggregates:
  system_scoped_recall = Σ clustered / Σ signals   (country-attributable)
  system_global_recall = Σ in-topic-today / Σ signals
  total_scoped_clusters = Σ per-country clusters

Read-only (reads embeddings + topic_members, clusters in memory, writes a report;
NO production writes). BOUNDED-PARALLEL — HDBSCAN releases the GIL, so N countries
cluster on N cores at once via asyncio.to_thread; --concurrency bounds memory
(each country ~0.5–1GB peak; keep N*cap within RAM). HEAVY → run OFF-PEAK.

Run (repo root, M1 ML env):
  python -m backend.scripts.recall_scoped_estimate --min-embedded 100 --per-country-cap 8000 --concurrency 4
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import asyncpg
import numpy as np

from backend.scripts.emergent_poc import _cluster

_COUNTRIES = """
    SELECT s.country_code, COUNT(*) AS n
    FROM signal_embeddings e JOIN signals_v2 s ON s.id = e.signal_id
    WHERE s.country_code IS NOT NULL AND s.country_code <> 'XX'
      AND s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
      AND s.headline IS NOT NULL AND length(s.headline) >= 20
    GROUP BY s.country_code HAVING COUNT(*) >= $2
    ORDER BY n DESC
"""
_FETCH = """
    SELECT s.id, se.vec::text AS emb
    FROM signal_embeddings se JOIN signals_v2 s ON s.id = se.signal_id
    WHERE s.country_code = $1
      AND s.timestamp > NOW() - ($2::int * INTERVAL '1 hour')
      AND s.headline IS NOT NULL AND length(s.headline) >= 20
    ORDER BY s.timestamp DESC
    LIMIT $3
"""
_BASELINE = ("SELECT COUNT(DISTINCT signal_id) FROM topic_members "
             "WHERE signal_id = ANY($1::bigint[])")


def _parse_vec(t: str) -> list[float]:
    return [float(x) for x in t.strip().lstrip("[").rstrip("]").split(",") if x]


async def _one(pool, sem, cc, hours, cap, done, total):
    async with sem:
        recs = None
        # Retry: under parallel load big fetches sometimes drop the connection
        # ("connection was closed in the middle of operation") — a fresh acquire
        # recovers, and dropping a high-volume country would bias the aggregate.
        for attempt in range(3):
            try:
                async with pool.acquire() as conn:
                    await conn.execute("SET statement_timeout = '600s'")
                    recs = await conn.fetch(_FETCH, cc, hours, cap)
                    if len(recs) < 50:
                        return None
                    ids = [int(r["id"]) for r in recs]
                    global_in = await conn.fetchval(_BASELINE, ids) or 0
                break
            except (asyncpg.PostgresError, ConnectionError, OSError) as ex:
                if attempt == 2:
                    print(f"  {cc}: FAILED after retries ({ex})", file=sys.stderr, flush=True)
                    raise
                await asyncio.sleep(3)
        n = len(recs)
        embs = np.array([_parse_vec(r["emb"]) for r in recs], dtype=np.float32)
        labels = await asyncio.to_thread(_cluster, embs, 5, 2, "leaf")
        noise = int((labels == -1).sum())
        clustered = n - noise
        n_clusters = int(labels.max()) + 1 if labels.max() >= 0 else 0
        largest = max((int((labels == c).sum()) for c in range(n_clusters)), default=0)
        blob = bool(largest > 0.4 * n)
        done[0] += 1
        r = {"country": cc, "n": n, "global_in_topic": global_in,
             "global_recall_pct": round(100.0 * global_in / n, 2),
             "scoped_clustered": clustered,
             "scoped_recall_pct": round(100.0 * clustered / n, 2),
             "clusters": n_clusters, "blob": blob}
        print(f"  [{done[0]}/{total}] {cc}: n={n} global={r['global_recall_pct']}% "
              f"scoped={r['scoped_recall_pct']}% clusters={n_clusters}"
              f"{' BLOB' if blob else ''}", file=sys.stderr, flush=True)
        return r


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--min-embedded", type=int, default=100)
    ap.add_argument("--per-country-cap", type=int, default=8000)
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)

    t0 = time.time()
    pool = await asyncpg.create_pool(
        db, min_size=2, max_size=args.concurrency + 3,
        max_inactive_connection_lifetime=0,  # don't let asyncpg reap mid-run
    )
    try:
        async with pool.acquire() as conn:
            await conn.execute("SET statement_timeout = '600s'")
            countries = await conn.fetch(_COUNTRIES, args.hours, args.min_embedded)
        total = len(countries)
        print(f"{total} countries with >= {args.min_embedded} embedded · "
              f"concurrency {args.concurrency} · cap {args.per_country_cap}", file=sys.stderr)
        sem = asyncio.Semaphore(args.concurrency)
        done = [0]
        tasks = [_one(pool, sem, r["country_code"], args.hours, args.per_country_cap, done, total)
                 for r in countries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await pool.close()

    rows = [r for r in results if isinstance(r, dict)]
    errs = [str(r) for r in results if isinstance(r, Exception)]
    tot_n = sum(r["n"] for r in rows)
    tot_clustered = sum(r["scoped_clustered"] for r in rows)
    tot_global = sum(r["global_in_topic"] for r in rows)
    tot_clusters = sum(r["clusters"] for r in rows)
    blobs = [r["country"] for r in rows if r["blob"]]
    sys_global = round(100.0 * tot_global / max(tot_n, 1), 2)
    sys_scoped = round(100.0 * tot_clustered / max(tot_n, 1), 2)

    summary = {
        "countries": len(rows), "errors": errs, "total_signals": tot_n,
        "system_global_recall_pct": sys_global,
        "system_scoped_recall_pct": sys_scoped,
        "lift_x": round(sys_scoped / max(sys_global, 0.01), 1),
        "total_scoped_clusters": tot_clusters, "blob_countries": blobs,
        "elapsed_sec": round(time.time() - t0),
        "per_country": sorted(rows, key=lambda r: -r["n"]),
    }
    out_dir = Path(__file__).resolve().parents[2] / "docs" / "research" / "recall-scoped"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "system-estimate.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    lines = [
        "# System-wide scoped-recall estimate (#229 R0)", "",
        f"**{len(rows)} countries, {tot_n:,} country-attributable signals** "
        f"(cap {args.per_country_cap}/country, {args.hours}h). {len(errs)} errors.", "",
        f"- system GLOBAL recall (in a topic today): **{sys_global}%**",
        f"- system SCOPED recall (every country clustered within): **{sys_scoped}%** "
        f"(~{summary['lift_x']}×)",
        f"- total scoped clusters formed: **{tot_clusters:,}** (vs ~68 topics system-wide today)",
        f"- blob countries (largest cluster >40%, treat with care): {blobs or 'none'}", "",
        "| country | n | global% | scoped% | clusters | blob |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda r: -r["n"]):
        lines.append(f"| {r['country']} | {r['n']} | {r['global_recall_pct']} | "
                     f"{r['scoped_recall_pct']} | {r['clusters']} | {'⚠' if r['blob'] else ''} |")
    (out_dir / "system-estimate.md").write_text("\n".join(lines))
    print(f"\nSYSTEM: global {sys_global}% → scoped {sys_scoped}% (~{summary['lift_x']}×), "
          f"{tot_clusters} clusters over {tot_n} signals, {len(rows)} countries, "
          f"{summary['elapsed_sec']}s")


if __name__ == "__main__":
    asyncio.run(main())
