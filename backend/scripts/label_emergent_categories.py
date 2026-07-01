"""R3.1 emergent-extension — label the non_crisis stories into emergent categories.

The seed-anchored typing (compute_category_typing.py) marks 182 topics with a crisis
class and 166 as `non_crisis`. This step gives the non_crisis stories their EMERGENT
category (the open half of anchored-emergent): coarse complete-linkage over their
centroids → super-clusters → DeepSeek names each → writes dynamic_topics.category.
Singletons keep category NULL (served as their own label — honest, no fabricated group).

Cheap (~166 centroids + a handful of DeepSeek calls). Daytime-safe.
  python -m backend.scripts.label_emergent_categories --dry-run
  python -m backend.scripts.label_emergent_categories --write
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg
import numpy as np

from backend.scripts.compute_category_typing import _DS_URL  # reuse DeepSeek endpoint

COARSE = 0.90  # complete-linkage cut for emergent super-categories (coarser than umbrella 0.98)


def _complete_linkage(sims: "np.ndarray", threshold: float) -> dict[int, list[int]]:
    n = sims.shape[0]
    order = sorted(((float(sims[i, j]), int(i), int(j))
                    for i, j in np.argwhere(np.triu(sims >= threshold, k=1))), reverse=True)
    cluster_of = list(range(n))
    members: dict[int, list[int]] = {i: [i] for i in range(n)}
    for _s, i, j in order:
        ci, cj = cluster_of[i], cluster_of[j]
        if ci == cj:
            continue
        mi, mj = members[ci], members[cj]
        if float(sims[np.ix_(mi, mj)].min()) >= threshold:
            for p in mj:
                cluster_of[p] = ci
            mi.extend(mj)
            del members[cj]
    return {r: idxs for r, idxs in members.items() if len(idxs) >= 2}


async def _ds_name(member_labels: list[str], key: str) -> str:
    import httpx
    lst = "; ".join(member_labels[:10])
    prompt = ("These non-crisis news stories cluster together. Give a SHORT (2-4 word) "
              "emergent CATEGORY name that covers them (e.g. 'Football / World Cup', "
              "'Celebrity & Entertainment', 'Local Governance'). Stories: " + lst +
              "\nAnswer with ONLY the category name.")
    async with httpx.AsyncClient() as c:
        r = await c.post(_DS_URL, json={"model": "deepseek-chat", "temperature": 0,
                         "messages": [{"role": "user", "content": prompt}]},
                         headers={"Authorization": f"Bearer {key}"}, timeout=30.0)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip().strip('"')[:60]


async def main() -> None:
    ap = argparse.ArgumentParser(description="R3.1 emergent-category labeling for non_crisis.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--threshold", type=float, default=COARSE)
    args = ap.parse_args()
    db = os.environ.get("DATABASE_URL")
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not db:
        print("DATABASE_URL required", file=sys.stderr); sys.exit(2)

    conn = await asyncpg.connect(db)
    try:
        rows = await conn.fetch(
            "SELECT id, label, centroid_vec FROM dynamic_topics "
            "WHERE state='active' AND is_umbrella=false AND crisis_class='non_crisis' "
            "AND centroid_vec IS NOT NULL")
        n = len(rows)
        if n < 2:
            print(f"only {n} non_crisis — nothing to cluster"); return
        V = np.array([list(r["centroid_vec"]) for r in rows], dtype=np.float32)
        V /= (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)
        clusters = _complete_linkage(V @ V.T, args.threshold)
        print(f"non_crisis={n} · emergent super-categories={len(clusters)} · "
              f"singletons={n - sum(len(v) for v in clusters.values())}")

        assignments: list[tuple[int, str]] = []
        for _root, idxs in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
            labels = [rows[i]["label"] or "?" for i in idxs]
            name = await _ds_name(labels, key) if (args.write and key) else labels[0][:40]
            print(f"  [{name}] <- {len(idxs)}: {', '.join(l[:22] for l in labels[:4])}")
            for i in idxs:
                assignments.append((int(rows[i]["id"]), name))

        if args.write:
            async with conn.transaction():
                for tid, name in assignments:
                    await conn.execute("UPDATE dynamic_topics SET category=$2 WHERE id=$1", tid, name)
            print(f"wrote {len(assignments)} emergent-category labels")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
