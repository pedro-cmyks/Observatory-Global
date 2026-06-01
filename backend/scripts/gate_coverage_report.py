#!/usr/bin/env python3
"""Report Atlas scope-gate coverage and abstention from live assignments.

This is read-only operational telemetry. Precision is established by the
calibration corpus; this report answers the complementary product question:
"how much of the live Atlas topic surface is the 90%-precision gate keeping?"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODEL_VERSION = "theme-hint-lex-v2"

GATE_COVERAGE_SQL = """
WITH scoped AS (
    SELECT
        t.slug,
        t.label,
        a.signal_id,
        a.gate_score,
        a.gate_kept,
        a.gate_model
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    WHERE a.method = 'lexicon'
      AND a.model_version = $1
      AND a.assigned_at >= NOW() - ($2::int * INTERVAL '1 hour')
      AND t.is_active = TRUE
),
overall AS (
    SELECT
        COUNT(*)::int AS assignments,
        COUNT(DISTINCT signal_id)::int AS distinct_signals,
        COUNT(*) FILTER (WHERE gate_score IS NOT NULL)::int AS scored,
        COUNT(*) FILTER (WHERE gate_kept IS TRUE)::int AS kept,
        COUNT(*) FILTER (WHERE gate_kept IS FALSE)::int AS abstained,
        COUNT(*) FILTER (WHERE gate_score IS NULL)::int AS unscored,
        AVG(gate_score) FILTER (WHERE gate_score IS NOT NULL)::float AS avg_gate_score
    FROM scoped
),
by_topic AS (
    SELECT
        slug,
        label,
        COUNT(*)::int AS assignments,
        COUNT(DISTINCT signal_id)::int AS distinct_signals,
        COUNT(*) FILTER (WHERE gate_score IS NOT NULL)::int AS scored,
        COUNT(*) FILTER (WHERE gate_kept IS TRUE)::int AS kept,
        COUNT(*) FILTER (WHERE gate_kept IS FALSE)::int AS abstained,
        COUNT(*) FILTER (WHERE gate_score IS NULL)::int AS unscored,
        AVG(gate_score) FILTER (WHERE gate_score IS NOT NULL)::float AS avg_gate_score
    FROM scoped
    GROUP BY slug, label
)
SELECT
    (SELECT row_to_json(overall) FROM overall) AS overall,
    COALESCE(
        jsonb_agg(to_jsonb(by_topic) ORDER BY kept DESC, assignments DESC, slug),
        '[]'::jsonb
    ) AS by_topic
FROM by_topic;
"""


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        return json.loads(value)
    return value


def enrich_counts(row: dict[str, Any]) -> dict[str, Any]:
    assignments = int(row.get("assignments") or 0)
    scored = int(row.get("scored") or 0)
    kept = int(row.get("kept") or 0)
    abstained = int(row.get("abstained") or 0)
    unscored = int(row.get("unscored") or 0)

    enriched = dict(row)
    enriched["assignments"] = assignments
    enriched["scored"] = scored
    enriched["kept"] = kept
    enriched["abstained"] = abstained
    enriched["unscored"] = unscored
    enriched["scored_rate"] = _ratio(scored, assignments)
    enriched["kept_rate_of_scored"] = _ratio(kept, scored)
    enriched["abstain_rate_of_scored"] = _ratio(abstained, scored)
    enriched["kept_rate_of_assignments"] = _ratio(kept, assignments)
    enriched["unscored_rate"] = _ratio(unscored, assignments)
    return enriched


def build_report(*, hours: int, db_row: Any) -> dict[str, Any]:
    overall_raw = dict(_json_value(db_row["overall"], {}))
    topics_raw = [dict(r) for r in _json_value(db_row["by_topic"], [])]

    return {
        "schema_version": "atlas-gate-coverage-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": hours,
        "model_version": MODEL_VERSION,
        "precision_target": 0.9,
        "overall": enrich_counts(overall_raw),
        "by_topic": [enrich_counts(topic) for topic in topics_raw],
        "interpretation": {
            "precision_source": (
                "Precision target comes from the scope-gate calibration corpus; "
                "this live report measures coverage and abstention only."
            ),
            "kept": "assignments visible as high-confidence gated evidence",
            "abstained": "scored assignments rejected by the gate",
            "unscored": "recent assignments not scored by the gate yet",
        },
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    import asyncpg

    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    conn = await asyncpg.connect(db_url)
    try:
        row = await conn.fetchrow(GATE_COVERAGE_SQL, MODEL_VERSION, args.hours)
    finally:
        await conn.close()

    return build_report(hours=args.hours, db_row=row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report Atlas gate coverage and abstention.")
    parser.add_argument("--hours", type=int, default=24)
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
