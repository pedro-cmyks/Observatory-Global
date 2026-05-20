"""Report Atlas-owned enrichment coverage for the hot product window."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

import asyncpg


SUMMARY_SQL = """
WITH hot AS (
    SELECT
        country_code,
        source_family,
        source_lang,
        nlp_method,
        nlp_processed_at,
        nlp_sentiment,
        signal_class,
        CASE
            WHEN nlp_processed_at IS NOT NULL THEN 'transformer'
            WHEN nlp_method IS NOT NULL THEN nlp_method
            WHEN signal_class IS NOT NULL THEN 'provenance_only'
            ELSE 'raw'
        END AS enrichment_method
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::INTERVAL
)
SELECT
    COUNT(*)::bigint AS total_rows,
    COUNT(*) FILTER (
        WHERE enrichment_method IN (
            'transformer',
            'lexicon',
            'fast_neutral',
            'topic_lexicon'
        )
    )::bigint AS atlas_owned_rows,
    COUNT(*) FILTER (WHERE enrichment_method = 'transformer')::bigint AS transformer_rows,
    COUNT(*) FILTER (
        WHERE enrichment_method IN ('lexicon', 'fast_neutral', 'topic_lexicon')
    )::bigint AS fast_lane_rows,
    COUNT(*) FILTER (WHERE enrichment_method = 'provenance_only')::bigint AS provenance_only_rows,
    COUNT(*) FILTER (WHERE enrichment_method = 'raw')::bigint AS raw_rows
FROM hot
"""


BREAKDOWN_SQL = """
WITH hot AS (
    SELECT
        COALESCE(source_family, 'unknown') AS source_family,
        COALESCE(source_lang, 'unknown') AS source_lang,
        COALESCE(country_code, 'XX') AS country_code,
        CASE
            WHEN nlp_processed_at IS NOT NULL THEN 'transformer'
            WHEN nlp_method IS NOT NULL THEN nlp_method
            WHEN signal_class IS NOT NULL THEN 'provenance_only'
            ELSE 'raw'
        END AS enrichment_method
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::INTERVAL
)
SELECT
    source_family,
    source_lang,
    country_code,
    COUNT(*)::bigint AS rows,
    COUNT(*) FILTER (
        WHERE enrichment_method NOT IN ('transformer', 'lexicon', 'fast_neutral', 'topic_lexicon')
    )::bigint AS gap_rows,
    COUNT(*) FILTER (WHERE enrichment_method = 'provenance_only')::bigint AS provenance_only_rows,
    COUNT(*) FILTER (WHERE enrichment_method = 'raw')::bigint AS raw_rows,
    COUNT(*) FILTER (WHERE enrichment_method = 'transformer')::bigint AS transformer_rows
FROM hot
GROUP BY source_family, source_lang, country_code
ORDER BY gap_rows DESC, rows DESC
LIMIT $2
"""


def coverage_pct(atlas_owned_rows: int, total_rows: int) -> float:
    if total_rows <= 0:
        return 100.0
    return round((atlas_owned_rows / total_rows) * 100, 2)


async def build_report(hours: int, limit: int) -> dict[str, Any]:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("SET statement_timeout = 45000")
        summary = dict(await conn.fetchrow(SUMMARY_SQL, str(hours)))
        breakdown_rows = await conn.fetch(BREAKDOWN_SQL, str(hours), limit)
        total = int(summary["total_rows"] or 0)
        atlas_owned = int(summary["atlas_owned_rows"] or 0)
        return {
            "window_hours": hours,
            "target": "90-100% product-served rows have Atlas-owned enrichment",
            "coverage_pct": coverage_pct(atlas_owned, total),
            "summary": {k: int(v or 0) for k, v in summary.items()},
            "largest_enrichment_gaps": [dict(row) for row in breakdown_rows],
            "method_note": (
                "Atlas-owned includes transformer and fast-lane method tags. "
                "Provenance-only is reported separately and is not counted toward the SLA because "
                "it is classification/provenance, not enough NLP enrichment."
            ),
        }
    finally:
        await conn.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas hot-window NLP SLA report")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = asyncio.run(build_report(hours=args.hours, limit=args.limit))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
