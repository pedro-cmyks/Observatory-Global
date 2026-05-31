#!/usr/bin/env python3
"""Train + persist the Atlas emergent-precision gate.

The scope gate (`train_scope_gate.py`) calibrates per-(signal, atlas-topic)
keep decisions against 30 hand-curated lenses. The emergent layer needs the
same ≥90% precision discipline applied to *any* centroid coming out of
HDBSCAN clustering on the raw signal stream — no atlas-topic prior. This
script trains a cluster-agnostic relevance classifier reusing the same
consensus corpus.

Features per row (no atlas-specific signals):
  [signal_emb (768) || topic_centroid (768) || cos(signal, centroid) (1)]

Where `topic_centroid` is the L2-normalized mean of e5-base embeddings of
ALL rows assigned to that topic in the corpus (not just is_evidence=1).
This matches HDBSCAN inference: a cluster centroid is the mean of *all*
members, including the noise the gate must learn to reject. Training on
"clean" evidence-only centroids would leak label information into the
feature and degrade generalization to real cluster centroids.

Single global keep-threshold (no per-topic table — at inference we apply
this gate to arbitrary HDBSCAN centroids that have no atlas-topic id).

Shared math (logreg, folds, OOF, AUC, standardize) imported from
`phase_b_scope_gate_probe` to stay aligned with the scope gate.

Schema: atlas-emergent-precision-gate-v1
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
from train_scope_gate import _threshold_at_precision  # noqa: E402


def _build_features(emb: np.ndarray, slugs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build [signal_emb || topic_centroid || cos] feature matrix.

    Centroid built from ALL assignments of each topic (not is_evidence
    filtered) so the training distribution matches HDBSCAN inference.

    Returns:
        X: (n_rows, 2*emb_dim + 1) feature matrix.
        centroid_mat: (n_rows, emb_dim) per-row centroid (kept for audit).
    """
    centroids: dict[str, np.ndarray] = {}
    for s in np.unique(slugs):
        sel = slugs == s
        c = emb[sel].mean(axis=0)
        c /= max(float(np.linalg.norm(c)), 1e-9)
        centroids[str(s)] = c
    centroid_mat = np.vstack([centroids[str(s)] for s in slugs])
    cos_vec = np.sum(emb * centroid_mat, axis=1, keepdims=True)
    X = np.hstack([emb, centroid_mat, cos_vec])
    return X, centroid_mat


def main() -> None:
    base = Path("docs/research/atlas-paper/phase-1-validation")
    ap = argparse.ArgumentParser(description="Train + persist the emergent precision gate.")
    ap.add_argument(
        "--corpus", type=Path,
        default=base / "labels/consensus/2026-05-28-3vendor-5k-consensus-corpus.jsonl",
    )
    ap.add_argument(
        "--embeddings", type=Path,
        default=base / "labels/consensus/2026-05-29-3vendor-5k-e5-embeddings.jsonl",
    )
    ap.add_argument(
        "--out", type=Path,
        default=base / "models/2026-05-30-emergent-precision-gate-v1.json",
    )
    ap.add_argument(
        "--report", type=Path,
        default=base / "models/2026-05-30-emergent-precision-gate-v1.calibration.json",
    )
    ap.add_argument("--target-precision", type=float, default=0.90)
    ap.add_argument("--embed-model", default="intfloat/multilingual-e5-base",
                    help="Embedding model id recorded in the gate (must match --embeddings).")
    args = ap.parse_args()

    G._selftest()
    rows = G._load(args.corpus)
    emb_map = G._load_embeddings(args.embeddings)
    keys = [(int(r["signal_id"]), r.get("assigned_topic_slug")) for r in rows]
    mask = np.array([k in emb_map for k in keys])
    rows = [r for r, m in zip(rows, mask) if m]
    keys = [k for k, m in zip(keys, mask) if m]

    y = np.array([r["is_evidence"] for r in rows], dtype=int)
    emb = np.vstack([emb_map[k] for k in keys])
    slugs = np.array([r.get("assigned_topic_slug") for r in rows], dtype=object)
    X, _ = _build_features(emb, slugs)
    print(
        f"training rows {len(y)} ({int(y.sum())} evidence) | "
        f"feature dim {X.shape[1]} (emb {emb.shape[1]} + centroid {emb.shape[1]} + cos 1)"
    )

    # --- honest OOF for calibration ---
    p_oof = G._pooled_oof(X, y, standardize=True)
    overall_auc = round(G.roc_auc(y, p_oof), 4)
    global_op = _threshold_at_precision(p_oof, y, args.target_precision)

    # --- final model on ALL rows (deployment weights) ---
    mu, sd = G._standardize_fit(X)
    Xs = (X - mu) / sd
    model = G.NumpyLogReg().fit(Xs, y)

    gate = {
        "schema": "atlas-emergent-precision-gate-v1",
        "trained": "2026-05-30",
        "feature_spec": {
            "order": ["signal_embedding", "cluster_centroid", "cosine_similarity"],
            "embedding_model": args.embed_model,
            "embedding_dim": int(emb.shape[1]),
            "centroid_construction": (
                "L2-normalized mean of e5-base embeddings of ALL cluster "
                "members (no label filter). At training the cluster = the "
                "topic; at inference the cluster = HDBSCAN cluster."
            ),
            "embedding_text": "passage: <headline>",
            "total_dim": int(X.shape[1]),
            "standardize": True,
        },
        "scaler_mean": mu.tolist(),
        "scaler_std": sd.tolist(),
        "lr_coef": model.w[:-1].tolist(),
        "lr_intercept": float(model.w[-1]),
        "target_precision": args.target_precision,
        "global_threshold": global_op["threshold"],
    }
    report = {
        "schema": "atlas-emergent-precision-gate-v1-calibration",
        "corpus": str(args.corpus),
        "embeddings": str(args.embeddings),
        "n_rows": int(len(y)),
        "n_evidence": int(y.sum()),
        "base_rate_precision": round(float(y.mean()), 4),
        "target_precision": args.target_precision,
        "oof_roc_auc": overall_auc,
        "global_operating_point": global_op,
        "note": (
            "Threshold + precision/recall measured on pooled 5-fold OOF "
            "predictions (honest). Persisted weights are the final fit on "
            "all rows. Single global threshold — no per-topic table — "
            "because at inference the gate scores arbitrary HDBSCAN centroids "
            "with no atlas-topic identity."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(gate), encoding="utf-8")
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"OOF AUC {overall_auc} | global keep@{args.target_precision:.0%}: "
        f"recall {global_op['recall']} (thr {global_op['threshold']}, "
        f"kept {global_op['kept']})"
    )
    print(f"gate -> {args.out}\nreport -> {args.report}")


if __name__ == "__main__":
    main()
