#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.evidence_role_schema import read_jsonl


VISIBLE_TIERS = {"verified", "candidate", "context_rich"}


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


def summarize_consensus(rows: list[dict[str, Any]]) -> dict[str, Any]:
    role_counts = Counter(row.get("consensus_role") for row in rows)
    training_rows = [row for row in rows if row.get("is_training_gold")]
    return {
        "schema_version": "atlas-evidence-role-student-report-v1",
        "training_rows": len(training_rows),
        "role_counts": dict(role_counts),
        "status": "needs_more_labels"
        if len(training_rows) < 100
        else "ready_for_student_training",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train/evaluate the local evidence-role student."
    )
    parser.add_argument("--consensus", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.consensus)
    report = summarize_consensus(rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
