"""External-baseline comparison (PR3-09) — the ≥1 external baseline P1 + P8 require.

The paper bar: Atlas's engine must be measured against a STANDARD off-the-shelf method,
not only the internal v1-compat-vs-unified-v2 A/B. This runs a panel of external
clustering baselines over the SAME e5 corpus and the SAME structural, label-free metrics
Atlas reports, so the comparison isolates Atlas's contribution (scoped clustering +
lifecycle) from the representation (e5, held constant).

Baselines (all sklearn/hdbscan — no py3.14 wheel fight; BERTopic-proper is numba-blocked
on py3.14 and left as a follow-up, but its CORE is HDBSCAN-over-embeddings, which IS here):
  - KMeans (flat-embedding, the classic partition baseline)
  - Agglomerative/Ward (flat-embedding, hierarchical)
  - HDBSCAN-global (density; the algorithm BERTopic wraps, minus UMAP+c-TF-IDF)
  - Atlas: nearest active-centroid assignment with the admission gate (how serving categorizes)

Metrics (label-free, identical across methods): n_topics, coverage% (non-noise),
mean intra-topic coherence (cosine), median topic size, silhouette. Fair-K: the flat
methods use K = the number of Atlas topics the sample actually touches (matched granularity).

Read-only. Usage (from backend/, model venv w/ sklearn):
    python -m scripts.external_baseline_comparison [--n 10000] [--gate 0.85]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys


def _parse_vec(v) -> list[float]:
    # signal_embeddings.vec is pgvector ('[...]'); dynamic_topics.centroid_vec is a
    # Postgres real[] ('{...}'). Handle both bracket styles.
    if isinstance(v, str):
        return [float(x) for x in v.strip("[]{}").split(",")]
    return list(v)


async def _load(n: int):
    import asyncpg
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(
            """
            SELECT e.signal_id, e.vec::text AS vec, s.headline
            FROM signal_embeddings e JOIN signals_v2 s ON s.id = e.signal_id
            WHERE s.timestamp > NOW() - INTERVAL '168 hours'
              AND s.headline IS NOT NULL AND length(s.headline) >= 20
            ORDER BY s.timestamp DESC
            LIMIT $1
            """,
            n,
        )
        cents = await conn.fetch(
            "SELECT id, centroid_vec::text AS vec FROM dynamic_topics "
            "WHERE state='active' AND centroid_vec IS NOT NULL"
        )
    finally:
        await conn.close()
    return rows, cents


def _coherence(X, labels, rng, max_pairs=2000):
    """Mean intra-topic pairwise cosine (X is L2-normalised → dot = cosine)."""
    import numpy as np
    per = []
    for lab in set(labels.tolist()):
        if lab < 0:  # HDBSCAN noise
            continue
        idx = np.where(labels == lab)[0]
        if len(idx) < 2:
            continue
        if len(idx) > 60:  # sample pairs for big clusters
            idx = rng.choice(idx, 60, replace=False)
        V = X[idx]
        sims = V @ V.T
        iu = np.triu_indices(len(idx), k=1)
        per.append(float(sims[iu].mean()))
    return float(np.mean(per)) if per else 0.0


def _metrics(name, X, labels, rng):
    import numpy as np
    n = len(labels)
    noise = int((labels < 0).sum())
    topics = sorted(set(int(l) for l in labels if l >= 0))
    sizes = [int((labels == t).sum()) for t in topics]
    return {
        "method": name,
        "n_topics": len(topics),
        "coverage_pct": round(100.0 * (n - noise) / n, 1),
        "coherence": round(_coherence(X, labels, rng), 3),
        "median_topic_size": int(np.median(sizes)) if sizes else 0,
        "max_topic_size": max(sizes) if sizes else 0,
        "blob_frac_pct": round(100.0 * max(sizes) / n, 1) if sizes else 0.0,
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--gate", type=float, default=0.85, help="Atlas admission cosine")
    ap.add_argument("--out", default="docs/research/embedding-ablation/2026-07-01-external-baseline.json")
    args = ap.parse_args()

    import numpy as np
    rng = np.random.default_rng(42)

    print(f"loading {args.n} embedded signals + Atlas centroids…", file=sys.stderr)
    rows, cents = await _load(args.n)
    X = np.asarray([_parse_vec(r["vec"]) for r in rows], dtype=np.float32)
    X /= (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    C = np.asarray([_parse_vec(c["vec"]) for c in cents], dtype=np.float32)
    C /= (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)
    print(f"loaded X={X.shape}, centroids={C.shape}", file=sys.stderr)

    # ── Atlas: nearest active centroid + admission gate ──
    sims = X @ C.T                       # (n, n_centroids)
    nearest = sims.argmax(axis=1)
    best = sims.max(axis=1)
    atlas_labels = np.where(best >= args.gate, nearest, -1)
    k_atlas = len(set(int(l) for l in atlas_labels if l >= 0))  # matched-K for flat methods
    print(f"Atlas touches {k_atlas} topics at gate {args.gate}", file=sys.stderr)

    results = [_metrics("Atlas (scoped, gated)", X, atlas_labels, rng)]

    # ── KMeans (flat-embedding) ──
    from sklearn.cluster import MiniBatchKMeans, AgglomerativeClustering
    K = max(2, k_atlas)
    print(f"KMeans K={K}…", file=sys.stderr)
    km = MiniBatchKMeans(n_clusters=K, random_state=42, n_init=3, batch_size=1024).fit(X)
    results.append(_metrics(f"KMeans (flat, K={K})", X, km.labels_, rng))

    # ── Agglomerative/Ward (flat-embedding, hierarchical) — subsample if big (O(n^2)) ──
    if args.n <= 12000:
        print(f"Agglomerative Ward K={K}…", file=sys.stderr)
        ag = AgglomerativeClustering(n_clusters=K, linkage="ward").fit(X)
        results.append(_metrics(f"Agglomerative/Ward (flat, K={K})", X, ag.labels_, rng))
    else:
        print("skip Agglomerative (n>12000, O(n^2) memory)", file=sys.stderr)

    # ── HDBSCAN-global (density; BERTopic's core minus UMAP+cTFIDF) ──
    try:
        import hdbscan
        mcs = max(15, args.n // 400)
        print(f"HDBSCAN-global min_cluster_size={mcs}…", file=sys.stderr)
        hd = hdbscan.HDBSCAN(min_cluster_size=mcs, metric="euclidean").fit(X)
        results.append(_metrics(f"HDBSCAN-global (mcs={mcs})", X, hd.labels_, rng))
    except Exception as e:  # noqa: BLE001
        print(f"HDBSCAN failed: {e}", file=sys.stderr)

    report = {
        "n_docs": int(len(X)), "atlas_gate": args.gate, "k_atlas": k_atlas,
        "note": "same e5 corpus + same label-free metrics; BERTopic-proper numba-blocked on "
                "py3.14 (its core HDBSCAN-over-embeddings IS the HDBSCAN-global row).",
        "results": results,
    }
    print("\n" + json.dumps(report, indent=2))
    print("\n" + "=" * 90)
    hdr = f"{'method':<32}{'topics':>8}{'cover%':>8}{'coher':>8}{'medSize':>9}{'blob%':>7}"
    print(hdr); print("-" * 90)
    for r in results:
        print(f"{r['method']:<32}{r['n_topics']:>8}{r['coverage_pct']:>8}"
              f"{r['coherence']:>8}{r['median_topic_size']:>9}{r['blob_frac_pct']:>7}")

    try:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nwrote {args.out}", file=sys.stderr)
    except OSError as e:
        print(f"(write failed: {e})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
