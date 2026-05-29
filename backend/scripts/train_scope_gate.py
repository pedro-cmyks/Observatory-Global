#!/usr/bin/env python3
"""Train and persist the production Atlas scope gate.

The Phase B probe established that an `embedding + Atlas confidence`
logistic gate keeps a 90%-precise slice of Atlas assignments covering ~84%
of true evidence. This script trains the FINAL deployable model on the
full binary consensus corpus and persists everything an inference path
needs:
  - feature scaler (mean/std over [emb || atlas_conf]),
  - logistic weights (coef + intercept),
  - a GLOBAL keep-threshold calibrated to >=90% precision,
  - PER-TOPIC keep-thresholds (each calibrated to >=90% precision on that
    topic; topics too thin or unreachable abstain / fall back to global),
  - an honest calibration report (thresholds + coverage measured on
    out-of-fold predictions, not in-sample).

Honesty split: thresholds and reported precision/coverage come from pooled
stratified 5-fold OOF predictions (no in-sample optimism); the persisted
weights are the final model fit on ALL rows for deployment.

Shared math (logreg, folds, metrics) is imported from
`phase_b_scope_gate_probe` so the gate and its probe never diverge.

Schema: atlas-scope-gate-v1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase_b_scope_gate_probe as G  # noqa: E402

MIN_TOPIC_POSITIVES = 10  # below this, a per-topic threshold is not trustworthy
DEFAULT_EMBED_MODEL = "text-embedding-3-small"


def _threshold_at_precision(
    scores: np.ndarray, y: np.ndarray, target: float
) -> dict[str, Any]:
    """Lowest score threshold whose kept set (score >= thr) has precision >=
    target, maximising recall. Returns the operating point or None if
    unreachable."""
    order = np.argsort(-scores, kind="mergesort")
    ys = y[order]
    ss = scores[order]
    tp = np.cumsum(ys)
    fp = np.cumsum(1 - ys)
    n_pos = float(y.sum())
    precision = tp / np.maximum(tp + fp, 1e-12)
    recall = tp / max(n_pos, 1e-12)
    best = None
    for i in range(len(ys)):
        if precision[i] >= target and (best is None or recall[i] > best["recall"]):
            best = {
                "threshold": round(float(ss[i]), 5),
                "precision": round(float(precision[i]), 4),
                "recall": round(float(recall[i]), 4),
                "kept": int(tp[i] + fp[i]),
            }
    return best or {"threshold": None, "precision": None, "recall": 0.0, "kept": 0}


def main() -> None:
    base = Path("docs/research/atlas-paper/phase-1-validation")
    ap = argparse.ArgumentParser(description="Train + persist the production scope gate.")
    ap.add_argument("--corpus", type=Path,
                    default=base / "labels/consensus/2026-05-28-3vendor-5k-consensus-corpus.jsonl")
    ap.add_argument("--embeddings", type=Path,
                    default=base / "labels/consensus/2026-05-28-3vendor-5k-openai-embeddings.jsonl")
    ap.add_argument("--out", type=Path, default=base / "models/2026-05-29-scope-gate-v1.json")
    ap.add_argument("--report", type=Path, default=base / "models/2026-05-29-scope-gate-v1.calibration.json")
    ap.add_argument("--target-precision", type=float, default=0.90)
    ap.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL,
                    help="Embedding model id recorded in the gate (must match the --embeddings source).")
    args = ap.parse_args()

    G._selftest()
    rows = G._load(args.corpus)
    emb_map = G._load_embeddings(args.embeddings)
    keys = [(int(r["signal_id"]), r.get("assigned_topic_slug")) for r in rows]
    mask = np.array([k in emb_map for k in keys])
    rows = [r for r, m in zip(rows, mask) if m]
    keys = [k for k, m in zip(keys, mask) if m]

    y = np.array([r["is_evidence"] for r in rows], dtype=int)
    atlas = G._atlas_feats(rows)
    emb = np.vstack([emb_map[k] for k in keys])
    slugs = np.array([r.get("assigned_topic_slug") for r in rows], dtype=object)
    X = np.hstack([emb, atlas])
    print(f"training rows {len(y)} ({int(y.sum())} evidence) | feature dim {X.shape[1]}")

    # --- honest OOF for calibration ---
    p_oof = G._pooled_oof(X, y, standardize=True)
    overall_auc = round(G.roc_auc(y, p_oof), 4)

    global_op = _threshold_at_precision(p_oof, y, args.target_precision)

    # --- per-topic calibration (OOF) ---
    per_topic: dict[str, Any] = {}
    for slug in sorted(set(slugs.tolist())):
        sel = slugs == slug
        ys, ps = y[sel], p_oof[sel]
        n, n_pos = int(sel.sum()), int(ys.sum())
        if n_pos < MIN_TOPIC_POSITIVES:
            per_topic[slug] = {
                "n": n, "n_positive": n_pos, "mode": "fallback_global",
                "threshold": global_op["threshold"],
                "reason": f"only {n_pos} positives (< {MIN_TOPIC_POSITIVES})",
            }
            continue
        op = _threshold_at_precision(ps, ys, args.target_precision)
        if op["threshold"] is None:
            per_topic[slug] = {
                "n": n, "n_positive": n_pos, "mode": "abstain",
                "threshold": None,
                "reason": f"cannot reach {args.target_precision:.0%} precision at any threshold",
            }
        else:
            per_topic[slug] = {"n": n, "n_positive": n_pos, "mode": "calibrated", **op}

    # --- final model on ALL rows (deployment weights) ---
    mu, sd = G._standardize_fit(X)
    Xs = (X - mu) / sd
    model = G.NumpyLogReg().fit(Xs, y)

    gate = {
        "schema": "atlas-scope-gate-v1",
        "trained": "2026-05-29",
        "feature_spec": {
            "order": ["embedding", "atlas_confidence", "atlas_matched_terms"],
            "embedding_model": args.embed_model,
            "embedding_dim": int(emb.shape[1]),
            "embedding_text": "headline | assigned_topic_label",
            "total_dim": int(X.shape[1]),
            "standardize": True,
        },
        "scaler_mean": mu.tolist(),
        "scaler_std": sd.tolist(),
        "lr_coef": model.w[:-1].tolist(),
        "lr_intercept": float(model.w[-1]),
        "target_precision": args.target_precision,
        "global_threshold": global_op["threshold"],
        "per_topic_threshold": {s: v["threshold"] for s, v in per_topic.items()},
    }
    report = {
        "schema": "atlas-scope-gate-v1-calibration",
        "corpus": str(args.corpus),
        "n_rows": int(len(y)),
        "n_evidence": int(y.sum()),
        "base_rate_precision": round(float(y.mean()), 4),
        "target_precision": args.target_precision,
        "oof_roc_auc": overall_auc,
        "global_operating_point": global_op,
        "per_topic": per_topic,
        "note": (
            "Thresholds + precision/recall measured on pooled 5-fold OOF "
            "predictions (honest). Persisted weights are the final fit on all "
            "rows. mode=calibrated: topic hits target precision; "
            "mode=fallback_global: too few positives, uses global threshold; "
            "mode=abstain: cannot reach target at any threshold."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(gate), encoding="utf-8")
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- console summary ---
    modes = {}
    for v in per_topic.values():
        modes[v["mode"]] = modes.get(v["mode"], 0) + 1
    print(f"OOF AUC {overall_auc} | global keep@{args.target_precision:.0%}: "
          f"recall {global_op['recall']} (thr {global_op['threshold']})")
    print(f"per-topic modes: {modes}")
    print(f"gate -> {args.out}\nreport -> {args.report}")


if __name__ == "__main__":
    main()
