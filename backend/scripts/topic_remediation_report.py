#!/usr/bin/env python3
"""M3: per-topic and match-source remediation report from the consensus gold.

Read-only. Quantifies two precision levers grounded in the RQ1 gold:

  1. **Match source.** theme-hint-lex-v2 assignments come from GDELT theme
     hints, lexicon terms, or both. Split precision by source to test whether
     pure GDELT-theme-hint matches (lex_count==0, theme_hits>0) are the
     low-precision tail.
  2. **Per-topic precision.** Rank topics by gold precision so the
     catastrophic tail (0%-precision topics) can be retired or hard-gated.

Truth = consensus gold_decision (correct=1, incorrect/partial=0, unclear
dropped).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]


def _match_source(evidence: Any) -> str:
    ev = evidence
    if isinstance(ev, str):
        try:
            ev = json.loads(ev)
        except json.JSONDecodeError:
            return "unknown"
    if not isinstance(ev, dict):
        return "unknown"
    lex = int(ev.get("lex_count") or 0)
    theme = int(ev.get("theme_hits") or 0)
    if lex == 0 and theme > 0:
        return "theme_only"
    if lex > 0 and theme > 0:
        return "lex+theme"
    if lex > 0:
        return "lex_only"
    return "neither"


def _precision(correct: int, total: int) -> float | None:
    return round(correct / total, 4) if total else None


def build_report(gold: list[dict[str, Any]], min_n: int) -> dict[str, Any]:
    rows = [r for r in gold if r.get("gold_decision") not in (None, "unclear")]

    by_source: dict[str, list[int]] = defaultdict(list)
    by_topic: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        truth = 1 if r["gold_decision"] == "correct" else 0
        by_source[_match_source(r.get("evidence"))].append(truth)
        by_topic[str(r.get("assigned_topic_slug") or "")].append(truth)

    source_table = {
        src: {"n": len(v), "correct": sum(v), "precision": _precision(sum(v), len(v))}
        for src, v in sorted(by_source.items(), key=lambda kv: -len(kv[1]))
    }

    topic_table = []
    for slug, v in by_topic.items():
        if len(v) < min_n:
            continue
        topic_table.append(
            {"slug": slug, "n": len(v), "correct": sum(v), "precision": _precision(sum(v), len(v))}
        )
    topic_table.sort(key=lambda t: (t["precision"] if t["precision"] is not None else 1.0))

    # what-if: drop theme_only matches entirely
    kept = [r for r in rows if _match_source(r.get("evidence")) != "theme_only"]
    kept_correct = sum(1 for r in kept if r["gold_decision"] == "correct")
    baseline_correct = sum(1 for r in rows if r["gold_decision"] == "correct")

    return {
        "schema_version": "atlas-rq1-topic-remediation-v1",
        "n_scored": len(rows),
        "baseline_precision": _precision(baseline_correct, len(rows)),
        "precision_by_match_source": source_table,
        "what_if_drop_theme_only": {
            "kept": len(kept),
            "coverage": _precision(len(kept), len(rows)),
            "precision": _precision(kept_correct, len(kept)),
        },
        "worst_topics": topic_table[:12],
        "remediation": {
            "M3a": "Hard-gate or down-weight theme_only matches (lex_count==0, theme_hits>0); they are the low-precision GDELT-theme-hint tail.",
            "M3b": "Retire or near-fully gate the 0%-precision topics until their lexicon/definition is fixed.",
        },
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Per-topic / match-source remediation report (M3).")
    ap.add_argument("--gold", required=True, type=Path)
    ap.add_argument("--min-topic-n", type=int, default=8)
    ap.add_argument("--output", required=True, type=Path)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(_read_jsonl(args.gold), args.min_topic_n)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
