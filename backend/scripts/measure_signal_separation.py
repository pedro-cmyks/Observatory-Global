#!/usr/bin/env python
"""SIGNAL-level separation: does whitening ("all-but-top" k=1) help CLUSTERING?

  same-story = two SIGNALS in the same topic (topic_members).
  diff-story = two signals in different topics.
  separation = gap between same/diff cosine distributions + ROC-AUC.

If whitening raises AUC/gap at the SIGNAL level, HDBSCAN over whitened signal
embeddings should cross the recall/purity cliff (raw e5 can't get both — see
2026-06-29 engine notes). READ-ONLY, sampled.
"""
from __future__ import annotations
import os, asyncio, random, itertools
import numpy as np
import asyncpg


def parse_vec(t: str) -> np.ndarray:
    return np.fromstring(t.strip().lstrip("[").rstrip("]"), sep=",", dtype=np.float32)


async def load():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute("SET statement_timeout = 60000")
    rows = await conn.fetch(
        """
        WITH m AS (
          SELECT topic_id, signal_id,
                 row_number() OVER (PARTITION BY topic_id ORDER BY random()) AS rn,
                 count(*) OVER (PARTITION BY topic_id) AS cnt
          FROM topic_members
          WHERE role='evidence' AND engine_version='v1-compat'
            AND assigned_at > NOW() - INTERVAL '21 days')
        SELECT m.topic_id, e.vec::text AS vec
        FROM m JOIN signal_embeddings e ON e.signal_id = m.signal_id
        WHERE m.cnt >= 3 AND m.rn <= 20
        LIMIT 4000
        """
    )
    await conn.close()
    tops, vecs = [], []
    for r in rows:
        v = parse_vec(r["vec"])
        if v.shape[0] >= 100:
            tops.append(r["topic_id"]); vecs.append(v)
    return np.array(tops), np.stack(vecs)


def norm(m):
    n = np.linalg.norm(m, axis=1, keepdims=True); n[n == 0] = 1; return m / n


def all_but_top(m, k):
    x = m - m.mean(0, keepdims=True)
    if k > 0:
        _, _, Vt = np.linalg.svd(x, full_matrices=False)
        top = Vt[:k]; x = x - (x @ top.T) @ top
    return x


def pairs(V, groups_by, n=5000, seed=0):
    rng = random.Random(seed); Vn = norm(V)
    by = {}
    for i, g in enumerate(groups_by):
        by.setdefault(g, []).append(i)
    same = [p for g in by.values() if len(g) >= 2 for p in itertools.combinations(g, 2)]
    rng.shuffle(same); same = same[:n]
    idx = list(range(len(groups_by))); diff = []
    while len(diff) < n:
        a, b = rng.sample(idx, 2)
        if groups_by[a] != groups_by[b]:
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


async def main():
    tops, V = await load()
    print(f"signals={len(tops)}  topics={len(set(tops))}  dim={V.shape[1]}")
    s, d = pairs(V, tops); report("e5 raw", s, d)
    for k in (1, 3, 5, 10):
        s, d = pairs(all_but_top(V, k), tops); report(f"all-but-top k={k}", s, d)


if __name__ == "__main__":
    asyncio.run(main())
