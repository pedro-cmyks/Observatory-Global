"""R0 probe — scoped (per-country) clustering recall (#229 lever 2).

The global HDBSCAN pass clusters <1% of a country's signals (measured 2026-06-30:
US 24,709 signals/24h → 136 in a topic = 0.6%; CN 8,720→4). The hypothesis
(engine spec 2026-06-30-atlas-engine-recall-scoped-clustering.md): clustering
WITHIN a country — where its regional stories are the MAJORITY, not noise drowned
in a 200K global space — recovers far more topics.

This probe tests that on ONE country: pull its PERSISTED embeddings (no re-embed —
#223 already paid for `signal_embeddings`), HDBSCAN over them across a small param
grid, and report recall (% clustered) + cluster structure vs the global baseline
(how many of that country's signals are in a topic today).

Read-only: reads embeddings + topic_members, clusters in memory, writes only a
report. No DB writes, no vector invalidation. Runs on the M1 ML env (numpy +
hdbscan + asyncpg + DATABASE_URL). MODERATE compute (HDBSCAN over ~5–30K vectors)
— run OFF-PEAK / as a single careful pass, never stacked on the embed cron.

Run (repo root, M1 ML env):
  python -m backend.scripts.recall_scoped_probe --country US --hours 168 --max-n 30000
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg
import numpy as np

from backend.scripts.emergent_poc import _cluster

# Scoped grid: within a single country the corpus is smaller + more coherent, so
# smaller min_cluster_size is viable (the global floor is 30; a country's stories
# can be tens of signals). leaf keeps fine regional sub-stories; eom merges.
GRID = [
    ("leaf", 5, 2), ("leaf", 8, 3), ("leaf", 12, 3),
    ("eom", 8, 3), ("eom", 15, 5),
]

_FETCH = """
    SELECT s.id, s.headline, s.source_lang, se.vec::text AS emb
    FROM signal_embeddings se
    JOIN signals_v2 s ON s.id = se.signal_id
    WHERE s.country_code = $1
      AND s.timestamp > NOW() - ($2::int * INTERVAL '1 hour')
      AND s.headline IS NOT NULL AND length(s.headline) >= 20
    ORDER BY s.timestamp DESC
    LIMIT $3
"""

# Of the EXACT signals we fetched (the sample the scoped pass clusters), how many
# are already in a (global) topic — the directly-comparable global recall. (Bug
# fix 2026-06-30: the old version divided the country's FULL in-topic count by the
# capped sample size n, giving impossible >100% baselines.)
_BASELINE_INTERSECT = (
    "SELECT COUNT(DISTINCT signal_id) FROM topic_members "
    "WHERE signal_id = ANY($1::bigint[])"
)


def _parse_vec(text: str) -> list[float]:
    return [float(x) for x in text.strip().lstrip("[").rstrip("]").split(",") if x]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", required=True, help="ISO 2-letter, e.g. US")
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--max-n", type=int, default=30000)
    args = ap.parse_args()
    cc = args.country.upper()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)

    conn = await asyncpg.connect(db)
    try:
        # The big vec::text fetch (~5KB/row) blows the DB statement_timeout at
        # scale (the same timeout that froze the embed cron). This is a read-only
        # research probe → lift the limit for its session.
        await conn.execute("SET statement_timeout = '600s'")
        rows = await conn.fetch(_FETCH, cc, args.hours, args.max_n)
        ids = [int(r["id"]) for r in rows]
        baseline = (await conn.fetchval(_BASELINE_INTERSECT, ids)) if ids else 0
    finally:
        await conn.close()

    n = len(rows)
    if n < 50:
        print(f"{cc}: only {n} embedded signals in window — too few to probe", file=sys.stderr)
        sys.exit(1)
    embs = np.array([_parse_vec(r["emb"]) for r in rows], dtype=np.float32)
    base_recall = round(100.0 * (baseline or 0) / n, 2)
    print(f"{cc}: {n} embedded signals · global baseline in-topic={baseline} ({base_recall}%)",
          file=sys.stderr)

    results = []
    for sel, mcs, ms in GRID:
        labels = _cluster(embs, mcs, ms, sel)
        noise = int((labels == -1).sum())
        clustered = n - noise
        n_clusters = int(labels.max()) + 1 if labels.max() >= 0 else 0
        sizes = sorted(
            (int((labels == c).sum()) for c in range(n_clusters)), reverse=True
        )
        results.append({
            "selection": sel, "min_cluster_size": mcs, "min_samples": ms,
            "n_clusters": n_clusters,
            "clustered": clustered,
            "scoped_recall_pct": round(100.0 * clustered / n, 2),
            "noise_pct": round(100.0 * noise / n, 2),
            "largest_cluster": sizes[0] if sizes else 0,
            "median_cluster": sizes[len(sizes) // 2] if sizes else 0,
            # blob guard: a single cluster swallowing >40% of the country = the
            # #224 black-hole, NOT a recall win.
            "blob_flag": bool(sizes and sizes[0] > 0.4 * n),
        })
        print(
            f"  sel={sel} mcs={mcs} ms={ms} -> clusters={n_clusters} "
            f"scoped_recall={results[-1]['scoped_recall_pct']}% "
            f"noise={results[-1]['noise_pct']}% largest={results[-1]['largest_cluster']}"
            f"{' BLOB!' if results[-1]['blob_flag'] else ''}",
            file=sys.stderr,
        )

    # Best = highest recall WITHOUT a blob (purity guard), then most clusters.
    ranked = sorted(
        [r for r in results if not r["blob_flag"]] or results,
        key=lambda r: (-r["scoped_recall_pct"], -r["n_clusters"]),
    )

    out_dir = Path(__file__).resolve().parents[2] / "docs" / "research" / "recall-scoped"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "country": cc, "hours": args.hours, "embedded_signals": n,
        "global_baseline_in_topic": baseline, "global_baseline_recall_pct": base_recall,
        "results": results, "best_non_blob": ranked[0] if ranked else None,
    }
    (out_dir / f"scoped-probe-{cc}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False))

    lines = [
        f"# Scoped clustering recall probe — {cc} (#229 lever 2, R0)", "",
        f"{n} embedded signals (last {args.hours}h). **Global baseline: {baseline} "
        f"in a topic = {base_recall}%.** Goal: a scoped pass lifts recall WITHOUT a "
        "blob (largest cluster > 40% = #224 black-hole, not a win).", "",
        "| sel | mcs | ms | clusters | scoped_recall% | noise% | largest | median | blob |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda r: -r["scoped_recall_pct"]):
        lines.append(
            f"| {r['selection']} | {r['min_cluster_size']} | {r['min_samples']} | "
            f"{r['n_clusters']} | {r['scoped_recall_pct']} | {r['noise_pct']} | "
            f"{r['largest_cluster']} | {r['median_cluster']} | "
            f"{'⚠' if r['blob_flag'] else ''} |"
        )
    lines += [
        "", "## Read",
        f"- Global baseline for {cc} is {base_recall}%. If a non-blob config here "
        "beats it MATERIALLY, scoped regional passes are the recall lever — wire "
        "the per-country loop (engine spec R1) on the M1 off-peak.",
        "- If the best non-blob config is also ~1% (no lift), scoping does not help "
        "for this country → the ceiling is intrinsic (escalate to article bodies / "
        "language-scoped passes).",
    ]
    (out_dir / f"scoped-probe-{cc}.md").write_text("\n".join(lines))
    print(f"\nwrote {out_dir}/scoped-probe-{cc}.{{json,md}}", file=sys.stderr)
    print("BEST non-blob:", json.dumps(ranked[0] if ranked else None, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
