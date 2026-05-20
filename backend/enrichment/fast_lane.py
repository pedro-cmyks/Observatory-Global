"""Fast-lane hot-window enrichment.

This is intentionally cheaper than transformer NLP. It gives product-served
rows an Atlas-owned sentiment method quickly while keeping `nlp_processed_at`
NULL so the transformer worker can still overwrite the row later.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
from dataclasses import dataclass

import asyncpg

from enrichment.lexicon_sentiment import score_headline


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [fast_lane] %(levelname)s %(message)s")

DEFAULT_HOURS = 24
DEFAULT_LIMIT = 10_000
FAST_NEUTRAL_CONFIDENCE = 0.01


@dataclass(frozen=True)
class FastLaneDecision:
    sentiment: float
    confidence: float
    method: str
    lang: str | None


def classify_fast_lane(headline: str | None, source_lang: str | None) -> FastLaneDecision:
    """Return a fast-lane decision for a single headline.

    `fast_neutral` is explicit low-confidence fallback, not a claim that the
    story is semantically neutral. It means Atlas did not find sentiment-bearing
    terms in the fast path.
    """
    sentiment, confidence, lang = score_headline(headline or "", source_lang)
    if confidence > 0 or sentiment != 0:
        return FastLaneDecision(sentiment, confidence, "lexicon", lang)
    return FastLaneDecision(0.0, FAST_NEUTRAL_CONFIDENCE, "fast_neutral", lang)


SELECT_SQL = """
SELECT id, headline, source_lang
FROM signals_v2
WHERE nlp_method IS NULL
  AND headline IS NOT NULL
  AND LENGTH(headline) > 10
  AND created_at > NOW() - ($1 || ' hours')::INTERVAL
ORDER BY created_at DESC
LIMIT $2
"""


UPDATE_SQL = """
UPDATE signals_v2
SET nlp_sentiment = $1,
    nlp_confidence = $2,
    nlp_method = $3
WHERE id = $4
  AND nlp_method IS NULL
"""


async def run_fast_lane(conn: asyncpg.Connection, *, hours: int, limit: int, dry_run: bool) -> dict:
    rows = await conn.fetch(SELECT_SQL, str(hours), limit)
    records: list[tuple[float, float, str, int]] = []
    counts = {"lexicon": 0, "fast_neutral": 0}

    for row in rows:
        decision = classify_fast_lane(row["headline"], row["source_lang"])
        counts[decision.method] = counts.get(decision.method, 0) + 1
        records.append((decision.sentiment, decision.confidence, decision.method, row["id"]))

    if records and not dry_run:
        await conn.executemany(UPDATE_SQL, records)

    return {
        "fetched": len(rows),
        "updated": 0 if dry_run else len(records),
        "dry_run": dry_run,
        "hours": hours,
        "limit": limit,
        "method_counts": counts,
    }


async def _cli(hours: int, limit: int, dry_run: bool) -> None:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")
    conn = await asyncpg.connect(db_url)
    started = time.monotonic()
    try:
        result = await run_fast_lane(conn, hours=hours, limit=limit, dry_run=dry_run)
    finally:
        await conn.close()
    logger.info("Fast-lane done: %s duration=%.1fs", result, time.monotonic() - started)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas fast-lane hot-window enrichment")
    parser.add_argument("--hours", type=int, default=DEFAULT_HOURS)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    asyncio.run(_cli(args.hours, args.limit, args.dry_run))


if __name__ == "__main__":
    main()
