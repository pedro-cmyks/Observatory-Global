#!/usr/bin/env python3
"""Build a consensus gold file from N LLM-annotator JSONL outputs.

Each annotator file is the output of `llm_annotator.py` (one row per
signal with `annotator_decision`). This script joins them by signal_id,
takes the majority vote on the decision, and attaches it as
`gold_decision` onto the benchmark sample rows so the downstream
`llm_baseline_classifier.py` / `llm_baseline_compare.py` can treat the
multi-vendor consensus as the gold standard (the MOC-sanctioned
defensible benchmark path, replacing single-human review).

Tie / no-majority items become `gold_decision = "unclear"` and are
skipped by the scoring scripts.

No API calls. Read-only inputs; writes one gold JSONL.

Schema version: atlas-annotator-consensus-gold-v1
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


CONSENSUS_SCHEMA = "atlas-annotator-consensus-gold-v1"


def load_decisions(path: Path, field: str) -> dict[int, str]:
    out: dict[int, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            sid = row.get("signal_id")
            decision = row.get(field)
            if sid is None or not decision:
                continue
            out[int(sid)] = str(decision)
    return out


def majority_vote(decisions: list[str]) -> tuple[str, str]:
    """Return (consensus_decision, agreement_tag).

    agreement_tag is one of: unanimous, majority, tie. Ties resolve to
    'unclear' so the scoring scripts drop them.
    """
    counts = Counter(decisions)
    if not counts:
        return "unclear", "tie"
    top, top_n = counts.most_common(1)[0]
    n = len(decisions)
    if top_n == n:
        return top, "unanimous"
    # tie if the top count is shared by another label
    shared = [label for label, c in counts.items() if c == top_n]
    if len(shared) > 1:
        return "unclear", "tie"
    return top, "majority"


def build_gold(
    *, sample_path: Path, annotator_decisions: dict[str, dict[int, str]], decision_field: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with sample_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            sid = row.get("signal_id")
            if sid is None:
                continue
            sid = int(sid)
            votes = [
                decisions[sid]
                for decisions in annotator_decisions.values()
                if sid in decisions
            ]
            if not votes:
                continue
            consensus, tag = majority_vote(votes)
            gold = dict(row)
            gold["gold_decision"] = consensus
            gold["consensus_agreement"] = tag
            gold["consensus_n_annotators"] = len(votes)
            gold["consensus_votes"] = votes
            gold["consensus_provenance"] = decision_field
            gold["schema_version"] = CONSENSUS_SCHEMA
            rows.append(gold)
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts = Counter(r["gold_decision"] for r in rows)
    tag_counts = Counter(r["consensus_agreement"] for r in rows)
    return {
        "total_rows": len(rows),
        "decision_counts": dict(decision_counts),
        "agreement_counts": dict(tag_counts),
        "usable_for_scoring": sum(
            1 for r in rows if r["gold_decision"] != "unclear"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build consensus gold from annotator files.")
    parser.add_argument("--sample", required=True, type=Path, help="benchmark sample JSONL")
    parser.add_argument(
        "--annotator",
        required=True,
        nargs="+",
        help="annotator JSONL files (>=2)",
    )
    parser.add_argument("--decision-field", default="annotator_decision")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    annotator_decisions = {
        path: load_decisions(Path(path), args.decision_field) for path in args.annotator
    }
    rows = build_gold(
        sample_path=args.sample,
        annotator_decisions=annotator_decisions,
        decision_field=args.decision_field,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(summarize(rows), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
