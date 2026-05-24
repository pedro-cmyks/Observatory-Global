from __future__ import annotations

import logging
from typing import Any

from app import db

logger = logging.getLogger(__name__)

THREAD_MODEL_VERSION = "theme-hint-lex-v2"

THREADS_SQL = """
WITH scoped AS (
    SELECT
        sta.signal_id,
        sta.topic_id,
        sta.confidence,
        at.slug AS topic_slug,
        at.label AS topic_label,
        at.parent_domain AS parent_domain,
        s.country_code,
        COALESCE(c.name, s.country_code) AS country_name,
        s.source_name,
        s.timestamp,
        s.nlp_sentiment,
        s.persons
    FROM signal_topic_assignments sta
    JOIN atlas_topics at ON at.id = sta.topic_id
    JOIN signals_v2 s ON s.id = sta.signal_id
    LEFT JOIN countries_v2 c ON c.code = s.country_code
    WHERE sta.model_version = 'theme-hint-lex-v2'
      AND sta.assigned_at >= NOW() - ($1::int * INTERVAL '1 hour')
      AND ($3::text IS NULL OR at.slug = $3::text)
      AND ($4::text[] IS NULL OR s.country_code = ANY($4::text[]))
),
topic_agg AS (
    -- Performance: signal_topic_assignments PK is
    -- (signal_id, topic_id, method, model_version) so COUNT(*) equals
    -- COUNT(DISTINCT signal_id) within a (topic_slug, model_version) group.
    -- Switching to COUNT(*) drops the topic_agg GroupAggregate sort that
    -- pushed the enriched query from ~50 ms to 845 ms on 24k rows.
    SELECT
        topic_slug,
        topic_label,
        parent_domain,
        COUNT(*)::int AS signal_count,
        COUNT(DISTINCT NULLIF(source_name, ''))::int AS source_count,
        COUNT(DISTINCT NULLIF(country_code, ''))::int AS country_count,
        AVG(confidence)::float AS avg_confidence,
        MIN(timestamp) AS first_seen,
        (
            COUNT(*) FILTER (WHERE timestamp >= NOW() - INTERVAL '10 hours')
            - COUNT(*) FILTER (
                WHERE timestamp < NOW() - INTERVAL '10 hours'
                  AND timestamp >= NOW() - INTERVAL '20 hours'
            )
        )::int AS changed_10h,
        (
            AVG(nlp_sentiment) FILTER (WHERE timestamp >= NOW() - INTERVAL '10 hours')
            - AVG(nlp_sentiment) FILTER (
                WHERE timestamp < NOW() - INTERVAL '10 hours'
                  AND timestamp >= NOW() - INTERVAL '20 hours'
            )
        )::float AS sentiment_swing_10h
    FROM scoped
    GROUP BY topic_slug, topic_label, parent_domain
),
entity_base AS (
    SELECT
        topic_slug,
        unnest(persons) AS person
    FROM scoped
    WHERE persons IS NOT NULL
),
entity_ranked AS (
    SELECT
        topic_slug,
        person,
        COUNT(*) AS cnt,
        ROW_NUMBER() OVER (PARTITION BY topic_slug ORDER BY COUNT(*) DESC, person) AS rn
    FROM entity_base
    WHERE person IS NOT NULL AND person <> ''
    GROUP BY topic_slug, person
),
entity_lists AS (
    SELECT
        topic_slug,
        ARRAY_AGG(person ORDER BY cnt DESC, person) FILTER (WHERE rn <= 5) AS top_entities
    FROM entity_ranked
    GROUP BY topic_slug
),
timeline_base AS (
    SELECT
        topic_slug,
        date_trunc('hour', timestamp) AS hour,
        COUNT(*) AS cnt
    FROM scoped
    GROUP BY topic_slug, date_trunc('hour', timestamp)
),
timeline AS (
    SELECT
        topic_slug,
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'hour', TO_CHAR(hour, 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                'count', cnt
            )
            ORDER BY hour
        ) AS hourly_timeline
    FROM timeline_base
    GROUP BY topic_slug
),
country_ranked AS (
    SELECT
        topic_slug,
        country_code,
        country_name,
        COUNT(*) AS cnt,
        ROW_NUMBER() OVER (PARTITION BY topic_slug ORDER BY COUNT(*) DESC, country_code) AS rn
    FROM scoped
    WHERE country_code IS NOT NULL
    GROUP BY topic_slug, country_code, country_name
),
country_lists AS (
    SELECT
        topic_slug,
        ARRAY_AGG(country_code ORDER BY cnt DESC, country_code) FILTER (WHERE rn <= 3)
            AS top_countries,
        ARRAY_AGG(country_name ORDER BY cnt DESC, country_code) FILTER (WHERE rn <= 3)
            AS top_country_names
    FROM country_ranked
    GROUP BY topic_slug
),
source_ranked AS (
    SELECT
        topic_slug,
        source_name,
        COUNT(*) AS cnt,
        ROW_NUMBER() OVER (PARTITION BY topic_slug ORDER BY COUNT(*) DESC, source_name) AS rn
    FROM scoped
    WHERE source_name IS NOT NULL AND source_name <> ''
    GROUP BY topic_slug, source_name
),
source_lists AS (
    SELECT
        topic_slug,
        ARRAY_AGG(source_name ORDER BY cnt DESC, source_name) FILTER (WHERE rn <= 5)
            AS top_sources
    FROM source_ranked
    GROUP BY topic_slug
),
related_counts AS (
    SELECT
        scoped.topic_slug,
        sta2.topic_id,
        COUNT(DISTINCT scoped.signal_id)::int AS co_signals
    FROM scoped
    JOIN signal_topic_assignments sta2
      ON sta2.signal_id = scoped.signal_id
     AND sta2.model_version = 'theme-hint-lex-v2'
     AND sta2.topic_id <> scoped.topic_id
    GROUP BY scoped.topic_slug, sta2.topic_id
),
related_ranked AS (
    SELECT
        topic_slug,
        topic_id,
        co_signals,
        ROW_NUMBER() OVER (
            PARTITION BY topic_slug
            ORDER BY co_signals DESC, topic_id
        ) AS rn
    FROM related_counts
),
related AS (
    SELECT
        rr.topic_slug,
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'topic', at2.slug,
                'label', at2.label,
                'co_signals', rr.co_signals
            )
            ORDER BY rr.co_signals DESC, at2.slug
        ) FILTER (WHERE rr.rn <= 5) AS related_topics
    FROM related_ranked rr
    JOIN atlas_topics at2 ON at2.id = rr.topic_id
    GROUP BY rr.topic_slug
)
SELECT
    ta.topic_slug,
    ta.topic_label,
    ta.parent_domain,
    ta.signal_count,
    ta.source_count,
    ta.country_count,
    ta.avg_confidence,
    ta.first_seen,
    ta.changed_10h,
    ta.sentiment_swing_10h,
    COALESCE(cl.top_countries, ARRAY[]::text[]) AS top_countries,
    COALESCE(cl.top_country_names, ARRAY[]::text[]) AS top_country_names,
    COALESCE(sl.top_sources, ARRAY[]::text[]) AS top_sources,
    COALESCE(el.top_entities, ARRAY[]::text[]) AS top_entities,
    COALESCE(tlh.hourly_timeline, '[]'::jsonb) AS hourly_timeline,
    COALESCE(r.related_topics, '[]'::jsonb) AS related_topics
FROM topic_agg ta
LEFT JOIN country_lists cl ON cl.topic_slug = ta.topic_slug
LEFT JOIN source_lists sl ON sl.topic_slug = ta.topic_slug
LEFT JOIN entity_lists el ON el.topic_slug = ta.topic_slug
LEFT JOIN timeline tlh ON tlh.topic_slug = ta.topic_slug
LEFT JOIN related r ON r.topic_slug = ta.topic_slug
ORDER BY ta.changed_10h DESC, ta.signal_count DESC
LIMIT $2
"""

THREAD_EVIDENCE_SQL = """
SELECT
    id,
    headline,
    source_name,
    source_url,
    country_code,
    country_name,
    timestamp,
    nlp_sentiment,
    confidence,
    syndication_count
FROM (
    SELECT DISTINCT ON (LOWER(s.headline))
        s.id,
        s.headline,
        s.source_name,
        s.source_url,
        s.country_code,
        COALESCE(c.name, s.country_code) AS country_name,
        s.timestamp,
        s.nlp_sentiment,
        sta.confidence,
        COUNT(*) OVER (PARTITION BY LOWER(s.headline))::int AS syndication_count
    FROM signal_topic_assignments sta
    JOIN atlas_topics at ON at.id = sta.topic_id
    JOIN signals_v2 s ON s.id = sta.signal_id
    LEFT JOIN countries_v2 c ON c.code = s.country_code
    WHERE sta.model_version = 'theme-hint-lex-v2'
      AND sta.assigned_at >= NOW() - ($1::int * INTERVAL '1 hour')
      AND at.slug = $2::text
      AND ($3::text[] IS NULL OR s.country_code = ANY($3::text[]))
    ORDER BY LOWER(s.headline), sta.confidence DESC, s.timestamp DESC
) deduped
ORDER BY confidence DESC, timestamp DESC
LIMIT $4
"""


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return list(value) if not isinstance(value, str) else [value]


def _record_get(row: Any, key: str, default: Any = None) -> Any:
    try:
        return row[key]
    except (KeyError, TypeError):
        return default


def confidence_band(
    *,
    evidence_count: int,
    source_count: int,
    geo_count: int,
    assignment_confidence: float,
) -> str:
    if assignment_confidence < 0.5 or source_count <= 1:
        return "degraded"
    if (
        evidence_count >= 50
        and source_count >= 6
        and geo_count >= 2
        and assignment_confidence >= 0.75
    ):
        return "high"
    if evidence_count >= 10 and source_count >= 3 and assignment_confidence >= 0.6:
        return "medium"
    return "thin"


def build_thread_id(anchor_slug: str, country_codes: list[str]) -> str:
    suffix = "-".join(code.lower() for code in country_codes[:3] if code)
    return f"{anchor_slug}--{suffix}" if suffix else anchor_slug


def parse_thread_id(thread_id: str) -> tuple[str, list[str]]:
    if "--" not in thread_id:
        return thread_id, []
    anchor_slug, country_part = thread_id.split("--", 1)
    country_codes = [part.upper() for part in country_part.split("-") if part]
    return anchor_slug, country_codes


def build_thread_label(*, anchor_label: str, top_countries: list[str], changed_10h: int) -> str:
    if len(top_countries) >= 2:
        place = f"{top_countries[0]} and {top_countries[1]}"
    elif top_countries:
        place = top_countries[0]
    else:
        place = "multiple regions"

    verb = "intensifies" if changed_10h > 0 else "continues"
    return f"{anchor_label} {verb} in {place}"


def _why_now(changed_10h: int, country_names: list[str]) -> str:
    place = " and ".join(country_names[:2]) if country_names else "multiple regions"
    if changed_10h > 0:
        return f"{changed_10h} more signals in the last 10h, concentrated in {place}."
    if changed_10h < 0:
        return f"{abs(changed_10h)} fewer signals in the last 10h, still concentrated in {place}."
    return f"Signal volume is steady in the last 10h, concentrated in {place}."


def _trend_label(changed_10h: int, signal_count: int) -> str:
    """Map 10h volume delta to a coarse trend pill so cards stay readable.

    Threshold is relative to total signal_count so a +50 swing reads as
    'surging' on a 200-signal topic but as 'stable' on a 20,000-signal one.
    """
    if signal_count <= 0:
        return "stable"
    ratio = changed_10h / signal_count
    if ratio >= 0.05:
        return "surging"
    if ratio <= -0.05:
        return "fading"
    return "stable"


def assemble_thread(
    row: Any,
    *,
    evidence_samples: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    topic_slug = str(_record_get(row, "topic_slug"))
    topic_label = str(_record_get(row, "topic_label"))
    parent_domain = _record_get(row, "parent_domain")
    country_codes = [str(code) for code in _as_list(_record_get(row, "top_countries"))]
    country_names = [str(name) for name in _as_list(_record_get(row, "top_country_names"))]
    changed_10h = int(_record_get(row, "changed_10h") or 0)
    signal_count = int(_record_get(row, "signal_count") or 0)
    source_count = int(_record_get(row, "source_count") or 0)
    country_count = int(_record_get(row, "country_count") or 0)
    avg_confidence = float(_record_get(row, "avg_confidence") or 0)
    first_seen = _record_get(row, "first_seen")
    top_entities = [str(person) for person in _as_list(_record_get(row, "top_entities"))]
    hourly_timeline = _as_list(_record_get(row, "hourly_timeline"))
    label = build_thread_label(
        anchor_label=topic_label,
        top_countries=country_names,
        changed_10h=changed_10h,
    )

    return {
        "thread_id": build_thread_id(topic_slug, country_codes),
        "label": label,
        "summary": label,
        "anchor_topics": [topic_slug],
        "parent_domain": parent_domain,
        "signal_count": signal_count,
        "source_count": source_count,
        "country_count": country_count,
        "avg_confidence": round(avg_confidence, 3),
        "first_seen": first_seen.isoformat() if hasattr(first_seen, "isoformat") else first_seen,
        "changed_10h": changed_10h,
        "trend": _trend_label(changed_10h, signal_count),
        "sentiment_swing_10h": _record_get(row, "sentiment_swing_10h"),
        "top_countries": country_codes,
        "top_country_names": country_names,
        "top_sources": [str(source) for source in _as_list(_record_get(row, "top_sources"))],
        "top_entities": top_entities,
        "hourly_timeline": hourly_timeline,
        "source_mix": {
            "top_sources": [str(source) for source in _as_list(_record_get(row, "top_sources"))],
            "source_count": source_count,
        },
        "confidence": confidence_band(
            evidence_count=signal_count,
            source_count=source_count,
            geo_count=country_count,
            assignment_confidence=avg_confidence,
        ),
        "why_now": _why_now(changed_10h, country_names),
        "subthreads": [],
        "related_threads": _as_list(_record_get(row, "related_topics")),
        "evidence_samples": evidence_samples or [],
    }


def evidence_role(syndication_count: int) -> str:
    if syndication_count >= 5:
        return "syndicated"
    if syndication_count >= 2:
        return "repeated"
    return "representative"


def _serialize_evidence(row: Any) -> dict[str, Any]:
    timestamp = _record_get(row, "timestamp")
    syndication = int(_record_get(row, "syndication_count") or 1)
    return {
        "id": str(_record_get(row, "id")),
        "headline": _record_get(row, "headline"),
        "source": _record_get(row, "source_name"),
        "url": _record_get(row, "source_url"),
        "country_code": _record_get(row, "country_code"),
        "country_name": _record_get(row, "country_name"),
        "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else timestamp,
        "sentiment": _record_get(row, "nlp_sentiment"),
        "confidence": _record_get(row, "confidence"),
        "syndication_count": syndication,
        "evidence_role": evidence_role(syndication),
    }


async def _fetch_threads_with_conn(
    conn: Any,
    *,
    hours: int,
    limit: int,
    topic_slug: str | None,
    country_codes: list[str] | None,
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        THREADS_SQL,
        hours,
        limit,
        topic_slug,
        country_codes or None,
        timeout=8,
    )
    return [assemble_thread(row) for row in rows]


async def fetch_threads(
    *,
    hours: int = 24,
    limit: int = 10,
    topic_slug: str | None = None,
    country_codes: list[str] | None = None,
    conn: Any = None,
) -> list[dict[str, Any]]:
    if conn is not None:
        return await _fetch_threads_with_conn(
            conn,
            hours=hours,
            limit=limit,
            topic_slug=topic_slug,
            country_codes=country_codes,
        )

    if db.pool is None:
        logger.warning("thread intelligence requested without database pool")
        return []

    async with db.pool.acquire() as own_conn:
        return await _fetch_threads_with_conn(
            own_conn,
            hours=hours,
            limit=limit,
            topic_slug=topic_slug,
            country_codes=country_codes,
        )


async def fetch_thread_detail(
    *,
    thread_id: str,
    hours: int = 24,
) -> dict[str, Any] | None:
    topic_slug, country_codes = parse_thread_id(thread_id)
    threads = await fetch_threads(
        hours=hours,
        limit=1,
        topic_slug=topic_slug,
        country_codes=country_codes or None,
    )
    if not threads:
        return None

    if db.pool is None:
        return threads[0]

    async with db.pool.acquire() as conn:
        evidence_rows = await conn.fetch(
            THREAD_EVIDENCE_SQL,
            hours,
            topic_slug,
            country_codes or None,
            8,
            timeout=8,
        )

    threads[0]["evidence_samples"] = [_serialize_evidence(row) for row in evidence_rows]
    return threads[0]
