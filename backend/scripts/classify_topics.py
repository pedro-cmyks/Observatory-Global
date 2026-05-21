"""Classify recent signals into atlas_topics using theme hints + lexicon.

This is the first-pass topic classifier for signals_v2. It uses two evidence
sources from atlas_topics:

  - gdelt_theme_hints: array of GDELT GKG theme codes to intersect against
    signals_v2.themes (set membership via the && operator).
  - lexicon_terms: substrings checked against signals_v2.headline.

Confidence formula (normalized to 0..1, satisfies the existing CHECK
constraint on signal_topic_assignments.confidence):

    specificity = theme_hits / GREATEST(hint_count, 1)
    lex_score   = 1.0 if any lexicon term matches the headline else 0.0
    confidence  = 0.4 * specificity + 0.6 * lex_score

A signal must qualify with either a lexicon hit or at least three theme
matches. That keeps precision usable (~65% in spot checks) at the cost of
recall, which is acceptable while we wait on the multilingual NLP swap
(issues #162 / #167).

Each qualifying (signal, topic) is inserted as method='lexicon',
model_version='theme-hint-lex-v1'. Top-2 topics per signal are kept.
Evidence jsonb stores the raw theme_hits + lex_match for transparency.

CLI:
    python -m backend.scripts.classify_topics --window-hours 24 --batch-size 5000
    python -m backend.scripts.classify_topics --window-hours 1 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import asyncpg


LOGGER = logging.getLogger("classify_topics")

METHOD = "lexicon"
MODEL_VERSION = "theme-hint-lex-v1"
MIN_THEME_HITS_NO_LEX = 3
TOP_N_PER_SIGNAL = 2
MIN_CONFIDENCE = 0.3


CLASSIFY_SQL = """
WITH window_signals AS (
    SELECT id, themes, headline
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::interval
      AND themes IS NOT NULL
      AND array_length(themes, 1) > 0
    ORDER BY id
    LIMIT $2 OFFSET $3
),
expansions AS (
    SELECT
        s.id AS signal_id,
        t.id AS topic_id,
        t.slug,
        cardinality(
            ARRAY(SELECT unnest(s.themes) INTERSECT SELECT unnest(t.gdelt_theme_hints))
        ) AS theme_hits,
        cardinality(t.gdelt_theme_hints) AS hint_count,
        ARRAY(
            SELECT lt FROM unnest(t.lexicon_terms) lt
            WHERE s.headline IS NOT NULL
              AND lower(s.headline) LIKE '%' || lower(lt) || '%'
        ) AS matched_lex_terms
    FROM window_signals s
    JOIN atlas_topics t ON s.themes && t.gdelt_theme_hints AND t.is_active = true
),
qualified AS (
    SELECT
        signal_id,
        topic_id,
        slug,
        theme_hits,
        hint_count,
        cardinality(matched_lex_terms) > 0 AS lex_match,
        matched_lex_terms,
        (0.4 * (theme_hits::numeric / GREATEST(hint_count, 1))
         + 0.6 * (CASE WHEN cardinality(matched_lex_terms) > 0 THEN 1.0 ELSE 0.0 END)
        )::double precision AS confidence
    FROM expansions
    WHERE cardinality(matched_lex_terms) > 0
       OR theme_hits >= $4
),
ranked AS (
    SELECT
        signal_id, topic_id, slug, theme_hits, hint_count, lex_match,
        matched_lex_terms, confidence,
        ROW_NUMBER() OVER (
            PARTITION BY signal_id
            ORDER BY confidence DESC, theme_hits DESC, topic_id
        ) AS rnk
    FROM qualified
    WHERE confidence >= $5
)
SELECT signal_id, topic_id, slug, theme_hits, hint_count, lex_match,
       matched_lex_terms, confidence
FROM ranked
WHERE rnk <= $6;
"""


INSERT_SQL = """
INSERT INTO signal_topic_assignments
    (signal_id, topic_id, method, confidence, model_name, model_version, evidence, assigned_at)
VALUES
    ($1, $2, $3, $4, $5, $6, $7::jsonb, NOW())
ON CONFLICT (signal_id, topic_id, method, model_version)
DO UPDATE SET
    confidence = EXCLUDED.confidence,
    evidence = EXCLUDED.evidence,
    assigned_at = NOW();
"""


async def fetch_batch(
    conn: asyncpg.Connection,
    window_hours: int,
    batch_size: int,
    offset: int,
) -> list[asyncpg.Record]:
    return await conn.fetch(
        CLASSIFY_SQL,
        str(window_hours),
        batch_size,
        offset,
        MIN_THEME_HITS_NO_LEX,
        MIN_CONFIDENCE,
        TOP_N_PER_SIGNAL,
    )


async def insert_rows(conn: asyncpg.Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    payload = [
        (
            row["signal_id"],
            row["topic_id"],
            METHOD,
            row["confidence"],
            "atlas-topic-hint-lex",
            MODEL_VERSION,
            json.dumps(
                {
                    "theme_hits": row["theme_hits"],
                    "hint_count": row["hint_count"],
                    "lex_match": row["lex_match"],
                    "matched_lex_terms": row["matched_lex_terms"],
                }
            ),
        )
        for row in rows
    ]
    await conn.executemany(INSERT_SQL, payload)
    return len(payload)


async def count_signals_in_window(conn: asyncpg.Connection, window_hours: int) -> int:
    return await conn.fetchval(
        "SELECT COUNT(*) FROM signals_v2 "
        "WHERE timestamp > NOW() - ($1 || ' hours')::interval "
        "AND themes IS NOT NULL AND array_length(themes, 1) > 0",
        str(window_hours),
    )


async def run(args: argparse.Namespace) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    LOGGER.info(
        "classify_topics start window=%sh batch=%s dry_run=%s",
        args.window_hours,
        args.batch_size,
        args.dry_run,
    )

    conn = await asyncpg.connect(database_url)
    try:
        total = await count_signals_in_window(conn, args.window_hours)
        LOGGER.info("candidate signals in window: %d", total)

        offset = 0
        total_assignments = 0
        topic_counts: dict[str, int] = {}

        while offset < total:
            rows = await fetch_batch(conn, args.window_hours, args.batch_size, offset)
            if not rows:
                break

            batch_rows = [dict(r) for r in rows]
            for r in batch_rows:
                topic_counts[r["slug"]] = topic_counts.get(r["slug"], 0) + 1

            if args.dry_run:
                LOGGER.info(
                    "[dry-run] offset=%d batch=%d would-insert=%d",
                    offset,
                    args.batch_size,
                    len(batch_rows),
                )
            else:
                inserted = await insert_rows(conn, batch_rows)
                total_assignments += inserted
                LOGGER.info(
                    "offset=%d batch=%d inserted=%d total=%d",
                    offset,
                    args.batch_size,
                    inserted,
                    total_assignments,
                )

            offset += args.batch_size
            if args.max_batches and (offset // args.batch_size) >= args.max_batches:
                LOGGER.info("max_batches reached, stopping early")
                break

        LOGGER.info("done total_assignments=%d", total_assignments)
        LOGGER.info("per_topic_counts:")
        for slug, n in sorted(topic_counts.items(), key=lambda kv: -kv[1]):
            LOGGER.info("  %s: %d", slug, n)

    finally:
        await conn.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Classify recent signals to atlas_topics")
    parser.add_argument("--window-hours", type=int, default=24,
                        help="Look-back window for signals (default 24).")
    parser.add_argument("--batch-size", type=int, default=5000,
                        help="Signals per batch (default 5000).")
    parser.add_argument("--max-batches", type=int, default=0,
                        help="Cap number of batches (0 = no cap).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute and report, do not insert.")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
