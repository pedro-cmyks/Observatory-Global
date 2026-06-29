"""Clustering-recall sweep (spec 2026-06-29 §4B.4) — the cheap lever.

The embedding-input ablation showed enrichment buys ~1pp recall while ~70% of
DIVERSE coverage (Gaza) falls to HDBSCAN noise. So the bottleneck is clustering
RECALL (#229), not the embedding input. This sweeps HDBSCAN params over a SINGLE
title-only embedding (embed once, cluster many) to find a configuration that
lowers diverse-coverage noise WITHOUT over-fragmenting into junk.

No re-embed, no vector invalidation. Read-only. Runs on the M1 (torch + e5 +
hdbscan + DATABASE_URL), free compute.

Run (repo root, M1 ML env):
  python -m backend.scripts.cluster_recall_sweep --hours 168 --max-n 8000

Reuses the ablation's pull/dedupe/probe helpers so the sample + Gaza/Vegas probes
are identical to §4B.3. Outputs JSON + Markdown under docs/research/embedding-ablation/.
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

from backend.scripts.emergent_poc import _build_embedder, _cluster
from backend.scripts.embedding_input_ablation import (
    _pull,
    _dedupe_clean,
    _probe_idxs,
    _recall_metric,
)

# Grid. min_cluster_size drives granularity (smaller → more, finer clusters →
# less noise but risk of junk splits); min_samples drives conservativeness
# (smaller → more points absorbed into clusters → less noise); selection 'leaf'
# keeps fine sub-clusters, 'eom' merges to stable parents.
GRID_MCS = [3, 4, 5, 8]
GRID_MS = [1, 2, 3]
GRID_SEL = ["leaf", "eom"]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--max-n", type=int, default=8000)
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)

    conn = await asyncpg.connect(db)
    try:
        raw = await _pull(conn, args.hours, args.max_n)
    finally:
        await conn.close()
    rows = _dedupe_clean(raw)
    gaza_idxs = _probe_idxs(rows, lambda h: ("gaza" in h or "israel" in h or "palestin" in h))
    print(f"sample {len(rows)} rows · gaza probe {len(gaza_idxs)}", file=sys.stderr)

    embed, device = _build_embedder()
    print(f"e5 on {device} — embedding title-only ONCE...", file=sys.stderr)
    embs = embed([f"passage: {r['headline']}" for r in rows]).astype(np.float32)

    results = []
    for sel in GRID_SEL:
        for mcs in GRID_MCS:
            for ms in GRID_MS:
                labels = _cluster(embs, mcs, ms, sel)
                n = len(rows)
                noise = int((labels == -1).sum())
                gr = _recall_metric(labels, gaza_idxs)
                # PURITY of the modal Gaza cluster: of the cluster that holds the
                # most Gaza rows, what fraction of its members are Gaza? Low purity
                # = a mega-blob that swallowed unrelated stories (high recall is
                # then a #224 black-hole artifact, NOT a win). This is the metric
                # that distinguishes a genuine merge from a blob.
                gaza_set = set(gaza_idxs)
                from collections import Counter as _C
                modal = _C(int(labels[i]) for i in gaza_idxs if labels[i] != -1)
                if modal:
                    cid, gaza_in = modal.most_common(1)[0]
                    csize = int((labels == cid).sum())
                    gaza_purity = round(gaza_in / max(csize, 1), 3)
                    modal_size = csize
                else:
                    gaza_purity, modal_size = None, 0
                results.append({
                    "selection": sel, "min_cluster_size": mcs, "min_samples": ms,
                    "n_clusters": int(labels.max()) + 1 if labels.max() >= 0 else 0,
                    "global_noise": round(noise / max(n, 1), 3),
                    "gaza_recall": gr["best_cluster_recall"],
                    "gaza_noise": gr["noise_frac"],
                    "gaza_purity": gaza_purity,
                    "modal_cluster_size": modal_size,
                    "gaza_spanned": gr["n_clusters_spanned"],
                })
                print(
                    f"  sel={sel} mcs={mcs} ms={ms} -> clusters={results[-1]['n_clusters']} "
                    f"global_noise={results[-1]['global_noise']} "
                    f"gaza_recall={gr['best_cluster_recall']} gaza_noise={gr['noise_frac']}",
                    file=sys.stderr,
                )

    # Rank by: lowest gaza_noise, then highest gaza_recall, then not-too-fragmented.
    ranked = sorted(
        results,
        key=lambda r: (r["gaza_noise"] if r["gaza_noise"] is not None else 1.0,
                       -(r["gaza_recall"] or 0.0)),
    )

    out_dir = Path(__file__).resolve().parents[2] / "docs" / "research" / "embedding-ablation"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"sample_size": len(rows), "gaza_probe_n": len(gaza_idxs),
               "baseline_note": "production uses mcs=5 ms=3 leaf (gaza_noise ~0.72 in smoke)",
               "results": results, "ranked_top": ranked[:8]}
    (out_dir / "cluster-sweep-latest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    lines = [
        "# Clustering-recall sweep (spec §4B.4)", "",
        f"Sample {len(rows)} deduped rows · gaza probe {len(gaza_idxs)} · title-only embedding.",
        "Goal: lower `gaza_noise` (diverse coverage shattered to noise) without over-fragmenting.", "",
        "Production baseline today: `mcs=5 ms=3 leaf`.", "",
        "| sel | mcs | ms | clusters | global_noise | gaza_recall | gaza_noise | gaza_purity | modal_size |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in ranked:
        lines.append(
            f"| {r['selection']} | {r['min_cluster_size']} | {r['min_samples']} | "
            f"{r['n_clusters']} | {r['global_noise']} | {r['gaza_recall']} | {r['gaza_noise']} | "
            f"{r['gaza_purity']} | {r['modal_cluster_size']} |"
        )
    lines += [
        "", "## Read",
        "- Top rows = lowest Gaza-noise configs. If one materially beats the baseline "
        "`mcs=5 ms=3 leaf` WITHOUT global_noise/cluster-count exploding into junk, that "
        "param set feeds the snapshot + persisted clustering crons (#229 lever 1/2).",
        "- If nothing beats baseline meaningfully, the recall ceiling is intrinsic to "
        "headline-only short text → escalate to scoped REGIONAL passes (#229 lever 2) or "
        "the article-body lever (§4C).",
    ]
    (out_dir / "cluster-sweep-latest.md").write_text("\n".join(lines))
    print(f"\nwrote {out_dir}/cluster-sweep-latest.{{json,md}}", file=sys.stderr)
    print("TOP:", json.dumps(ranked[:5], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
