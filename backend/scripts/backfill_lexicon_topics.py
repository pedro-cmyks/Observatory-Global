"""Bulk SQL lexicon classifier for atlas_topic assignments (Issue #171).

This is the v2 sibling of `classify_topics.py`. It uses a single-statement
bulk INSERT … SELECT against `signals_v2` + `atlas_topics` instead of the
batched per-window Python loop. Designed to:

  1. Lift recall vs `classify_topics.py` (which required either a lexicon
     hit OR ≥3 GDELT theme hints — measured ~0.8% of 24h volume after the
     mig 031 hint realignment). v2 accepts a single theme hint as evidence
     when the topic's lexicon set is poorly populated for that language.
  2. Stay precision-bounded by ranking on a calibrated formula plus a
     min_confidence floor higher than v1.
  3. Coexist with v1 in `signal_topic_assignments`: v2 writes
     `method='lexicon'`, `model_version='theme-hint-lex-v2'`. The PK
     `(signal_id, topic_id, method, model_version)` keeps v1 and v2 rows
     independent so we can A/B compare before retiring v1.
  4. Be idempotent: ON CONFLICT (signal_id, topic_id, method, model_version)
     DO UPDATE refreshes confidence + evidence + assigned_at without
     duplicating rows.

Confidence formula (v2)
-----------------------

A signal qualifies for a topic when at least one piece of evidence is
present:
  - lex_count   = number of distinct lexicon_terms substring-matching
                  lower(headline)
  - theme_hits  = cardinality(themes ∩ gdelt_theme_hints)
  qualified    := lex_count >= 1 OR theme_hits >= 1

The score is

    base         = 0.55
    lex_bonus    = 0.10 * LEAST(lex_count, 3)        -- cap +0.30
    theme_bonus  = 0.05 * LEAST(theme_hits, 4)       -- cap +0.20
    both_bonus   = 0.05 if (lex_count > 0 AND theme_hits >= 2) else 0
    confidence   = LEAST(0.95, base + lex_bonus + theme_bonus + both_bonus)

Examples:
  1 lex term, 0 theme hits → 0.65
  0 lex, 1 theme hit       → 0.60
  0 lex, 3 theme hits      → 0.70
  2 lex, 2 themes          → 0.55 + 0.20 + 0.10 + 0.05 = 0.90
  4 lex, 4 themes          → 0.55 + 0.30 + 0.20 + 0.05 = 1.10 → cap 0.95

A `MIN_CONFIDENCE` floor (default 0.55) is applied, then top-2 topics per
signal are kept (same as v1).

Evidence column captures `matched_terms`, `theme_overlap`, and the
component scores for transparency.

CLI
---

Smoke last hour, no insert::

    python -m backend.scripts.backfill_lexicon_topics --window-hours 1 --dry-run

Backfill last 24h::

    python -m backend.scripts.backfill_lexicon_topics --window-hours 24

Incremental every 15 min from worker cron::

    python -m backend.scripts.backfill_lexicon_topics --window-hours 0.5

"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from typing import Any

import asyncpg


LOGGER = logging.getLogger("backfill_lexicon_topics")

METHOD = "lexicon"
MODEL_NAME = "atlas-topic-hint-lex"
MODEL_VERSION = "theme-hint-lex-v2"

# Same min_confidence floor across CLI default and inline SQL filter.
DEFAULT_MIN_CONFIDENCE = 0.55
TOP_N_PER_SIGNAL = 2
DEFAULT_MIN_HEADLINE_LEN = 20

# Statement timeout in milliseconds. Backfilling 24h of signals_v2 against
# 30 active topics is bounded by the trigram GIN on lower(headline) plus
# the GIN on signals_v2.themes, both shipped in mig 022. On the live
# 259k hot rows this stays under a minute end-to-end; bump if larger
# windows are needed.
STATEMENT_TIMEOUT_MS = 600_000  # 10 minutes


CLASSIFY_AND_INSERT_SQL = """
WITH window_signals AS (
    SELECT id, themes, headline
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::interval
      AND headline IS NOT NULL
      AND length(headline) >= $2
),
expansions AS (
    SELECT
        s.id                                            AS signal_id,
        t.id                                            AS topic_id,
        t.slug                                          AS slug,
        COALESCE(
            cardinality(
                ARRAY(
                    SELECT unnest(s.themes)
                    INTERSECT
                    SELECT unnest(t.gdelt_theme_hints)
                )
            ),
            0
        )                                                AS theme_hits,
        COALESCE(cardinality(t.gdelt_theme_hints), 0)    AS hint_count,
        ARRAY(
            SELECT lt
            FROM unnest(t.lexicon_terms) lt
            WHERE lower(s.headline) LIKE '%' || lower(lt) || '%'
        )                                                AS matched_lex_terms
    FROM window_signals s
    CROSS JOIN atlas_topics t
    WHERE t.is_active = true
      AND (
            s.themes && t.gdelt_theme_hints
         OR EXISTS (
                SELECT 1
                FROM unnest(t.lexicon_terms) lt
                WHERE lower(s.headline) LIKE '%' || lower(lt) || '%'
            )
      )
),
scored AS (
    SELECT
        signal_id,
        topic_id,
        slug,
        theme_hits,
        hint_count,
        cardinality(matched_lex_terms)                   AS lex_count,
        matched_lex_terms,
        LEAST(
            0.95::double precision,
            (0.55
              + 0.10 * LEAST(cardinality(matched_lex_terms), 3)
              + 0.05 * LEAST(theme_hits, 4)
              + CASE
                    WHEN cardinality(matched_lex_terms) > 0 AND theme_hits >= 2
                    THEN 0.05
                    ELSE 0.0
                END
            )::double precision
        )                                                AS confidence
    FROM expansions
    WHERE cardinality(matched_lex_terms) >= 1
       OR theme_hits >= 1
),
ranked AS (
    SELECT
        signal_id, topic_id, slug, theme_hits, hint_count,
        lex_count, matched_lex_terms, confidence,
        ROW_NUMBER() OVER (
            PARTITION BY signal_id
            ORDER BY confidence DESC, theme_hits DESC, lex_count DESC, topic_id
        ) AS rnk
    FROM scored
    WHERE confidence >= $3
)
INSERT INTO signal_topic_assignments
    (signal_id, topic_id, method, confidence, model_name, model_version,
     evidence, assigned_at)
SELECT
    signal_id,
    topic_id,
    $4,
    confidence,
    $5,
    $6,
    jsonb_build_object(
        'theme_hits',         theme_hits,
        'hint_count',         hint_count,
        'lex_count',          lex_count,
        'matched_terms',      to_jsonb(matched_lex_terms),
        'formula',            'theme-hint-lex-v2',
        'base',               0.55,
        'lex_component',      0.10 * LEAST(lex_count, 3),
        'theme_component',    0.05 * LEAST(theme_hits, 4),
        'cross_component',    CASE
                                  WHEN lex_count > 0 AND theme_hits >= 2
                                  THEN 0.05 ELSE 0
                              END
    ),
    NOW()
FROM ranked
WHERE rnk <= $7
ON CONFLICT (signal_id, topic_id, method, model_version)
DO UPDATE SET
    confidence = EXCLUDED.confidence,
    evidence   = EXCLUDED.evidence,
    assigned_at = NOW()
RETURNING signal_id, topic_id, confidence
"""


DRY_RUN_SQL = """
WITH window_signals AS (
    SELECT id, themes, headline
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::interval
      AND headline IS NOT NULL
      AND length(headline) >= $2
),
expansions AS (
    SELECT
        s.id AS signal_id,
        t.id AS topic_id,
        t.slug,
        COALESCE(
            cardinality(
                ARRAY(
                    SELECT unnest(s.themes)
                    INTERSECT
                    SELECT unnest(t.gdelt_theme_hints)
                )
            ),
            0
        ) AS theme_hits,
        ARRAY(
            SELECT lt
            FROM unnest(t.lexicon_terms) lt
            WHERE lower(s.headline) LIKE '%' || lower(lt) || '%'
        ) AS matched_lex_terms
    FROM window_signals s
    CROSS JOIN atlas_topics t
    WHERE t.is_active = true
      AND (
            s.themes && t.gdelt_theme_hints
         OR EXISTS (
                SELECT 1
                FROM unnest(t.lexicon_terms) lt
                WHERE lower(s.headline) LIKE '%' || lower(lt) || '%'
            )
      )
),
scored AS (
    SELECT
        signal_id,
        slug,
        theme_hits,
        cardinality(matched_lex_terms) AS lex_count,
        LEAST(
            0.95::double precision,
            (0.55
              + 0.10 * LEAST(cardinality(matched_lex_terms), 3)
              + 0.05 * LEAST(theme_hits, 4)
              + CASE
                    WHEN cardinality(matched_lex_terms) > 0 AND theme_hits >= 2
                    THEN 0.05
                    ELSE 0.0
                END
            )::double precision
        ) AS confidence
    FROM expansions
    WHERE cardinality(matched_lex_terms) >= 1
       OR theme_hits >= 1
),
ranked AS (
    SELECT
        signal_id, slug, theme_hits, lex_count, confidence,
        ROW_NUMBER() OVER (
            PARTITION BY signal_id
            ORDER BY confidence DESC, theme_hits DESC, lex_count DESC
        ) AS rnk
    FROM scored
    WHERE confidence >= $3
)
SELECT
    slug,
    COUNT(*)::bigint                            AS assignments,
    COUNT(DISTINCT signal_id)::bigint           AS distinct_signals,
    ROUND(AVG(confidence)::numeric, 3)          AS avg_confidence,
    ROUND(MIN(confidence)::numeric, 3)          AS min_confidence,
    ROUND(MAX(confidence)::numeric, 3)          AS max_confidence,
    COUNT(*) FILTER (WHERE confidence >= 0.75)::bigint AS high_conf,
    COUNT(*) FILTER (WHERE lex_count >= 1)::bigint     AS lex_supported,
    COUNT(*) FILTER (WHERE theme_hits >= 1)::bigint    AS theme_supported
FROM ranked
WHERE rnk <= $4
GROUP BY slug
ORDER BY assignments DESC
"""


COVERAGE_SQL = """
WITH window_signals AS (
    SELECT id
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::interval
      AND headline IS NOT NULL
      AND length(headline) >= $2
)
SELECT
    COUNT(*)::bigint AS candidate_signals
FROM window_signals
"""


async def run_dry(
    conn: asyncpg.Connection,
    window_hours: float,
    min_headline_len: int,
    min_confidence: float,
    top_n: int,
) -> dict[str, Any]:
    per_topic = await conn.fetch(
        DRY_RUN_SQL,
        str(window_hours),
        min_headline_len,
        min_confidence,
        top_n,
    )
    coverage = await conn.fetchrow(
        COVERAGE_SQL, str(window_hours), min_headline_len
    )
    total_assignments = sum(int(r["assignments"]) for r in per_topic)
    distinct_signals = (
        sum(int(r["distinct_signals"]) for r in per_topic) if per_topic else 0
    )
    return {
        "candidate_signals": int(coverage["candidate_signals"]) if coverage else 0,
        "total_assignments": total_assignments,
        "distinct_signals_assigned_upper_bound": distinct_signals,
        "topics_fired": len(per_topic),
        "per_topic": [
            {
                "slug": r["slug"],
                "assignments": int(r["assignments"]),
                "distinct_signals": int(r["distinct_signals"]),
                "avg_confidence": float(r["avg_confidence"]),
                "min_confidence": float(r["min_confidence"]),
                "max_confidence": float(r["max_confidence"]),
                "high_confidence_assignments": int(r["high_conf"]),
                "lex_supported_assignments": int(r["lex_supported"]),
                "theme_supported_assignments": int(r["theme_supported"]),
            }
            for r in per_topic
        ],
    }


async def run_insert(
    conn: asyncpg.Connection,
    window_hours: float,
    min_headline_len: int,
    min_confidence: float,
    top_n: int,
) -> dict[str, Any]:
    rows = await conn.fetch(
        CLASSIFY_AND_INSERT_SQL,
        str(window_hours),
        min_headline_len,
        min_confidence,
        METHOD,
        MODEL_NAME,
        MODEL_VERSION,
        top_n,
    )
    confidences = [float(r["confidence"]) for r in rows]
    return {
        "assignments_upserted": len(rows),
        "distinct_signals": len({r["signal_id"] for r in rows}),
        "distinct_topics": len({r["topic_id"] for r in rows}),
        "avg_confidence": round(sum(confidences) / len(confidences), 4)
        if confidences
        else 0.0,
        "high_confidence_count": sum(1 for c in confidences if c >= 0.75),
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    database_url = (
        args.database_url
        or os.environ.get("DATABASE_URL")
        or os.environ.get("SUPABASE_DB_URL")
    )
    if not database_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL required")

    LOGGER.info(
        "backfill_lexicon_topics start window=%sh min_conf=%.2f min_len=%d top_n=%d dry_run=%s",
        args.window_hours,
        args.min_confidence,
        args.min_headline_len,
        args.top_n,
        args.dry_run,
    )

    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")
        if args.dry_run:
            result = await run_dry(
                conn,
                args.window_hours,
                args.min_headline_len,
                args.min_confidence,
                args.top_n,
            )
        else:
            result = await run_insert(
                conn,
                args.window_hours,
                args.min_headline_len,
                args.min_confidence,
                args.top_n,
            )
    finally:
        await conn.close()

    result["method"] = METHOD
    result["model_name"] = MODEL_NAME
    result["model_version"] = MODEL_VERSION
    result["window_hours"] = args.window_hours
    result["min_confidence"] = args.min_confidence
    result["min_headline_len"] = args.min_headline_len
    result["top_n_per_signal"] = args.top_n
    result["dry_run"] = bool(args.dry_run)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bulk SQL lexicon classifier (Issue #171). Writes "
            "method='lexicon' model_version='theme-hint-lex-v2' to "
            "signal_topic_assignments."
        )
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL / SUPABASE_DB_URL.",
    )
    parser.add_argument(
        "--window-hours",
        type=float,
        default=24.0,
        help="Look-back window for signals_v2 (default 24h).",
    )
    parser.add_argument(
        "--min-headline-len",
        type=int,
        default=DEFAULT_MIN_HEADLINE_LEN,
        help="Skip signals with headlines shorter than this (default 20 chars).",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
        help="Floor on the v2 confidence score (default 0.55).",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=TOP_N_PER_SIGNAL,
        help="Keep top-N topics per signal (default 2).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and report per-topic distribution, do not insert.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = _parse_args()
    report = asyncio.run(run(args))
    print(json.dumps(report, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
