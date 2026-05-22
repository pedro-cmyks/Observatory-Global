"""Report effective NLP coverage in product-served cells.

Unlike `nlp_sla_report.py` (row-level), this measures whether the cells the
product actually serves (country/topic aggregates) qualify for transformer-
sourced sentiment under the briefing fusion threshold.

The briefing fuses sentiment via `app.services.sentiment_fusion.choose_sentiment`:
when bucket NLP coverage clears `BRIEFING_NLP_COVERAGE_THRESHOLD` (default 0.30)
the response uses transformer sentiment; otherwise it falls back to GDELT V2Tone.

This script aggregates the same matviews the API reads from:
- `country_hourly_v2`            — hot country surfaces.
- `theme_country_hourly_v2`      — hot theme/country surfaces.
- `historical_topic_country_daily` — long-window processed history.

Output answers: "of the product cells we serve, what fraction would render
with transformer-sourced sentiment today?" — the metric that matters more
than the raw 4% transformer-row ratio.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

import asyncpg


HOT_COUNTRY_SQL = """
WITH cells AS (
    SELECT
        country_code,
        SUM(signal_count)::bigint                       AS signals,
        SUM(nlp_signal_count)::bigint                   AS nlp_signals,
        CASE WHEN SUM(signal_count) > 0
             THEN SUM(nlp_signal_count)::float / SUM(signal_count)
             ELSE 0.0
        END                                             AS nlp_coverage
    FROM country_hourly_v2
    WHERE hour > NOW() - ($1 || ' hours')::INTERVAL
    GROUP BY country_code
)
SELECT
    COUNT(*)::bigint                                                AS country_cells,
    SUM(signals)::bigint                                            AS signals_served,
    SUM(nlp_signals)::bigint                                        AS nlp_signals_served,
    COUNT(*) FILTER (WHERE nlp_coverage >= $2)::bigint              AS cells_nlp_qualified,
    COUNT(*) FILTER (WHERE nlp_coverage <  $2)::bigint              AS cells_gdelt_fallback,
    COALESCE(
      SUM(signals) FILTER (WHERE nlp_coverage >= $2)::bigint, 0
    )                                                               AS signals_nlp_weighted,
    COALESCE(
      SUM(signals) FILTER (WHERE nlp_coverage <  $2)::bigint, 0
    )                                                               AS signals_gdelt_weighted,
    AVG(nlp_coverage)::float                                        AS avg_cell_coverage
FROM cells
"""


HOT_TOP_GAPS_SQL = """
SELECT
    country_code,
    SUM(signal_count)::bigint                                       AS signals,
    SUM(nlp_signal_count)::bigint                                   AS nlp_signals,
    CASE WHEN SUM(signal_count) > 0
         THEN ROUND((SUM(nlp_signal_count)::float / SUM(signal_count))::numeric, 4)
         ELSE 0
    END                                                             AS nlp_coverage
FROM country_hourly_v2
WHERE hour > NOW() - ($1 || ' hours')::INTERVAL
GROUP BY country_code
HAVING SUM(signal_count) >= $2 AND (
    SUM(nlp_signal_count)::float / NULLIF(SUM(signal_count), 0)
) < $3
ORDER BY signals DESC
LIMIT $4
"""


HOT_THEME_SQL = """
WITH cells AS (
    SELECT
        theme,
        country_code,
        SUM(signal_count)::bigint                       AS signals,
        SUM(nlp_signal_count)::bigint                   AS nlp_signals,
        CASE WHEN SUM(signal_count) > 0
             THEN SUM(nlp_signal_count)::float / SUM(signal_count)
             ELSE 0.0
        END                                             AS nlp_coverage
    FROM theme_country_hourly_v2
    WHERE hour > NOW() - ($1 || ' hours')::INTERVAL
    GROUP BY theme, country_code
)
SELECT
    COUNT(*)::bigint                                                AS theme_country_cells,
    SUM(signals)::bigint                                            AS signals_served,
    SUM(nlp_signals)::bigint                                        AS nlp_signals_served,
    COUNT(*) FILTER (WHERE nlp_coverage >= $2)::bigint              AS cells_nlp_qualified,
    COUNT(*) FILTER (WHERE nlp_coverage <  $2)::bigint              AS cells_gdelt_fallback,
    COALESCE(
      SUM(signals) FILTER (WHERE nlp_coverage >= $2)::bigint, 0
    )                                                               AS signals_nlp_weighted,
    COALESCE(
      SUM(signals) FILTER (WHERE nlp_coverage <  $2)::bigint, 0
    )                                                               AS signals_gdelt_weighted,
    AVG(nlp_coverage)::float                                        AS avg_cell_coverage
FROM cells
"""


HISTORICAL_SQL = """
SELECT
    COUNT(*)::bigint                                                AS daily_cells,
    SUM(signal_count)::bigint                                       AS signals_served,
    COUNT(*) FILTER (WHERE sentiment_coverage >= $1)::bigint        AS cells_nlp_qualified,
    COUNT(*) FILTER (WHERE sentiment_coverage <  $1)::bigint        AS cells_gdelt_fallback,
    COALESCE(
      SUM(signal_count) FILTER (WHERE sentiment_coverage >= $1)::bigint, 0
    )                                                               AS signals_nlp_weighted,
    COALESCE(
      SUM(signal_count) FILTER (WHERE sentiment_coverage <  $1)::bigint, 0
    )                                                               AS signals_gdelt_weighted,
    AVG(sentiment_coverage)::float                                  AS avg_cell_coverage,
    MIN(day)::text                                                  AS first_day,
    MAX(day)::text                                                  AS last_day
FROM historical_topic_country_daily
WHERE day >= (CURRENT_DATE - $2::INT)
"""


HOT_BUCKET_DISTRIBUTION_SQL = """
WITH cells AS (
    SELECT
        country_code,
        SUM(signal_count)::float                        AS signals,
        SUM(nlp_signal_count)::float                    AS nlp_signals
    FROM country_hourly_v2
    WHERE hour > NOW() - ($1 || ' hours')::INTERVAL
    GROUP BY country_code
)
SELECT
    bucket,
    COUNT(*)::bigint  AS cells,
    SUM(signals)::bigint AS signals
FROM (
    SELECT
        CASE
            WHEN signals = 0 THEN 'no_signals'
            WHEN nlp_signals / signals = 0 THEN '0%'
            WHEN nlp_signals / signals < 0.10 THEN '<10%'
            WHEN nlp_signals / signals < 0.20 THEN '10-20%'
            WHEN nlp_signals / signals < 0.30 THEN '20-30%'
            WHEN nlp_signals / signals < 0.50 THEN '30-50%'
            WHEN nlp_signals / signals < 0.80 THEN '50-80%'
            ELSE '80-100%'
        END AS bucket,
        signals,
        nlp_signals
    FROM cells
) b
GROUP BY bucket
ORDER BY bucket
"""


def _percent(num: float | int, denom: float | int) -> float:
    if not denom:
        return 0.0
    return round((float(num) / float(denom)) * 100.0, 2)


async def build_report(
    *,
    database_url: str,
    hot_hours: int,
    historical_days: int,
    threshold: float,
    min_signals: int,
    top_limit: int,
) -> dict[str, Any]:
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute("SET statement_timeout = 45000")

        hot_country = dict(
            await conn.fetchrow(HOT_COUNTRY_SQL, str(hot_hours), threshold)
        )
        hot_theme = dict(
            await conn.fetchrow(HOT_THEME_SQL, str(hot_hours), threshold)
        )
        historical = dict(
            await conn.fetchrow(HISTORICAL_SQL, threshold, historical_days)
        )
        gaps = await conn.fetch(
            HOT_TOP_GAPS_SQL, str(hot_hours), min_signals, threshold, top_limit
        )
        distribution = await conn.fetch(
            HOT_BUCKET_DISTRIBUTION_SQL, str(hot_hours)
        )

        def _summarize(row: dict[str, Any]) -> dict[str, Any]:
            served = int(row.get("signals_served") or 0)
            weighted = int(row.get("signals_nlp_weighted") or 0)
            qualified = int(row.get("cells_nlp_qualified") or 0)
            total_cells = int(
                row.get("country_cells")
                or row.get("theme_country_cells")
                or row.get("daily_cells")
                or 0
            )
            return {
                "cells_total": total_cells,
                "cells_nlp_qualified": qualified,
                "cells_gdelt_fallback": int(row.get("cells_gdelt_fallback") or 0),
                "cells_pct_nlp_qualified": _percent(qualified, total_cells),
                "signals_served": served,
                "signals_nlp_weighted": weighted,
                "signals_gdelt_weighted": int(row.get("signals_gdelt_weighted") or 0),
                "signals_pct_under_nlp_source": _percent(weighted, served),
                "avg_cell_coverage": round(float(row.get("avg_cell_coverage") or 0), 4),
            }

        return {
            "threshold": threshold,
            "fusion_rule": (
                "Briefing returns transformer sentiment when bucket nlp_coverage "
                f">= {threshold}; otherwise falls back to GDELT V2Tone."
            ),
            "hot_window": {
                "hours": hot_hours,
                "country_cells": _summarize(hot_country),
                "theme_country_cells": _summarize(hot_theme),
                "coverage_distribution_countries": [dict(r) for r in distribution],
            },
            "historical_window": {
                "days": historical_days,
                "first_day": historical.get("first_day"),
                "last_day": historical.get("last_day"),
                "summary": _summarize(historical),
            },
            "largest_country_gaps_hot": [
                {
                    "country_code": r["country_code"],
                    "signals": int(r["signals"]),
                    "nlp_signals": int(r["nlp_signals"]),
                    "nlp_coverage": float(r["nlp_coverage"]),
                }
                for r in gaps
            ],
            "interpretation": (
                "cells_pct_nlp_qualified counts cells regardless of volume. "
                "signals_pct_under_nlp_source weights by volume served — this is "
                "the share of product reads that render with transformer sentiment."
            ),
        }
    finally:
        await conn.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Product-cell-level effective NLP coverage report"
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"),
    )
    parser.add_argument("--hot-hours", type=int, default=24)
    parser.add_argument("--historical-days", type=int, default=7)
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(os.environ.get("BRIEFING_NLP_COVERAGE_THRESHOLD", "0.30")),
        help="Match briefing fusion threshold (default 0.30).",
    )
    parser.add_argument(
        "--min-signals",
        type=int,
        default=200,
        help="Minimum cell volume before listing it as a gap (avoid one-row noise).",
    )
    parser.add_argument("--top-limit", type=int, default=15)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL required")
    report = asyncio.run(
        build_report(
            database_url=args.database_url,
            hot_hours=args.hot_hours,
            historical_days=args.historical_days,
            threshold=args.threshold,
            min_signals=args.min_signals,
            top_limit=args.top_limit,
        )
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
