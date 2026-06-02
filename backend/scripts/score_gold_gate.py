#!/usr/bin/env python3
"""Offline: score the consensus gold through the scope gate (RQ1 / M1).

Read-only, no DB. Reuses the production gate's exact feature pipeline
(`score_assignments_gate.py`): embed "query: headline | topic_label" with
the gate's local e5-base encoder, build [embedding || confidence ||
matched_terms], apply the persisted scaler + logistic + per-topic
threshold. Then, using the 3-vendor consensus `gold_decision` as truth,
report precision and coverage of the kept set at the gate's operating
threshold and across a threshold sweep.

This converts improvement-method M1 (the scope gate as the precision
lever) from a proposal into a measured precision-vs-coverage curve.

Truth mapping (matches llm_baseline_compare._outcomes_for_atlas):
  correct -> 1 ; incorrect/partial -> 0 ; unclear -> dropped.

Run with the ML venv that has torch + transformers:
  /Users/pedro/AtlasLocalWorker/mlvenv/bin/python (or atlasvenv if it has ML deps)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from score_assignments_gate import (
    _build_embedder,
    _load_gate,
    _matched_terms,
    _score_and_decide,
)


def load_gold(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        decision = r.get("gold_decision")
        if decision == "unclear" or decision is None:
            continue
        rows.append(r)
    return rows


def _truth(decision: str) -> int:
    return 1 if decision == "correct" else 0


def precision_coverage(
    scores: np.ndarray, truths: np.ndarray, threshold: float
) -> dict[str, Any]:
    kept = scores >= threshold
    n_total = len(truths)
    n_kept = int(kept.sum())
    correct_kept = int(truths[kept].sum()) if n_kept else 0
    return {
        "threshold": round(float(threshold), 4),
        "kept": n_kept,
        "coverage": round(n_kept / n_total, 4) if n_total else None,
        "precision_kept": round(correct_kept / n_kept, 4) if n_kept else None,
    }


def build_report(
    *, gold: list[dict[str, Any]], scores: np.ndarray, kept_at_gate: list[bool], gate_id: str
) -> dict[str, Any]:
    truths = np.array([_truth(r["gold_decision"]) for r in gold])
    n = len(truths)
    baseline_precision = round(float(truths.sum()) / n, 4) if n else None

    # gate's own operating point (per-topic thresholds already applied)
    kept = np.array(kept_at_gate)
    n_kept = int(kept.sum())
    op = {
        "kept": n_kept,
        "coverage": round(n_kept / n, 4) if n else None,
        "precision_kept": round(int(truths[kept].sum()) / n_kept, 4) if n_kept else None,
    }

    sweep = [
        precision_coverage(scores, truths, t)
        for t in [0.5, 0.6, 0.7, 0.8, 0.85, 0.878, 0.9, 0.95]
    ]

    return {
        "schema_version": "atlas-rq1-gate-precision-coverage-v1",
        "gate_id": gate_id,
        "n_gold_scored": n,
        "baseline_no_gate": {"coverage": 1.0, "precision_kept": baseline_precision},
        "gate_operating_point": op,
        "threshold_sweep": sweep,
        "note": (
            "Truth = 3-vendor consensus gold_decision (correct=1, "
            "incorrect/partial=0, unclear dropped). Operating point uses the "
            "gate's per-topic thresholds; sweep uses a single global threshold."
        ),
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Score consensus gold through the scope gate (M1).")
    ap.add_argument("--gold", required=True, type=Path)
    ap.add_argument(
        "--gate",
        type=Path,
        default=Path("models/2026-05-29-scope-gate-v1-e5base.json"),
    )
    ap.add_argument("--gate-id", default="atlas-scope-gate-v1-e5base")
    ap.add_argument("--output", required=True, type=Path)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    gate = _load_gate(args.gate)
    gold = load_gold(args.gold)
    if not gold:
        raise SystemExit(f"no usable gold rows in {args.gold}")

    embed, device = _build_embedder(gate["feature_spec"]["embedding_model"])
    texts = [
        f"query: {(r.get('headline') or '').strip()} | {(r.get('assigned_topic_label') or '').strip()}"
        for r in gold
    ]
    emb = embed(texts)
    conf = np.array([float(r.get("confidence") or 0.0) for r in gold])
    mt = np.array([_matched_terms(r.get("evidence")) for r in gold])
    slugs = [str(r.get("assigned_topic_slug") or "") for r in gold]

    scores, kept = _score_and_decide(gate, emb, conf, mt, slugs)
    report = build_report(gold=gold, scores=scores, kept_at_gate=kept, gate_id=args.gate_id)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"device={device}")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
