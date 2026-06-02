#!/usr/bin/env python3
"""M1<->M2 bridge: do scope_mismatch errors carry recoverable evidence roles?

The RQ1 story is: the scope gate (M1) lifts precision by abstaining
off_topic matches, but the residual errors it keeps are mostly
`scope_mismatch` (right domain, wrong granularity). M2's claim is that
those are not garbage — they are real evidence at the wrong level, which
the evidence-role student types as non-noise (context / reaction /
analysis / primary), i.e. recoverable as graded context rather than
counted as precision misses.

This script tests that claim directly on the RQ1 batch-03 consensus gold:
  1. score every row with the scope gate (kept/abstained);
  2. predict an evidence role for every row with the student v1 model;
  3. take the majority annotator error_type per row;
  4. cross-tab: for consensus-incorrect rows, student non-noise rate by
     error_type (scope_mismatch vs off_topic).

Read-only, no DB. Run with the ML venv (torch + transformers):
  /Users/pedro/AtlasLocalWorker/mlvenv/bin/python -m scripts.bridge_gate_student_scope
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from scripts.score_assignments_gate import (
    _build_embedder,
    _load_gate,
    _matched_terms,
    _score_and_decide,
)

NON_NOISE = {"primary_evidence", "context", "reaction", "analysis", "entity_reference"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]


def _majority(vals: list[Any]) -> Any:
    vals = [v for v in vals if v]
    if not vals:
        return None
    c = Counter(vals)
    top, n = c.most_common(1)[0]
    if sum(1 for _, k in c.items() if k == n) > 1:
        return None
    return top


def _annotator_error_types(annotator_glob: str) -> dict[int, str]:
    per_signal: dict[int, list[str]] = {}
    for f in sorted(glob.glob(annotator_glob)):
        for r in _read_jsonl(Path(f)):
            sid = r.get("signal_id")
            et = r.get("annotator_error_type")
            if sid is None:
                continue
            per_signal.setdefault(int(sid), []).append(et)
    return {sid: _majority(ets) for sid, ets in per_signal.items()}


def _student_predict(model: dict[str, Any], head_emb: np.ndarray, label_emb: np.ndarray):
    cos = np.sum(head_emb * label_emb, axis=1, keepdims=True)
    X = np.hstack([head_emb, cos])
    mean = np.asarray(model["scaler_mean"])
    std = np.asarray(model["scaler_std"])
    Xs = (X - mean) / std
    coef = np.asarray(model["lr_coef"])          # (n_classes, n_features)
    intercept = np.asarray(model["lr_intercept"])  # (n_classes,)
    z = Xs @ coef.T + intercept
    z = z - z.max(axis=1, keepdims=True)
    proba = np.exp(z)
    proba = proba / proba.sum(axis=1, keepdims=True)
    classes = model["classes"]
    idx = proba.argmax(axis=1)
    roles = [classes[i] for i in idx]
    scores = proba.max(axis=1)
    return roles, scores


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Gate<->student scope-mismatch recovery bridge.")
    ap.add_argument("--gold", required=True, type=Path, help="batch-03 consensus gold jsonl")
    ap.add_argument("--annotator-glob", required=True, help="glob of annotator jsonl files")
    ap.add_argument("--gate", required=True, type=Path)
    ap.add_argument("--student", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    gold = [r for r in _read_jsonl(args.gold) if r.get("gold_decision") not in (None, "unclear")]
    gate = _load_gate(args.gate)
    student = json.loads(args.student.read_text(encoding="utf-8"))
    err_types = _annotator_error_types(args.annotator_glob)

    embed, device = _build_embedder(gate["feature_spec"]["embedding_model"])
    headlines = [(r.get("headline") or "").strip() for r in gold]
    labels = [(r.get("assigned_topic_label") or "").strip() for r in gold]
    head_emb = embed([f"query: {h}" for h in headlines])
    label_emb = embed([f"query: {l}" for l in labels])

    # gate
    gate_text_emb = embed([f"query: {h} | {l}" for h, l in zip(headlines, labels)])
    conf = np.array([float(r.get("confidence") or 0.0) for r in gold])
    mt = np.array([_matched_terms(r.get("evidence")) for r in gold])
    slugs = [str(r.get("assigned_topic_slug") or "") for r in gold]
    _, gate_kept = _score_and_decide(gate, gate_text_emb, conf, mt, slugs)

    # student
    roles, _scores = _student_predict(student, head_emb, label_emb)

    # cross-tabs
    incorrect = [
        i for i, r in enumerate(gold) if r["gold_decision"] in ("incorrect", "partial")
    ]
    kept_incorrect = [i for i in incorrect if gate_kept[i]]

    def non_noise_rate(indices: list[int]) -> dict[str, Any]:
        if not indices:
            return {"n": 0, "non_noise": 0, "non_noise_rate": None, "role_dist": {}}
        roles_sub = [roles[i] for i in indices]
        nn = sum(1 for r in roles_sub if r in NON_NOISE)
        return {
            "n": len(indices),
            "non_noise": nn,
            "non_noise_rate": round(nn / len(indices), 4),
            "role_dist": dict(Counter(roles_sub)),
        }

    by_error: dict[str, dict[str, Any]] = {}
    for et in ("scope_mismatch", "off_topic", "no_majority"):
        if et == "no_majority":
            idxs = [i for i in incorrect if err_types.get(int(gold[i]["signal_id"])) is None]
        else:
            idxs = [i for i in incorrect if err_types.get(int(gold[i]["signal_id"])) == et]
        by_error[et] = non_noise_rate(idxs)

    report = {
        "schema_version": "atlas-gate-student-bridge-v1",
        "device": device,
        "n_gold": len(gold),
        "n_incorrect": len(incorrect),
        "n_gate_kept_incorrect": len(kept_incorrect),
        "student_role_dist_on_gate_kept_incorrect": non_noise_rate(kept_incorrect),
        "incorrect_by_annotator_error_type": by_error,
        "interpretation": (
            "If scope_mismatch rows show a high non_noise_rate while off_topic rows "
            "show a low one, the residual gate-kept errors are recoverable graded "
            "evidence (M2), not garbage — closing the gap to the LLM upper bound."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
