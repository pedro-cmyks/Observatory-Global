#!/usr/bin/env python
"""OpenAI-space headline-lane tau from the FULL-HISTORY archive shards.

Pedro (2026-07-05): don't wait weeks — the archive embed pipeline
(/Volumes/Ext/Atlas/Embeddings/openai-3-small, text-embedding-3-small fp16)
IS the wild corpus. This measures the junk floor for query↔headline matching
in OpenAI space — the number the research semantic lane's OpenAI cutover
(L3 review W2a-ii, decision D2) was gated on.

Method = wild-junk-quantile (sem-assign 2026-07-04): sample pseudo-queries
from one set of shards, a corpus from DISJOINT shards, take each query's max
cosine over the corpus → the quantile distribution is the junk floor. The
same caveat as the e5 measurement applies (headline-as-pseudo-query
over-estimates vs real short queries), but cross-shard sampling over the
FULL HISTORY removes same-day syndication near-dupes far better than the
7-day hot corpus could (the pipeline also sha1-dedupes globally: n_dup 2.5M
already removed).

READ-ONLY on the shards; safe to run while the pipeline appends new ones.

Usage: python backend/scripts/calibrate_openai_headline_tau.py
         [--queries 2000] [--corpus 60000] [--clearance 0.005]
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

SHARD_DIR = Path("/Volumes/Ext/Atlas/Embeddings/openai-3-small")


def _load_sample(shards: list[Path], n: int, rng: random.Random) -> np.ndarray:
    """Uniformly sample ~n vectors across the given shards (fp32, L2-normed)."""
    out: list[np.ndarray] = []
    per = max(1, n // max(1, len(shards)))
    for p in shards:
        try:
            vecs = np.load(p)["vecs"].astype(np.float32)
        except Exception:
            continue  # partially-written shard while the pipeline runs
        take = min(per, len(vecs))
        idx = rng.sample(range(len(vecs)), take)
        out.append(vecs[idx])
        if sum(len(x) for x in out) >= n:
            break
    m = np.concatenate(out)[:n]
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", type=int, default=2000)
    ap.add_argument("--corpus", type=int, default=60000)
    ap.add_argument("--clearance", type=float, default=0.005)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    shards = sorted(SHARD_DIR.glob("shard-*.npz"))
    if len(shards) < 4:
        print(json.dumps({"error": "not enough shards", "found": len(shards)}))
        return 2
    rng = random.Random(args.seed)
    rng.shuffle(shards)
    # Disjoint shard sets → queries and corpus can never share a document.
    split = max(2, len(shards) // 5)
    q = _load_sample(shards[:split], args.queries, rng)
    c = _load_sample(shards[split:], args.corpus, rng)

    # Chunked max-cosine: queries (nq,1536) vs corpus (nc,1536).
    max_sim = np.full(len(q), -1.0, dtype=np.float32)
    step = 8192
    for i in range(0, len(c), step):
        sims = q @ c[i:i + step].T
        np.maximum(max_sim, sims.max(axis=1), out=max_sim)

    v = np.sort(max_sim)
    pick = lambda p: float(v[min(len(v) - 1, int(p * len(v)))])  # noqa: E731
    suggested = float(v[min(len(v) - 1, int((1.0 - args.clearance) * len(v)))])

    manifest = json.loads((SHARD_DIR / "manifest.json").read_text())
    print(json.dumps({
        "space": "text-embedding-3-small",
        "archive_vectors_available": manifest.get("n_vectors"),
        "shards_used": {"query_pool": split, "corpus_pool": len(shards) - split},
        "sampled": {"queries": len(q), "corpus": len(c)},
        "junk_quantiles": {"p50": round(pick(0.50), 4), "p90": round(pick(0.90), 4),
                           "p95": round(pick(0.95), 4), "p99": round(pick(0.99), 4),
                           "p995": round(pick(0.995), 4), "max": round(float(v[-1]), 4)},
        "suggested_headline_tau": round(suggested, 4),
        "clearance": args.clearance,
        "e5_comparison": {"junk_p50": 0.8873, "current_tau": 0.84,
                          "note": "e5 hot-corpus measurement 2026-07-05 — junk median ABOVE the tau"},
        "note": ("Cross-shard full-history sampling; global sha1-dedup already applied "
                 "by the pipeline. Headline-as-pseudo-query still over-estimates vs real "
                 "user queries — treat suggested tau as the UPPER calibration anchor and "
                 "the p95 as the floor candidate when the OpenAI cutover ships (W2a-ii/D2)."),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
