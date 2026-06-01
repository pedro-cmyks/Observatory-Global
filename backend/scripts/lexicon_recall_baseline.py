#!/usr/bin/env python3
"""Standing baseline: lexicon candidate-generator recall vs the gold set.

Read-only. The 2026-06-01 coverage root-cause diagnosis
(docs/research/topic-quality/2026-06-01-coverage-root-cause-lexicon-recall.md)
found that ~91% of true cluster evidence never receives a lexicon
assignment, so the scope gate never gets to keep or abstain on it. This
script turns that one-off observation into a repeatable metric so the
candidate-generator migration (lexicon -> embedding cluster membership)
has a baseline recall to beat.

For each gold consensus signal it asks: did the lexicon candidate
generator produce ANY assignment for this signal? Recall is reported
overall and per consensus role, with primary_evidence broken out as the
headline number.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODEL_VERSION = "theme-hint-lex-v2"

ASSIGNED_SIGNALS_SQL = """
SELECT DISTINCT signal_id
FROM signal_topic_assignments
WHERE method = 'lexicon'
  AND model_version = $1
  AND signal_id = ANY($2::bigint[]);
"""


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def load_gold(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("signal_id") is None:
                continue
            rows.append(row)
    return rows


def build_report(
    *, gold: list[dict[str, Any]], assigned_ids: set[int], gold_path: Path
) -> dict[str, Any]:
    by_role_total: dict[str, int] = defaultdict(int)
    by_role_with_candidate: dict[str, int] = defaultdict(int)
    total = 0
    total_with_candidate = 0

    for row in gold:
        role = str(row.get("consensus_role") or "unknown")
        has_candidate = int(row["signal_id"]) in assigned_ids
        total += 1
        by_role_total[role] += 1
        if has_candidate:
            total_with_candidate += 1
            by_role_with_candidate[role] += 1

    per_role = []
    for role in sorted(by_role_total, key=lambda r: by_role_total[r], reverse=True):
        gold_n = by_role_total[role]
        with_cand = by_role_with_candidate[role]
        per_role.append(
            {
                "role": role,
                "gold_rows": gold_n,
                "with_lexicon_candidate": with_cand,
                "missing_candidate": gold_n - with_cand,
                "candidate_recall": _ratio(with_cand, gold_n),
            }
        )

    primary = next(
        (r for r in per_role if r["role"] == "primary_evidence"),
        {"gold_rows": 0, "with_lexicon_candidate": 0, "candidate_recall": None},
    )

    return {
        "schema_version": "atlas-lexicon-recall-baseline-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": MODEL_VERSION,
        "gold_source": str(gold_path),
        "overall": {
            "gold_rows": total,
            "with_lexicon_candidate": total_with_candidate,
            "missing_candidate": total - total_with_candidate,
            "candidate_recall": _ratio(total_with_candidate, total),
        },
        "primary_evidence": {
            "gold_rows": primary["gold_rows"],
            "with_lexicon_candidate": primary["with_lexicon_candidate"],
            "candidate_recall": primary["candidate_recall"],
        },
        "by_role": per_role,
        "interpretation": {
            "candidate_recall": (
                "fraction of gold signals for which the lexicon candidate "
                "generator produced any topic assignment; the scope gate can "
                "only keep/abstain on signals that have a candidate"
            ),
            "baseline_to_beat": (
                "the embedding-based cluster-membership candidate generator "
                "should raise primary_evidence candidate_recall well above this "
                "baseline without regressing verified precision"
            ),
        },
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    import asyncpg

    gold = load_gold(args.gold)
    if not gold:
        raise SystemExit(f"no gold rows with signal_id found in {args.gold}")

    signal_ids = sorted({int(r["signal_id"]) for r in gold})

    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch(ASSIGNED_SIGNALS_SQL, MODEL_VERSION, signal_ids)
    finally:
        await conn.close()

    assigned_ids = {int(r["signal_id"]) for r in rows}
    return build_report(gold=gold, assigned_ids=assigned_ids, gold_path=args.gold)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baseline lexicon candidate-generator recall vs the gold set."
    )
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path(
            "docs/research/atlas-paper/phase-1-validation/labels/"
            "evidence-role-consensus/2026-06-01-consensus.jsonl"
        ),
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = asyncio.run(run(args))
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
