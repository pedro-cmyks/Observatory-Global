#!/usr/bin/env python3
"""Evidence-role student v2 — DB-enriched features (M2 follow-up).

v1 used headline-only features and could not suppress off_topic/noise
(see the M1<->M2 bridge). v2 adds the cluster-membership and provenance
signals the design doc calls for:

  - e5 headline embedding (768);
  - cosine(headline, cluster_label);
  - cosine(headline, cluster_description);
  - cosine(headline, cluster centroid_vec)  <-- the membership signal;
  - cluster cohesion, log(n_signals);
  - country_match (signal country in cluster top_country_codes);
  - source_family one-hot (top families + other);
  - is_english (source_lang == 'en').

Honest stratified 5-fold CV on the 3-vendor consensus gold. No LLM at
inference. Persists model + eval report; intended to be compared against
v1 (`2026-06-02-student-v1-eval.json`).

Run with the ML venv (torch + transformers + scikit-learn) and DATABASE_URL:
  /Users/pedro/AtlasLocalWorker/mlvenv/bin/python -m scripts.train_evidence_role_student_v2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from scripts.evidence_role_schema import read_jsonl
from scripts.score_assignments_gate import _build_embedder
from scripts.train_evidence_role_student import (
    MIN_CLASS_COUNT,
    N_SPLITS,
    EMBED_MODEL,
    _cluster_tier_summary,
)

TOP_FAMILIES = ["news_agency", "newspaper", "broadcaster", "ngo", "state_media", "magazine"]


def _parse_cluster_id(cid: str) -> tuple[str, int] | None:
    if not cid or "/" not in cid:
        return None
    snap, _, pk = cid.rpartition("/")
    try:
        return snap, int(pk)
    except ValueError:
        return None


async def _fetch_db_features(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    import asyncpg

    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL required for v2 features")
    conn = await asyncpg.connect(db)
    try:
        sids = sorted({int(r["signal_id"]) for r in rows})
        sig_rows = await conn.fetch(
            "SELECT id, source_family, source_lang, country_code FROM signals_v2 WHERE id = ANY($1::bigint[])",
            sids,
        )
        sigs = {int(r["id"]): dict(r) for r in sig_rows}

        # gold cluster_pk == emergent_clusters.id (primary key)
        pks = set()
        for r in rows:
            pc = _parse_cluster_id(str(r.get("cluster_id") or ""))
            if pc:
                pks.add(pc[1])
        cl_rows = await conn.fetch(
            "SELECT id, description, cohesion, n_signals, top_country_codes, centroid_vec "
            "FROM emergent_clusters WHERE id = ANY($1::bigint[])",
            sorted(pks),
        )
        out_clusters = {int(r["id"]): dict(r) for r in cl_rows}
        return {"sigs": sigs, "clusters": out_clusters}
    finally:
        await conn.close()


def _family_onehot(family: str | None) -> list[float]:
    fam = (family or "").lower()
    vec = [1.0 if fam == f else 0.0 for f in TOP_FAMILIES]
    vec.append(0.0 if fam in TOP_FAMILIES else 1.0)  # other
    return vec


def _build_features(rows: list[dict[str, Any]], db: dict[str, Any]) -> np.ndarray:
    embed, _ = _build_embedder(EMBED_MODEL)
    head_emb = embed([f"query: {(r.get('headline') or '').strip()}" for r in rows])
    label_emb = embed([f"query: {(r.get('cluster_label') or '').strip()}" for r in rows])

    descs = []
    for r in rows:
        pc = _parse_cluster_id(str(r.get("cluster_id") or ""))
        cl = db["clusters"].get(pc[1], {}) if pc else {}
        descs.append(f"query: {(cl.get('description') or '').strip()}")
    desc_emb = embed(descs)

    feats = []
    for i, r in enumerate(rows):
        pc = _parse_cluster_id(str(r.get("cluster_id") or ""))
        cl = db["clusters"].get(pc[1], {}) if pc else {}
        sig = db["sigs"].get(int(r["signal_id"]), {})

        h = head_emb[i]
        cos_label = float(np.dot(h, label_emb[i]))
        cos_desc = float(np.dot(h, desc_emb[i]))
        cv = cl.get("centroid_vec")
        if cv:
            c = np.asarray(cv, dtype=np.float64)
            norm = np.linalg.norm(c)
            cos_centroid = float(np.dot(h, c) / norm) if norm > 0 else 0.0
        else:
            cos_centroid = 0.0
        cohesion = float(cl.get("cohesion") or 0.0)
        n_sig = float(cl.get("n_signals") or 0)
        log_n = math.log1p(n_sig)
        countries = cl.get("top_country_codes") or []
        cc = sig.get("country_code")
        country_match = 1.0 if (cc and cc in countries) else 0.0
        is_en = 1.0 if (sig.get("source_lang") == "en") else 0.0
        fam = _family_onehot(sig.get("source_family"))

        extra = [cos_label, cos_desc, cos_centroid, cohesion, log_n, country_match, is_en] + fam
        feats.append(np.concatenate([h, np.array(extra, dtype=np.float64)]))
    return np.vstack(feats)


def _cv_eval(X: np.ndarray, y: np.ndarray, labels: list[str]):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline

    pipe = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=4000, C=1.0, class_weight="balanced"),
    )
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=20260602)
    y_pred = cross_val_predict(pipe, X, y, cv=skf)
    y_proba = cross_val_predict(pipe, X, y, cv=skf, method="predict_proba")
    role_score = y_proba.max(axis=1)
    rep = classification_report(y, y_pred, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y, y_pred, labels=labels).tolist()
    summary = {
        "classification_report": rep,
        "confusion_matrix": {"labels": labels, "matrix": cm},
        "primary_evidence_precision": round(rep.get("primary_evidence", {}).get("precision", 0.0), 4),
        "primary_evidence_recall": round(rep.get("primary_evidence", {}).get("recall", 0.0), 4),
        "noise_recall": round(rep.get("noise", {}).get("recall", 0.0), 4),
        "noise_precision": round(rep.get("noise", {}).get("precision", 0.0), 4),
        "macro_f1": round(rep.get("macro avg", {}).get("f1-score", 0.0), 4),
        "accuracy": round(rep.get("accuracy", 0.0), 4),
    }
    return summary, y_pred, role_score


def _fit_final(X: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler().fit(X)
    clf = LogisticRegression(max_iter=4000, C=1.0, class_weight="balanced").fit(
        scaler.transform(X), y
    )
    return {
        "schema": "atlas-evidence-role-student-v2",
        "embedding_model": EMBED_MODEL,
        "feature_spec": "concat[e5(headline)(768), cos_label, cos_desc, cos_centroid, cohesion, log_n_signals, country_match, is_english, family_onehot(7)]",
        "classes": list(clf.classes_),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_std": scaler.scale_.tolist(),
        "lr_coef": clf.coef_.tolist(),
        "lr_intercept": clf.intercept_.tolist(),
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Train/evaluate evidence-role student v2 (DB features).")
    ap.add_argument("--consensus", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--model-out", required=True, type=Path)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    rows = [r for r in read_jsonl(args.consensus) if r.get("consensus_role")]
    rows = [r for r in rows if r.get("is_training_gold", True)]
    counts = Counter(r["consensus_role"] for r in rows)
    kept_labels = sorted([c for c, n in counts.items() if n >= MIN_CLASS_COUNT])
    dropped = {c: n for c, n in counts.items() if n < MIN_CLASS_COUNT}
    rows = [r for r in rows if r["consensus_role"] in kept_labels]

    db = asyncio.run(_fetch_db_features(rows))
    n_clusters_joined = len(db["clusters"])
    X = _build_features(rows, db)
    y = np.array([r["consensus_role"] for r in rows])

    cv, y_pred, role_score = _cv_eval(X, y, kept_labels)
    tiers = _cluster_tier_summary(rows, y_pred, role_score)
    model = _fit_final(X, y)

    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    args.model_out.write_text(json.dumps(model, ensure_ascii=False) + "\n", encoding="utf-8")

    report = {
        "schema_version": "atlas-evidence-role-student-report-v2-rich",
        "n_training_rows": len(rows),
        "n_clusters_joined": n_clusters_joined,
        "n_features": int(X.shape[1]),
        "role_counts": {c: counts[c] for c in kept_labels},
        "dropped_rare_classes": dropped,
        "cv": {"n_splits": N_SPLITS, **cv},
        "cluster_tiers": tiers,
        "model_out": str(args.model_out),
        "status": "trained_v2",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n_training_rows", "n_clusters_joined", "n_features", "cv", "cluster_tiers")}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
