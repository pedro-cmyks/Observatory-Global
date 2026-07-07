#!/usr/bin/env python
"""Measure how SEPARABLE same-story vs different-story topics are in the centroid
space — and whether whitening ("all-but-the-top") de-compresses it. READ-ONLY.

  same-story  = two topics sharing a parent umbrella (parent_id) — assembled dups.
  diff-story  = two topics under different umbrellas.
  separation  = gap between the same/diff cosine distributions + ROC-AUC
                (0.5 = space can't tell them apart; 1.0 = perfectly separable).

Whitening subtracts the mean and removes the top-k principal directions (the
common anisotropic cone). If AUC/gap rises, the space got MORE discriminative.
"""
from __future__ import annotations
import os, asyncio, random, itertools, json
import numpy as np
import asyncpg


async def load():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    rows = await conn.fetch(
        """SELECT id, parent_id, centroid_vec FROM dynamic_topics
           WHERE parent_id IS NOT NULL AND centroid_vec IS NOT NULL"""
    )
    await conn.close()
    parents, vecs = [], []
    for r in rows:
        parents.append(int(r["parent_id"]))
        vecs.append(np.asarray(r["centroid_vec"], dtype=np.float32))
    return np.array(parents), np.stack(vecs)


def norm(m):
    n = np.linalg.norm(m, axis=1, keepdims=True); n[n == 0] = 1; return m / n


def all_but_top(m, k):
    x = m - m.mean(0, keepdims=True)
    if k > 0:
        _, _, Vt = np.linalg.svd(x, full_matrices=False)
        top = Vt[:k]
        x = x - (x @ top.T) @ top
    return x


# ---- Global-fit whitening (the ASSET this task produces) -------------------
# Fit mu + top principal directions on a broad sample ONCE, then apply the SAME
# transform everywhere (vs all_but_top which refits per-matrix). This mirrors
# app/services/whitening.apply_whitening so the measurement uses the exact math
# the app will load.

def fit_whitening(sample: np.ndarray, k_max: int):
    """Return (mu float32[dim], components float32[k_max][dim]) from a sample.

    Top principal directions via eigendecomposition of the dim×dim covariance
    (BLAS-fast) rather than a full SVD of the n×dim matrix — the latter computes
    the huge n×dim U we don't need and crawls on the mindful M1. Eigenvectors of
    Xc^T Xc are exactly the right singular vectors of Xc."""
    Xc = (sample - sample.mean(0, keepdims=True)).astype(np.float64)
    mu = sample.mean(0).astype(np.float32)
    cov = Xc.T @ Xc                       # (dim, dim), symmetric PSD
    w, V = np.linalg.eigh(cov)            # ascending eigenvalues
    comps = V[:, ::-1].T[:k_max]          # top-k_max directions, descending
    return mu, np.ascontiguousarray(comps, dtype=np.float32)


def apply_fitted(vecs: np.ndarray, mu: np.ndarray, comps: np.ndarray, k: int):
    """Center by mu, project out first-k components, L2-normalize."""
    y = vecs.astype(np.float32) - mu
    if k > 0 and len(comps):
        top = comps[:k]
        y = y - (y @ top.T) @ top
    n = np.linalg.norm(y, axis=1, keepdims=True); n[n == 0] = 1.0
    return y / n


# ---- Signal-level separation (signal_embeddings × topic_members) -----------

async def load_signal_sample(n_fit=50_000):
    """Broad random sample of e5 signal vectors to FIT the global transform on.

    TABLESAMPLE BERNOULLI (not ORDER BY random()) — a full sort of 186k×768
    trips the pooler statement_timeout. Bernoulli streams a per-row coin flip."""
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute("SET statement_timeout = 0")
    total = await conn.fetchval("SELECT count(*) FROM signal_embeddings")
    pct = min(100.0, 100.0 * n_fit / max(total, 1))
    rows = await conn.fetch(
        f"""SELECT vec::text AS t FROM signal_embeddings
            TABLESAMPLE BERNOULLI ({pct:.4f}) LIMIT $1""", n_fit)
    await conn.close()
    return np.array([json.loads(r["t"]) for r in rows], dtype=np.float32)


async def load_evidence_signals(per_topic_cap=60, min_per_topic=4):
    """Evidence signals grouped by topic_id, for same/diff-topic pair sampling."""
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute("SET statement_timeout = 0")
    rows = await conn.fetch(
        """
        SELECT tm.topic_id, se.vec::text AS t
        FROM topic_members tm
        JOIN signal_embeddings se ON se.signal_id = tm.signal_id
        WHERE tm.role = 'evidence'
        """)
    await conn.close()
    by_t: dict[str, list] = {}
    for r in rows:
        by_t.setdefault(r["topic_id"], []).append(json.loads(r["t"]))
    rng = random.Random(0)
    topics, vecs, tid = [], [], []
    for t, vs in by_t.items():
        if len(vs) < min_per_topic:
            continue
        if len(vs) > per_topic_cap:
            vs = rng.sample(vs, per_topic_cap)
        for v in vs:
            topics.append(t); vecs.append(v)
    return np.array(topics), np.asarray(vecs, dtype=np.float32)


def signal_pair_cosines(Vn, topics, n=8000, seed=0):
    rng = random.Random(seed)
    by_t: dict = {}
    for i, t in enumerate(topics):
        by_t.setdefault(t, []).append(i)
    same = []
    for g in by_t.values():
        if len(g) >= 2:
            same += list(itertools.combinations(g, 2))
    rng.shuffle(same); same = same[:n]
    idx = list(range(len(topics))); diff = []
    guard = 0
    while len(diff) < n and guard < n * 40:
        a, b = rng.sample(idx, 2); guard += 1
        if topics[a] != topics[b]:
            diff.append((a, b))
    s = np.array([float(Vn[a] @ Vn[b]) for a, b in same])
    d = np.array([float(Vn[a] @ Vn[b]) for a, b in diff])
    return s, d


async def main_signals(k_sweep=(0, 1, 2, 3, 5), k_max=5, n_fit=50_000):
    print("=== SIGNAL-LEVEL separation (signal_embeddings × topic_members role=evidence) ===")
    fit = await load_signal_sample(n_fit)
    print(f"fit sample={fit.shape[0]}  dim={fit.shape[1]}")
    mu, comps = fit_whitening(fit, k_max)
    topics, V = await load_evidence_signals()
    n_topics = len(set(topics))
    print(f"evidence signals={len(topics)}  topics(>=4)={n_topics}  dim={V.shape[1]}")
    print("  k   same_p50  diff_p50    gap     AUC")
    for k in k_sweep:
        Vn = apply_fitted(V, mu, comps, k)
        s, d = signal_pair_cosines(Vn, topics)
        print(f"  {k:<3} {np.median(s):8.3f} {np.median(d):9.3f} {np.median(s)-np.median(d):+8.3f}  {auc(s, d):.3f}")


def pair_cosines(V, parents, n=4000, seed=0):
    rng = random.Random(seed)
    Vn = norm(V)
    by_p = {}
    for i, p in enumerate(parents):
        by_p.setdefault(p, []).append(i)
    same = [pair for g in by_p.values() if len(g) >= 2
            for pair in itertools.combinations(g, 2)]
    rng.shuffle(same); same = same[:n]
    idx = list(range(len(parents))); diff = []
    while len(diff) < n:
        a, b = rng.sample(idx, 2)
        if parents[a] != parents[b]:
            diff.append((a, b))
    s = np.array([float(Vn[a] @ Vn[b]) for a, b in same])
    d = np.array([float(Vn[a] @ Vn[b]) for a, b in diff])
    return s, d


def auc(s, d):
    allv = np.concatenate([s, d]); order = allv.argsort()
    ranks = np.empty(len(allv)); ranks[order] = np.arange(1, len(allv) + 1)
    return (ranks[:len(s)].sum() - len(s) * (len(s) + 1) / 2) / (len(s) * len(d))


def report(name, s, d):
    print(f"  {name:18} same_p50={np.median(s):.3f}  diff_p50={np.median(d):.3f}"
          f"  gap={np.median(s) - np.median(d):+.3f}  AUC={auc(s, d):.3f}")


async def load_all():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    rows = await conn.fetch(
        "SELECT id, parent_id, label, centroid_vec FROM dynamic_topics WHERE centroid_vec IS NOT NULL")
    await conn.close()
    ids, parents, labels, vecs = [], [], [], []
    for r in rows:
        ids.append(int(r["id"])); parents.append(r["parent_id"]); labels.append(r["label"])
        vecs.append(np.asarray(r["centroid_vec"], dtype=np.float32))
    return np.array(ids), parents, labels, np.stack(vecs)


def top_neighbors(Vn, ids, labels, pi, exclude, k=6):
    sims = Vn @ Vn[pi]
    out = []
    for j in np.argsort(-sims):
        if j == pi or int(ids[j]) in exclude:
            continue
        out.append(f"{labels[j][:24]} {sims[j]:.2f}")
        if len(out) >= k:
            break
    return out


async def main():
    parents, V = await load()
    print(f"child topics={len(parents)}  umbrellas(w/ children)={len(set(parents))}  dim={V.shape[1]}")
    s, d = pair_cosines(V, parents); report("e5 raw", s, d)
    for k in (1, 5, 15, 30, 60):
        s, d = pair_cosines(all_but_top(V, k), parents); report(f"all-but-top k={k}", s, d)

    # Neighbor quality (measure-before-finalize): raw vs whitened, NO token gate.
    ids, aparents, labels, Vall = await load_all()
    id2idx = {int(i): n for n, i in enumerate(ids)}
    excl = {517, 52, 1419} | {int(ids[i]) for i, p in enumerate(aparents) if p == 1837}
    Vn_raw = norm(Vall)
    Vn_w = norm(all_but_top(Vall, 1))
    for pid, name in [(1837, "Venezuela Earthquakes"), (52, "Colombia election"), (1419, "Peru election")]:
        pi = id2idx.get(pid)
        if pi is None:
            continue
        print(f"\n== neighbors of {name} (raw cosine, no gate) ==")
        print("  RAW:      " + " | ".join(top_neighbors(Vn_raw, ids, labels, pi, excl)))
        print("  WHITENED: " + " | ".join(top_neighbors(Vn_w, ids, labels, pi, excl)))


if __name__ == "__main__":
    import sys
    if "--signals" in sys.argv:
        asyncio.run(main_signals())
    else:
        asyncio.run(main())
