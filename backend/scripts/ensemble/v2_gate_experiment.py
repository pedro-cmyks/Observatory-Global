"""Taxonomy revision — v2 GATE experiment (#204), measure-first, offline, no prod.

The payoff measurement: does an embedding ($0-inference) gate trained on the gold
base beat the current lexical gate's 48.7% precision / 46.4% force-fit?

Two models over the e5 embeddings of the gold-labeled signals:
  1. BINARY gate — in-scope vs OUT_OF_SCOPE (the reject decision; the main lift).
  2. END-TO-END — among signals the v2 gate KEEPS (predicts in-scope), assign the
     category and check exact match vs gold → the apples-to-apples analog of the
     current gate's 48.7% category precision.

Stratified train/test split; reports the held-out numbers + the lift vs baseline.
e5 vectors are the same substrate the production engine already persists, so a
positive result is directly shippable as a gate feature.

Run: python -m backend.scripts.ensemble.v2_gate_experiment
"""
from __future__ import annotations

import asyncio
import json
import os

import asyncpg
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support
from sklearn.model_selection import train_test_split

GOLD = "docs/research/taxonomy-revision/goldset.json"
OOS = "OUT_OF_SCOPE"
SEED = 42


async def _load_vectors(ids: list[int]) -> dict[int, np.ndarray]:
    c = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await c.fetch(
            "select signal_id, vec::text AS v from signal_embeddings where signal_id = any($1)",
            ids)
    finally:
        await c.close()
    out = {}
    for r in rows:
        out[r["signal_id"]] = np.fromstring(r["v"].strip("[]"), sep=",", dtype=np.float32)
    return out


def main() -> int:
    with open(GOLD) as f:
        recs = json.load(f)["records"]
    ids = [r["id"] for r in recs]
    vecs = asyncio.run(_load_vectors(ids))

    # keep only gold rows that have an e5 vector
    data = [(r, vecs[r["id"]]) for r in recs if r["id"] in vecs]
    X = np.vstack([v for _, v in data])
    gold = np.array([r["gold"] for r, _ in data])
    y_oos = (gold == OOS).astype(int)  # 1 = OUT_OF_SCOPE
    print(f"labeled-embedding set: {len(data)} | in-scope={int((y_oos==0).sum())} "
          f"OOS={int(y_oos.sum())}")

    # stratified split (by OOS so both classes present in test)
    idx = np.arange(len(data))
    tr, te = train_test_split(idx, test_size=0.25, random_state=SEED, stratify=y_oos)

    # ---- 1) BINARY gate: in-scope vs OOS ----
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
    clf.fit(X[tr], y_oos[tr])
    pred_oos = clf.predict(X[te])
    # "keep" = predicted in-scope (pred_oos==0). its precision = of kept, how many
    # are truly in-scope per gold → the analog of the gate's in-scope precision.
    keep = pred_oos == 0
    keep_true_inscope = (y_oos[te][keep] == 0).sum()
    keep_prec = keep_true_inscope / max(keep.sum(), 1)
    # reject recall = of true OOS, how many v2 correctly rejects
    rej_recall = (pred_oos[y_oos[te] == 1] == 1).mean()
    p, rcl, f1, _ = precision_recall_fscore_support(
        y_oos[te], pred_oos, labels=[0, 1], zero_division=0)
    print("\n=== v2 BINARY gate (in-scope vs OUT_OF_SCOPE), held-out ===")
    print(f"  in-scope precision (KEEP precision): {keep_prec*100:.1f}%  "
          f"[baseline lexical gate: 53.6%]")
    print(f"  reject recall (OOS caught)         : {rej_recall*100:.1f}%")
    print(f"  in-scope  P/R/F1 = {p[0]*100:.1f}/{rcl[0]*100:.1f}/{f1[0]*100:.1f}")
    print(f"  OUT_OF_SCOPE P/R/F1 = {p[1]*100:.1f}/{rcl[1]*100:.1f}/{f1[1]*100:.1f}")

    # threshold sweep — the product knob: keep only high-confidence in-scope.
    # p_inscope = P(in-scope) = 1 - P(OOS). Keep when p_inscope >= thr.
    p_inscope = clf.predict_proba(X[te])[:, list(clf.classes_).index(0)]
    truth_inscope = (y_oos[te] == 0)
    print("\n  threshold sweep (keep if P(in-scope) >= thr):")
    print("    thr   keep%   in-scope precision   in-scope recall")
    for thr in (0.50, 0.60, 0.70, 0.80, 0.90):
        k = p_inscope >= thr
        if k.sum() == 0:
            continue
        prec = truth_inscope[k].mean()
        rec = (truth_inscope & k).sum() / max(truth_inscope.sum(), 1)
        print(f"    {thr:.2f}  {100*k.mean():5.1f}   {prec*100:16.1f}%   {rec*100:13.1f}%")

    # ---- 2) END-TO-END: category precision among KEPT ----
    # train a multiclass category model on in-scope training rows; apply to the
    # rows the binary gate KEEPS in test; exact-match vs gold (analog of 48.7%).
    in_tr = tr[y_oos[tr] == 0]
    cats_tr = gold[in_tr]
    # drop singleton categories from training (can't generalize) but keep eval honest
    catmodel = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
    catmodel.fit(X[in_tr], cats_tr)
    te_keep_idx = te[keep]
    if len(te_keep_idx):
        cat_pred = catmodel.predict(X[te_keep_idx])
        gold_keep = gold[te_keep_idx]
        # end-to-end correct = kept AND gold is in-scope AND category matches
        e2e_correct = ((gold_keep != OOS) & (cat_pred == gold_keep)).sum()
        e2e_prec = e2e_correct / len(te_keep_idx)
        ff = (gold_keep == OOS).mean()
        print("\n=== v2 END-TO-END (of KEPT signals), held-out ===")
        print(f"  kept signals (test)        : {len(te_keep_idx)}")
        print(f"  exact category precision   : {e2e_prec*100:.1f}%  "
              f"[baseline lexical gate: 48.7%]")
        print(f"  force-fit (kept but OOS)   : {ff*100:.1f}%  "
              f"[baseline: 46.4%]")
    print("\n(measure-first; embedding gate = $0 inference, e5 vectors already persisted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
