#!/usr/bin/env python3
"""Train + evaluate the local evidence-role student (M2, v1).

Implements the first real student from the design doc
(`docs/superpowers/specs/2026-06-01-narrative-cluster-evidence-roles-design.md`):
a local multinomial logistic regression over `intfloat/multilingual-e5-base`
embeddings that predicts an evidence role per signal. No LLM at inference.

Feature set (v1, headline-derivable only):
  - e5 embedding of "query: {headline}" (768-d);
  - cosine(headline, cluster_label) as one extra feature.
The richer design features (cluster centroid, gate_score, source family,
country match, cohesion) need DB joins and are deferred to v2.

Evaluation is an honest stratified 5-fold cross-validation on the
3-vendor consensus gold (`cross_val_predict`), so no row is scored by a
model trained on it. Reports macro/weighted metrics, per-class
precision/recall, the confusion matrix, and the two numbers the product
tiers hinge on: primary_evidence precision (verified-claim quality) and
noise recall (suppression quality). A final model is fit on all rows and
persisted for production parity.

Run with the ML venv (torch + transformers + scikit-learn):
  /Users/pedro/AtlasLocalWorker/mlvenv/bin/python
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from scripts.evidence_role_schema import read_jsonl
from scripts.score_assignments_gate import _build_embedder

VISIBLE_TIERS = {"verified", "candidate", "context_rich"}
MIN_CLASS_COUNT = 5  # classes rarer than the fold count are dropped from CV
N_SPLITS = 5
EMBED_MODEL = "intfloat/multilingual-e5-base"


def tier_from_roles(rows: list[dict[str, Any]]) -> str:
    primary = [r for r in rows if r.get("predicted_role") == "primary_evidence"]
    non_noise = [r for r in rows if r.get("predicted_role") != "noise"]
    context_like = [
        r
        for r in rows
        if r.get("predicted_role") in {"context", "reaction", "analysis", "entity_reference"}
    ]
    strong_primary = [r for r in primary if float(r.get("role_score") or 0.0) >= 0.85]
    if len(strong_primary) >= 2:
        return "verified"
    if primary and len(non_noise) >= 2:
        return "candidate"
    if len(context_like) >= 2:
        return "context_rich"
    return "suppressed"


def visible_coverage(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    visible = sum(1 for row in rows if row.get("tier") in VISIBLE_TIERS)
    return round(visible / len(rows), 4)


def _embed_features(rows: list[dict[str, Any]]) -> np.ndarray:
    embed, _ = _build_embedder(EMBED_MODEL)
    head_texts = [f"query: {(r.get('headline') or '').strip()}" for r in rows]
    label_texts = [f"query: {(r.get('cluster_label') or '').strip()}" for r in rows]
    head_emb = embed(head_texts)
    label_emb = embed(label_texts)
    # both are L2-normalized -> dot product is cosine
    cos = np.sum(head_emb * label_emb, axis=1, keepdims=True)
    return np.hstack([head_emb, cos])


def _cv_eval(X: np.ndarray, y: np.ndarray, labels: list[str]):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline

    pipe = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced"),
    )
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=20260602)
    y_pred = cross_val_predict(pipe, X, y, cv=skf)
    y_proba = cross_val_predict(pipe, X, y, cv=skf, method="predict_proba")
    role_score = y_proba.max(axis=1)

    report = classification_report(
        y, y_pred, labels=labels, output_dict=True, zero_division=0
    )
    cm = confusion_matrix(y, y_pred, labels=labels).tolist()
    summary = {
        "classification_report": report,
        "confusion_matrix": {"labels": labels, "matrix": cm},
        "primary_evidence_precision": round(
            report.get("primary_evidence", {}).get("precision", 0.0), 4
        ),
        "primary_evidence_recall": round(
            report.get("primary_evidence", {}).get("recall", 0.0), 4
        ),
        "noise_recall": round(report.get("noise", {}).get("recall", 0.0), 4),
        "macro_f1": round(report.get("macro avg", {}).get("f1-score", 0.0), 4),
        "accuracy": round(report.get("accuracy", 0.0), 4),
        "role_score_mean": round(float(role_score.mean()), 4),
    }
    return summary, y_pred, role_score


def _cluster_tier_summary(
    rows: list[dict[str, Any]], y_pred: np.ndarray, role_score: np.ndarray
) -> dict[str, Any]:
    by_cluster: dict[str, list[dict[str, Any]]] = {}
    for row, pred, score in zip(rows, y_pred, role_score):
        enriched = {"predicted_role": str(pred), "role_score": float(score)}
        by_cluster.setdefault(str(row.get("cluster_id")), []).append(enriched)
    tiers: Counter = Counter()
    visible = 0
    for cluster_rows in by_cluster.values():
        tier = tier_from_roles(cluster_rows)
        tiers[tier] += 1
        if tier in VISIBLE_TIERS:
            visible += 1
    n_clusters = len(by_cluster)
    return {
        "n_clusters": n_clusters,
        "tier_counts": dict(tiers),
        "visible_cluster_coverage": round(visible / n_clusters, 4) if n_clusters else 0.0,
    }


def _fit_final(X: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler().fit(X)
    clf = LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced").fit(
        scaler.transform(X), y
    )
    return {
        "schema": "atlas-evidence-role-student-v1",
        "embedding_model": EMBED_MODEL,
        "feature_spec": "concat[e5(query: headline)(768), cosine(headline,cluster_label)(1)]",
        "classes": list(clf.classes_),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_std": scaler.scale_.tolist(),
        "lr_coef": clf.coef_.tolist(),
        "lr_intercept": clf.intercept_.tolist(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train/evaluate the evidence-role student.")
    parser.add_argument("--consensus", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--model-out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [r for r in read_jsonl(args.consensus) if r.get("consensus_role")]
    rows = [r for r in rows if r.get("is_training_gold", True)]

    counts = Counter(r["consensus_role"] for r in rows)
    kept_labels = sorted([c for c, n in counts.items() if n >= MIN_CLASS_COUNT])
    dropped = {c: n for c, n in counts.items() if n < MIN_CLASS_COUNT}
    rows = [r for r in rows if r["consensus_role"] in kept_labels]

    X = _embed_features(rows)
    y = np.array([r["consensus_role"] for r in rows])

    cv, y_pred, role_score = _cv_eval(X, y, kept_labels)
    tiers = _cluster_tier_summary(rows, y_pred, role_score)
    model = _fit_final(X, y)

    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    args.model_out.write_text(json.dumps(model, ensure_ascii=False) + "\n", encoding="utf-8")

    report = {
        "schema_version": "atlas-evidence-role-student-report-v2",
        "n_training_rows": len(rows),
        "role_counts": {c: counts[c] for c in kept_labels},
        "dropped_rare_classes": dropped,
        "cv": {"n_splits": N_SPLITS, **cv},
        "cluster_tiers": tiers,
        "model_out": str(args.model_out),
        "targets": {"verified_precision": 0.9, "visible_coverage": 0.8},
        "status": "trained_v1",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: report[k] for k in ("n_training_rows", "role_counts", "dropped_rare_classes", "cv", "cluster_tiers")},
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
