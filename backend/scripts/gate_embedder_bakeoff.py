#!/usr/bin/env python3
"""Local-embedder bake-off for the Atlas scope gate (recall track, 2026-07-04).

The deployed gate rides e5-base (local, global recall 0.749 @90% precision);
a trained-but-undeployed OpenAI text-embedding-3-small variant reaches 0.843 —
but needs a paid external call in the classifier hot path. This script tests
whether a NEWER LOCAL multilingual embedder can match OpenAI's separation
(esp. on the hard tail: election-legitimacy, agriculture, telecom, oil-gas)
so the recall win comes with NO external dependency.

Method: reuse the EXACT gate math from phase_b_scope_gate_probe (pooled 5-fold
OOF, NumpyLogReg, per-topic threshold@90% precision) — only the embedding
changes. Embeds `"headline | assigned_topic_label"` (same text as production)
with a sentence-transformers model, X = [emb || atlas_conf || matched_terms],
reports global + per-topic recall@90%. Read-only; writes a JSON artifact only.

Run (one model at a time to bound M1 RAM):
  python -m scripts.gate_embedder_bakeoff --model intfloat/multilingual-e5-large --prefix "query: "
  python -m scripts.gate_embedder_bakeoff --model BAAI/bge-m3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase_b_scope_gate_probe as G  # noqa: E402
from train_scope_gate import _threshold_at_precision  # noqa: E402

HARD = [
    "election-legitimacy-dispute", "agriculture-crop-risk", "oil-gas-supply-risk",
    "currency-debt-stress", "telecom-internet-shutdown", "sanctions-diplomatic-pressure",
]
BASELINES = {"e5base(deployed)": 0.749, "openai-v1": 0.843}  # global recall@90%


def embed(model_id: str, texts: list[str], prefix: str, batch: int) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    st = SentenceTransformer(model_id, trust_remote_code=True, device="mps")
    vecs = st.encode(
        [prefix + t for t in texts],
        batch_size=batch, normalize_embeddings=True,
        show_progress_bar=True, convert_to_numpy=True,
    )
    return np.asarray(vecs, dtype=np.float64)


def per_topic_recall(p_oof, y, slugs, target=0.90, min_pos=10):
    out = {}
    for slug in sorted(set(slugs.tolist())):
        sel = slugs == slug
        ys, ps = y[sel], p_oof[sel]
        if int(ys.sum()) < min_pos:
            out[slug] = {"mode": "fallback_global", "recall": None}
            continue
        op = _threshold_at_precision(ps, ys, target)
        out[slug] = ({"mode": "abstain", "recall": 0.0}
                     if op["threshold"] is None
                     else {"mode": "calibrated", "recall": op["recall"],
                           "threshold": op["threshold"]})
    return out


def main() -> None:
    base = Path("docs/research/atlas-paper/phase-1-validation")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prefix", default="", help='e.g. "query: " for e5 models')
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--corpus", type=Path,
                    default=base / "labels/consensus/2026-05-28-3vendor-5k-consensus-corpus.jsonl")
    ap.add_argument("--out", type=Path,
                    default=base / "reports/phase-b/2026-07-04-bakeoff.jsonl")
    args = ap.parse_args()

    rows = G._load(args.corpus)
    texts = G._texts(rows)
    y = np.array([r["is_evidence"] for r in rows], dtype=int)
    slugs = np.array([r.get("assigned_topic_slug") for r in rows], dtype=object)
    atlas = G._atlas_feats(rows)

    print(f"model={args.model} prefix={args.prefix!r} rows={len(y)} pos={int(y.sum())}")
    emb = embed(args.model, texts, args.prefix, args.batch)
    X = np.hstack([emb, atlas])
    p = G._pooled_oof(X, y, standardize=True)

    auc = round(G.roc_auc(y, p), 4)
    g90 = G.max_recall_at_precision(y, p, 0.90)
    pt = per_topic_recall(p, y, slugs)

    print(f"\n=== {args.model} : dim {emb.shape[1]} ===")
    print(f"GLOBAL recall@90%: {g90['max_recall']:.3f}  (AUC {auc})  "
          f"| baselines {BASELINES}")
    print("hard topics recall@90%:")
    for t in HARD:
        v = pt.get(t, {})
        print(f"  {str(v.get('recall')):>6}  {t}")
    cal = [v["recall"] for v in pt.values() if v["mode"] == "calibrated"]
    ab = sum(1 for v in pt.values() if v["mode"] == "abstain")
    print(f"calibrated median recall {np.median(cal):.3f} (n={len(cal)}) | abstain={ab}")

    rec = {"model": args.model, "prefix": args.prefix, "dim": int(emb.shape[1]),
           "auc": auc, "global_recall_at_90": g90["max_recall"],
           "abstain": ab, "calibrated_median": round(float(np.median(cal)), 4),
           "hard": {t: pt.get(t, {}).get("recall") for t in HARD}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"appended -> {args.out}")


if __name__ == "__main__":
    main()
