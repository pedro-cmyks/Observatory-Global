#!/usr/bin/env python3
"""Audit atlas topic quality from live signal_topic_assignments.

This script is intentionally read-only. It produces a JSON artifact with:
- per-topic volume/confidence/lex/source/geo metrics;
- deterministic evidence samples per topic;
- coarse risk flags that make manual Path C review repeatable.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg


MODEL_VERSION = "theme-hint-lex-v2"


METRICS_SQL = """
WITH scoped AS (
    SELECT
        at.slug,
        at.label,
        at.parent_domain,
        sta.confidence,
        sta.evidence,
        s.id AS signal_id,
        s.headline,
        s.source_name,
        s.country_code,
        s.timestamp,
        s.persons
    FROM signal_topic_assignments sta
    JOIN atlas_topics at ON at.id = sta.topic_id
    JOIN signals_v2 s ON s.id = sta.signal_id
    WHERE sta.model_version = $1
      AND sta.assigned_at >= NOW() - ($2::int * INTERVAL '1 hour')
      AND at.is_active = TRUE
),
topic_metrics AS (
    SELECT
        slug,
        label,
        parent_domain,
        COUNT(*)::int AS assignments,
        COUNT(DISTINCT signal_id)::int AS distinct_signals,
        AVG(confidence)::float AS avg_confidence,
        COUNT(*) FILTER (
            WHERE COALESCE((evidence->>'lex_count')::int, 0) > 0
        )::int AS lex_assignments,
        COUNT(*) FILTER (
            WHERE COALESCE((evidence->>'lex_count')::int, 0) = 0
              AND COALESCE((evidence->>'theme_hits')::int, 0) > 0
        )::int AS theme_only_assignments,
        COUNT(DISTINCT NULLIF(source_name, ''))::int AS source_count,
        COUNT(DISTINCT NULLIF(country_code, ''))::int AS country_count,
        COUNT(*) FILTER (WHERE country_code IS NULL OR country_code = '' OR country_code = 'RB')::int
            AS unresolved_geo_count,
        COUNT(*) FILTER (WHERE persons IS NOT NULL AND array_length(persons, 1) > 0)::int
            AS rows_with_entities,
        (
            COUNT(*) FILTER (WHERE timestamp >= NOW() - INTERVAL '10 hours')
            - COUNT(*) FILTER (
                WHERE timestamp < NOW() - INTERVAL '10 hours'
                  AND timestamp >= NOW() - INTERVAL '20 hours'
            )
        )::int AS changed_10h
    FROM scoped
    GROUP BY slug, label, parent_domain
),
source_ranked AS (
    SELECT
        slug,
        source_name,
        COUNT(*)::int AS cnt,
        ROW_NUMBER() OVER (PARTITION BY slug ORDER BY COUNT(*) DESC, source_name) AS rn
    FROM scoped
    WHERE source_name IS NOT NULL AND source_name <> ''
    GROUP BY slug, source_name
),
country_ranked AS (
    SELECT
        slug,
        country_code,
        COUNT(*)::int AS cnt,
        ROW_NUMBER() OVER (PARTITION BY slug ORDER BY COUNT(*) DESC, country_code) AS rn
    FROM scoped
    WHERE country_code IS NOT NULL AND country_code <> ''
    GROUP BY slug, country_code
),
term_base AS (
    SELECT
        slug,
        jsonb_array_elements_text(COALESCE(evidence->'matched_terms', '[]'::jsonb)) AS term
    FROM scoped
),
term_ranked AS (
    SELECT
        slug,
        term,
        COUNT(*)::int AS cnt,
        ROW_NUMBER() OVER (PARTITION BY slug ORDER BY COUNT(*) DESC, term) AS rn
    FROM term_base
    WHERE term IS NOT NULL AND term <> ''
    GROUP BY slug, term
)
SELECT
    tm.*,
    COALESCE(
        jsonb_agg(DISTINCT jsonb_build_object('source', sr.source_name, 'count', sr.cnt))
            FILTER (WHERE sr.rn <= 5),
        '[]'::jsonb
    ) AS top_sources,
    COALESCE(
        jsonb_agg(DISTINCT jsonb_build_object('country', cr.country_code, 'count', cr.cnt))
            FILTER (WHERE cr.rn <= 5),
        '[]'::jsonb
    ) AS top_countries,
    COALESCE(
        jsonb_agg(DISTINCT jsonb_build_object('term', tr.term, 'count', tr.cnt))
            FILTER (WHERE tr.rn <= 8),
        '[]'::jsonb
    ) AS top_terms
FROM topic_metrics tm
LEFT JOIN source_ranked sr ON sr.slug = tm.slug AND sr.rn <= 5
LEFT JOIN country_ranked cr ON cr.slug = tm.slug AND cr.rn <= 5
LEFT JOIN term_ranked tr ON tr.slug = tm.slug AND tr.rn <= 8
GROUP BY
    tm.slug,
    tm.label,
    tm.parent_domain,
    tm.assignments,
    tm.distinct_signals,
    tm.avg_confidence,
    tm.lex_assignments,
    tm.theme_only_assignments,
    tm.source_count,
    tm.country_count,
    tm.unresolved_geo_count,
    tm.rows_with_entities,
    tm.changed_10h
ORDER BY tm.assignments DESC, tm.slug;
"""


SAMPLES_SQL = """
WITH scoped AS (
    SELECT
        at.slug,
        sta.confidence,
        sta.evidence,
        s.id AS signal_id,
        s.headline,
        s.source_name,
        s.country_code,
        s.timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY at.slug
            ORDER BY
                COALESCE((sta.evidence->>'lex_count')::int, 0) DESC,
                sta.confidence DESC,
                md5(s.id::text)
        ) AS evidence_rank,
        ROW_NUMBER() OVER (
            PARTITION BY at.slug
            ORDER BY md5(s.id::text)
        ) AS sample_rank
    FROM signal_topic_assignments sta
    JOIN atlas_topics at ON at.id = sta.topic_id
    JOIN signals_v2 s ON s.id = sta.signal_id
    WHERE sta.model_version = $1
      AND sta.assigned_at >= NOW() - ($2::int * INTERVAL '1 hour')
      AND at.is_active = TRUE
)
SELECT
    slug,
    confidence,
    COALESCE((evidence->>'lex_count')::int, 0)::int AS lex_count,
    COALESCE((evidence->>'theme_hits')::int, 0)::int AS theme_hits,
    COALESCE(evidence->'matched_terms', '[]'::jsonb) AS matched_terms,
    signal_id,
    headline,
    source_name,
    country_code,
    timestamp
FROM scoped
WHERE evidence_rank <= $3 OR sample_rank <= $4
ORDER BY slug, evidence_rank, sample_rank;
"""


@dataclass
class TopicQuality:
    slug: str
    label: str
    parent_domain: str | None
    assignments: int
    avg_confidence: float
    lex_pct: float
    theme_only_pct: float
    source_count: int
    country_count: int
    changed_10h: int
    preliminary_quality: str
    risk_flags: list[str]
    top_sources: list[dict[str, Any]]
    top_countries: list[dict[str, Any]]
    top_terms: list[dict[str, Any]]
    samples: list[dict[str, Any]]


def _as_json(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _preliminary_quality(
    *,
    assignments: int,
    avg_confidence: float,
    lex_pct: float,
    source_count: int,
    country_count: int,
    unresolved_geo_pct: float,
) -> tuple[str, list[str]]:
    flags: list[str] = []
    if assignments < 25:
        flags.append("thin_volume")
    if lex_pct < 0.1 and assignments >= 100:
        flags.append("theme_heavy")
    if avg_confidence < 0.65:
        flags.append("low_confidence")
    if source_count <= 3 and assignments >= 25:
        flags.append("source_concentration")
    if country_count <= 1 and assignments >= 100:
        flags.append("geo_concentration")
    if unresolved_geo_pct >= 0.05:
        flags.append("unresolved_geo")

    if "theme_heavy" in flags or "low_confidence" in flags:
        quality = "review"
    elif "thin_volume" in flags or "source_concentration" in flags:
        quality = "thin"
    elif assignments >= 50 and lex_pct >= 0.3 and source_count >= 5:
        quality = "promising"
    else:
        quality = "monitor"
    return quality, flags


async def run(args: argparse.Namespace) -> dict[str, Any]:
    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    conn = await asyncpg.connect(db_url)
    try:
        metric_rows = await conn.fetch(METRICS_SQL, MODEL_VERSION, args.hours)
        sample_rows = await conn.fetch(
            SAMPLES_SQL,
            MODEL_VERSION,
            args.hours,
            args.evidence_samples,
            args.random_samples,
        )
    finally:
        await conn.close()

    samples_by_slug: dict[str, list[dict[str, Any]]] = {}
    for row in sample_rows:
        samples_by_slug.setdefault(row["slug"], []).append(
            {
                "headline": row["headline"],
                "source": row["source_name"],
                "country": row["country_code"],
                "confidence": round(float(row["confidence"] or 0), 3),
                "lex_count": int(row["lex_count"] or 0),
                "theme_hits": int(row["theme_hits"] or 0),
                "matched_terms": _as_json(row["matched_terms"]),
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
            }
        )

    topics: list[TopicQuality] = []
    for row in metric_rows:
        assignments = int(row["assignments"] or 0)
        avg_confidence = float(row["avg_confidence"] or 0)
        lex_count = int(row["lex_assignments"] or 0)
        theme_count = int(row["theme_only_assignments"] or 0)
        unresolved_geo_count = int(row["unresolved_geo_count"] or 0)
        lex_pct = lex_count / assignments if assignments else 0.0
        theme_only_pct = theme_count / assignments if assignments else 0.0
        unresolved_geo_pct = unresolved_geo_count / assignments if assignments else 0.0
        quality, flags = _preliminary_quality(
            assignments=assignments,
            avg_confidence=avg_confidence,
            lex_pct=lex_pct,
            source_count=int(row["source_count"] or 0),
            country_count=int(row["country_count"] or 0),
            unresolved_geo_pct=unresolved_geo_pct,
        )
        topics.append(
            TopicQuality(
                slug=row["slug"],
                label=row["label"],
                parent_domain=row["parent_domain"],
                assignments=assignments,
                avg_confidence=round(avg_confidence, 4),
                lex_pct=round(lex_pct, 4),
                theme_only_pct=round(theme_only_pct, 4),
                source_count=int(row["source_count"] or 0),
                country_count=int(row["country_count"] or 0),
                changed_10h=int(row["changed_10h"] or 0),
                preliminary_quality=quality,
                risk_flags=flags,
                top_sources=_as_json(row["top_sources"]),
                top_countries=_as_json(row["top_countries"]),
                top_terms=_as_json(row["top_terms"]),
                samples=samples_by_slug.get(row["slug"], []),
            )
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": MODEL_VERSION,
        "hours": args.hours,
        "topic_count": len(topics),
        "topics": [asdict(topic) for topic in topics],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit atlas topic assignment quality.")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--evidence-samples", type=int, default=6)
    parser.add_argument("--random-samples", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = asyncio.run(run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {args.output} ({payload['topic_count']} topics)")


if __name__ == "__main__":
    main()
