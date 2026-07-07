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
import os, asyncio, random, itertools
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
    asyncio.run(main())
