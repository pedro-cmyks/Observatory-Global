#!/usr/bin/env python3
"""Report Atlas scope-gate keep-rate (recall proxy) BY LANGUAGE.

Read-only operational telemetry. `gate_coverage_report.py` answers
"how much of the surface does the gate keep, overall and per topic?".
This script answers the complementary diversity question (#214/#162):

  "Does the scope gate keep non-English signals at the same rate as
   English ones, or is it a language gate in a quality-gate costume?"

The gate scores `headline | topic_label` with a multilingual e5-base
encoder, but its keep-threshold was calibrated on an English-heavy
corpus. If the kept-rate-of-scored for, say, Spanish is far below the
English baseline, the gate is rejecting relevant non-English evidence
on language, not relevance — the Peru-recount 0/43 case generalized.

This report quantifies that deficit per language so the fix (relax /
recalibrate the gate on the language axis) is evidence-led, not a
blind removal that would re-admit the English GDELT noise the gate
filters correctly.

Env: DATABASE_URL (Supabase pooler). Run on the worker env that holds
the credentials:
  DATABASE_URL=... .venv/bin/python -m scripts.gate_recall_by_language --hours 168
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
BASELINE_LANG = "en"
# A language whose kept-rate-of-scored falls this far (absolute) below the
# English baseline is flagged as likely language-biased rejection, not
# relevance rejection. 0.15 chosen as a conservative product threshold; the
# point of the report is to show the real numbers, not to auto-act on them.
BIAS_DEFICIT_THRESHOLD = 0.15
# Languages with fewer scored rows than this are statistically too thin to
# call biased; reported but never flagged.
MIN_SCORED_FOR_FLAG = 30

GATE_RECALL_SQL = """
WITH scoped AS (
    SELECT
        COALESCE(NULLIF(s.source_lang, ''), 'unknown') AS lang,
        a.signal_id,
        a.gate_score,
        a.gate_kept
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    JOIN signals_v2 s   ON s.id = a.signal_id
    WHERE a.method = 'lexicon'
      AND a.model_version = $1
      AND a.assigned_at >= NOW() - ($2::int * INTERVAL '1 hour')
      AND t.is_active = TRUE
),
overall AS (
    SELECT
        COUNT(*)::int AS assignments,
        COUNT(*) FILTER (WHERE gate_score IS NOT NULL)::int AS scored,
        COUNT(*) FILTER (WHERE gate_kept IS TRUE)::int  AS kept,
        COUNT(*) FILTER (WHERE gate_kept IS FALSE)::int AS abstained,
        COUNT(*) FILTER (WHERE gate_score IS NULL)::int AS unscored,
        AVG(gate_score) FILTER (WHERE gate_score IS NOT NULL)::float AS avg_gate_score
    FROM scoped
),
by_lang AS (
    SELECT
        lang,
        COUNT(*)::int AS assignments,
        COUNT(DISTINCT signal_id)::int AS distinct_signals,
        COUNT(*) FILTER (WHERE gate_score IS NOT NULL)::int AS scored,
        COUNT(*) FILTER (WHERE gate_kept IS TRUE)::int  AS kept,
        COUNT(*) FILTER (WHERE gate_kept IS FALSE)::int AS abstained,
        COUNT(*) FILTER (WHERE gate_score IS NULL)::int AS unscored,
        AVG(gate_score) FILTER (WHERE gate_score IS NOT NULL)::float AS avg_gate_score
    FROM scoped
    GROUP BY lang
)
SELECT
    (SELECT row_to_json(overall) FROM overall) AS overall,
    COALESCE(
        jsonb_agg(to_jsonb(by_lang) ORDER BY scored DESC, lang),
        '[]'::jsonb
    ) AS by_lang
FROM by_lang;
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


def flag_bias(
    by_lang: list[dict[str, Any]],
    *,
    baseline_lang: str = BASELINE_LANG,
    deficit_threshold: float = BIAS_DEFICIT_THRESHOLD,
    min_scored: int = MIN_SCORED_FOR_FLAG,
) -> list[dict[str, Any]]:
    """Annotate each language row with its keep-rate deficit vs the baseline.

    Pure function over enriched rows. Adds:
      - keep_rate_deficit_vs_baseline: baseline_keep_rate - lang_keep_rate
        (positive = this language is kept LESS than the baseline)
      - language_bias_suspected: bool (deficit over threshold AND enough rows)
    Returns a NEW list; does not mutate inputs.
    """
    baseline = next((r for r in by_lang if r.get("lang") == baseline_lang), None)
    base_rate = baseline.get("kept_rate_of_scored") if baseline else None

    out: list[dict[str, Any]] = []
    for row in by_lang:
        r = dict(row)
        lang_rate = r.get("kept_rate_of_scored")
        scored = int(r.get("scored") or 0)
        deficit: float | None = None
        suspected = False
        if base_rate is not None and lang_rate is not None:
            deficit = round(base_rate - lang_rate, 4)
            suspected = (
                r.get("lang") != baseline_lang
                and scored >= min_scored
                and deficit >= deficit_threshold
            )
        r["keep_rate_deficit_vs_baseline"] = deficit
        r["language_bias_suspected"] = suspected
        out.append(r)
    return out


def build_report(*, hours: int, db_row: Any) -> dict[str, Any]:
    overall_raw = dict(_json_value(db_row["overall"], {}))
    langs_raw = [enrich_counts(dict(r)) for r in _json_value(db_row["by_lang"], [])]
    langs = flag_bias(langs_raw)
    flagged = [r["lang"] for r in langs if r.get("language_bias_suspected")]

    return {
        "schema_version": "atlas-gate-recall-by-language-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": hours,
        "model_version": MODEL_VERSION,
        "baseline_lang": BASELINE_LANG,
        "bias_deficit_threshold": BIAS_DEFICIT_THRESHOLD,
        "min_scored_for_flag": MIN_SCORED_FOR_FLAG,
        "overall": enrich_counts(overall_raw),
        "by_lang": langs,
        "languages_with_suspected_bias": flagged,
        "interpretation": {
            "kept_rate_of_scored": (
                "share of GATE-SCORED assignments the gate keeps, per language; "
                "the recall proxy. Compared to the English baseline."
            ),
            "keep_rate_deficit_vs_baseline": (
                "english keep-rate minus this language's keep-rate; positive "
                "means non-English evidence is kept less often."
            ),
            "language_bias_suspected": (
                "deficit over threshold with enough scored rows — the gate is "
                "likely rejecting on language, not relevance (the #214/#162 "
                "Peru-recount failure generalized). Fix = recalibrate the gate "
                "threshold on the language axis, NOT remove the gate globally."
            ),
        },
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    import asyncpg

    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    conn = await asyncpg.connect(db_url)
    try:
        row = await conn.fetchrow(GATE_RECALL_SQL, MODEL_VERSION, args.hours)
    finally:
        await conn.close()

    return build_report(hours=args.hours, db_row=row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report Atlas scope-gate keep-rate by language (recall bias)."
    )
    parser.add_argument("--hours", type=int, default=168)
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
