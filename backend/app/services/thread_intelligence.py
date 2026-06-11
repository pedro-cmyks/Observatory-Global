from __future__ import annotations

import html
import json
import logging
from typing import Any

from app import db
from app.core.gdelt_taxonomy import get_theme_label
from app.services.narrative_note import build_thread_narrative_note
from app.services.thread_packet import build_thread_packet

logger = logging.getLogger(__name__)

THREAD_MODEL_VERSION = "theme-hint-lex-v2"

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
    if len(top_countries) >= 2:
        place = f"{top_countries[0]} and {top_countries[1]}"
    elif top_countries:
        place = top_countries[0]
    else:
        place = "multiple regions"

    return f"{anchor_label} in {place}"


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
    lex_count = int(_record_get(row, "lex_count") or 0)
    theme_count = int(_record_get(row, "theme_count") or 0)
    source_count = int(_record_get(row, "source_count") or 0)
    country_count = int(_record_get(row, "country_count") or 0)
    avg_confidence = float(_record_get(row, "avg_confidence") or 0)
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
        "why_now": _why_now(changed_10h, country_names),
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
    return {
        "id": str(_record_get(row, "id")),
        "headline": headline,
        "snippet": _record_get(row, "snippet"),
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
    label_text = str(_record_get(cluster_row, "label") or f"cluster {cluster_id}")
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
    avg_conf = float(gate_threshold) if gate_threshold is not None else 0.9

    return _with_narrative_note({
        "thread_id": f"{EMERGENT_CLUSTER_THREAD_PREFIX}{cluster_id}",
        "label": label_text,
        "summary": description or label_text,
        "anchor_topics": [f"cluster-{cluster_id}"],
        "parent_domain": None,
        "signal_count": signal_count,
        "source_count": source_count,
        "country_count": country_count,
        "avg_confidence": round(avg_conf, 3),
        "first_seen": snap_at.isoformat() if hasattr(snap_at, "isoformat") else snap_at,
        "changed_10h": velocity,
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
            assignment_confidence=avg_conf,
        ),
        "why_now": _why_now(velocity, country_codes),
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
           timestamp,
           persons,
           themes,
           sentiment        AS nlp_sentiment,
           1::int           AS syndication_count,
           NULL::float      AS confidence
    FROM signals_v2
    WHERE id = ANY($1::bigint[])
    ORDER BY timestamp DESC
"""


_DYNAMIC_TOPICS_SQL = """
SELECT
    dt.id,
    dt.identity_key,
    dt.label,
    dt.first_seen,
    dt.last_seen,
    dt.agg_n_signals,
    dt.mean_cohesion,
    dt.noise_rate,
    -- current volume (#224): the latest member cluster's kept-signal count.
    -- Lifetime agg_n_signals accumulates forever and let stale identities
    -- dominate the list by construction.
    COALESCE((
        SELECT ec4.n_signals
        FROM dynamic_topic_members dtm4
        JOIN emergent_clusters ec4 ON ec4.id = dtm4.emergent_cluster_id
        WHERE dtm4.dynamic_topic_id = dt.id
        ORDER BY dtm4.snapshot_at DESC
        LIMIT 1
    ), 0)::int AS recent_n_signals,
    COALESCE(MAX(ec.velocity), 0)::int AS changed_10h,
    ARRAY(
        SELECT DISTINCT code
        FROM dynamic_topic_members dtm2
        JOIN emergent_clusters ec2 ON ec2.id = dtm2.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec2.top_country_codes, ARRAY[]::text[])) AS code
        WHERE dtm2.dynamic_topic_id = dt.id
        LIMIT 5
    ) AS top_country_codes,
    ARRAY(
        SELECT DISTINCT sid
        FROM dynamic_topic_members dtm3
        JOIN emergent_clusters ec3 ON ec3.id = dtm3.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec3.sample_signal_ids, ARRAY[]::bigint[])) AS sid
        WHERE dtm3.dynamic_topic_id = dt.id
        LIMIT 24
    ) AS sample_signal_ids
FROM dynamic_topics dt
LEFT JOIN dynamic_topic_members dtm ON dtm.dynamic_topic_id = dt.id
LEFT JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
WHERE dt.state = 'active'
  AND dt.last_seen > NOW() - ($1::int * INTERVAL '1 hour')
GROUP BY dt.id
ORDER BY recent_n_signals DESC, dt.last_seen DESC
LIMIT $2
"""


_DYNAMIC_TOPIC_DETAIL_SQL = """
SELECT
    dt.id,
    dt.identity_key,
    dt.label,
    dt.first_seen,
    dt.last_seen,
    dt.agg_n_signals,
    dt.mean_cohesion,
    dt.noise_rate,
    COALESCE(MAX(ec.velocity), 0)::int AS changed_10h,
    ARRAY(
        SELECT DISTINCT code
        FROM dynamic_topic_members dtm2
        JOIN emergent_clusters ec2 ON ec2.id = dtm2.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec2.top_country_codes, ARRAY[]::text[])) AS code
        WHERE dtm2.dynamic_topic_id = dt.id
        LIMIT 5
    ) AS top_country_codes,
    ARRAY(
        SELECT DISTINCT sid
        FROM dynamic_topic_members dtm3
        JOIN emergent_clusters ec3 ON ec3.id = dtm3.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec3.sample_signal_ids, ARRAY[]::bigint[])) AS sid
        WHERE dtm3.dynamic_topic_id = dt.id
        LIMIT 32
    ) AS sample_signal_ids
FROM dynamic_topics dt
LEFT JOIN dynamic_topic_members dtm ON dtm.dynamic_topic_id = dt.id
LEFT JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
WHERE dt.id = $1
  AND dt.state = 'active'
GROUP BY dt.id
"""


def assemble_dynamic_thread(topic_row: Any, sample_signals: list[Any]) -> dict[str, Any]:
    topic_id = int(_record_get(topic_row, "id"))
    label_text = str(_record_get(topic_row, "label") or f"dynamic topic {topic_id}")
    # current-window volume (#224); lifetime aggregate kept as metadata
    signal_count = int(
        _record_get(topic_row, "recent_n_signals")
        or _record_get(topic_row, "agg_n_signals")
        or 0
    )
    lifetime_signals = int(_record_get(topic_row, "agg_n_signals") or 0)
    changed_10h = int(_record_get(topic_row, "changed_10h") or 0)
    noise_rate = _record_get(topic_row, "noise_rate")
    avg_conf = 1.0 - float(noise_rate) if noise_rate is not None else 0.9
    cohesion = _record_get(topic_row, "mean_cohesion")
    first_seen = _record_get(topic_row, "first_seen")
    country_codes = [str(code) for code in (_record_get(topic_row, "top_country_codes") or [])]

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

    return _with_narrative_note({
        "thread_id": f"{DYNAMIC_TOPIC_THREAD_PREFIX}{topic_id}",
        "label": label_text,
        "summary": label_text,
        "anchor_topics": [str(_record_get(topic_row, "identity_key") or f"dynamic-topic-{topic_id}")],
        "parent_domain": None,
        "signal_count": signal_count,
        "lifetime_signal_count": lifetime_signals,
        "source_count": source_count,
        "country_count": country_count,
        "avg_confidence": round(max(min(avg_conf, 1.0), 0.0), 3),
        "first_seen": first_seen.isoformat() if hasattr(first_seen, "isoformat") else first_seen,
        "changed_10h": changed_10h,
        "trend": _trend_label(changed_10h, signal_count),
        "sentiment_swing_10h": None,
        "top_countries": country_codes,
        # Dynamic topics currently store country codes only. Leave names empty so
        # the frontend resolves display names instead of rendering ID + ID.
        "top_country_names": [],
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
            assignment_confidence=avg_conf,
        ),
        "why_now": _why_now(changed_10h, country_codes),
        "subthreads": [],
        "related_threads": [],
        "evidence_samples": [_serialize_evidence(sig) for sig in sample_signals],
        "narrative_note": None,
        "cluster_cohesion": float(cohesion) if cohesion is not None else None,
        "source": "dynamic_topics",
    })


async def _fetch_dynamic_threads_with_conn(
    conn: Any,
    *,
    hours: int,
    limit: int,
) -> list[dict[str, Any]]:
    has_topics = await conn.fetchval(
        "SELECT to_regclass('dynamic_topics') IS NOT NULL"
    )
    has_members = await conn.fetchval(
        "SELECT to_regclass('dynamic_topic_members') IS NOT NULL"
    )
    if not has_topics or not has_members:
        return []
    topic_rows = await conn.fetch(_DYNAMIC_TOPICS_SQL, hours, limit, timeout=8)
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
    """Returns atlas-anchored threads merged with emergent-cluster threads
    from the latest `emergent_clusters` snapshot, sorted by signal_count
    and trimmed to `limit`.

    When the caller filters by `topic_slug` or `country_codes`, the
    emergent path is skipped — those filters target the atlas taxonomy
    (atlas slugs / atlas country aggregates) and have no emergent
    analog yet. Emergent threads have their own detail dispatch via the
    `emergent-cluster-<id>` thread_id prefix.
    """
    is_atlas_filtered = bool(topic_slug or country_codes)

    async def _merged(active_conn: Any) -> list[dict[str, Any]]:
        dynamic: list[dict[str, Any]] = []
        if not is_atlas_filtered:
            try:
                dynamic = await _fetch_dynamic_threads_with_conn(
                    active_conn, hours=hours, limit=limit,
                )
            except Exception as exc:
                logger.warning("dynamic topics degraded: %s", exc)
                dynamic = []
        atlas = await _fetch_threads_with_conn(
            active_conn,
            hours=hours,
            limit=limit,
            topic_slug=topic_slug,
            country_codes=country_codes,
        )
        if is_atlas_filtered:
            return atlas
        if dynamic:
            # dynamic_topics is canonical when active rows exist; atlas and raw
            # emergent rows remain fallback sources to avoid reintroducing
            # static-taxonomy noise above the self-curated lifecycle.
            dynamic.sort(key=lambda t: int(t.get("signal_count") or 0), reverse=True)
            return dynamic[:limit]
        else:
            try:
                emergent = await _fetch_emergent_threads_with_conn(
                    active_conn, hours=hours, limit=limit,
                )
            except Exception as exc:
                logger.warning("emergent threads degraded: %s", exc)
                emergent = []
        combined = emergent + atlas
        combined.sort(key=lambda t: int(t.get("signal_count") or 0), reverse=True)
        return combined[:limit]

    if conn is not None:
        return await _merged(conn)

    if db.pool is None:
        logger.warning("thread intelligence requested without database pool")
        return []

    async with db.pool.acquire() as own_conn:
        return await _merged(own_conn)


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
