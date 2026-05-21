"""Report compact processed historical coverage in Supabase."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

import asyncpg


REPORT_SQL = """
SELECT
    MIN(day)::text AS first_day,
    MAX(day)::text AS last_day,
    COUNT(*)::bigint AS aggregate_rows,
    SUM(signal_count)::bigint AS represented_signals,
    AVG(sentiment_coverage)::float AS avg_sentiment_coverage,
    AVG(topic_coverage)::float AS avg_topic_coverage,
    AVG(entity_coverage)::float AS avg_entity_coverage,
    COUNT(DISTINCT model_version)::int AS model_versions,
    COUNT(DISTINCT country_code)::int AS countries,
    COUNT(DISTINCT topic_slug)::int AS topics
FROM historical_topic_country_daily
"""


TOP_TOPICS_SQL = """
SELECT topic_slug,
       SUM(signal_count)::bigint AS represented_signals,
       AVG(topic_coverage)::float AS avg_topic_coverage,
       AVG(sentiment_coverage)::float AS avg_sentiment_coverage
FROM historical_topic_country_daily
GROUP BY topic_slug
ORDER BY represented_signals DESC
LIMIT $1
"""


def _jsonable(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    return value


async def build_report(database_url: str, *, top_limit: int = 10) -> dict[str, Any]:
    conn = await asyncpg.connect(database_url)
    try:
        summary = await conn.fetchrow(REPORT_SQL)
        top_topics = await conn.fetch(TOP_TOPICS_SQL, top_limit)
        return {
            "summary": {key: _jsonable(value) for key, value in dict(summary).items()},
            "top_topics": [
                {key: _jsonable(value) for key, value in dict(row).items()}
                for row in top_topics
            ],
        }
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Report processed historical coverage")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"))
    parser.add_argument("--top-limit", type=int, default=10)
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    report = asyncio.run(build_report(args.database_url, top_limit=args.top_limit))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
