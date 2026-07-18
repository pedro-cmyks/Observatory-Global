from __future__ import annotations

import html
import json
import logging
import os
import re
from typing import Any

from app import db
from app.core.gdelt_taxonomy import get_theme_label
from app.core.iso_country_names import ISO_COUNTRY_NAMES, resolve_country_name
from app.services.narrative_note import build_thread_narrative_note
from app.services.subject_geography import infer_receipt_subject_geography
from app.services.thread_packet import build_thread_packet
from app.services.thread_ranking import rank_threads
from app.services.topic_relationship import classify_relationship

logger = logging.getLogger(__name__)

THREAD_MODEL_VERSION = "theme-hint-lex-v2"

# Unified Engine F0.3: the engine_version the read-flag serves from. Only
# 'v1-compat' exists until F3 writes 'unified-v2'.
V1_COMPAT_ENGINE_VERSION = "v1-compat"


class DatabaseBusyError(RuntimeError):
    """A database command timed out inside an Atlas serving boundary."""


def topic_members_engine_version() -> str:
    """F4 read-path parametrization: which engine_version the topic_members
    read paths serve. Default stays 'v1-compat' — the F4 cutover is ONE env
    var (ATLAS_TOPIC_MEMBERS_ENGINE_VERSION=unified-v2) once the A/B + gold
    gate hold, and reverting is the same var back. Only consulted where
    ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS already routes reads through
    topic_members; the legacy signal_topic_assignments path ignores it."""
    v = os.environ.get("ATLAS_TOPIC_MEMBERS_ENGINE_VERSION", "").strip()
    return v or V1_COMPAT_ENGINE_VERSION


def serve_threads_from_topic_members() -> bool:
    """F0.3 read-flag (spec 2026-06-29-atlas-unified-engine §10/§16). When ON,
    the atlas-evidence list path reads the typed `topic_members` table
    (role='evidence') via THREADS_SQL_TOPIC_MEMBERS instead of
    `signal_topic_assignments` via THREADS_SQL. Default OFF — prod keeps the
    current path until the A/B parity gate (`scripts/engine_serving_parity.py`)
    proves the unified read matches. The dynamic-topic list stays sourced from
    `dynamic_topics` aggregates either way (hybrid serving, spec §10)."""
    return os.environ.get(
        "ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS", ""
    ).strip().lower() in {"1", "true", "on", "yes"}

AGGREGATOR_DOMAINS = frozenset(
    {
        "zazoom.it",
        "yahoo.com",
        "msn.com",
        "news.google.com",
        "rediff.com",
        "tvguide.co.uk",
    }
)

THREADS_SQL = """
WITH scoped AS (
    SELECT
        sta.signal_id,
        sta.topic_id,
        sta.evidence,
        sta.confidence,
        sta.gate_kept,
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
        -- #214 gate-kept count: signals that cleared the relevance gate. The
        -- detail panel (themes.py) shows only these; the list must agree.
        COUNT(*) FILTER (WHERE gate_kept)::int AS gated_signal_count,
        COUNT(*) FILTER (WHERE gate_kept IS NOT NULL)::int AS gate_scored_count,
        COUNT(*) FILTER (
            WHERE COALESCE((evidence->>'lex_count')::int, 0) > 0
        )::int AS lex_count,
        COUNT(*) FILTER (
            WHERE COALESCE((evidence->>'lex_count')::int, 0) = 0
              AND COALESCE((evidence->>'theme_hits')::int, 0) > 0
        )::int AS theme_count,
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
    ta.gated_signal_count,
    ta.gate_scored_count,
    ta.lex_count,
    ta.theme_count,
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
ORDER BY
    CASE
        WHEN ta.signal_count >= 50
          AND ta.source_count >= 5
          AND ta.avg_confidence >= 0.65
          AND (ta.lex_count::float / NULLIF(ta.signal_count, 0)) >= 0.30
        THEN 0
        WHEN ta.signal_count >= 25
          AND ta.source_count >= 3
          AND ta.avg_confidence >= 0.60
        THEN 1
        ELSE 2
    END,
    ta.changed_10h DESC,
    ta.signal_count DESC
LIMIT $2
"""

# Unified Engine F0.3 (spec 2026-06-29-atlas-unified-engine §9.1). Byte-for-byte
# the same projection + ORDER BY as THREADS_SQL, but the atlas-evidence membership
# is read from the typed `topic_members` table (role='evidence') instead of
# `signal_topic_assignments` directly. Field mapping that preserves EXACT parity:
#   sta.gate_kept                         -> tm.gate_kept   (carried by the ETL)
#   sta.confidence                        -> tm.confidence  (carried)
#   evidence->>'lex_count' > 0            -> tm.basis = 'lexical'
#   evidence->>'lex_count'=0 AND themes>0 -> tm.basis = 'theme'
#   sta.assigned_at window                -> tm.assigned_at (ETL carries source time)
# $5 = engine_version (read flag selects it; F0.3 = 'v1-compat', F3+ = 'unified-v2').
# Related-topic co-occurrence joins tm2 (role='evidence', same engine_version);
# dynamic-topic ids never join atlas_topics.slug so only atlas relations surface,
# matching THREADS_SQL. Behind ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS (default off)
# until the A/B parity gate passes.
THREADS_SQL_TOPIC_MEMBERS = """
WITH scoped AS (
    SELECT
        tm.signal_id,
        tm.basis,
        tm.confidence,
        tm.gate_kept,
        at.slug AS topic_slug,
        at.label AS topic_label,
        at.parent_domain AS parent_domain,
        s.country_code,
        COALESCE(c.name, s.country_code) AS country_name,
        s.source_name,
        s.timestamp,
        s.nlp_sentiment,
        s.persons
    FROM topic_members tm
    JOIN atlas_topics at ON at.slug = tm.topic_id
    JOIN signals_v2 s ON s.id = tm.signal_id
    LEFT JOIN countries_v2 c ON c.code = s.country_code
    WHERE tm.engine_version = $5::text
      AND tm.role = 'evidence'
      AND tm.assigned_at >= NOW() - ($1::int * INTERVAL '1 hour')
      AND ($3::text IS NULL OR at.slug = $3::text)
      AND ($4::text[] IS NULL OR s.country_code = ANY($4::text[]))
),
topic_agg AS (
    -- topic_members PK is (signal_id, topic_id, role, engine_version) so within a
    -- (topic_slug, role='evidence', engine_version) group each signal appears once
    -- and COUNT(*) == COUNT(DISTINCT signal_id) — same accounting as THREADS_SQL.
    SELECT
        topic_slug,
        topic_label,
        parent_domain,
        COUNT(*)::int AS signal_count,
        COUNT(*) FILTER (WHERE gate_kept)::int AS gated_signal_count,
        COUNT(*) FILTER (WHERE gate_kept IS NOT NULL)::int AS gate_scored_count,
        COUNT(*) FILTER (WHERE basis = 'lexical')::int AS lex_count,
        COUNT(*) FILTER (WHERE basis = 'theme')::int AS theme_count,
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
    SELECT topic_slug, unnest(persons) AS person
    FROM scoped WHERE persons IS NOT NULL
),
entity_ranked AS (
    SELECT
        topic_slug, person, COUNT(*) AS cnt,
        ROW_NUMBER() OVER (PARTITION BY topic_slug ORDER BY COUNT(*) DESC, person) AS rn
    FROM entity_base
    WHERE person IS NOT NULL AND person <> ''
    GROUP BY topic_slug, person
),
entity_lists AS (
    SELECT topic_slug,
        ARRAY_AGG(person ORDER BY cnt DESC, person) FILTER (WHERE rn <= 5) AS top_entities
    FROM entity_ranked GROUP BY topic_slug
),
timeline_base AS (
    SELECT topic_slug, date_trunc('hour', timestamp) AS hour, COUNT(*) AS cnt
    FROM scoped GROUP BY topic_slug, date_trunc('hour', timestamp)
),
timeline AS (
    SELECT topic_slug,
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'hour', TO_CHAR(hour, 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                'count', cnt
            ) ORDER BY hour
        ) AS hourly_timeline
    FROM timeline_base GROUP BY topic_slug
),
country_ranked AS (
    SELECT
        topic_slug, country_code, country_name, COUNT(*) AS cnt,
        ROW_NUMBER() OVER (PARTITION BY topic_slug ORDER BY COUNT(*) DESC, country_code) AS rn
    FROM scoped WHERE country_code IS NOT NULL
    GROUP BY topic_slug, country_code, country_name
),
country_lists AS (
    SELECT topic_slug,
        ARRAY_AGG(country_code ORDER BY cnt DESC, country_code) FILTER (WHERE rn <= 3)
            AS top_countries,
        ARRAY_AGG(country_name ORDER BY cnt DESC, country_code) FILTER (WHERE rn <= 3)
            AS top_country_names
    FROM country_ranked GROUP BY topic_slug
),
source_ranked AS (
    SELECT
        topic_slug, source_name, COUNT(*) AS cnt,
        ROW_NUMBER() OVER (PARTITION BY topic_slug ORDER BY COUNT(*) DESC, source_name) AS rn
    FROM scoped WHERE source_name IS NOT NULL AND source_name <> ''
    GROUP BY topic_slug, source_name
),
source_lists AS (
    SELECT topic_slug,
        ARRAY_AGG(source_name ORDER BY cnt DESC, source_name) FILTER (WHERE rn <= 5)
            AS top_sources
    FROM source_ranked GROUP BY topic_slug
),
related_counts AS (
    SELECT
        scoped.topic_slug,
        tm2.topic_id AS related_slug,
        COUNT(DISTINCT scoped.signal_id)::int AS co_signals
    FROM scoped
    JOIN topic_members tm2
      ON tm2.signal_id = scoped.signal_id
     AND tm2.role = 'evidence'
     AND tm2.engine_version = $5::text
     AND tm2.topic_id <> scoped.topic_slug
    GROUP BY scoped.topic_slug, tm2.topic_id
),
related_ranked AS (
    SELECT
        topic_slug, related_slug, co_signals,
        ROW_NUMBER() OVER (
            PARTITION BY topic_slug ORDER BY co_signals DESC, related_slug
        ) AS rn
    FROM related_counts
),
related AS (
    SELECT
        rr.topic_slug,
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'topic', at2.slug, 'label', at2.label, 'co_signals', rr.co_signals
            ) ORDER BY rr.co_signals DESC, at2.slug
        ) FILTER (WHERE rr.rn <= 5) AS related_topics
    FROM related_ranked rr
    JOIN atlas_topics at2 ON at2.slug = rr.related_slug
    GROUP BY rr.topic_slug
)
SELECT
    ta.topic_slug,
    ta.topic_label,
    ta.parent_domain,
    ta.signal_count,
    ta.gated_signal_count,
    ta.gate_scored_count,
    ta.lex_count,
    ta.theme_count,
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
ORDER BY
    CASE
        WHEN ta.signal_count >= 50
          AND ta.source_count >= 5
          AND ta.avg_confidence >= 0.65
          AND (ta.lex_count::float / NULLIF(ta.signal_count, 0)) >= 0.30
        THEN 0
        WHEN ta.signal_count >= 25
          AND ta.source_count >= 3
          AND ta.avg_confidence >= 0.60
        THEN 1
        ELSE 2
    END,
    ta.changed_10h DESC,
    ta.signal_count DESC
LIMIT $2
"""

THREAD_EVIDENCE_SQL = """
SELECT
    id,
    headline,
    snippet,
    source_name,
    source_url,
    country_code,
    country_name,
    source_lang,
    timestamp,
    nlp_sentiment,
    confidence,
    syndication_count,
    themes,
    persons
FROM (
    SELECT DISTINCT ON (LOWER(s.headline))
        s.id,
        s.headline,
        s.snippet,
        s.source_name,
        s.source_url,
        s.country_code,
        COALESCE(c.name, s.country_code) AS country_name,
        s.source_lang,
        s.timestamp,
        s.nlp_sentiment,
        s.themes,
        s.persons,
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
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return [value]
            return parsed if isinstance(parsed, list) else [parsed]
        return [value]
    return list(value)


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


def build_thread_label(*, anchor_label: str, top_countries: list[str]) -> str:
    # Momentum is shown by the trend pill (accelerating/stable/fading); the
    # label stays a neutral topic+place phrase to avoid a second, contradictory
    # momentum signal in the title.
    # Expand any country that came through as a bare ISO code (countries_v2 /
    # COUNTRY_METADATA are partial; the diversity program surfaces long-tail
    # countries) so a label never reads "... in France and UG" (#204-lite).
    names = [resolve_country_name(c) for c in top_countries]
    if len(names) >= 2:
        place = f"{names[0]} and {names[1]}"
    elif names:
        place = names[0]
    else:
        place = "multiple regions"

    return f"{anchor_label} in {place}"


def _why_now(
    changed_10h: int,
    subject_countries: list[str] | None = None,
    subject_status: str | None = None,
) -> str:
    """One-line 'why is this moving now' for a thread card.

    `changed_10h` is a NET change: count(last 10h) - count(prior 10h). It is
    NOT a gross count of signals added, and it can exceed the window
    `signal_count` when the serving window is shorter than the 20h span the
    delta is measured over (#214: a reader saw "+53 in 10h" against a window
    total of 28). So the copy must read explicitly as a net up/down vs the
    PRIOR 10h, never as "N more signals than the thread has".

    #238 (subject vs coverage geography): the old template appended
    "concentrated in {top coverage countries}" — a coverage-proxy presented as
    a subject claim (live case: a verified-IT thread reading "concentrated in
    Iran and Russia"). The geo clause now appears ONLY when subject geography
    is VERIFIED from the receipts ("centered on X" — a subject claim we can
    stand behind); otherwise the sentence is movement-only. Coverage countries
    still serve as labeled chips — they never masquerade as the subject here.
    """
    place = ""
    if subject_status == "verified" and subject_countries:
        resolved = [resolve_country_name(c) for c in subject_countries[:2]]
        place = ", centered on " + " and ".join(resolved)
    if changed_10h > 0:
        return f"Up {changed_10h} vs the prior 10h (net new coverage){place}."
    if changed_10h < 0:
        return f"Down {abs(changed_10h)} vs the prior 10h (coverage cooling){place}."
    return f"Signal volume is steady vs the prior 10h{place}."


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


def _movement_label(changed_10h: int, period: str = "10h") -> str:
    """Short, reader-safe chip text for the movement delta (#214).

    The frontend chip historically rendered raw `+53 / 10h`, which a reader
    compares against the window `signal_count` ("28 signals") and reads as a
    contradiction. `changed_10h` is a NET delta vs the prior period, not a
    count of new signals, so the chip must SAY "vs prior <period>" to stop
    that false comparison. Sign-prefixed and self-describing; safe to render
    next to any `signal_count` without implying "more than the thread has".

    ``period`` defaults to ``"10h"`` (atlas/dynamic 10h buckets); the emergent
    path passes ``"prior snapshot"`` since its delta spans ~6h snapshots.
    """
    prefix = "prior " if period == "10h" else ""
    if changed_10h > 0:
        return f"+{changed_10h} vs {prefix}{period}"
    if changed_10h < 0:
        return f"{changed_10h} vs {prefix}{period}"
    return f"flat vs {prefix}{period}"


def _dominant_source_is_aggregator(top_sources: list[str]) -> bool:
    if not top_sources:
        return False
    return top_sources[0].lower() in AGGREGATOR_DOMAINS


def _has_unresolved_country_code(country_codes: list[str], country_names: list[str]) -> bool:
    for code, name in zip(country_codes, country_names, strict=False):
        if code and name and code.upper() == name.upper():
            return True
    return False


def _quality_metadata(
    *,
    signal_count: int,
    lex_count: int,
    theme_count: int,
    top_sources: list[str],
    country_codes: list[str],
    country_names: list[str],
    top_entities: list[str],
) -> dict[str, Any]:
    lex_pct = round(lex_count / signal_count, 4) if signal_count > 0 else 0
    return {
        "lex_pct": lex_pct,
        "method_mix": {
            "lex": lex_count,
            "theme": theme_count,
        },
        "source_flags": {
            "aggregator_dominant": _dominant_source_is_aggregator(top_sources),
        },
        "geo_flags": {
            "unresolved_country_code": _has_unresolved_country_code(
                country_codes,
                country_names,
            ),
        },
        "entity_flags": {
            "raw_entity_field_untyped": bool(top_entities),
        },
    }


def _with_narrative_note(thread: dict[str, Any]) -> dict[str, Any]:
    thread["narrative_note"] = build_thread_narrative_note(thread)
    return thread


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
    gated_signal_count = int(_record_get(row, "gated_signal_count") or 0)
    gate_scored_count = int(_record_get(row, "gate_scored_count") or 0)
    lex_count = int(_record_get(row, "lex_count") or 0)
    theme_count = int(_record_get(row, "theme_count") or 0)
    source_count = int(_record_get(row, "source_count") or 0)
    country_count = int(_record_get(row, "country_count") or 0)
    raw_avg_confidence = _record_get(row, "avg_confidence")
    avg_confidence = float(raw_avg_confidence or 0)
    first_seen = _record_get(row, "first_seen")
    top_entities = [str(person) for person in _as_list(_record_get(row, "top_entities"))]
    top_sources = [str(source) for source in _as_list(_record_get(row, "top_sources"))]
    hourly_timeline = _as_list(_record_get(row, "hourly_timeline"))
    label = build_thread_label(
        anchor_label=topic_label,
        top_countries=country_names,
    )

    return _with_narrative_note({
        "thread_id": build_thread_id(topic_slug, country_codes),
        "label": label,
        "summary": label,
        "anchor_topics": [topic_slug],
        "parent_domain": parent_domain,
        # atlas topics ARE the crisis taxonomy → crisis_relevant=true, category=domain.
        # Consistent with the R3 lens WITHOUT collapsing atlas (the pure collapse is
        # coverage-risky while dynamic recall is partial — kept as a future step).
        "category": parent_domain,
        "crisis_relevant": True,
        "signal_count": signal_count,
        # #214: gate-kept count (detail shows only these). gate_scored=0 means the
        # gate hasn't scored this topic yet (pending), not "0 relevant".
        "gated_signal_count": gated_signal_count,
        "gate_scored_count": gate_scored_count,
        "source_count": source_count,
        "country_count": country_count,
        "avg_confidence": round(avg_confidence, 3),
        "confidence_measured": raw_avg_confidence is not None,
        "confidence_source": "assignment" if raw_avg_confidence is not None else None,
        "first_seen": first_seen.isoformat() if hasattr(first_seen, "isoformat") else first_seen,
        "changed_10h": changed_10h,
        "movement_label": _movement_label(changed_10h),
        "trend": _trend_label(changed_10h, signal_count),
        "sentiment_swing_10h": _record_get(row, "sentiment_swing_10h"),
        "top_countries": country_codes,
        "top_country_names": country_names,
        "top_sources": top_sources,
        "top_people": [],
        "top_entities": top_entities,
        "hourly_timeline": hourly_timeline,
        "source_mix": {
            "top_sources": top_sources,
            "source_count": source_count,
        },
        "quality": _quality_metadata(
            signal_count=signal_count,
            lex_count=lex_count,
            theme_count=theme_count,
            top_sources=top_sources,
            country_codes=country_codes,
            country_names=country_names,
            top_entities=top_entities,
        ),
        "confidence": confidence_band(
            evidence_count=signal_count,
            source_count=source_count,
            geo_count=country_count,
            assignment_confidence=avg_confidence,
        ),
        # #238: atlas path computes no receipt-subject inference — movement-only,
        # never a coverage-country clause dressed as a subject claim.
        "why_now": _why_now(changed_10h),
        "subthreads": [],
        "related_threads": _as_list(_record_get(row, "related_topics")),
        "evidence_samples": evidence_samples or [],
        "narrative_note": None,
    })


def evidence_role(syndication_count: int) -> str:
    if syndication_count >= 5:
        return "syndicated"
    if syndication_count >= 2:
        return "repeated"
    return "representative"


def _serialize_evidence(row: Any) -> dict[str, Any]:
    timestamp = _record_get(row, "timestamp")
    syndication = int(_record_get(row, "syndication_count") or 1)
    raw_headline = _record_get(row, "headline")
    # signals_v2.headline is stored with XML numeric entities intact
    # (`&#x041D;...`). Unescape on the way out so the brief, the threads
    # focus panel, and any consumer renders human-readable text.
    headline = html.unescape(raw_headline) if raw_headline else raw_headline
    raw_country_code = _record_get(row, "country_code")
    country_code = raw_country_code
    # Stored GDELT rows are already converted at ingestion. The historical
    # Senegal collision is the exception: before SG(FIPS)->SN(ISO) existed,
    # those rows were persisted as SG, which is also valid ISO Singapore. Only
    # repair that ambiguous legacy value when the frozen headline itself names
    # Senegal. Some legacy rows have no source_family, so the receipt text —
    # not mutable ingestion metadata — is the disambiguator. Never run a second
    # blanket FIPS conversion over stored ISO rows.
    if raw_country_code == "SG" and headline:
        single_receipt_geo = infer_receipt_subject_geography([{
            "headline": headline,
            "source_name": _record_get(row, "source_name"),
            # NER places are derived from the frozen story text (not mutable
            # ingestion metadata), so they are a valid disambiguator here too
            # (e.g. body names Dakar → SN).
            "places": _as_list(_record_get(row, "nlp_places")),
        }])
        candidate_codes = {
            candidate.get("country")
            for candidate in single_receipt_geo.get("candidates", [])
        }
        if "SN" in candidate_codes:
            country_code = "SN"
    return {
        "id": str(_record_get(row, "id")),
        "headline": headline,
        "snippet": _record_get(row, "snippet"),
        "source": _record_get(row, "source_name"),
        "url": _record_get(row, "source_url"),
        "country_code": country_code,
        "country_name": _record_get(row, "country_name"),
        # B2 (L1 review 2026-07-05): the Brief translates evidence headlines
        # by default; the viewer needs the source language to decide.
        "source_lang": _record_get(row, "source_lang"),
        "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else timestamp,
        "sentiment": _record_get(row, "nlp_sentiment"),
        "confidence": _record_get(row, "confidence"),
        "syndication_count": syndication,
        "evidence_role": evidence_role(syndication),
    }


DYNAMIC_TOPIC_THREAD_PREFIX = "dynamic-topic-"
EMERGENT_CLUSTER_THREAD_PREFIX = "emergent-cluster-"


def assemble_emergent_thread(
    cluster_row: Any,
    sample_signals: list[Any],
    gate_threshold: float | None = None,
) -> dict[str, Any]:
    """Map an `emergent_clusters` row + its sample signals to the living
    thread contract used by the atlas-anchored path.

    Mirrors `assemble_thread` so `NarrativeThreads.tsx` renders emergent
    and atlas threads identically. Atlas-specific fields that do not yet
    have an emergent equivalent (`parent_domain`, real `first_seen`,
    `sentiment_swing_10h`) are left None until Phase 6's `dynamic_topics`
    lifecycle provides them.

    Mapping:
      thread_id        = f"emergent-cluster-{id}"  (detail dispatch prefix)
      anchor_topics    = [f"cluster-{id}"]
      label / summary  = cluster.label / cluster.description
      signal_count     = n_signals (post-gate kept)
      avg_confidence   = gate_threshold  (proxy; every kept member
                         already passed the >=90% precision gate)
      changed_10h      = velocity (delta vs prior snapshot, ~6h apart;
                         same sign semantics as atlas's 10h delta)
      trend / why_now  = reuse the atlas helpers on velocity.
    """
    cluster_id = int(_record_get(cluster_row, "id"))
    label_text = clean_thread_label(
        _record_get(cluster_row, "label"), sample_signals, f"cluster {cluster_id}",
        country_codes=[str(c) for c in (_record_get(cluster_row, "top_country_codes") or [])],
    )
    description = _record_get(cluster_row, "description")
    signal_count = int(_record_get(cluster_row, "n_signals") or 0)
    velocity_raw = _record_get(cluster_row, "velocity")
    velocity = int(velocity_raw) if velocity_raw is not None else 0
    cohesion = _record_get(cluster_row, "cohesion")
    snap_at = _record_get(cluster_row, "snapshot_at")
    country_codes = [
        str(code) for code in (_record_get(cluster_row, "top_country_codes") or [])
    ]

    sources: dict[str, int] = {}
    persons: dict[str, int] = {}
    timeline: dict[str, list[float]] = {}
    for sig in sample_signals:
        source_name = _record_get(sig, "source_name")
        if source_name:
            sources[source_name] = sources.get(source_name, 0) + 1
        for person in (_as_list(_record_get(sig, "persons")) or []):
            persons[str(person)] = persons.get(str(person), 0) + 1
        ts = _record_get(sig, "timestamp")
        if ts and hasattr(ts, "replace"):
            hour_iso = ts.replace(minute=0, second=0, microsecond=0).isoformat()
            timeline.setdefault(hour_iso, []).append(
                float(_record_get(sig, "nlp_sentiment") or 0)
            )

    top_sources = sorted(sources, key=lambda k: sources[k], reverse=True)[:5]
    top_entities = sorted(persons, key=lambda k: persons[k], reverse=True)[:10]
    hourly_timeline = [
        {
            "hour": hour,
            "count": len(vs),
            "avg_sentiment": (sum(vs) / len(vs)) if vs else 0,
        }
        for hour, vs in sorted(timeline.items())
    ]

    source_count = len(sources)
    country_count = len(country_codes)
    # `gate_threshold` is a cutoff applied to members, not a calibrated
    # confidence estimate for the cluster. Keep it for the internal quality
    # band, but never serialize it as a user-facing confidence percentage.
    avg_conf_for_band = float(gate_threshold) if gate_threshold is not None else 0.0

    return _with_narrative_note({
        "thread_id": f"{EMERGENT_CLUSTER_THREAD_PREFIX}{cluster_id}",
        "label": label_text,
        "summary": description or label_text,
        "anchor_topics": [f"cluster-{cluster_id}"],
        "parent_domain": None,
        "signal_count": signal_count,
        # Emergent n_signals is already the post-gate kept count (#214).
        "gated_signal_count": signal_count,
        "gate_scored_count": signal_count,
        "source_count": source_count,
        "country_count": country_count,
        "avg_confidence": None,
        "confidence_measured": False,
        "confidence_source": None,
        "first_seen": snap_at.isoformat() if hasattr(snap_at, "isoformat") else snap_at,
        "changed_10h": velocity,
        # Emergent velocity is a delta vs the PRIOR SNAPSHOT (~6h apart),
        # not a strict 10h window, so reuse the generic period phrasing.
        "movement_label": _movement_label(velocity, period="prior snapshot"),
        "trend": _trend_label(velocity, signal_count),
        "sentiment_swing_10h": None,
        "top_countries": country_codes,
        # Name resolution stays on the frontend (countryNames lib).
        "top_country_names": country_codes,
        "top_sources": top_sources,
        "top_people": [],
        "top_entities": top_entities,
        "hourly_timeline": hourly_timeline,
        "source_mix": {
            "top_sources": top_sources,
            "source_count": source_count,
        },
        "quality": _quality_metadata(
            signal_count=signal_count,
            lex_count=0,
            theme_count=0,
            top_sources=top_sources,
            country_codes=country_codes,
            country_names=country_codes,
            top_entities=top_entities,
        ),
        "confidence": confidence_band(
            evidence_count=signal_count,
            source_count=source_count,
            geo_count=country_count,
            assignment_confidence=avg_conf_for_band,
        ),
        # #238: emergent path computes no receipt-subject inference — movement-only.
        "why_now": _why_now(velocity),
        "subthreads": [],
        "related_threads": [],
        "evidence_samples": [_serialize_evidence(sig) for sig in sample_signals],
        "narrative_note": None,
        "cluster_cohesion": float(cohesion) if cohesion is not None else None,
        "source": "emergent_clusters",
    })


_EMERGENT_SAMPLE_SIGNALS_SQL = """
    SELECT id, headline, snippet, source_name, source_url, country_code,
           NULL::text       AS country_name,
           source_family,
           source_lang,
           timestamp,
           persons,
           themes,
           nlp_places,
           sentiment        AS nlp_sentiment,
           1::int           AS syndication_count,
           NULL::float      AS confidence
    FROM signals_v2
    WHERE id = ANY($1::bigint[])
    ORDER BY timestamp DESC
"""


# Shared SELECT for the dynamic-topics list. Eligibility is applied in a
# MATERIALIZED candidate_topics CTE before these correlated member aggregates:
# the old query evaluated them over the full active set and cold requests
# reached 7-9s. The CTE cap scales with the requested surface but has a hard
# ceiling so serving cost cannot grow without bound as the story corpus grows.
_DYNAMIC_TOPICS_SELECT = """
SELECT
    dt.id,
    dt.identity_key,
    dt.label,
    dt.first_seen,
    dt.last_seen,
    dt.agg_n_signals,
    dt.mean_cohesion,
    -- Umbrellas carry no own noise_rate (NULL -> confidence None -> the
    -- umbrella-first front page could never clear the Brief's lead bar).
    -- Their confidence is their CHILDREN's average (2026-07-18).
    COALESCE(dt.noise_rate, (SELECT AVG(c.noise_rate) FROM dynamic_topics c
                             WHERE c.parent_id = dt.id AND c.state='active')) AS noise_rate,
    dt.category,            -- R3.1 open category (crisis seed OR emergent) = the badge
    dt.crisis_class,        -- (legacy) seed-32 class or 'non_crisis'
    dt.crisis_relevant,     -- R3 lens flag: is this crisis-relevant? (analyst filter)
    dt.label_status,        -- Label Court verdict (entailed/partial/failed, NULL=unchecked)
    dt.label_proposed,      -- receipt-derived neutral label on 'failed' (never auto-served)
    COALESCE((
        -- current volume = kept-signal count at the topic's LATEST snapshot. SUM
        -- (not LIMIT 1) so an R2 umbrella (N child clusters at one snapshot) reflects
        -- its whole current volume; a normal topic has one cluster/snapshot so the
        -- sum equals that single cluster — unchanged behaviour.
        SELECT SUM(ec4.n_signals)
        FROM dynamic_topic_members dtm4
        JOIN emergent_clusters ec4 ON ec4.id = dtm4.emergent_cluster_id
        WHERE dtm4.dynamic_topic_id = dt.id
          AND dtm4.snapshot_at = (
              SELECT MAX(snapshot_at) FROM dynamic_topic_members WHERE dynamic_topic_id = dt.id
          )
    ), 0)::int AS recent_n_signals,
    COALESCE((
        -- movement = velocity at the topic's LATEST snapshot only. The old
        -- MAX(ec.velocity) spanned ALL snapshots (a lifetime max): 69/101
        -- multi-snapshot active topics served inflated changed_10h, feeding
        -- the trend arrow AND the 0.35 movement term in rank_threads — the
        -- #224 stale-looks-alive pathology (2026-07-01 L0-L3 data audit).
        -- SUM so an R2 umbrella aggregates its children's current velocity.
        SELECT SUM(ec5.velocity)
        FROM dynamic_topic_members dtm5
        JOIN emergent_clusters ec5 ON ec5.id = dtm5.emergent_cluster_id
        WHERE dtm5.dynamic_topic_id = dt.id
          AND dtm5.snapshot_at = (
              SELECT MAX(snapshot_at) FROM dynamic_topic_members WHERE dynamic_topic_id = dt.id
          )
    ), 0)::int AS changed_10h,
    ARRAY(
        SELECT DISTINCT code
        FROM dynamic_topic_members dtm2
        JOIN emergent_clusters ec2 ON ec2.id = dtm2.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec2.top_country_codes, ARRAY[]::text[])) AS code
        WHERE dtm2.dynamic_topic_id = dt.id
          AND dtm2.snapshot_at = (
              SELECT MAX(snapshot_at) FROM dynamic_topic_members
              WHERE dynamic_topic_id = dt.id
          )
        LIMIT 5
    ) AS top_country_codes,
    ARRAY(
        SELECT DISTINCT sid
        FROM dynamic_topic_members dtm3
        JOIN emergent_clusters ec3 ON ec3.id = dtm3.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec3.sample_signal_ids, ARRAY[]::bigint[])) AS sid
        WHERE dtm3.dynamic_topic_id = dt.id
          AND dtm3.snapshot_at = (
              SELECT MAX(snapshot_at) FROM dynamic_topic_members
              WHERE dynamic_topic_id = dt.id
          )
        LIMIT 24
    ) AS sample_signal_ids
FROM candidate_topics dt
"""

_DYNAMIC_TOPICS_TAIL = """
ORDER BY recent_n_signals DESC, dt.last_seen DESC
LIMIT $2
"""

_DYNAMIC_TOPICS_CANDIDATE_LIMIT = """
ORDER BY dt.last_seen DESC, dt.id DESC
LIMIT LEAST(GREATEST($2::int * 8, 80), 400)
)\n
"""

# Global list = top-level (umbrellas + singletons); childed dups hide under their
# umbrella and surface on drill / country view.
_DYNAMIC_TOPICS_SQL = """
WITH candidate_topics AS MATERIALIZED (
SELECT dt.*
FROM dynamic_topics dt
WHERE dt.state = 'active'
  AND dt.parent_id IS NULL
  AND dt.last_seen > NOW() - (GREATEST($1::int, 72) * INTERVAL '1 hour')
  -- #250: 72h floor — a major event (VE earthquake, 380+169 signals) fell off
  -- its own country's view at hour 25 (cliff). Ranking still favors fresh;
  -- recent-but-fading stories DECAY down the list instead of vanishing.
""" + _DYNAMIC_TOPICS_CANDIDATE_LIMIT + _DYNAMIC_TOPICS_SELECT + _DYNAMIC_TOPICS_TAIL

# Country view = the per-country CHILDREN, scoped by the PRIMARY country of a member
# cluster ($3) — the R1 scoped topics for that country (e.g. "Venezuela Earthquake
# Death Toll" for VE), not the global atlas-generic ones. Umbrellas are global →
# excluded; children are NOT parent-filtered (a country wants its own version).
_DYNAMIC_TOPICS_COUNTRY_SQL = """
WITH candidate_topics AS MATERIALIZED (
SELECT dt.*
FROM dynamic_topics dt
WHERE dt.state = 'active'
  AND dt.is_umbrella = false
  AND EXISTS (
      SELECT 1 FROM dynamic_topic_members dtmc
      JOIN emergent_clusters ecc ON ecc.id = dtmc.emergent_cluster_id
      WHERE dtmc.dynamic_topic_id = dt.id AND ecc.top_country_codes[1] = $3
  )
  AND dt.last_seen > NOW() - (GREATEST($1::int, 72) * INTERVAL '1 hour')
  -- #250: 72h floor — a major event (VE earthquake, 380+169 signals) fell off
  -- its own country's view at hour 25 (cliff). Ranking still favors fresh;
  -- recent-but-fading stories DECAY down the list instead of vanishing.
""" + _DYNAMIC_TOPICS_CANDIDATE_LIMIT + _DYNAMIC_TOPICS_SELECT + _DYNAMIC_TOPICS_TAIL


_DYNAMIC_TOPIC_DETAIL_SQL = """
SELECT
    dt.id,
    dt.identity_key,
    dt.label,
    dt.first_seen,
    dt.last_seen,
    dt.agg_n_signals,
    dt.mean_cohesion,
    -- Umbrellas carry no own noise_rate (NULL -> confidence None -> the
    -- umbrella-first front page could never clear the Brief's lead bar).
    -- Their confidence is their CHILDREN's average (2026-07-18).
    COALESCE(dt.noise_rate, (SELECT AVG(c.noise_rate) FROM dynamic_topics c
                             WHERE c.parent_id = dt.id AND c.state='active')) AS noise_rate,
    dt.category,            -- R3.1 open category (crisis seed OR emergent) = the badge
    dt.crisis_class,        -- (legacy) seed-32 class or 'non_crisis'
    dt.crisis_relevant,     -- R3 lens flag: is this crisis-relevant? (analyst filter)
    dt.label_status,        -- Label Court verdict (entailed/partial/failed, NULL=unchecked)
    dt.label_proposed,      -- receipt-derived neutral label on 'failed' (never auto-served)
    COALESCE((
        -- movement = velocity at the topic's LATEST snapshot only. The old
        -- MAX(ec.velocity) spanned ALL snapshots (a lifetime max): 69/101
        -- multi-snapshot active topics served inflated changed_10h, feeding
        -- the trend arrow AND the 0.35 movement term in rank_threads — the
        -- #224 stale-looks-alive pathology (2026-07-01 L0-L3 data audit).
        -- SUM so an R2 umbrella aggregates its children's current velocity.
        SELECT SUM(ec5.velocity)
        FROM dynamic_topic_members dtm5
        JOIN emergent_clusters ec5 ON ec5.id = dtm5.emergent_cluster_id
        WHERE dtm5.dynamic_topic_id = dt.id
          AND dtm5.snapshot_at = (
              SELECT MAX(snapshot_at) FROM dynamic_topic_members WHERE dynamic_topic_id = dt.id
          )
    ), 0)::int AS changed_10h,
    ARRAY(
        SELECT DISTINCT code
        FROM dynamic_topic_members dtm2
        JOIN emergent_clusters ec2 ON ec2.id = dtm2.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec2.top_country_codes, ARRAY[]::text[])) AS code
        WHERE dtm2.dynamic_topic_id = dt.id
          AND dtm2.snapshot_at = (
              SELECT MAX(snapshot_at) FROM dynamic_topic_members
              WHERE dynamic_topic_id = dt.id
          )
        LIMIT 5
    ) AS top_country_codes,
    ARRAY(
        SELECT DISTINCT sid
        FROM dynamic_topic_members dtm3
        JOIN emergent_clusters ec3 ON ec3.id = dtm3.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec3.sample_signal_ids, ARRAY[]::bigint[])) AS sid
        WHERE dtm3.dynamic_topic_id = dt.id
          AND dtm3.snapshot_at = (
              SELECT MAX(snapshot_at) FROM dynamic_topic_members
              WHERE dynamic_topic_id = dt.id
          )
        LIMIT 32
    ) AS sample_signal_ids
FROM dynamic_topics dt
WHERE dt.id = $1
  AND dt.state = 'active'
"""


# --- #204: thread-label hygiene (serving-layer) -----------------------------
# DeepSeek's "(label failed)" stub and other placeholders were persisted into
# dynamic_topics.label / emergent_clusters.label (snapshot_emergent_topics.py)
# and then served verbatim, so they reached the Brief front page and the
# console. Clean at the serving choke point both story paths pass through: a
# real label passes through (HTML-unescaped); a placeholder falls back to a
# representative evidence headline (mirrors build_unified_topics' creation-time
# "Emerging: <headline>" fallback). Non-English title *translation* is a
# separate follow-up (#204 part b).
# Mirror of scripts/label_hygiene.PLACEHOLDER_LABELS (app/ must not import
# from scripts/): keep the two sets in sync.
_PLACEHOLDER_LABELS = {"", "(no label)", "(label failed)", "(label failed.)", "none", "null"}
_LABEL_MAX = 90
# Sentinel: the caller did not supply the topic's category, so the
# unlabeled-foreign-headline rule below cannot be evaluated (emergent
# clusters have no category concept — the rule must stay off for them).
_NO_CATEGORY = object()


def _is_placeholder_label(label: str | None) -> bool:
    if not label:
        return True
    s = html.unescape(str(label)).strip()
    if not s:
        return True
    low = s.lower()
    return low in _PLACEHOLDER_LABELS or low.startswith("(label failed")


def _is_foreign_script(text: str) -> bool:
    """True when the text's letters are dominated by non-Latin script.

    Used ONLY together with ``category IS NULL`` (an untyped topic — the
    pipeline never processed it, so its "label" is almost certainly a raw
    scraped headline, not a curated title). A real DeepSeek label in
    Spanish/French/etc. is Latin-script and never trips this."""
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 4:
        return False
    latin = sum(1 for c in letters if ord(c) < 0x250)
    return latin / len(letters) < 0.3


def _receipt_fallback_label(
    sample_signals: list[Any], country_codes: list[str] | None = None
) -> str | None:
    """Receipt-derived neutral display label: dominant geo + top clean
    headline — ``Emerging (VE): <headline>`` (or without the geo when the
    thread has no country codes). None when no clean receipt exists."""
    try:
        from app.services.research_semantic import is_junk_headline
    except Exception:  # pragma: no cover - never break serving on an import hiccup
        def is_junk_headline(h: Any) -> bool:
            return not h or len([w for w in str(h).split() if any(c.isalpha() for c in w)]) < 3
    for sig in sample_signals or []:
        headline = _record_get(sig, "headline")
        if headline and not is_junk_headline(str(headline)):
            clean = html.unescape(str(headline)).strip()
            if len(clean) > _LABEL_MAX:
                clean = clean[: _LABEL_MAX - 1].rstrip() + "…"
            geo = next((str(c).strip().upper() for c in (country_codes or []) if c), None)
            return f"Emerging ({geo}): {clean}" if geo else f"Emerging: {clean}"
    return None


def clean_thread_label(
    raw_label: Any,
    sample_signals: list[Any],
    fallback: str,
    *,
    country_codes: list[str] | None = None,
    category: Any = _NO_CATEGORY,
) -> str:
    """Return a real thread title. A real label is returned HTML-unescaped.

    Display-only hygiene — never hides a thread, fixes its label:
    - placeholder / NULL / "(label failed)" stub → receipt-derived neutral
      fallback (dominant geo + top clean headline); generic ``fallback``
      (e.g. 'dynamic topic 42') only when no clean receipt exists.
    - a persisted creation-time fallback ("Emerging: …") is refreshed from
      the CURRENT receipts (it froze a headline at creation); kept as-is
      when no fresher receipt is available.
    - an untyped topic (``category`` passed and NULL) whose label is a raw
      foreign-script headline gets the same receipt-derived neutral
      fallback; a typed topic's foreign-script label is served untouched.
    """
    label = None if raw_label is None else str(raw_label)
    if not _is_placeholder_label(label):
        clean = html.unescape(label).strip()
        low = clean.lower()
        # only the machine-generated forms — a real title like "Emerging
        # Markets Crisis" must pass through untouched
        stale_creation_fallback = low.startswith("emerging:") or low.startswith("emerging (")
        unlabeled_foreign = (
            category is not _NO_CATEGORY
            and category is None
            and _is_foreign_script(clean)
        )
        if not stale_creation_fallback and not unlabeled_foreign:
            return clean
        derived = _receipt_fallback_label(sample_signals, country_codes)
        # keep the stored receipt-derived label over a raw-id fallback
        return derived or clean
    derived = _receipt_fallback_label(sample_signals, country_codes)
    return derived or fallback


def assemble_dynamic_thread(topic_row: Any, sample_signals: list[Any]) -> dict[str, Any]:
    topic_id = int(_record_get(topic_row, "id"))
    label_text = clean_thread_label(
        _record_get(topic_row, "label"), sample_signals, f"dynamic topic {topic_id}",
        country_codes=[str(c) for c in (_record_get(topic_row, "top_country_codes") or [])],
        category=_record_get(topic_row, "category", _NO_CATEGORY),
    )
    # current-window volume (#224); lifetime aggregate kept as metadata
    signal_count = int(
        _record_get(topic_row, "recent_n_signals")
        or _record_get(topic_row, "agg_n_signals")
        or 0
    )
    lifetime_signals = int(_record_get(topic_row, "agg_n_signals") or 0)
    changed_10h = int(_record_get(topic_row, "changed_10h") or 0)
    noise_rate = _record_get(topic_row, "noise_rate")
    avg_conf = 1.0 - float(noise_rate) if noise_rate is not None else None
    cohesion = _record_get(topic_row, "mean_cohesion")
    first_seen = _record_get(topic_row, "first_seen")
    country_codes = [str(code) for code in (_record_get(topic_row, "top_country_codes") or [])]
    # R3.1: the story's category (crisis_class = a seed-32 class, or 'non_crisis').
    # Reuse parent_domain to carry the badge so the existing frontend renders it — a
    # dynamic thread stops showing the generic "narrative thread" badge and shows its
    # crisis class, killing the atlas-vs-dynamic badge asymmetry.
    category = _record_get(topic_row, "category")
    crisis_relevant = _record_get(topic_row, "crisis_relevant")
    # R3 (crisis-relevance-as-lens): the OPEN category IS the badge for every story —
    # crisis seed ("Armed Conflict") or emergent ("World Cup 2026"). No crisis/non_crisis
    # second class: a diverse uncategorized singleton simply has no category (generic
    # badge). `crisis_relevant` is a separate FLAG the analyst filters on, not a divide.
    badge_domain = category

    sources: dict[str, int] = {}
    persons: dict[str, int] = {}
    timeline: dict[str, list[float]] = {}
    for sig in sample_signals:
        source_name = _record_get(sig, "source_name")
        if source_name:
            sources[source_name] = sources.get(source_name, 0) + 1
        for person in (_as_list(_record_get(sig, "persons")) or []):
            persons[str(person)] = persons.get(str(person), 0) + 1
        ts = _record_get(sig, "timestamp")
        if ts and hasattr(ts, "replace"):
            hour_iso = ts.replace(minute=0, second=0, microsecond=0).isoformat()
            timeline.setdefault(hour_iso, []).append(
                float(_record_get(sig, "nlp_sentiment") or 0)
            )

    top_sources = sorted(sources, key=lambda k: sources[k], reverse=True)[:5]
    top_entities = sorted(persons, key=lambda k: persons[k], reverse=True)[:10]
    hourly_timeline = [
        {
            "hour": hour,
            "count": len(vs),
            "avg_sentiment": (sum(vs) / len(vs)) if vs else 0,
        }
        for hour, vs in sorted(timeline.items())
    ]
    source_count = len(sources)
    country_count = len(country_codes)
    subject_geography = infer_receipt_subject_geography([
        {
            "headline": _record_get(sig, "headline"),
            "source_name": _record_get(sig, "source_name"),
            # #238 C-clean slice 2: NER places from the story body (mig 078
            # nlp_places, JSONB → may arrive as a JSON string from asyncpg).
            # Location evidence for the domestic-story class whose headlines
            # never name the country; empty until the M1 fleet backfills.
            "places": _as_list(_record_get(sig, "nlp_places")),
        }
        for sig in sample_signals
    ])
    subject_countries = list(subject_geography.get("verified_subject_countries") or [])
    subject_country_names = [resolve_country_name(code) for code in subject_countries]

    return _with_narrative_note({
        "thread_id": f"{DYNAMIC_TOPIC_THREAD_PREFIX}{topic_id}",
        "label": label_text,
        "summary": label_text,
        "anchor_topics": [str(_record_get(topic_row, "identity_key") or f"dynamic-topic-{topic_id}")],
        "parent_domain": badge_domain,          # R3: the open category IS the badge
        "category": category,
        "crisis_relevant": bool(crisis_relevant) if crisis_relevant is not None else None,
        "signal_count": signal_count,
        "lifetime_signal_count": lifetime_signals,
        "source_count": source_count,
        "country_count": country_count,
        "avg_confidence": (
            round(max(min(avg_conf, 1.0), 0.0), 3) if avg_conf is not None else None
        ),
        "confidence_measured": avg_conf is not None,
        "confidence_source": "noise_rate" if avg_conf is not None else None,
        "first_seen": first_seen.isoformat() if hasattr(first_seen, "isoformat") else first_seen,
        "changed_10h": changed_10h,
        "movement_label": _movement_label(changed_10h),
        "trend": _trend_label(changed_10h, signal_count),
        "sentiment_swing_10h": None,
        "top_countries": country_codes,
        # Dynamic topics currently store country codes only. Leave names empty so
        # the frontend resolves display names instead of rendering ID + ID.
        "top_country_names": [],
        "subject_countries": subject_countries,
        "subject_country_names": subject_country_names,
        "subject_geography_status": subject_geography.get("status", "missing"),
        "subject_geography_reason_codes": list(
            subject_geography.get("reason_codes") or []
        ),
        "top_sources": top_sources,
        "top_people": [],
        "top_entities": top_entities,
        "hourly_timeline": hourly_timeline,
        "source_mix": {
            "top_sources": top_sources,
            "source_count": source_count,
        },
        "quality": {
            "lex_pct": 0,
            "method_mix": {"dynamic": signal_count},
            "source_flags": {"aggregator_dominant": _dominant_source_is_aggregator(top_sources)},
            "geo_flags": {"unresolved_country_code": False},
            "entity_flags": {"raw_entity_field_untyped": bool(top_entities)},
            "noise_rate": float(noise_rate) if noise_rate is not None else None,
        },
        "confidence": confidence_band(
            evidence_count=signal_count,
            source_count=source_count,
            geo_count=country_count,
            assignment_confidence=avg_conf if avg_conf is not None else 0.0,
        ),
        "why_now": _why_now(
            changed_10h,
            subject_countries=subject_countries,
            subject_status=subject_geography.get("status"),
        ),
        "subthreads": [],
        "related_threads": [],
        "evidence_samples": [_serialize_evidence(sig) for sig in sample_signals],
        "narrative_note": None,
        "cluster_cohesion": float(cohesion) if cohesion is not None else None,
        # Label Court (#204/#224): the verdict on this thread's own label vs its
        # receipts. NULL until the nightly court runs; the surface falls back to
        # the confidence band when unchecked. `label_proposed` is the neutral
        # receipt-derived alternative on 'failed' (advisory, never auto-served).
        "label_status": _record_get(topic_row, "label_status"),
        "label_proposed": _record_get(topic_row, "label_proposed"),
        "source": "dynamic_topics",
    })


async def _fetch_dynamic_threads_with_conn(
    conn: Any,
    *,
    hours: int,
    limit: int,
    country_code: str | None = None,
) -> list[dict[str, Any]]:
    has_topics = await conn.fetchval(
        "SELECT to_regclass('dynamic_topics') IS NOT NULL"
    )
    has_members = await conn.fetchval(
        "SELECT to_regclass('dynamic_topic_members') IS NOT NULL"
    )
    if not has_topics or not has_members:
        return []
    # 15s (was 8): the top-level query runs several correlated array subqueries per
    # row over the full active set; cold it lands ~7-9s and an 8s cap intermittently
    # degraded it to atlas-only (dropping the R2 umbrellas). Redis caches the result
    # so the cold hit is once per window. (Perf follow-up: fold the array subqueries.)
    if country_code:
        # country view = R1 scoped CHILDREN whose primary country is country_code
        topic_rows = await conn.fetch(
            _DYNAMIC_TOPICS_COUNTRY_SQL, hours, limit, country_code.upper(), timeout=15
        )
    else:
        topic_rows = await conn.fetch(_DYNAMIC_TOPICS_SQL, hours, limit, timeout=15)
    threads: list[dict[str, Any]] = []
    for topic in topic_rows:
        sample_ids = list(topic["sample_signal_ids"] or [])
        sample_signals = []
        if sample_ids:
            sample_signals = await conn.fetch(
                _EMERGENT_SAMPLE_SIGNALS_SQL, sample_ids, timeout=8,
            )
        threads.append(assemble_dynamic_thread(topic, list(sample_signals)))
    return threads


async def _thread_public_attention(
    conn: Any,
    related_themes: list[dict],
) -> dict | None:
    """Best-effort public-attention slice for a thread, keyed on its top GDELT
    theme. Reuses the trends/wiki match query logic. Any failure -> None, so it
    can never break thread detail."""
    if not related_themes:
        return None
    theme = related_themes[0].get("theme")
    if not theme:
        return None
    try:
        label = get_theme_label(theme).lower()
        theme_words = [w for w in label.split() if len(w) > 3]
        if not theme_words:
            return None

        # Trends match — same query as GET /api/v2/trends/match
        trends_conditions = " OR ".join(
            [f"LOWER(keyword) LIKE '%' || ${i + 1} || '%'" for i in range(len(theme_words))]
        )
        trends_query = f"""
            SELECT keyword, country_code, rank
            FROM trends_v2
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            AND ({trends_conditions})
            ORDER BY rank ASC
            LIMIT 10
        """
        trends_rows = await conn.fetch(trends_query, *theme_words)
        trends_matches = [
            {"keyword": r["keyword"], "country_code": r["country_code"], "rank": r["rank"]}
            for r in trends_rows
        ]

        # Wiki match — same query as GET /api/v2/wiki/match
        wiki_conditions = " OR ".join(
            [f"LOWER(article_title) LIKE '%' || ${i + 1} || '%'" for i in range(len(theme_words))]
        )
        wiki_query = f"""
            SELECT article_title, SUM(views) as views, COUNT(DISTINCT country_code) as country_count
            FROM wiki_pageviews_v2
            WHERE fetch_date >= CURRENT_DATE - ('1 days')::INTERVAL
            AND ({wiki_conditions})
            GROUP BY article_title
            ORDER BY views DESC
            LIMIT 5
        """
        wiki_rows = await conn.fetch(wiki_query, *theme_words)
        wiki_matches = [
            {"title": r["article_title"], "views": r["views"], "country_count": r["country_count"]}
            for r in wiki_rows
        ]

        result = {"trends": trends_matches, "wiki": wiki_matches}
        return result if (trends_matches or wiki_matches) else None
    except Exception:
        return None


async def _fetch_dynamic_thread_detail(
    conn: Any,
    *,
    dynamic_topic_id: int,
) -> dict[str, Any] | None:
    has_topics = await conn.fetchval(
        "SELECT to_regclass('dynamic_topics') IS NOT NULL"
    )
    has_members = await conn.fetchval(
        "SELECT to_regclass('dynamic_topic_members') IS NOT NULL"
    )
    if not has_topics or not has_members:
        return None
    topic = await conn.fetchrow(_DYNAMIC_TOPIC_DETAIL_SQL, dynamic_topic_id, timeout=8)
    if topic is None:
        return None
    sample_ids = list(topic["sample_signal_ids"] or [])
    sample_signals = []
    if sample_ids:
        sample_signals = await conn.fetch(
            _EMERGENT_SAMPLE_SIGNALS_SQL, sample_ids, timeout=8,
        )
    detail = assemble_dynamic_thread(topic, list(sample_signals))
    packet_rows = [
        {**dict(r), "sentiment": (r["nlp_sentiment"] if "nlp_sentiment" in r else r["sentiment"])}
        for r in sample_signals
    ]
    detail["packet"] = build_thread_packet(packet_rows)
    detail["packet"]["public_attention"] = await _thread_public_attention(conn, detail["packet"]["relatedThemes"])
    return detail


async def _fetch_emergent_threads_with_conn(
    conn: Any,
    *,
    hours: int,
    limit: int,
) -> list[dict[str, Any]]:
    """Surface the latest `emergent_clusters` snapshot as living threads.

    Returns [] when:
      - the emergent_clusters table is missing (pre-mig 046 deploys),
      - no snapshot landed within the requested `hours` window,
      - the cluster sample_signal_ids set is empty.

    The atlas path is unaffected by any failure here; the caller merges
    whatever survives.
    """
    has_table = await conn.fetchval(
        "SELECT to_regclass('emergent_clusters') IS NOT NULL"
    )
    if not has_table:
        return []
    snap_row = await conn.fetchrow(
        f"SELECT MAX(snapshot_at) AS snap FROM emergent_clusters "
        f"WHERE snapshot_at > NOW() - INTERVAL '{int(hours)} hours'"
    )
    snap = snap_row["snap"] if snap_row else None
    if snap is None:
        return []
    cluster_rows = await conn.fetch(
        """
        SELECT id, label, description, snapshot_at, snapshot_window_h,
               sample_signal_ids, top_country_codes, n_signals,
               raw_signal_count, velocity, cohesion, gate_threshold
        FROM emergent_clusters
        WHERE snapshot_at = $1
        ORDER BY velocity DESC NULLS LAST, n_signals DESC
        LIMIT $2
        """,
        snap,
        limit,
        timeout=8,
    )
    threads: list[dict[str, Any]] = []
    for cluster in cluster_rows:
        sample_ids = list(cluster["sample_signal_ids"] or [])
        sample_signals = []
        if sample_ids:
            sample_signals = await conn.fetch(
                _EMERGENT_SAMPLE_SIGNALS_SQL, sample_ids, timeout=8,
            )
        gate_thr = cluster["gate_threshold"]
        threads.append(assemble_emergent_thread(
            cluster,
            list(sample_signals),
            gate_threshold=float(gate_thr) if gate_thr is not None else None,
        ))
    return threads


async def _fetch_emergent_thread_detail(
    conn: Any,
    *,
    cluster_id: int,
) -> dict[str, Any] | None:
    """Detail-fetch variant for a single emergent cluster thread."""
    has_table = await conn.fetchval(
        "SELECT to_regclass('emergent_clusters') IS NOT NULL"
    )
    if not has_table:
        return None
    cluster = await conn.fetchrow(
        """
        SELECT id, label, description, snapshot_at, snapshot_window_h,
               sample_signal_ids, top_country_codes, n_signals,
               raw_signal_count, velocity, cohesion, gate_threshold
        FROM emergent_clusters WHERE id = $1
        """,
        cluster_id,
        timeout=8,
    )
    if cluster is None:
        return None
    sample_ids = list(cluster["sample_signal_ids"] or [])
    sample_signals = []
    if sample_ids:
        sample_signals = await conn.fetch(
            _EMERGENT_SAMPLE_SIGNALS_SQL, sample_ids, timeout=8,
        )
    gate_thr = cluster["gate_threshold"]
    detail = assemble_emergent_thread(
        cluster,
        list(sample_signals),
        gate_threshold=float(gate_thr) if gate_thr is not None else None,
    )
    packet_rows = [
        {**dict(r), "sentiment": (r["nlp_sentiment"] if "nlp_sentiment" in r else r["sentiment"])}
        for r in sample_signals
    ]
    detail["packet"] = build_thread_packet(packet_rows)
    detail["packet"]["public_attention"] = await _thread_public_attention(conn, detail["packet"]["relatedThemes"])
    return detail


async def _fetch_threads_with_conn(
    conn: Any,
    *,
    hours: int,
    limit: int,
    topic_slug: str | None,
    country_codes: list[str] | None,
) -> list[dict[str, Any]]:
    if serve_threads_from_topic_members():
        rows = await conn.fetch(
            THREADS_SQL_TOPIC_MEMBERS,
            hours,
            limit,
            topic_slug,
            country_codes or None,
            topic_members_engine_version(),
            timeout=8,
        )
    else:
        rows = await conn.fetch(
            THREADS_SQL,
            hours,
            limit,
            topic_slug,
            country_codes or None,
            timeout=8,
        )
    return [assemble_thread(row) for row in rows]


# Atlas topic slugs where a person appears in the FULL signal persons array
# (precise — not the capped top_entities). Low-risk: a separate lightweight
# query, never touches the THREADS_SQL spine.
_PERSON_TOPIC_SLUGS_SQL = """
    SELECT DISTINCT at.slug
    FROM signal_topic_assignments sta
    JOIN atlas_topics at ON at.id = sta.topic_id
    JOIN signals_v2 s ON s.id = sta.signal_id,
         unnest(s.persons) AS p
    WHERE sta.model_version = 'theme-hint-lex-v2'
      AND sta.assigned_at >= NOW() - ($1::int * INTERVAL '1 hour')
      AND s.persons IS NOT NULL
      AND LOWER(p) LIKE '%' || LOWER($2) || '%'
"""


def thread_matches_person(
    thread: dict[str, Any], matching_slugs: set[str], person_lower: str
) -> bool:
    """True if a thread relates to the focused person (#234). Atlas threads
    match precisely — their topic slug is among ``matching_slugs`` (the slugs
    where the person appears in the full signal `persons` array). Dynamic /
    emergent threads have no atlas slug, so they fall back to their capped
    `top_entities`. Empty person → no filter."""
    if not person_lower:
        return True
    entities = thread.get("top_entities") or []
    if any(person_lower in str(e).lower() for e in entities):
        return True
    tid = str(thread.get("thread_id", ""))
    if tid.startswith("dynamic-topic-") or tid.startswith("emergent-cluster-"):
        return False
    anchor = thread.get("anchor_topics") or []
    return any(str(s).lower() in matching_slugs for s in anchor)


def _is_atlas_thread(thread: dict[str, Any]) -> bool:
    """Atlas-anchored list threads are identified by a thread_id that does
    NOT carry the dynamic/emergent prefixes. Dynamic and emergent threads
    already attach evidence_samples in their assembly paths; atlas-fill
    threads do not (the list query is aggregate-only)."""
    tid = str(thread.get("thread_id", ""))
    return not (
        tid.startswith(DYNAMIC_TOPIC_THREAD_PREFIX)
        or tid.startswith(EMERGENT_CLUSTER_THREAD_PREFIX)
    )


async def _attach_atlas_evidence(
    active_conn: Any,
    threads: list[dict[str, Any]],
    *,
    hours: int,
    enrich_top_n: int = 10,
    per_thread: int = 4,
) -> None:
    """Attach a few evidence headline samples to atlas-fill threads in the
    LIST path so the top-ranked thread carries its evidence in the briefing
    payload (regression after unified ranking — atlas threads can now lead).

    Bounded to avoid an N+1 explosion: only the first ``enrich_top_n`` threads
    (the briefing shows ~10) that are atlas-anchored AND currently missing
    evidence are enriched, one bounded query each. Resilient: any failure
    degrades that thread to evidence_samples=[] and never raises."""
    enriched = 0
    for thread in threads:
        if enriched >= enrich_top_n:
            break
        if thread.get("evidence_samples"):
            continue
        if not _is_atlas_thread(thread):
            continue
        anchor_topics = thread.get("anchor_topics") or []
        topic_slug = str(anchor_topics[0]) if anchor_topics else ""
        if not topic_slug:
            continue
        enriched += 1
        country_codes = [str(c) for c in (thread.get("top_countries") or []) if c]
        try:
            evidence_rows = await active_conn.fetch(
                THREAD_EVIDENCE_SQL,
                hours,
                topic_slug,
                country_codes or None,
                per_thread,
                timeout=8,
            )
            thread["evidence_samples"] = [
                _serialize_evidence(row) for row in evidence_rows
            ]
        except Exception as exc:  # noqa: BLE001 - degrade, never 500
            logger.warning(
                "atlas evidence enrichment degraded for %s: %s",
                thread.get("thread_id"),
                exc,
            )
            thread["evidence_samples"] = thread.get("evidence_samples") or []


# ── Cross-language event de-duplication (serve-time, conservative) ───────────
#
# Clustering (project_dynamic_topics.py) splits ONE real-world event into two
# dynamic-topic identities when its coverage is in different languages: an
# English headline and a Russian/Spanish/etc. headline about the same event
# embed to different e5 centroids, well below MATCH_THRESHOLD (0.88), so they
# never link into one identity. Each gets its own DeepSeek label
# ("Venezuela Earthquakes" vs "Venezuela Earthquake Disaster"), so the existing
# exact-lowercased-label dedup in the merge below cannot catch them.
#
# The proper fix is at the clustering layer (a cross-language event signature —
# see the data-layer proposal in the handoff). This serve-time guard is a
# CONSERVATIVE safety net: it collapses two watchlist rows ONLY when they very
# clearly describe the same event, and never fuses two genuinely distinct
# same-country stories.
#
# Merge fires only when BOTH hold (strong conjunction):
#   1. identical PRIMARY-country set (top-2 codes as a set), AND
#   2. a shared DISTINCTIVE label token after removing the country name(s) and
#      generic words — the event signature (e.g. "earthquake"). Two same-country
#      threads with different subject words ("Venezuela Earthquakes" vs
#      "Venezuela Election Dispute") share NO distinctive token, so they stay
#      separate. A bare country-name overlap is explicitly insufficient.

# Generic label tokens that recur across topic labels WITHOUT identifying the
# event. "in/and/the" are structural ("X in A and B"); the rest are common news
# words. Kept compact; matching takes the *intersection* of distinctive tokens,
# so a stray generic leak cannot, on its own, fuse two threads.
_LABEL_GENERIC_TOKENS = frozenset(
    {
        "in", "and", "the", "of", "on", "for", "to", "a", "an", "amid", "as",
        "after", "over", "with", "from", "news", "update", "updates", "latest",
        "crisis", "report", "reports", "story", "stories", "live", "regions",
        "multiple", "region", "regional",
    }
)

# Country-name tokens (lowercased words from every ISO name) so the place itself
# is never treated as the event signature. "venezuela", "united", "states",
# "korea", etc. — same place is necessary but never sufficient to merge.
_COUNTRY_NAME_TOKENS = frozenset(
    tok
    for name in ISO_COUNTRY_NAMES.values()
    for tok in re.findall(r"[a-z]{2,}", name.lower())
)


def _distinctive_label_tokens(label: str, country_codes: list[str]) -> set[str]:
    """Distinctive (event-identifying) tokens of a thread label.

    Lowercases, splits on non-letters, drops generic news/structure words, the
    place name (both the resolved country name tokens and any ISO name token),
    and applies a tiny English plural stem so "earthquake"/"earthquakes" match.
    Returns an empty set when the label carries no distinctive token (then the
    pair is treated as undecidable and never merged).
    """
    place_tokens: set[str] = set()
    for code in country_codes:
        place_tokens |= set(
            re.findall(r"[a-z]{2,}", resolve_country_name(code).lower())
        )

    out: set[str] = set()
    for raw in re.findall(r"[^\W\d_]{2,}", (label or "").lower(), re.UNICODE):
        if raw in _LABEL_GENERIC_TOKENS:
            continue
        if raw in place_tokens or raw in _COUNTRY_NAME_TOKENS:
            continue
        # crude English plural stem: earthquakes -> earthquake, riots -> riot.
        stem = raw[:-1] if (len(raw) > 4 and raw.endswith("s")) else raw
        out.add(stem)
    return out


def _primary_country_key(thread: dict[str, Any], top_k: int = 2) -> frozenset[str]:
    codes = [str(c).upper() for c in (thread.get("top_countries") or []) if c]
    return frozenset(codes[:top_k])


def same_event(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """True iff two threads clearly describe the same real-world event.

    Conservative by construction: requires an identical non-empty primary-country
    set AND at least one shared distinctive label token. Either condition alone
    is insufficient, so two distinct same-country stories never merge.
    """
    key_a = _primary_country_key(a)
    key_b = _primary_country_key(b)
    if not key_a or key_a != key_b:
        return False
    tokens_a = _distinctive_label_tokens(str(a.get("label") or ""), list(key_a))
    tokens_b = _distinctive_label_tokens(str(b.get("label") or ""), list(key_b))
    if not tokens_a or not tokens_b:
        return False
    return bool(tokens_a & tokens_b)


def _merge_event_pair(keep: dict[str, Any], drop: dict[str, Any]) -> dict[str, Any]:
    """Fold ``drop`` into ``keep`` (the higher-ranked survivor).

    The two threads are different-language coverage of one event, so their signal
    sets are DISJOINT — volume/source counts are SUMMED (union of distinct
    coverage), and changed_10h is summed (both deltas are real new signals).
    Country / source / entity / evidence lists are unioned, keep's order first.
    """
    def _union(primary: list, extra: list) -> list:
        seen: set = set()
        out: list = []
        for item in (primary or []) + (extra or []):
            marker = json.dumps(item, sort_keys=True, default=str) if isinstance(
                item, (dict, list)
            ) else item
            if marker in seen:
                continue
            seen.add(marker)
            out.append(item)
        return out

    keep["signal_count"] = int(keep.get("signal_count") or 0) + int(
        drop.get("signal_count") or 0
    )
    keep["source_count"] = max(
        int(keep.get("source_count") or 0), int(drop.get("source_count") or 0)
    )
    keep["changed_10h"] = int(keep.get("changed_10h") or 0) + int(
        drop.get("changed_10h") or 0
    )
    keep["top_countries"] = _union(
        keep.get("top_countries"), drop.get("top_countries")
    )[:5]
    keep["top_country_names"] = _union(
        keep.get("top_country_names"), drop.get("top_country_names")
    )[:5]
    keep["top_sources"] = _union(keep.get("top_sources"), drop.get("top_sources"))[:5]
    keep["top_entities"] = _union(
        keep.get("top_entities"), drop.get("top_entities")
    )[:10]
    keep["evidence_samples"] = _union(
        keep.get("evidence_samples"), drop.get("evidence_samples")
    )
    # Record the fold so the merge is never a silent filter (project guardrail).
    merged_ids = list(keep.get("merged_thread_ids") or [])
    if drop.get("thread_id"):
        merged_ids.append(str(drop.get("thread_id")))
    if merged_ids:
        keep["merged_thread_ids"] = merged_ids
    # trend reflects the new combined movement
    keep["trend"] = _trend_label(
        int(keep.get("changed_10h") or 0), int(keep.get("signal_count") or 0)
    )
    return keep


def dedupe_same_event_threads(threads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse cross-language duplicates of one event, preserving input order.

    ``threads`` MUST already be in served (ranked) order: the first occurrence of
    an event survives and absorbs later duplicates, so the higher-ranked row is
    always the one kept. Pure and order-stable.
    """
    survivors: list[dict[str, Any]] = []
    for thread in threads:
        match = next((s for s in survivors if same_event(s, thread)), None)
        if match is None:
            survivors.append(thread)
        else:
            _merge_event_pair(match, thread)
    return survivors


_DISCUSSION_COUNT_SQL = """
SELECT at.slug AS slug, COUNT(DISTINCT a.signal_id)::int AS n,
       AVG(COALESCE(s.nlp_sentiment, s.sentiment))::float AS forum_sentiment
FROM signal_topic_assignments a
JOIN atlas_topics at ON at.id = a.topic_id
JOIN signals_v2 s ON s.id = a.signal_id
WHERE a.model_version = 'semantic-discussion-v1'
  AND a.assigned_at >= NOW() - ($1::int * INTERVAL '1 hour')
  AND at.slug = ANY($2::text[])
  AND ($3::text[] IS NULL OR s.country_code = ANY($3::text[]))
GROUP BY at.slug
"""


async def _attach_discussion_counts(
    conn: Any, threads: list[dict[str, Any]], *, hours: int,
    country_codes: list[str] | None,
) -> None:
    """#168/Tier2: people-side discussion members (forums attached semantically),
    counted SEPARATELY from gated evidence and never folded into signal_count.
    Also serves forum_sentiment (T2.3) so a thread can show press-vs-public."""
    slugs = sorted({
        s for t in threads for s in (t.get("anchor_topics") or [])
    })
    for t in threads:
        t.setdefault("discussion_count", 0)
        t.setdefault("forum_sentiment", None)
    if not slugs:
        return
    try:
        rows = await conn.fetch(_DISCUSSION_COUNT_SQL, hours, slugs, country_codes)
    except Exception as exc:  # additive — never break the thread list
        logger.warning("discussion counts degraded: %s", exc)
        return
    counts = {str(r["slug"]): int(r["n"]) for r in rows}
    sents = {
        str(r["slug"]): float(r["forum_sentiment"])
        for r in rows if r["forum_sentiment"] is not None
    }
    for t in threads:
        anchors = t.get("anchor_topics") or []
        t["discussion_count"] = sum(counts.get(s, 0) for s in anchors)
        # count-weighted forum sentiment across the thread's anchor topics
        num = sum(sents[s] * counts.get(s, 0) for s in anchors if s in sents)
        den = sum(counts.get(s, 0) for s in anchors if s in sents)
        t["forum_sentiment"] = round(num / den, 3) if den > 0 else None


async def fetch_threads(
    *,
    hours: int = 24,
    limit: int = 10,
    topic_slug: str | None = None,
    country_codes: list[str] | None = None,
    person: str | None = None,
    attach_evidence: bool = False,
    conn: Any = None,
) -> list[dict[str, Any]]:
    """Returns atlas-anchored threads merged with emergent-cluster threads
    from the latest `emergent_clusters` snapshot, sorted by signal_count
    and trimmed to `limit`.

    When the caller filters by `topic_slug` or `country_codes`, the
    emergent path is skipped — those filters target the atlas taxonomy
    (atlas slugs / atlas country aggregates) and have no emergent
    analog yet. Emergent threads have their own detail dispatch via the
    `emergent-cluster-<id>` thread_id prefix.
    """
    # Dynamic topics apply for the GLOBAL list and for a SINGLE-country view (the R1
    # scoped children for that country — "Venezuela Earthquake" for VE, not the atlas
    # generic "Armed conflict in Venezuela"). topic_slug + multi-country stay atlas-only
    # (no dynamic analog for an atlas slug; multi-country isn't a scoped partition).
    single_country = (
        country_codes[0] if (country_codes and len(country_codes) == 1) else None
    )
    atlas_only = bool(topic_slug) or (bool(country_codes) and single_country is None)

    async def _merged(active_conn: Any) -> list[dict[str, Any]]:
        # STORIES-ONLY list (Pedro, 2026-07-04 — supersedes the 2026-06-24
        # "unified ranking" merge): an atlas topic is a CATEGORY (the R3
        # lens), not a thread. Decide that product mode before doing database
        # work so the default path never pays for category rows it discards.
        _on = {"1", "true", "on", "yes"}
        category_rows = (
            os.environ.get("ATLAS_THREADS_CATEGORY_ROWS", "").strip().lower() in _on
            or (single_country is not None and os.environ.get(
                "ATLAS_COUNTRY_CATEGORY_ROWS", ""
            ).strip().lower() in _on)
        )
        if atlas_only:
            return await _fetch_threads_with_conn(
                active_conn,
                hours=hours,
                limit=limit,
                topic_slug=topic_slug,
                country_codes=country_codes,
            )

        dynamic: list[dict[str, Any]] = []
        try:
            dynamic = await _fetch_dynamic_threads_with_conn(
                active_conn, hours=hours, limit=limit, country_code=single_country,
            )
        except TimeoutError:
            raise
        except Exception as exc:
            logger.warning("dynamic topics degraded: %s", exc)
            dynamic = []
        # Serving category aggregates as sibling rows
        # next to real stories was level-mixing ("Gang control and urban
        # security n=319" beside "Ukraine War Updates n=107"). The global
        # list serves STORY rows only — dynamic topics, emergent clusters as
        # the degraded fallback; the category lives on each row as its badge
        # (crisis_class) and in the drill-down (memberStories). A thin
        # substrate yields a SHORT list, never category filler (same honesty
        # rule as the country 0-threads empty state).
        # X3 (2026-07-05, closes the 07-04 deferral): the SINGLE-COUNTRY view
        # is stories-only too — R1 scoped children ("Venezuela Earthquake"),
        # never atlas category aggregates as filler. A country with no scoped
        # stories gets a SHORT/empty list (the CLAUDE.md guardrail verbatim).
        # Kill-switches: ATLAS_THREADS_CATEGORY_ROWS=on restores the merge
        # everywhere; ATLAS_COUNTRY_CATEGORY_ROWS=on restores it for the
        # country view only (independent CountryBrief revert).
        if category_rows:
            atlas = await _fetch_threads_with_conn(
                active_conn,
                hours=hours,
                limit=limit,
                topic_slug=topic_slug,
                country_codes=country_codes,
            )
            dynamic_labels = {
                str(t.get("label") or "").strip().lower() for t in dynamic
            }
            atlas_extra = [
                t for t in atlas
                if str(t.get("label") or "").strip().lower() not in dynamic_labels
            ]
            ranked = rank_threads(dynamic + atlas_extra)
            return dedupe_same_event_threads(ranked)[:limit]
        if dynamic:
            return dedupe_same_event_threads(rank_threads(dynamic))[:limit]
        # X3: the emergent fallback is GLOBAL (no country scoping) — serving
        # it inside a country view would be filler. Honest empty instead.
        if single_country is not None:
            return []
        try:
            emergent = await _fetch_emergent_threads_with_conn(
                active_conn, hours=hours, limit=limit,
            )
        except TimeoutError:
            raise
        except Exception as exc:
            logger.warning("emergent threads degraded: %s", exc)
            emergent = []
        return dedupe_same_event_threads(rank_threads(emergent))[:limit]

    async def _run(active_conn: Any) -> list[dict[str, Any]]:
        threads = await _merged(active_conn)
        if person:
            person_lower = person.strip().lower()
            try:
                rows = await active_conn.fetch(_PERSON_TOPIC_SLUGS_SQL, hours, person_lower)
                matching_slugs = {str(r["slug"]).lower() for r in rows}
            except Exception as exc:
                logger.warning("person thread filter degraded: %s", exc)
                matching_slugs = set()
            threads = [
                t for t in threads
                if thread_matches_person(t, matching_slugs, person_lower)
            ]
        if attach_evidence and threads:
            await _attach_atlas_evidence(active_conn, threads, hours=hours)
        if threads:
            await _attach_discussion_counts(
                active_conn, threads, hours=hours, country_codes=country_codes,
            )
        return threads

    try:
        if conn is not None:
            return await _run(conn)

        if db.pool is None:
            logger.warning("thread intelligence requested without database pool")
            return []

        async with db.pool.acquire() as own_conn:
            return await _run(own_conn)
    except TimeoutError as exc:
        raise DatabaseBusyError("database command timed out") from exc


async def fetch_thread_detail(
    *,
    thread_id: str,
    hours: int = 24,
) -> dict[str, Any] | None:
    if thread_id.startswith(DYNAMIC_TOPIC_THREAD_PREFIX):
        topic_id_str = thread_id[len(DYNAMIC_TOPIC_THREAD_PREFIX):]
        if not topic_id_str.isdigit():
            return None
        if db.pool is None:
            return None
        async with db.pool.acquire() as conn:
            return await _fetch_dynamic_thread_detail(
                conn, dynamic_topic_id=int(topic_id_str),
            )

    # Emergent cluster threads route through their own detail builder.
    # The shape returned matches `assemble_emergent_thread`, so the
    # ThreadFocusPanel renders the same fields as the atlas branch.
    if thread_id.startswith(EMERGENT_CLUSTER_THREAD_PREFIX):
        cluster_id_str = thread_id[len(EMERGENT_CLUSTER_THREAD_PREFIX):]
        if not cluster_id_str.isdigit():
            return None
        if db.pool is None:
            return None
        async with db.pool.acquire() as conn:
            return await _fetch_emergent_thread_detail(
                conn, cluster_id=int(cluster_id_str),
            )

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
    threads[0]["narrative_note"] = build_thread_narrative_note(threads[0])
    packet_rows = [
        {**dict(r), "sentiment": (r["nlp_sentiment"] if "nlp_sentiment" in r else r["sentiment"])}
        for r in evidence_rows
    ]
    threads[0]["packet"] = build_thread_packet(packet_rows)
    threads[0]["packet"]["public_attention"] = await _thread_public_attention(conn, threads[0]["packet"]["relatedThemes"])
    return threads[0]


# ── Unified Engine F0.4 — topic relationship (spec §9.2) ─────────────────────
_TOPIC_ROLE_COUNTS_SQL = """
SELECT role, COUNT(DISTINCT COALESCE(signal_id::text, member_ref))::int AS n
FROM topic_members
WHERE topic_id = $1
  AND assigned_at >= NOW() - ($3::int * INTERVAL '1 hour')
  AND (
        -- evidence stays engine-versioned (serving parity with the gated counts)
        (role = 'evidence' AND engine_version = $2)
        -- discussion/mood: the v1-compat engine holds ~0 of these (mood is
        -- structurally empty there) while unified-v2 carries the real social
        -- lanes — pinning to $2 made the endpoint assert "no discussion/mood"
        -- for topics that HAVE both (2026-07-01 L0-L3 audit). Count them
        -- engine-agnostic, deduped by signal so a member in both engines
        -- counts once. This is the documented v1‖v2 UNION debt, paid here.
     OR (role IN ('discussion','mood'))
        -- movement is the EVENT layer (CAMEO movement-v1 + disaster-v1), a
        -- separate substrate keyed by member_ref, independent of the signal
        -- engine version — count every event-kind movement member
     OR (role = 'movement' AND member_kind = 'event')
      )
GROUP BY role
"""


async def fetch_topic_relationship(
    *, topic_id: str, hours: int = 168
) -> dict[str, Any]:
    """The #168 relationship type for a topic, computed from its typed
    `topic_members` role counts (evidence/discussion/mood/movement). Reads the
    'v1-compat' engine version; F3 exposes 'unified-v2'. Honesty invariant
    (spec §15): evidence is press-only; discussion/mood are social
    (verified=false) and are NEVER folded into the evidence count."""
    counts = {"evidence": 0, "discussion": 0, "mood": 0, "movement": 0}
    if db.pool is None:
        logger.warning("topic relationship requested without database pool")
        return classify_relationship(**counts)
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            _TOPIC_ROLE_COUNTS_SQL,
            topic_id,
            topic_members_engine_version(),
            hours,
            timeout=8,
        )
    for r in rows:
        role = str(r["role"])
        if role in counts:
            counts[role] = int(r["n"])
    return classify_relationship(**counts)
