"""Whitening cluster sweep — does "all-but-top(k)" whitening cross the recall/
purity cliff that raw e5 + HDBSCAN could not (2026-06-29 engine notes)?

Context. The 2026-06-29 sweep found NO HDBSCAN config gives both high recall and
high purity on raw e5: `leaf` = purity 1.0 but shatters (Gaza recall 0.04, ~70%
noise); `eom`/big mcs = recall 0.97 but mega-blob (0.49 purity, the #224 black
hole). The 2026-07-06/07 signal-separation harness (measure_signal_separation.py)
diagnosed WHY: raw e5 cosine is scale-COMPRESSED (same/diff story medians
0.916/0.788, both pegged), so density can't separate structure — even though the
pair AUC is already 0.985. All-but-top(k=1) whitening de-compresses it 4.4x
(same 0.557 / diff -0.008). This harness tests the operational claim: with that
contrast restored, does a single HDBSCAN config now hit BOTH high recall AND high
purity?

Method. Faithful to the production clustering input (reuses emergent_poc pull/
clean/cluster + the ablation's Gaza probe). Embed ONCE per space, then cluster
RAW and WHITENED(k) across the same mcs/min_samples/selection grid. Every config
reports recall AND purity together so the frontier is visible. Spaces:
  - e5 (multilingual-e5-base, the production embedder), raw + whitened k∈{1,2,3}
  - OpenAI text-embedding-3-small (optional, needs OPENAI_API_KEY), raw + whitened

Read-only. Runs on the M1 (torch + e5 + hdbscan + DATABASE_URL). OpenAI branch
embeds the same deduped sample via the API (~few thousand short headlines, cents).

Run (repo root, M1 ML env):
  python -m backend.scripts.cluster_whiten_sweep --hours 168 --max-n 8000
  OPENAI_API_KEY=... python -m backend.scripts.cluster_whiten_sweep --openai

Outputs JSON + Markdown under docs/research/embedding-whitening/.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path

import asyncpg
import numpy as np

from backend.scripts.emergent_poc import (
    _build_embedder,
    _cluster,
    _cluster_stats,
    whiten_all_but_top,
)
from backend.scripts.embedding_input_ablation import (
    _pull,
    _dedupe_clean,
    _probe_idxs,
)

# Grid mirrors cluster_recall_sweep so the raw baseline is comparable. Trimmed
# to the informative corners (min_samples 1 vs 3, both selections) so the sweep
# finishes on the M1 in minutes; the full ms grid added no separating info.
GRID_MCS = [4, 5, 8]
GRID_MS = [1, 3]
GRID_SEL = ["leaf", "eom"]
WHITEN_KS = [1, 2, 3]


def _config_metrics(labels: np.ndarray, embs: np.ndarray, rows: list[dict],
                    gaza_idxs: list[int]) -> dict:
    """Recall AND purity for one clustering, together — the joint frontier point.

    gaza_recall = largest single cluster's share of the Gaza probe set (did the
      diverse coverage get pulled together?).
    gaza_purity = of that modal cluster, what fraction of its MEMBERS are Gaza?
      Low purity = a mega-blob swallowed unrelated stories → the recall is a
      black-hole artifact, not a real merge. This pair is the cliff test.
    """
    n = len(rows)
    noise = int((labels == -1).sum())
    n_clusters = int(labels.max()) + 1 if labels.max() >= 0 else 0

    labs = [int(labels[i]) for i in gaza_idxs]
    in_cluster = [l for l in labs if l != -1]
    gaza_noise = round(sum(1 for l in labs if l == -1) / max(len(gaza_idxs), 1), 3)
    modal = Counter(in_cluster)
    if modal:
        cid, gaza_in = modal.most_common(1)[0]
        csize = int((labels == cid).sum())
        gaza_recall = round(gaza_in / max(len(gaza_idxs), 1), 3)
        gaza_purity = round(gaza_in / max(csize, 1), 3)
        modal_size = csize
    else:
        gaza_recall, gaza_purity, modal_size = 0.0, None, 0

    clusters = _cluster_stats(labels, embs, rows)
    cohesion = round(float(np.mean([c["cohesion"] for c in clusters])) if clusters else 0.0, 3)

    # Joint score: reward pulling the probe together (recall) AND keeping the
    # cluster clean (purity), with a mild penalty for global fragmentation into
    # noise. F1 of recall/purity is 0 unless BOTH are high — that IS the cliff.
    if gaza_purity is not None and (gaza_recall + gaza_purity) > 0:
        f1 = 2 * gaza_recall * gaza_purity / (gaza_recall + gaza_purity)
    else:
        f1 = 0.0
    joint = round(f1 * (1 - round(noise / max(n, 1), 3)), 3)

    return {
        "n_clusters": n_clusters,
        "global_noise": round(noise / max(n, 1), 3),
        "gaza_recall": gaza_recall,
        "gaza_purity": gaza_purity,
        "gaza_noise": gaza_noise,
        "modal_cluster_size": modal_size,
        "cohesion": cohesion,
        "recall_purity_f1": round(f1, 3),
        "joint_score": joint,
    }


def _sweep_space(space: str, embs: np.ndarray, rows: list[dict],
                 gaza_idxs: list[int]) -> list[dict]:
    out = []
    for sel in GRID_SEL:
        for mcs in GRID_MCS:
            for ms in GRID_MS:
                labels = _cluster(embs, mcs, ms, sel)
                m = _config_metrics(labels, embs, rows, gaza_idxs)
                m.update({"space": space, "selection": sel,
                          "min_cluster_size": mcs, "min_samples": ms})
                out.append(m)
                print(
                    f"  [{space}] sel={sel} mcs={mcs} ms={ms} -> "
                    f"recall={m['gaza_recall']} purity={m['gaza_purity']} "
                    f"f1={m['recall_purity_f1']} joint={m['joint_score']} "
                    f"noise={m['global_noise']} clusters={m['n_clusters']}",
                    file=sys.stderr,
                )
    return out


def _openai_embed(texts: list[str]) -> np.ndarray:
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=60.0)
    vecs: list[list[float]] = []
    B = 512
    for i in range(0, len(texts), B):
        batch = [t[:8000] for t in texts[i:i + B]]
        resp = client.embeddings.create(model="text-embedding-3-small", input=batch)
        vecs.extend(d.embedding for d in resp.data)
        print(f"  openai embedded {min(i + B, len(texts))}/{len(texts)}", file=sys.stderr)
    return np.asarray(vecs, dtype=np.float32)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--max-n", type=int, default=8000)
    ap.add_argument("--openai", action="store_true",
                    help="Also embed the SAME sample via OpenAI text-embedding-3-small "
                         "(needs OPENAI_API_KEY) and sweep raw + whitened.")
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
    if len(gaza_idxs) < 10:
        print("gaza probe too small — sample window may be thin", file=sys.stderr)

    embed, device = _build_embedder()
    print(f"e5 on {device} — embedding title-only ONCE...", file=sys.stderr)
    e5 = embed([f"passage: {r['headline']}" for r in rows]).astype(np.float32)

    all_results: list[dict] = []
    all_results += _sweep_space("e5_raw", e5, rows, gaza_idxs)
    for k in WHITEN_KS:
        w = whiten_all_but_top(e5, k)
        all_results += _sweep_space(f"e5_whiten_k{k}", w, rows, gaza_idxs)

    if args.openai:
        if not os.environ.get("OPENAI_API_KEY"):
            print("--openai set but OPENAI_API_KEY missing; skipping", file=sys.stderr)
        else:
            print("embedding same sample via OpenAI...", file=sys.stderr)
            oa = _openai_embed([r["headline"] for r in rows])
            all_results += _sweep_space("openai_raw", oa, rows, gaza_idxs)
            for k in WHITEN_KS:
                w = whiten_all_but_top(oa, k)
                all_results += _sweep_space(f"openai_whiten_k{k}", w, rows, gaza_idxs)

    # Best joint config per space + the global frontier.
    by_space: dict[str, dict] = {}
    for r in all_results:
        cur = by_space.get(r["space"])
        if cur is None or r["joint_score"] > cur["joint_score"]:
            by_space[r["space"]] = r
    ranked = sorted(all_results, key=lambda r: -r["joint_score"])

    out_dir = Path(__file__).resolve().parents[2] / "docs" / "research" / "embedding-whitening"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "sample_size": len(rows),
        "gaza_probe_n": len(gaza_idxs),
        "hours": args.hours,
        "whiten_ks": WHITEN_KS,
        "grid": {"mcs": GRID_MCS, "min_samples": GRID_MS, "selection": GRID_SEL},
        "cliff_test": "a space CROSSES the cliff if its best config has high "
                      "gaza_recall AND high gaza_purity (recall_purity_f1 high) "
                      "without global_noise exploding.",
        "best_per_space": by_space,
        "all_results": all_results,
    }
    (out_dir / "whiten-sweep-latest.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False))

    lines = [
        "# Whitening cluster sweep — crossing the recall/purity cliff", "",
        f"Sample {len(rows)} deduped rows · Gaza probe {len(gaza_idxs)} · "
        f"title-only embedding · window {args.hours}h.", "",
        "Cliff test: does a space's BEST config hit high recall AND high purity "
        "together (F1) — the pair the 2026-06-29 raw-e5 sweep could not?", "",
        "## Best joint config per embedding space", "",
        "| space | sel | mcs | ms | recall | purity | R/P F1 | noise | clusters | modal |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for space in ["e5_raw", "e5_whiten_k1", "e5_whiten_k2", "e5_whiten_k3",
                  "openai_raw", "openai_whiten_k1", "openai_whiten_k2", "openai_whiten_k3"]:
        r = by_space.get(space)
        if not r:
            continue
        lines.append(
            f"| {space} | {r['selection']} | {r['min_cluster_size']} | {r['min_samples']} | "
            f"{r['gaza_recall']} | {r['gaza_purity']} | {r['recall_purity_f1']} | "
            f"{r['global_noise']} | {r['n_clusters']} | {r['modal_cluster_size']} |"
        )
    lines += [
        "", "## Global frontier (top 12 by joint score)", "",
        "| space | sel | mcs | ms | recall | purity | R/P F1 | joint | noise |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in ranked[:12]:
        lines.append(
            f"| {r['space']} | {r['selection']} | {r['min_cluster_size']} | {r['min_samples']} | "
            f"{r['gaza_recall']} | {r['gaza_purity']} | {r['recall_purity_f1']} | "
            f"{r['joint_score']} | {r['global_noise']} |"
        )
    lines += [
        "", "## Read",
        "- If a whitened space's best `R/P F1` materially beats `e5_raw`'s best "
        "(raw is expected ~0 — high recall XOR high purity, never both), whitening "
        "CROSSES the cliff → wire it into the snapshot clustering behind "
        "`--whiten-k` (reversible).",
        "- Compare `e5_whiten_k1` vs `openai_raw` vs `openai_whiten_k*`: whitening "
        "is free (no API), OpenAI costs tokens. If whitened-e5 matches OpenAI, "
        "whitening is the cheaper cliff-crosser.",
        "- Watch `global_noise` on the winning config: a low-noise, high-F1 config "
        "is the real win (fewer near-duplicate topics at the source, less "
        "constellation-assembly downstream).",
    ]
    (out_dir / "whiten-sweep-latest.md").write_text("\n".join(lines))
    print(f"\nwrote {out_dir}/whiten-sweep-latest.{{json,md}}", file=sys.stderr)
    print("BEST PER SPACE:", json.dumps(by_space, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
