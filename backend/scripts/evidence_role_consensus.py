#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.evidence_role_schema import normalize_reason_codes, read_jsonl, write_jsonl


MIN_TEACHERS_FOR_GOLD = 2


def consensus_for_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    first = group[0]
    counts = Counter(row["role"] for row in group)
    role, count = counts.most_common(1)[0]
    if len(group) < MIN_TEACHERS_FOR_GOLD:
        agreement = "insufficient_teachers"
        consensus_role = None
    elif count == len(group):
        agreement = f"{count}_of_{len(group)}"
        consensus_role = role
    elif count >= 2:
        agreement = f"{count}_of_{len(group)}"
        consensus_role = role
    else:
        agreement = "no_majority"
        consensus_role = None

    agreeing = [row for row in group if row["role"] == consensus_role] if consensus_role else []
    reason_codes = normalize_reason_codes(
        code for row in agreeing for code in (row.get("reason_codes") or [])
    )
    avg_conf = (
        round(
            sum(float(row.get("role_confidence") or 0.0) for row in agreeing)
            / len(agreeing),
            4,
        )
        if agreeing
        else None
    )

    return {
        "schema_version": "atlas-evidence-role-consensus-v1",
        "signal_id": first["signal_id"],
        "cluster_id": first["cluster_id"],
        "headline": first.get("headline"),
        "cluster_label": first.get("cluster_label"),
        "candidate_topic_slug": first.get("candidate_topic_slug"),
        "consensus_role": consensus_role,
        "consensus_confidence": avg_conf,
        "agreement": agreement,
        "teacher_count": len(group),
        "teacher_roles": dict(counts),
        "reason_codes": reason_codes,
        "rationales": [
            {
                "teacher_vendor": row.get("teacher_vendor"),
                "role": row.get("role"),
                "rationale": row.get("rationale"),
            }
            for row in group
        ],
        "is_training_gold": consensus_role is not None,
    }


def build_consensus(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        for row in read_jsonl(path):
            grouped[(str(row["cluster_id"]), str(row["signal_id"]))].append(row)

    consensus: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    for group in grouped.values():
        row = consensus_for_group(group)
        if row["is_training_gold"]:
            consensus.append(row)
        else:
            disagreements.append(row)
    return consensus, disagreements


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build evidence-role consensus labels from teacher outputs."
    )
    parser.add_argument("--teacher", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--disagreements", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    consensus, disagreements = build_consensus(args.teacher)
    write_jsonl(args.output, consensus)
    write_jsonl(args.disagreements, disagreements)
    print(
        json.dumps(
            {"consensus": len(consensus), "disagreements": len(disagreements)},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
