"""Taxonomy revision — train + persist the v2 reject gate (#204), measure-first.

Trains the binary in-scope/OUT_OF_SCOPE LogisticRegression over the e5 embeddings
of the FULL gold base, persists it (joblib + metadata), then VALIDATES on a fresh
real-stream sample (recent signals NOT in the gold) — because the gold is ~65%
OOS but the live stream is ~91% OOS, so the keep-rate + reject quality must be
checked on the real distribution before any wiring.

No prod change: writes a model artifact + prints a validation report (keep-rate at
each threshold + spot-check of rejected vs kept headlines for eyeballing).

Run: python -m backend.scripts.ensemble.train_v2_gate
"""
from __future__ import annotations

import asyncio
import json
import os

import asyncpg
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

GOLD = "docs/research/taxonomy-revision/goldset.json"
MODEL_PATH = "backend/models/v2_gate.joblib"
OOS = "OUT_OF_SCOPE"


def _parse_vec(txt: str) -> np.ndarray:
    return np.fromstring(txt.strip("[]"), sep=",", dtype=np.float32)


async def _vecs_for(conn, ids: list[int]) -> dict[int, np.ndarray]:
    rows = await conn.fetch(
        "select signal_id, vec::text v from signal_embeddings where signal_id = any($1)", ids)
    return {r["signal_id"]: _parse_vec(r["v"]) for r in rows}


async def _real_stream_sample(conn, exclude: set[int], n: int) -> list[dict]:
    rows = await conn.fetch(
        """SELECT s.id, s.headline, e.vec::text v
           FROM signals_v2 s JOIN signal_embeddings e ON e.signal_id=s.id
           WHERE s.headline IS NOT NULL AND length(s.headline)>=25
             AND s.timestamp > NOW() - INTERVAL '72 hours'
           ORDER BY random() LIMIT $1""", n + len(exclude))
    out = []
    for r in rows:
        if r["id"] in exclude:
            continue
        out.append({"id": r["id"], "headline": r["headline"], "vec": _parse_vec(r["v"])})
        if len(out) >= n:
            break
    return out


async def run() -> int:
    with open(GOLD) as f:
        recs = json.load(f)["records"]
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        vecs = await _vecs_for(conn, [r["id"] for r in recs])
        data = [(r, vecs[r["id"]]) for r in recs if r["id"] in vecs]
        X = np.vstack([v for _, v in data])
        y_oos = np.array([(r["gold"] == OOS) for r, _ in data], dtype=int)
        print(f"training on {len(data)} gold-embedded (in-scope={int((y_oos==0).sum())} "
              f"OOS={int(y_oos.sum())})")

        clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
        clf.fit(X, y_oos)
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({"model": clf, "in_scope_class": 0, "trained_n": len(data),
                     "model_version": "v2-gate-e5-lr-1", "dim": int(X.shape[1])},
                    MODEL_PATH)
        print(f"persisted → {MODEL_PATH}")

        # ---- real-stream validation (the honest distribution check) ----
        gold_ids = {r["id"] for r, _ in data}
        sample = await _real_stream_sample(conn, gold_ids, 600)
    finally:
        await conn.close()

    Xs = np.vstack([s["vec"] for s in sample])
    inscope_idx = list(clf.classes_).index(0)
    p_inscope = clf.predict_proba(Xs)[:, inscope_idx]
    print(f"\n=== real-stream validation ({len(sample)} fresh signals, not in gold) ===")
    print("  thr   keep%   (kept = served as evidence)")
    for thr in (0.50, 0.60, 0.70):
        k = p_inscope >= thr
        print(f"  {thr:.2f}  {100*k.mean():5.1f}")
    # spot-check at 0.50
    order = np.argsort(p_inscope)
    print("\n  10 LOWEST P(in-scope) — should be junk/non-crisis (REJECTED):")
    for i in order[:10]:
        print(f"    [{p_inscope[i]:.2f}] {sample[i]['headline'][:78]}")
    print("\n  10 HIGHEST P(in-scope) — should be real crisis (KEPT):")
    for i in order[::-1][:10]:
        print(f"    [{p_inscope[i]:.2f}] {sample[i]['headline'][:78]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
