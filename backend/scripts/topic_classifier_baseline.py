"""Baseline + A/B report for atlas_topic classifier versions.

Used to validate Issue #171 (v2 SQL bulk classifier) against the legacy
`classify_topics.py` (v1 / `theme-hint-lex-v1`). Answers three questions
on a single look-back window:

  1. How many candidate signals exist? (denominator)
  2. How many distinct signals does each model_version assign at least one
     topic to? (recall numerator per version)
  3. How does per-topic distribution shift between v1 and v2?

This script is read-only. Run it before and after
`backfill_lexicon_topics.py` to measure the lift. Recommended sequence::

    # measure v1 baseline (24h)
    python -m backend.scripts.topic_classifier_baseline --window-hours 24 > baseline.json

    # apply v2 to last 24h
    python -m backend.scripts.backfill_lexicon_topics --window-hours 24

    # compare (both versions now live in signal_topic_assignments)
    python -m backend.scripts.topic_classifier_baseline --window-hours 24 > after.json

The script does NOT mutate any table.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

import asyncpg


CANDIDATE_SQL = """
SELECT
    COUNT(*)::bigint                                                    AS candidate_total,
    COUNT(*) FILTER (
        WHERE themes IS NOT NULL AND array_length(themes, 1) > 0
    )::bigint                                                           AS candidate_with_themes,
    COUNT(*) FILTER (
        WHERE headline IS NOT NULL AND length(headline) >= $2
    )::bigint                                                           AS candidate_with_headline
FROM signals_v2
WHERE timestamp > NOW() - ($1 || ' hours')::interval
"""


# Recall numerator per model_version. distinct_signals_with_any_topic =
# number of unique signals in the window that received >= 1 assignment
# from this version.
RECALL_PER_VERSION_SQL = """
WITH window_signals AS (
    SELECT id
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::interval
)
SELECT
    a.model_version,
    a.method,
    COUNT(*)::bigint                                AS assignments,
    COUNT(DISTINCT a.signal_id)::bigint             AS distinct_signals,
    ROUND(AVG(a.confidence)::numeric, 4)            AS avg_confidence,
    ROUND(
        (COUNT(*) FILTER (WHERE a.confidence >= 0.75))::numeric
        / NULLIF(COUNT(*), 0),
        4
    )                                               AS high_conf_share
FROM signal_topic_assignments a
JOIN window_signals s ON s.id = a.signal_id
GROUP BY a.model_version, a.method
ORDER BY assignments DESC
"""


# Per-topic distribution per version on the same window.
PER_TOPIC_BY_VERSION_SQL = """
WITH window_signals AS (
    SELECT id
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::interval
)
SELECT
    a.model_version,
    t.slug,
    COUNT(*)::bigint                            AS assignments,
    COUNT(DISTINCT a.signal_id)::bigint         AS distinct_signals,
    ROUND(AVG(a.confidence)::numeric, 4)        AS avg_confidence
FROM signal_topic_assignments a
JOIN window_signals s ON s.id = a.signal_id
JOIN atlas_topics t ON t.id = a.topic_id
GROUP BY a.model_version, t.slug
ORDER BY a.model_version, assignments DESC
"""


# Cross-version agreement on the same signal: how often v1 and v2 produce
# the same top-1 topic, drop, change, etc. Bounded to the window.
AGREEMENT_SQL = """
WITH window_signals AS (
    SELECT id
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::interval
),
ranked AS (
    SELECT
        a.signal_id,
        a.model_version,
        a.topic_id,
        a.confidence,
        ROW_NUMBER() OVER (
            PARTITION BY a.signal_id, a.model_version
            ORDER BY a.confidence DESC, a.topic_id
        ) AS rnk
    FROM signal_topic_assignments a
    JOIN window_signals s ON s.id = a.signal_id
    WHERE a.method = 'lexicon'
),
top1 AS (
    SELECT signal_id, model_version, topic_id, confidence
    FROM ranked
    WHERE rnk = 1
),
joined AS (
    SELECT
        v1.signal_id,
        v1.topic_id  AS v1_topic,
        v1.confidence AS v1_conf,
        v2.topic_id  AS v2_topic,
        v2.confidence AS v2_conf
    FROM top1 v1
    FULL OUTER JOIN top1 v2
      ON v1.signal_id = v2.signal_id
     AND v1.model_version = 'theme-hint-lex-v1'
     AND v2.model_version = 'theme-hint-lex-v2'
    WHERE COALESCE(v1.model_version, 'theme-hint-lex-v1') = 'theme-hint-lex-v1'
      AND COALESCE(v2.model_version, 'theme-hint-lex-v2') = 'theme-hint-lex-v2'
)
SELECT
    COUNT(*)::bigint                                                AS signals_compared,
    COUNT(*) FILTER (
        WHERE v1_topic IS NOT NULL AND v2_topic IS NOT NULL
          AND v1_topic = v2_topic
    )::bigint                                                       AS same_top1,
    COUNT(*) FILTER (
        WHERE v1_topic IS NOT NULL AND v2_topic IS NOT NULL
          AND v1_topic <> v2_topic
    )::bigint                                                       AS different_top1,
    COUNT(*) FILTER (
        WHERE v1_topic IS NULL AND v2_topic IS NOT NULL
    )::bigint                                                       AS only_v2,
    COUNT(*) FILTER (
        WHERE v1_topic IS NOT NULL AND v2_topic IS NULL
    )::bigint                                                       AS only_v1
FROM joined
"""


CONFIDENCE_HISTOGRAM_SQL = """
WITH window_signals AS (
    SELECT id
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::interval
)
SELECT
    a.model_version,
    width_bucket(a.confidence, 0.0, 1.0, 10) AS bucket,
    COUNT(*)::bigint                          AS assignments
FROM signal_topic_assignments a
JOIN window_signals s ON s.id = a.signal_id
GROUP BY a.model_version, bucket
ORDER BY a.model_version, bucket
"""


def _percent(num: float | int, denom: float | int) -> float:
    if not denom:
        return 0.0
    return round((float(num) / float(denom)) * 100.0, 4)


async def build_report(
    *,
    database_url: str,
    window_hours: float,
    min_headline_len: int,
) -> dict[str, Any]:
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute("SET statement_timeout = 60000")

        candidates = dict(
            await conn.fetchrow(
                CANDIDATE_SQL, str(window_hours), min_headline_len
            )
        )
        recall_rows = await conn.fetch(
            RECALL_PER_VERSION_SQL, str(window_hours)
        )
        per_topic_rows = await conn.fetch(
            PER_TOPIC_BY_VERSION_SQL, str(window_hours)
        )
        try:
            agreement = dict(await conn.fetchrow(AGREEMENT_SQL, str(window_hours)))
        except Exception:  # pragma: no cover - defensive on empty windows
            agreement = {
                "signals_compared": 0,
                "same_top1": 0,
                "different_top1": 0,
                "only_v1": 0,
                "only_v2": 0,
            }
        histogram_rows = await conn.fetch(
            CONFIDENCE_HISTOGRAM_SQL, str(window_hours)
        )

        denom = int(candidates.get("candidate_total") or 0)

        recall_summary = [
            {
                "model_version": r["model_version"],
                "method": r["method"],
                "assignments": int(r["assignments"]),
                "distinct_signals": int(r["distinct_signals"]),
                "recall_pct_of_window": _percent(
                    int(r["distinct_signals"]), denom
                ),
                "avg_confidence": float(r["avg_confidence"] or 0),
                "high_conf_share": float(r["high_conf_share"] or 0),
            }
            for r in recall_rows
        ]

        per_topic: dict[str, list[dict[str, Any]]] = {}
        for r in per_topic_rows:
            per_topic.setdefault(r["model_version"], []).append(
                {
                    "slug": r["slug"],
                    "assignments": int(r["assignments"]),
                    "distinct_signals": int(r["distinct_signals"]),
                    "avg_confidence": float(r["avg_confidence"] or 0),
                }
            )

        histogram: dict[str, list[dict[str, Any]]] = {}
        for r in histogram_rows:
            histogram.setdefault(r["model_version"], []).append(
                {
                    "bucket_0_to_10": int(r["bucket"]) if r["bucket"] is not None else None,
                    "assignments": int(r["assignments"]),
                }
            )

        return {
            "window_hours": window_hours,
            "candidates": {
                "total_signals_in_window": denom,
                "with_themes": int(candidates.get("candidate_with_themes") or 0),
                "with_headline_min_len": int(
                    candidates.get("candidate_with_headline") or 0
                ),
                "min_headline_len": min_headline_len,
            },
            "recall_per_version": recall_summary,
            "agreement_v1_vs_v2": {
                "signals_compared": int(agreement.get("signals_compared") or 0),
                "same_top1": int(agreement.get("same_top1") or 0),
                "different_top1": int(agreement.get("different_top1") or 0),
                "only_v1": int(agreement.get("only_v1") or 0),
                "only_v2": int(agreement.get("only_v2") or 0),
                "top1_match_pct": _percent(
                    int(agreement.get("same_top1") or 0),
                    int(agreement.get("signals_compared") or 0),
                ),
            },
            "per_topic_by_version": per_topic,
            "confidence_histogram_by_version": histogram,
            "interpretation": (
                "recall_pct_of_window = distinct_signals / total_signals_in_window. "
                "Compare v1 vs v2 across that metric. agreement.top1_match_pct gauges "
                "how often the top topic is preserved (proxy for precision parity). "
                "only_v2 counts new signals recovered by v2; only_v1 counts signals lost "
                "from v1 to v2 — both are sanity-check thresholds before promoting v2."
            ),
        }
    finally:
        await conn.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baseline + A/B report for atlas topic classifier versions."
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL")
        or os.environ.get("SUPABASE_DB_URL"),
    )
    parser.add_argument("--window-hours", type=float, default=24.0)
    parser.add_argument("--min-headline-len", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL required")
    report = asyncio.run(
        build_report(
            database_url=args.database_url,
            window_hours=args.window_hours,
            min_headline_len=args.min_headline_len,
        )
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
