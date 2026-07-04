import html
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from app import db
from app.main_v2 import app
from app.utils import _is_valid_person, _resolve_persons, extract_domain, rank_key_people
from app.services.subjects import build_key_subjects, merge_entity_rows

logger = logging.getLogger("atlas.themes")
from app.core.gdelt_taxonomy import classify_source, get_concepts_for_theme
from app.services.processed_historical import (
    build_historical_coverage,
    query_historical_topic_detail,
    use_processed_history,
)
from app.services.thread_packet import build_thread_packet
import httpx

router = APIRouter()

@router.get("/api/v2/focus")
async def get_focus_data(
    focus_type: str = Query(..., description="Type: theme, person, country, source"),
    value: str = Query(..., description="Value to focus on"),
    hours: int = Query(24, ge=1, le=8760)
):
    """
    Get filtered data for Focus Mode.
    Returns nodes, related topics, and top sources matching the focus.
    """
    async with db.pool.acquire() as conn:
        # Build WHERE clause based on focus type
        if focus_type == "theme":
            # Thread ids resolve via typed membership (see focus_filters) —
            # ANY(themes) is GDELT-only and blanked the lens for threads.
            from app.services.focus_filters import thread_focus_filter
            thread_filter = thread_focus_filter(value)
            if thread_filter:
                focus_filter, filter_value = thread_filter
            else:
                focus_filter = "$1 = ANY(themes)"
                filter_value = value.upper()
        elif focus_type == "person":
            focus_filter = "EXISTS (SELECT 1 FROM unnest(persons) p WHERE LOWER(p) LIKE LOWER($1))"
            filter_value = f"%{value}%"
        elif focus_type == "country":
            focus_filter = "country_code = $1"
            filter_value = value.upper()
        elif focus_type == "source":
            focus_filter = "LOWER(source_name) LIKE LOWER($1)"
            filter_value = f"%{value}%"
        else:
            return {"error": f"Unknown focus type: {focus_type}"}
        
        # 1. Get nodes (countries) with signal counts
        nodes = await conn.fetch(f"""
            SELECT 
                country_code,
                COUNT(*) as signal_count,
                ROUND(AVG(sentiment)::numeric, 2) as avg_sentiment,
                COUNT(DISTINCT source_name) as unique_sources
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
            GROUP BY country_code
            ORDER BY signal_count DESC
        """, filter_value)
        
        # 2. Get related topics (co-occurring themes)
        related = await conn.fetch(f"""
            SELECT 
                unnest(themes) as topic,
                COUNT(*) as count
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
            GROUP BY topic
            ORDER BY count DESC
            LIMIT 15
        """, filter_value)
        
        # Filter out the focus value itself if it's a theme
        related_topics = [
            {"topic": r['topic'], "count": int(r['count'])}
            for r in related
            if r['topic'].upper() != value.upper()
        ][:10]
        
        # 3. Get top sources
        sources = await conn.fetch(f"""
            SELECT 
                source_name,
                COUNT(*) as count,
                ROUND(AVG(sentiment)::numeric, 2) as avg_sentiment
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
              AND source_name IS NOT NULL
            GROUP BY source_name
            ORDER BY count DESC
            LIMIT 10
        """, filter_value)
        
        # 4. Get recent headlines (deduped by title prefix)
        headlines = await conn.fetch(f"""
            SELECT DISTINCT ON (LEFT(source_url, 100))
                source_url,
                source_name,
                headline,
                timestamp
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
              AND source_url IS NOT NULL
            ORDER BY LEFT(source_url, 100), timestamp DESC
            LIMIT 10
        """, filter_value)

        # 5. Get key people mentioned in matching signals. distinct_outlets /
        # distinct_headlines feed the syndication-resistant ranking (#176): a
        # wire story republished by many outlets must not outrank local actors.
        # Pull a wide pool (40) so the corroboration floor still leaves results.
        persons_rows = await conn.fetch(f"""
            SELECT
                p AS person,
                COUNT(*) AS signal_count,
                COUNT(DISTINCT source_name) AS distinct_outlets,
                COUNT(DISTINCT headline) AS distinct_headlines,
                ROUND(AVG(sentiment)::numeric, 2) AS avg_sentiment,
                COUNT(DISTINCT country_code) AS country_count
            FROM signals_v2, unnest(persons) p
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
              AND p <> ''
              AND LENGTH(p) > 3
            GROUP BY p
            ORDER BY signal_count DESC
            LIMIT 40
        """, filter_value)

        key_people = [
            {
                "person": r['person'],
                "signal_count": int(r['signal_count']),
                "avg_sentiment": float(r['avg_sentiment'] or 0),
                "country_count": int(r['country_count'])
            }
            for r in rank_key_people([dict(r) for r in persons_rows], limit=8)
        ]
        # Typed subjects (#176 reframe): person is one type — "El Niño" surfaces
        # as an event, "República Dominicana" as a place, instead of vanishing or
        # posing as people. NER (spaCy) gives real verified types; the untyped
        # GDELT pool fills names NER missed, flagged unverified. NER query
        # degrades to GDELT-only on error (e.g. malformed nlp_persons jsonb).
        try:
            ner_rows = await conn.fetch(f"""
                SELECT e->>'name' AS name, e->>'type' AS ner_type,
                       COUNT(*) AS signal_count,
                       COUNT(DISTINCT source_name) AS distinct_outlets,
                       COUNT(DISTINCT headline) AS distinct_headlines
                FROM signals_v2,
                     jsonb_array_elements(
                       CASE WHEN jsonb_typeof(nlp_persons) = 'array' THEN nlp_persons
                            WHEN jsonb_typeof(nlp_persons_xlm) = 'array' THEN nlp_persons_xlm
                            ELSE '[]'::jsonb END
                     ) e
                WHERE timestamp > NOW() - INTERVAL '{hours} hours'
                  AND {focus_filter}
                  AND e->>'name' IS NOT NULL AND e->>'type' IS NOT NULL
                GROUP BY e->>'name', e->>'type'
                ORDER BY signal_count DESC
                LIMIT 40
            """, filter_value)
        except Exception as exc:
            logger.warning("NER subjects degraded: %s", exc)
            ner_rows = []
        key_subjects = build_key_subjects(
            merge_entity_rows(
                [dict(r) for r in ner_rows],
                [{
                    "name": r['person'],
                    "ner_type": None,
                    "signal_count": int(r['signal_count']),
                    "distinct_outlets": int(r['distinct_outlets']),
                    "distinct_headlines": int(r['distinct_headlines']),
                } for r in persons_rows],
            ),
            limit=8,
        )

        # Calculate totals
        total_signals = sum(int(n['signal_count']) for n in nodes)
        total_countries = len(nodes)

        return {
            "focus": {
                "type": focus_type,
                "value": value,
                "hours": hours
            },
            "summary": {
                "total_signals": total_signals,
                "total_countries": total_countries,
                "generated_at": datetime.now(timezone.utc).isoformat()
            },
            "nodes": [
                {
                    "country_code": r['country_code'],
                    "signal_count": int(r['signal_count']),
                    "avg_sentiment": float(r['avg_sentiment'] or 0),
                    "unique_sources": int(r['unique_sources'])
                }
                for r in nodes
            ],
            "related_topics": related_topics,
            "top_sources": [
                {
                    "source": extract_domain(r['source_name']),
                    "count": int(r['count']),
                    "avg_sentiment": float(r['avg_sentiment'] or 0)
                }
                for r in sources
            ],
            "headlines": [
                {
                    "url": r['source_url'],
                    "source": r['source_name'],
                    "headline": r['headline'],
                    "time": r['timestamp'].isoformat() if r['timestamp'] else None
                }
                for r in headlines
            ],
            "key_people": key_people,
            "key_subjects": key_subjects
        }

@router.get("/api/v2/theme/{theme_code}/drift")
async def get_theme_drift(
    theme_code: str,
    country_code: str = Query(None, description="Filter by country"),
    days: int = Query(14, ge=1, le=90)
):
    """Get daily sentiment and volume trajectory for a theme."""
    try:
        async with db.pool.acquire() as conn:
            where_conditions = [
                "$1 = ANY(themes)",
                f"timestamp > NOW() - INTERVAL '{days} days'"
            ]
            params = [theme_code.upper()]
            
            if country_code:
                where_conditions.append("country_code = $2")
                params.append(country_code.upper())
            
            where_clause = " AND ".join(where_conditions)
            
            drift_data = await conn.fetch(f"""
                SELECT 
                    DATE_TRUNC('day', timestamp) as date,
                    AVG(sentiment) as sentiment,
                    COUNT(*) as volume
                FROM signals_v2
                WHERE {where_clause}
                GROUP BY DATE_TRUNC('day', timestamp)
                ORDER BY date ASC
            """, *params)
            
            return {
                "theme": theme_code.upper(),
                "country": country_code.upper() if country_code else "GLO",
                "days": days,
                "drift": [
                    {
                        "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                        "sentiment": round(row["sentiment"], 3) if row["sentiment"] is not None else 0,
                        "volume": row["volume"]
                    }
                    for row in drift_data
                ]
            }
    except Exception as e:
        logger.error(f"Error fetching theme drift for {theme_code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def _emergent_cluster_detail(
    conn,
    *,
    cluster_row,
    hours: int,
    country_code: Optional[str] = None,
):
    """Theme-detail payload for an emergent cluster surfaced by the brief.

    The brief Watchlist sources its rows from the latest `emergent_clusters`
    snapshot (HDBSCAN cluster, ≥90%-precision-gated, DeepSeek labeled).
    Clicking a row navigates to /api/v2/theme/cluster-<id>; this branch
    resolves it by joining `signals_v2` against the cluster's persisted
    `sample_signal_ids` (the kept-set preview the snapshot recorded). v1
    sample size is small (~8) so the topSources/countryBreakdown/timeline
    stats are computed from the preview, not the full cluster — flagged
    via the `emergent_cluster_preview_sample` warning.
    """
    await conn.execute("SET statement_timeout = 15000")
    sample_ids = list(cluster_row["sample_signal_ids"] or [])
    raw_total = int(cluster_row["raw_signal_count"] or 0)
    gated_total = int(cluster_row["n_signals"] or 0)
    base_payload = {
        "theme": f"cluster-{cluster_row['id']}",
        "label": cluster_row["label"],
        "description": cluster_row["description"],
        "country": country_code,
        "hours": hours,
        "total": gated_total,
        "rawTotal": raw_total,
        "gated": gated_total,
        "snapshotAt": cluster_row["snapshot_at"].isoformat()
            if cluster_row["snapshot_at"] else None,
        "velocity": int(cluster_row["velocity"])
            if cluster_row["velocity"] is not None else None,
        "cohesion": float(cluster_row["cohesion"])
            if cluster_row["cohesion"] is not None else None,
        "source": "emergent_clusters",
        "relatedThemes": [],
        "countryFraming": [],
        "relatedConcepts": [],
    }
    if not sample_ids:
        return {
            **base_payload,
            "signalSample": 0,
            "avgSentiment": 0,
            "signals": [],
            "graphSignals": [],
            "countryBreakdown": [
                {"code": c, "count": 0, "sentiment": 0.0}
                for c in (cluster_row["top_country_codes"] or [])
            ],
            "topSources": [],
            "topPersons": [],
            "timeline": [],
            "warnings": ["emergent_cluster_empty_sample"],
        }

    where = ["s.id = ANY($1::bigint[])"]
    params: list = [sample_ids]
    if country_code:
        where.append("s.country_code = $2")
        params.append(country_code)
    where_clause = " AND ".join(where)

    signals = await conn.fetch(f"""
        SELECT s.id, s.source_lang, s.timestamp, s.country_code, s.source_name,
               s.source_url, s.sentiment, s.headline, s.themes, s.persons
        FROM signals_v2 s
        WHERE {where_clause}
        ORDER BY s.timestamp DESC
    """, *params)

    sample = len(signals)
    avg_sentiment = (
        sum(float(s["sentiment"] or 0) for s in signals) / sample if sample else 0
    )

    packet = build_thread_packet(signals, own_topic=None)

    return {
        **base_payload,
        "signalSample": sample,
        "avgSentiment": round(avg_sentiment, 3),
        "signals": packet["graphSignals"],
        "graphSignals": packet["graphSignals"],
        "countryBreakdown": packet["countryBreakdown"],
        "topSources": packet["topSources"],
        "topPersons": packet["topPersons"],
        "timeline": packet["timeline"],
        "warnings": ["emergent_cluster_preview_sample"],
    }


async def _dynamic_topic_detail(
    conn,
    *,
    topic_row,
    sample_ids: list[int],
    top_country_codes: list[str],
    hours: int,
    country_code: Optional[str] = None,
):
    """Theme-detail payload for the dynamic_topics canonical watchlist.

    Dynamic topics are lifecycle-managed groups of one or more emergent
    clusters. The detail view uses the persisted member preview samples, so it
    stays API-free and avoids re-running clustering when a watchlist row is
    clicked.
    """
    await conn.execute("SET statement_timeout = 15000")
    gated_total = int(topic_row["agg_n_signals"] or 0)
    noise_rate = (
        float(topic_row["noise_rate"])
        if topic_row["noise_rate"] is not None else None
    )
    base_payload = {
        "theme": f"dynamic-topic-{topic_row['id']}",
        "label": topic_row["label"],
        "description": None,
        "country": country_code,
        "hours": hours,
        "total": gated_total,
        "rawTotal": gated_total,
        "gated": gated_total,
        "snapshotAt": topic_row["last_seen"].isoformat()
            if topic_row["last_seen"] else None,
        "velocity": None,
        "cohesion": float(topic_row["mean_cohesion"])
            if topic_row["mean_cohesion"] is not None else None,
        "noiseRate": noise_rate,
        "source": "dynamic_topics",
        "relatedThemes": [],
        "countryFraming": [],
        "relatedConcepts": [],
    }
    if not sample_ids:
        return {
            **base_payload,
            "signalSample": 0,
            "avgSentiment": 0,
            "signals": [],
            "graphSignals": [],
            "countryBreakdown": [
                {"code": c, "count": 0, "sentiment": 0.0}
                for c in top_country_codes
            ],
            "topSources": [],
            "topPersons": [],
            "timeline": [],
            "warnings": ["dynamic_topic_empty_sample"],
        }

    where = ["s.id = ANY($1::bigint[])"]
    params: list = [sample_ids]
    if country_code:
        where.append("s.country_code = $2")
        params.append(country_code)
    where_clause = " AND ".join(where)

    signals = await conn.fetch(f"""
        SELECT s.id, s.source_lang, s.timestamp, s.country_code, s.source_name,
               s.source_url, s.sentiment, s.headline, s.themes, s.persons
        FROM signals_v2 s
        WHERE {where_clause}
        ORDER BY s.timestamp DESC
    """, *params)

    sample = len(signals)
    avg_sentiment = (
        sum(float(s["sentiment"] or 0) for s in signals) / sample if sample else 0
    )

    packet = build_thread_packet(signals, own_topic=None)

    # Semantic membership (#214/#162): the English lexicon never assigns most
    # non-English signals, so they can't appear above via sample_ids. Route
    # their thread membership through the multilingual e5 centroid ANN. Append
    # honestly-labeled, never folded into the gated counts. Degrade silently —
    # a semantic miss must never break the thread detail.
    warnings = ["dynamic_topic_member_preview_sample"]
    semantic_members: list = []
    try:
        from app.services.research_semantic import fetch_semantic_thread_members

        semantic_members = await fetch_semantic_thread_members(
            conn, int(topic_row["id"]), hours=hours, exclude_ids=sample_ids,
        )
        if country_code:
            semantic_members = [
                m for m in semantic_members if m.get("country_code") == country_code
            ]
    except Exception:
        semantic_members = []
    non_english = [m for m in semantic_members if m.get("source_lang") not in ("en", "xx")]
    if semantic_members:
        warnings.append("semantic_members_appended")

    return {
        **base_payload,
        "signalSample": sample,
        "avgSentiment": round(avg_sentiment, 3),
        "signals": packet["graphSignals"],
        "graphSignals": packet["graphSignals"],
        "countryBreakdown": packet["countryBreakdown"],
        "topSources": packet["topSources"],
        "topPersons": packet["topPersons"],
        "timeline": packet["timeline"],
        "semanticMembers": semantic_members,
        "semanticMemberCount": len(semantic_members),
        "semanticNonEnglishCount": len(non_english),
        "warnings": warnings,
    }


_EXT_THRESHOLDS: Optional[tuple[dict, float]] = None


def _extended_gate_thresholds() -> tuple[dict, float]:
    """Per-topic 'extended coverage' thresholds (~75% precision) — the second
    tier BELOW the 90%-precision gate_kept, ABOVE raw below-gate. Lets a detail
    surface honest graded coverage instead of dumping raw. Missing file →
    ({}, 1.0) = tier disabled (nothing ever qualifies as extended)."""
    global _EXT_THRESHOLDS
    if _EXT_THRESHOLDS is None:
        import json as _json
        from pathlib import Path as _Path
        p = _Path(__file__).resolve().parents[2] / "models" / "scope_gate_extended_thresholds.json"
        try:
            d = _json.loads(p.read_text(encoding="utf-8"))
            _EXT_THRESHOLDS = (d.get("per_topic_threshold", {}), float(d.get("global_threshold", 1.0)))
        except Exception:
            _EXT_THRESHOLDS = ({}, 1.0)
    return _EXT_THRESHOLDS


def _gate_tier(gate_kept, gate_score, ext_thr: float) -> str:
    """verified (90% precise) · extended (~75%) · candidate (below both)."""
    if gate_kept:
        return "verified"
    if gate_score is not None and float(gate_score) >= ext_thr:
        return "extended"
    return "candidate"


async def _atlas_topic_detail(
    conn,
    *,
    topic_id: int,
    slug: str,
    label: str,
    hours: int,
    country_code: Optional[str] = None,
):
    """Theme-detail payload for an Atlas topic slug, scored by the scope gate.

    The /api/v2/theme/{theme_code} hot path treats theme_code as a GDELT code
    (`$1 = ANY(themes)`). Atlas slugs (e.g. "disease-outbreak") are not GDELT
    codes, so on hot windows they resolve here instead: signals come from
    signal_topic_assignments (theme-hint-lex-v2) and, once the scope gate has
    scored them, only gate-kept assignments are shown — the same precise
    evidence the briefing's gated_signal_count advertises. Before the gate has
    scored a topic (gate_scored = 0) we fall back to all assignments and flag
    the panel gate-pending. Returns the get_theme_details shape so ThemeDetail
    renders unchanged, plus gated/raw/coverage extras.
    """
    await conn.execute("SET statement_timeout = 15000")
    where = [
        "a.topic_id = $1",
        "a.method = 'lexicon'",
        "a.model_version = 'theme-hint-lex-v2'",
        f"a.assigned_at > NOW() - INTERVAL '{int(hours)} hours'",
    ]
    params: list = [topic_id]
    if country_code:
        where.append("s.country_code = $2")
        params.append(country_code)
    where_clause = " AND ".join(where)

    per_topic_ext, global_ext = _extended_gate_thresholds()
    ext_thr = float(per_topic_ext.get(slug, global_ext))
    ext_ph = f"${len(params) + 1}"
    counts_params = params + [ext_thr]

    counts = await conn.fetchrow(f"""
        SELECT COUNT(*)::bigint                                       AS raw,
               COUNT(*) FILTER (WHERE a.gate_kept)::bigint            AS gated,
               COUNT(*) FILTER (WHERE a.gate_kept IS NOT NULL)::bigint AS scored,
               COUNT(*) FILTER (WHERE a.gate_kept IS NOT NULL AND NOT a.gate_kept
                                     AND a.gate_score >= {ext_ph})::bigint AS extended
        FROM signal_topic_assignments a
        JOIN signals_v2 s ON s.id = a.signal_id
        WHERE {where_clause}
    """, *counts_params)
    raw_n = int(counts["raw"] or 0) if counts else 0
    gated_n = int(counts["gated"] or 0) if counts else 0
    scored_n = int(counts["scored"] or 0) if counts else 0
    extended_n = int(counts["extended"] or 0) if counts else 0
    gate_pending = scored_n == 0
    # Two-tier coverage (2026-07-04, Pedro): serve VERIFIED (gate_kept, 90%
    # precision) + EXTENDED (gate_score >= the ~75%-precision per-topic
    # threshold) as graded, labeled coverage — instead of the old binary that
    # dumped ALL raw below-gate when the 90% tier kept near-zero (#214 / the
    # election-legitimacy '1 of 1,269' case). Raw fallback stays as the last
    # resort ONLY when even the extended tier is near-empty on a large pool.
    served_n = gated_n + extended_n
    below_gate_fallback = (not gate_pending) and raw_n > 0 and (
        served_n == 0 or (served_n < 5 and raw_n >= 20)
    )
    if gate_pending or below_gate_fallback:
        serve_clause = ""
        serve_params = params
    else:
        serve_clause = f" AND (a.gate_kept OR a.gate_score >= {ext_ph})"
        serve_params = params + [ext_thr]

    signals = await conn.fetch(f"""
        SELECT s.id, s.source_lang, s.timestamp, s.country_code, s.source_name,
               s.source_url, s.sentiment, s.headline, s.themes, s.persons,
               a.gate_score, a.gate_kept
        FROM signal_topic_assignments a
        JOIN signals_v2 s ON s.id = a.signal_id
        WHERE {where_clause}{serve_clause}
        ORDER BY s.timestamp DESC
        LIMIT 200
    """, *serve_params)

    country_breakdown = await conn.fetch(f"""
        SELECT s.country_code,
               COUNT(*)::bigint AS count,
               AVG(s.sentiment) AS avg_sentiment
        FROM signal_topic_assignments a
        JOIN signals_v2 s ON s.id = a.signal_id
        WHERE {where_clause}{serve_clause} AND s.country_code IS NOT NULL
        GROUP BY s.country_code
        ORDER BY count DESC
        LIMIT 15
    """, *serve_params)

    timeline = await conn.fetch(f"""
        SELECT date_trunc('hour', s.timestamp) AS hour,
               COUNT(*)::bigint AS count,
               AVG(s.sentiment) AS avg_sentiment
        FROM signal_topic_assignments a
        JOIN signals_v2 s ON s.id = a.signal_id
        WHERE {where_clause}{serve_clause}
        GROUP BY hour
        ORDER BY hour
    """, *serve_params)

    top_sources = await conn.fetch(f"""
        SELECT s.source_name,
               COUNT(*)::bigint AS count,
               AVG(s.sentiment) AS avg_sentiment
        FROM signal_topic_assignments a
        JOIN signals_v2 s ON s.id = a.signal_id
        WHERE {where_clause}{serve_clause} AND s.source_name IS NOT NULL
        GROUP BY s.source_name
        ORDER BY count DESC
        LIMIT 20
    """, *serve_params)

    sample = len(signals)
    avg_sentiment = (
        sum(float(s["sentiment"] or 0) for s in signals) / sample if sample else 0
    )

    person_counts: dict = {}
    for s in signals:
        for p in (s["persons"] or []):
            person_counts[p] = person_counts.get(p, 0) + 1
    top_persons = [
        {"name": p, "count": c}
        for p, c in sorted(person_counts.items(), key=lambda x: x[1], reverse=True)
        if _is_valid_person(p)
    ][:10]

    related_counts: dict = {}
    for s in signals:
        for t in (s["themes"] or []):
            related_counts[t] = related_counts.get(t, 0) + 1
    related_themes = [
        {"theme": t, "count": c}
        for t, c in sorted(related_counts.items(), key=lambda x: x[1], reverse=True)
    ][:10]

    def _sig(r):
        return {
            "id": r["id"],
            "source_lang": r["source_lang"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
            "country": r["country_code"],
            "source": r["source_name"],
            "url": r["source_url"],
            "headline": html.unescape(r["headline"]) if r["headline"] else r["headline"],
            "sentiment": float(r["sentiment"] or 0),
            "otherThemes": (r["themes"] or [])[:5],
            "persons": (r["persons"] or [])[:5],
            "gateScore": float(r["gate_score"]) if r["gate_score"] is not None else None,
            "gateKept": bool(r["gate_kept"]) if r["gate_kept"] is not None else None,
            "tier": _gate_tier(r["gate_kept"], r["gate_score"], ext_thr),
        }

    signal_rows = [_sig(r) for r in signals]
    warnings = ["atlas_topic_gated"] + (["gate_pending"] if gate_pending else [])
    if below_gate_fallback:
        warnings.append("below_gate_evidence")
    elif not gate_pending and extended_n > 0:
        warnings.append("extended_coverage")

    # R3 spine drill-down (Pedro 2026-07-02: "los temas grandes deben dejar
    # ver los temas pequeños"): an atlas topic is a CATEGORY; R3.1 typed every
    # dynamic story with its category (seeded from atlas labels), so the
    # specific stories under this topic are already linked in data — serve
    # them instead of leaving the big bucket opaque.
    try:
        member_story_rows = await conn.fetch(
            """
            SELECT dt.id, dt.label, dt.agg_n_signals, dt.last_seen, dt.crisis_relevant
            FROM dynamic_topics dt
            JOIN atlas_topics at ON LOWER(dt.category) = LOWER(at.label)
            WHERE at.slug = $1 AND dt.state = 'active' AND NOT dt.is_umbrella
            ORDER BY dt.last_seen DESC, dt.agg_n_signals DESC
            LIMIT 12
            """,
            slug,
        )
    except Exception:
        member_story_rows = []
    member_stories = [
        {
            "id": f"dynamic-topic-{r['id']}",
            "label": r["label"],
            "n": int(r["agg_n_signals"] or 0),
            "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
            "crisis_relevant": bool(r["crisis_relevant"]) if r["crisis_relevant"] is not None else None,
        }
        for r in member_story_rows
    ]

    return {
        "memberStories": member_stories,
        "theme": slug,
        "label": label,
        "country": country_code,
        "hours": hours,
        "total": raw_n if (gate_pending or below_gate_fallback) else served_n,
        "rawTotal": raw_n,
        "gated": gated_n,
        "verified": gated_n,
        "extended": extended_n,
        "extendedThreshold": round(ext_thr, 4),
        "gateScored": scored_n,
        "gateCoverage": round(gated_n / scored_n, 4) if scored_n else None,
        "gatePending": gate_pending,
        "signalSample": sample,
        "avgSentiment": round(avg_sentiment, 3),
        "signals": signal_rows,
        "graphSignals": signal_rows,
        "countryBreakdown": [
            {"code": r["country_code"], "count": int(r["count"]), "sentiment": float(r["avg_sentiment"] or 0)}
            for r in country_breakdown
        ],
        "relatedThemes": related_themes,
        "topSources": [
            {
                "name": extract_domain(r["source_name"]),
                "count": int(r["count"]),
                "sentiment": float(r["avg_sentiment"] or 0),
                "family": classify_source(r["source_name"] or ""),
            }
            for r in top_sources
        ],
        "topPersons": top_persons,
        "timeline": [
            {"hour": t["hour"].isoformat(), "count": int(t["count"]), "sentiment": float(t["avg_sentiment"] or 0)}
            for t in timeline
        ],
        "countryFraming": [],
        "relatedConcepts": [],
        "source": "signal_topic_assignments_gated",
        "warnings": warnings,
    }


@router.get("/api/v2/theme/{theme_code}")
async def get_theme_details(
    theme_code: str,
    country_code: str = Query(None, description="Filter by country"),
    hours: int = Query(24, ge=1, le=8760)
):
    """Get detailed information about a theme including rich context."""
    from app.core.gdelt_taxonomy import get_concepts_for_theme
    from app.services.thread_intelligence import parse_thread_id

    # Thread ids from /api/v2/threads use 'slug--cc[-cc...]'. Clients open
    # threads with that full id, but atlas_topics.slug has no suffix — the
    # lookup missed, fell through to the GDELT '$1 = ANY(themes)' path and
    # returned 0 while the list showed N (#214; Pedro's 2026-06-12 PE review:
    # election-legitimacy-dispute--pe listed 48, opened to an empty gate
    # message during a live vote-count dispute). Parse the suffix here so the
    # atlas branch — and its below-gate fallback — always resolves.
    if "--" in theme_code:
        base_slug, thread_countries = parse_thread_id(theme_code)
        if base_slug and thread_countries and all(len(c) == 2 for c in thread_countries):
            theme_code = base_slug
            # Single-country thread id scopes the detail to that country;
            # multi-country ids stay global unless the caller filtered.
            if not country_code and len(thread_countries) == 1:
                country_code = thread_countries[0]

    # For long windows, cap signals_v2 scans at 48h; use pre-agg tables for aggregates
    signals_hours = min(hours, 48) if hours > 24 else hours
    try:
        async with db.pool.acquire() as conn:
            # dynamic-topic-<id> / cluster-<id> ids contain "-" but are NOT
            # atlas slugs — they have dedicated resolvers below. Letting them
            # into the historical branch returned total=0 for every dynamic
            # thread at hours>24 (E2 diagnosis 2026-07-02).
            _has_dedicated_resolver = (
                theme_code.lower().startswith("dynamic-topic-")
                or theme_code.lower().startswith("cluster-")
            )
            if use_processed_history(hours) and "-" in theme_code and not _has_dedicated_resolver:
                topic_slug = theme_code.lower()
                historical = await query_historical_topic_detail(
                    conn,
                    topic_slug=topic_slug,
                    hours=hours,
                    country_code=country_code.upper() if country_code else None,
                )
                if not historical:
                    # list/detail reconciliation: the thread list counts
                    # signal_topic_assignments for ALL windows, but processed
                    # history may have no row for this atlas slug. Before
                    # declaring zero, resolve through the same assignment source
                    # the list used, so a thread that lists with N signals never
                    # opens to 0 (Phase 0.5).
                    atlas_row = await conn.fetchrow(
                        "SELECT id, slug, label FROM atlas_topics WHERE slug = $1",
                        topic_slug,
                    )
                    if atlas_row:
                        return await _atlas_topic_detail(
                            conn,
                            topic_id=atlas_row["id"],
                            slug=atlas_row["slug"],
                            label=atlas_row["label"],
                            hours=hours,
                            country_code=country_code.upper() if country_code else None,
                        )
                    return {
                        "theme": theme_code,
                        "country": country_code,
                        "hours": hours,
                        "total": 0,
                        "avgSentiment": 0,
                        "signals": [],
                        "graphSignals": [],
                        "countryBreakdown": [],
                        "relatedThemes": [],
                        "topSources": [],
                        "topPersons": [],
                        "timeline": [],
                        "countryFraming": [],
                        "relatedConcepts": [],
                        "source": "historical_topic_country_daily",
                        "coverage": (await build_historical_coverage(conn, hours=hours)).to_dict(),
                        "warnings": ["historical_processed", "no_processed_topic_history"],
                    }

                stats = historical["stats"]
                coverage = await build_historical_coverage(conn, hours=hours)
                return {
                    "theme": topic_slug,
                    "country": country_code,
                    "hours": hours,
                    "total": int(stats["signal_count"] or 0),
                    "signalSample": 0,
                    "avgSentiment": round(float(stats["avg_sentiment"] or 0), 3),
                    "signals": [
                        {
                            "timestamp": row["signal_timestamp"].isoformat()
                            if row["signal_timestamp"] else None,
                            "country": row["country_code"],
                            "source": row["source_name"],
                            "url": row["source_url"],
                            "headline": row["headline"],
                            "sentiment": float(row["sentiment"] or 0),
                            "otherThemes": [],
                            "persons": [],
                        }
                        for row in historical["evidence"]
                    ],
                    "graphSignals": [],
                    "countryBreakdown": [
                        {
                            "code": row["country_code"],
                            "name": row["country_name"] or row["country_code"],
                            "count": int(row["signal_count"] or 0),
                            "sentiment": float(row["avg_sentiment"] or 0),
                        }
                        for row in historical["countries"]
                    ],
                    "relatedThemes": [],
                    "topSources": [
                        {
                            "name": f"{row['source_family']}:{row['signal_class']}",
                            "count": int(row["signal_count"] or 0),
                            "sentiment": 0,
                            "family": row["source_family"],
                        }
                        for row in historical["source_mix"]
                    ],
                    "topPersons": [],
                    "timeline": [
                        {
                            "hour": datetime.combine(row["day"], datetime.min.time()).replace(
                                tzinfo=timezone.utc
                            ).isoformat(),
                            "count": int(row["signal_count"] or 0),
                            "sentiment": float(row["avg_sentiment"] or 0),
                        }
                        for row in historical["timeline"]
                    ],
                    "countryFraming": [],
                    "relatedConcepts": [],
                    "source": "historical_topic_country_daily",
                    "coverage": coverage.to_dict(),
                    "warnings": ["historical_processed", "atlas_topic_slug", "source_mix_not_source_names"],
                    "historical": {
                        "countryCount": int(stats["country_count"] or 0),
                        "topicCoverage": round(float(stats["topic_coverage"] or 0), 4),
                        "sentimentCoverage": round(float(stats["sentiment_coverage"] or 0), 4),
                        "entityCoverage": round(float(stats["entity_coverage"] or 0), 4),
                        "sourceDiversity": round(float(stats["source_diversity"] or 0), 4),
                    },
                }

            # Dynamic topic slug: 'dynamic-topic-<id>'. Surfaced by the brief
            # Watchlist once the self-curated lifecycle has active rows.
            # Resolves through the dynamic topic's member clusters so clicks
            # keep rendering in ThemeDetail without re-running clustering.
            if (
                theme_code.lower().startswith("dynamic-topic-")
                and theme_code[len("dynamic-topic-"):].isdigit()
            ):
                topic_id = int(theme_code[len("dynamic-topic-"):])
                has_dynamic = await conn.fetchval(
                    "SELECT to_regclass('dynamic_topics') IS NOT NULL"
                )
                has_dynamic_members = await conn.fetchval(
                    "SELECT to_regclass('dynamic_topic_members') IS NOT NULL"
                )
                has_emergent = await conn.fetchval(
                    "SELECT to_regclass('emergent_clusters') IS NOT NULL"
                )
                if has_dynamic and has_dynamic_members and has_emergent:
                    topic_row = await conn.fetchrow("""
                        SELECT
                            dt.id,
                            dt.label,
                            dt.agg_n_signals,
                            dt.mean_cohesion,
                            dt.noise_rate,
                            dt.last_seen,
                            COALESCE((
                                SELECT array_agg(DISTINCT sid.signal_id)
                                FROM dynamic_topic_members dtm
                                JOIN emergent_clusters ec
                                  ON ec.id = dtm.emergent_cluster_id
                                LEFT JOIN LATERAL unnest(ec.sample_signal_ids)
                                  AS sid(signal_id) ON TRUE
                                WHERE dtm.dynamic_topic_id = dt.id
                                  AND sid.signal_id IS NOT NULL
                            ), ARRAY[]::bigint[]) AS sample_signal_ids,
                            COALESCE((
                                SELECT array_agg(DISTINCT cc.country_code)
                                FROM dynamic_topic_members dtm
                                JOIN emergent_clusters ec
                                  ON ec.id = dtm.emergent_cluster_id
                                LEFT JOIN LATERAL unnest(ec.top_country_codes)
                                  AS cc(country_code) ON TRUE
                                WHERE dtm.dynamic_topic_id = dt.id
                                  AND cc.country_code IS NOT NULL
                            ), ARRAY[]::text[]) AS top_country_codes
                        FROM dynamic_topics dt
                        WHERE dt.id = $1
                          AND dt.state = 'active'
                    """, topic_id)
                    if topic_row:
                        return await _dynamic_topic_detail(
                            conn,
                            topic_row=topic_row,
                            sample_ids=list(topic_row["sample_signal_ids"] or []),
                            top_country_codes=list(topic_row["top_country_codes"] or []),
                            hours=hours,
                            country_code=country_code.upper() if country_code else None,
                        )

            # Emergent cluster slug: 'cluster-<id>'. Surfaced by the brief
            # Watchlist fallback from the latest emergent_clusters snapshot
            # (mig 046). Resolves to the persisted preview sample so ThemeDetail
            # renders the cluster's headlines without re-running clustering.
            if theme_code.lower().startswith("cluster-") and theme_code[len("cluster-"):].isdigit():
                cluster_id = int(theme_code[len("cluster-"):])
                has_emergent = await conn.fetchval(
                    "SELECT to_regclass('emergent_clusters') IS NOT NULL"
                )
                if has_emergent:
                    cluster_row = await conn.fetchrow(
                        "SELECT id, label, description, snapshot_at, "
                        "snapshot_window_h, sample_signal_ids, top_country_codes, "
                        "n_signals, raw_signal_count, velocity, cohesion "
                        "FROM emergent_clusters WHERE id = $1",
                        cluster_id,
                    )
                    if cluster_row:
                        return await _emergent_cluster_detail(
                            conn,
                            cluster_row=cluster_row,
                            hours=hours,
                            country_code=country_code.upper() if country_code else None,
                        )

            # Atlas-topic slug on a hot window. The historical branch above only
            # fires for long windows; here an atlas slug (e.g. "disease-outbreak")
            # is not a GDELT code, so resolve it against the gated assignments
            # instead of the $1 = ANY(themes) GDELT path below. UPPER_SNAKE GDELT
            # codes never contain "-", so the hyphen reliably marks an atlas slug.
            if "-" in theme_code:
                topic_row = await conn.fetchrow(
                    "SELECT id, slug, label FROM atlas_topics WHERE slug = $1",
                    theme_code.lower(),
                )
                if topic_row:
                    return await _atlas_topic_detail(
                        conn,
                        topic_id=topic_row["id"],
                        slug=topic_row["slug"],
                        label=topic_row["label"],
                        hours=hours,
                        country_code=country_code.upper() if country_code else None,
                    )

            await conn.execute("SET statement_timeout = 25000")
            # Build WHERE clause based on filters
            where_conditions = [
                "$1 = ANY(themes)",
                f"timestamp > NOW() - INTERVAL '{signals_hours} hours'"
            ]
            params = [theme_code.upper()]
            
            if country_code:
                where_conditions.append("country_code = $2")
                params.append(country_code.upper())
            
            where_clause = " AND ".join(where_conditions)
            
            # Get signals
            signals = await conn.fetch(f"""
                SELECT
                    id,
                    source_lang,
                    timestamp,
                    country_code,
                    source_name,
                    source_url,
                    sentiment,
                    themes,
                    persons
                FROM signals_v2
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT 200
            """, *params)

            # Representative temporal sample for graph views.
            # Keep `signals` as latest coverage; spread graphSignals across hours.
            graph_signals = await conn.fetch(f"""
                WITH ranked AS (
                    SELECT
                        id,
                        source_lang,
                        timestamp,
                        country_code,
                        source_name,
                        source_url,
                        sentiment,
                        themes,
                        persons,
                        ROW_NUMBER() OVER (
                            PARTITION BY date_trunc('hour', timestamp)
                            ORDER BY timestamp DESC
                        ) as rn
                    FROM signals_v2
                    WHERE {where_clause}
                )
                SELECT
                    id,
                    source_lang,
                    timestamp,
                    country_code,
                    source_name,
                    source_url,
                    sentiment,
                    themes,
                    persons
                FROM ranked
                WHERE rn <= 8
                ORDER BY timestamp ASC
                LIMIT 240
            """, *params)
            
            # Get timeline — use pre-agg for long windows to avoid full scan
            if hours > 24:
                timeline = await conn.fetch("""
                    SELECT hour,
                           SUM(signal_count)::bigint as count,
                           CASE WHEN SUM(signal_count) > 0
                                THEN (SUM(avg_sentiment * signal_count) / SUM(signal_count))::float
                                ELSE 0::float END as avg_sentiment
                    FROM theme_country_hourly_v2
                    WHERE theme = $1 AND hour > NOW() - INTERVAL '%s hours'
                    GROUP BY hour ORDER BY hour
                """ % hours, theme_code.upper())
            else:
                timeline = await conn.fetch(f"""
                    SELECT
                        date_trunc('hour', timestamp) as hour,
                        COUNT(*) as count,
                        AVG(sentiment) as avg_sentiment
                    FROM signals_v2
                    WHERE {where_clause}
                    GROUP BY hour
                    ORDER BY hour
                """, *params)
            
            # Get country breakdown — use pre-agg for long windows
            if hours > 24:
                country_breakdown = await conn.fetch("""
                    SELECT country_code,
                           SUM(signal_count)::bigint as count,
                           CASE WHEN SUM(signal_count) > 0
                                THEN (SUM(avg_sentiment * signal_count) / SUM(signal_count))::float
                                ELSE 0::float END as avg_sentiment
                    FROM theme_country_hourly_v2
                    WHERE theme = $1 AND hour > NOW() - INTERVAL '%s hours'
                    GROUP BY country_code ORDER BY count DESC LIMIT 15
                """ % hours, theme_code.upper())
            else:
                country_breakdown = await conn.fetch(f"""
                    SELECT
                        country_code,
                        COUNT(*) as count,
                        AVG(sentiment) as avg_sentiment
                    FROM signals_v2
                    WHERE $1 = ANY(themes)
                    AND timestamp > NOW() - INTERVAL '{hours} hours'
                    GROUP BY country_code
                    ORDER BY count DESC
                    LIMIT 15
                """, theme_code.upper())
            
            # Get related themes (co-occurrence) — cap to 48h to avoid full scan
            related_themes_data = await conn.fetch(f"""
                SELECT
                    unnest(themes) as related_theme,
                    COUNT(*) as count
                FROM signals_v2
                WHERE $1 = ANY(themes)
                AND timestamp > NOW() - INTERVAL '{signals_hours} hours'
                GROUP BY related_theme
                ORDER BY count DESC
                LIMIT 20
            """, theme_code.upper())
            
            # Filter out current theme from related
            related_themes = [
                {"theme": r['related_theme'], "count": int(r['count'])}
                for r in related_themes_data
                if r['related_theme'].upper() != theme_code.upper()
            ][:10]
            
            # Get top sources
            top_sources = await conn.fetch(f"""
                SELECT 
                    source_name,
                    COUNT(*) as count,
                    AVG(sentiment) as avg_sentiment
                FROM signals_v2
                WHERE {where_clause}
                AND source_name IS NOT NULL
                GROUP BY source_name
                ORDER BY count DESC
                LIMIT 20
            """, *params)

            # Calculate summary stats
            # Get true total from pre-agg (not the LIMIT 200 capped array)
            if hours > 24:
                true_total_row = await conn.fetchrow("""
                    SELECT SUM(signal_count)::bigint as n
                    FROM theme_country_hourly_v2
                    WHERE theme = $1 AND hour > NOW() - INTERVAL '%s hours'
                """ % hours, theme_code.upper())
                true_total = int(true_total_row['n'] or 0) if true_total_row else len(signals)
            else:
                true_total_row = await conn.fetchrow(f"""
                    SELECT COUNT(*)::bigint as n FROM signals_v2 WHERE {where_clause}
                """, *params)
                true_total = int(true_total_row['n'] or 0) if true_total_row else len(signals)
            total = len(signals)
            avg_sentiment = sum(float(s['sentiment'] or 0) for s in signals) / total if total > 0 else 0
            
            # Get unique persons mentioned
            all_persons = []
            for s in signals:
                if s['persons']:
                    all_persons.extend(s['persons'])
            person_counts = {}
            for p in all_persons:
                person_counts[p] = person_counts.get(p, 0) + 1
            top_persons = [
                {"name": p[0], "count": p[1]}
                for p in sorted(person_counts.items(), key=lambda x: x[1], reverse=True)
                if _is_valid_person(p[0])
            ][:10]

            # --- Country Framing: how different countries cover the same theme ---
            framing_rows = await conn.fetch(f"""
                SELECT
                    s.country_code,
                    co.name as country_name,
                    COUNT(*) as signal_count,
                    ROUND(AVG(s.sentiment)::numeric, 2) as avg_sentiment
                FROM signals_v2 s
                LEFT JOIN countries_v2 co ON s.country_code = co.code
                WHERE $1 = ANY(s.themes)
                  AND s.timestamp > NOW() - INTERVAL '{signals_hours} hours'
                  AND s.country_code IS NOT NULL
                GROUP BY s.country_code, co.name
                ORDER BY signal_count DESC
                LIMIT 6
            """, theme_code.upper())

            country_framing = []
            for fr in framing_rows:
                cc = fr['country_code']
                # Get top 3 co-occurring sub-themes for this country
                sub_rows = await conn.fetch(f"""
                    SELECT sub_theme, COUNT(*) as cnt
                    FROM (
                        SELECT unnest(themes) as sub_theme
                        FROM signals_v2
                        WHERE $1 = ANY(themes)
                          AND country_code = $2
                          AND timestamp > NOW() - INTERVAL '{signals_hours} hours'
                    ) t
                    WHERE sub_theme != $1
                    GROUP BY sub_theme
                    ORDER BY cnt DESC
                    LIMIT 3
                """, theme_code.upper(), cc)

                avg_s = float(fr['avg_sentiment'] or 0)
                if avg_s > 0.5:
                    sentiment_label = "positive"
                elif avg_s > -0.5:
                    sentiment_label = "neutral"
                elif avg_s > -2.0:
                    sentiment_label = "negative"
                else:
                    sentiment_label = "very_negative"

                country_framing.append({
                    "country_code": cc,
                    "country_name": fr['country_name'] or cc,
                    "signal_count": int(fr['signal_count']),
                    "avg_sentiment": avg_s,
                    "top_sub_themes": [r['sub_theme'] for r in sub_rows],
                    "sentiment_label": sentiment_label
                })

            return {
                "theme": theme_code,
                "country": country_code,
                "hours": hours,
                "total": true_total,
                "signalSample": total,
                "avgSentiment": round(avg_sentiment, 3),
                "signals": [
                    {
                        "id": r['id'],
                        "source_lang": r['source_lang'],
                        "timestamp": r['timestamp'].isoformat(),
                        "country": r['country_code'],
                        "source": r['source_name'],
                        "url": r['source_url'],
                        "sentiment": float(r['sentiment'] or 0),
                        "otherThemes": [t for t in (r['themes'] or []) if t.upper() != theme_code.upper()][:5],
                        "persons": (r['persons'] or [])[:5]
                    }
                    for r in signals
                ],
                "graphSignals": [
                    {
                        "id": r['id'],
                        "source_lang": r['source_lang'],
                        "timestamp": r['timestamp'].isoformat(),
                        "country": r['country_code'],
                        "source": r['source_name'],
                        "url": r['source_url'],
                        "sentiment": float(r['sentiment'] or 0),
                        "otherThemes": [t for t in (r['themes'] or []) if t.upper() != theme_code.upper()][:5],
                        "persons": (r['persons'] or [])[:5]
                    }
                    for r in graph_signals
                ],
                "countryBreakdown": [
                    {"code": r['country_code'], "count": int(r['count']), "sentiment": float(r['avg_sentiment'] or 0)}
                    for r in country_breakdown
                ],
                "relatedThemes": related_themes,
                "topSources": [
                    {
                        "name": extract_domain(r['source_name']),
                        "count": int(r['count']),
                        "sentiment": float(r['avg_sentiment'] or 0),
                        "family": classify_source(r['source_name'] or ""),
                    }
                    for r in top_sources
                ],
                "topPersons": top_persons,
                "timeline": [
                    {"hour": t['hour'].isoformat(), "count": int(t['count']), "sentiment": float(t['avg_sentiment'] or 0)}
                    for t in timeline
                ],
                "countryFraming": country_framing,
                "relatedConcepts": get_concepts_for_theme(theme_code)
            }
    except Exception as e:
        print(f"Error in theme endpoint: {e}")
        import traceback
        traceback.print_exc()
        return {
            "theme": theme_code,
            "country": country_code,
            "hours": hours,
            "total": 0,
            "avgSentiment": 0,
            "signals": [],
            "countryBreakdown": [],
            "relatedThemes": [],
            "topSources": [],
            "topPersons": [],
            "timeline": [],
            "countryFraming": [],
            "error": str(e)
        }


def _clean_theme_label(theme_code: str) -> str:
    """Convert theme code like WB_475_DIGITAL_GOVERNMENT to 'Digital Government'."""
    label = theme_code.upper()
    # Strip known prefixes
    prefixes = (
        "WB_", "TAX_", "GDELT_", "CRISISLEX_", "USPEC_", "UN_", 
        "SOC_", "ENV_", "ECON_", "EPU_", "MIL_", "CRIME_", "HEALTH_"
    )
    for prefix in prefixes:
        if label.startswith(prefix):
            # Also strip the numeric segment that follows e.g. WB_475_
            parts = label.split("_", 2)
            label = parts[-1] if len(parts) >= 2 else label
            break
    # Special cleanup for known redundant suffixes
    if label == "CRISISLEXREC":
        label = "CRISIS RECOVERY"
    
    # Remove any remaining leading numeric segment (e.g. "475_DIGITAL" → "DIGITAL")
    parts = label.split("_", 1)
    if parts[0].isdigit() and len(parts) == 2:
        label = parts[1]
    return label.replace("_", " ").title()


@router.get("/api/v2/theme/{theme_code}/insight")
async def get_theme_insight(
    theme_code: str,
    hours: int = Query(24, ge=1, le=8760),
):
    """
    Generate a 2-3 sentence AI meta-summary of HOW a topic is covered across
    global media. Describes observable coverage patterns only — never editorialises
    about the topic itself.

    Results are cached in Redis for 15 minutes (900 seconds).
    Falls back gracefully when ANTHROPIC_API_KEY is not set or the LLM call fails.
    """
    import math

    cache_key = f"insight:{theme_code.upper()}:{hours}"
    generated_at = datetime.now(timezone.utc).isoformat()

    # --- Cache check ---
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached_raw = await app.state.redis.get(cache_key)
            if cached_raw:
                cached_data = json.loads(cached_raw)
                cached_data["cached"] = True
                return cached_data
        except Exception:
            pass  # Redis hiccup — proceed without cache

    # --- Lightweight DB queries ---
    tc = theme_code.upper()
    # E1 (capture-doc): dynamic threads matched ZERO rows here ($1=ANY(themes)
    # is the GDELT universe) → data_points 0/0/0 → empty/fabricated insight for
    # the product's PRIMARY thread type. Resolve their own membership instead.
    dyn_id = None
    if theme_code.lower().startswith("dynamic-topic-"):
        try:
            dyn_id = int(theme_code.split("-")[-1])
        except ValueError:
            dyn_id = None
    if dyn_id is not None:
        try:
            async with db.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT dt.label,
                           COALESCE((SELECT SUM(ec.n_signals)
                             FROM dynamic_topic_members m
                             JOIN emergent_clusters ec ON ec.id = m.emergent_cluster_id
                             WHERE m.dynamic_topic_id = dt.id
                               AND m.snapshot_at = (SELECT MAX(snapshot_at)
                                   FROM dynamic_topic_members WHERE dynamic_topic_id = dt.id)
                           ), 0)::int AS total_n,
                           ARRAY(
                             SELECT DISTINCT sid FROM dynamic_topic_members m2
                             JOIN emergent_clusters ec2 ON ec2.id = m2.emergent_cluster_id
                             CROSS JOIN LATERAL unnest(COALESCE(ec2.sample_signal_ids, ARRAY[]::bigint[])) sid
                             WHERE m2.dynamic_topic_id = dt.id LIMIT 48
                           ) AS sample_ids
                    FROM dynamic_topics dt WHERE dt.id = $1
                    """, dyn_id, timeout=8)
                if not row:
                    return {"theme": theme_code, "insight": None, "error": "not_found",
                            "data_points": {}, "generated_at": generated_at}
                sample_ids = list(row["sample_ids"] or [])
                sstats = await conn.fetchrow(
                    """
                    SELECT COUNT(*) AS n, COUNT(DISTINCT country_code) AS cc,
                           COUNT(DISTINCT source_name) AS sc, AVG(sentiment) AS avg_s
                    FROM signals_v2 WHERE id = ANY($1::bigint[])
                    """, sample_ids, timeout=8) if sample_ids else None
                stats_row = {
                    "total_signals": int(row["total_n"] or 0),
                    "country_count": int(sstats["cc"] or 0) if sstats else 0,
                    "source_count": int(sstats["sc"] or 0) if sstats else 0,
                    "global_sentiment": float(sstats["avg_s"] or 0.0) if sstats else 0.0,
                }
                country_rows = await conn.fetch(
                    """
                    SELECT country_code, COUNT(*) AS cnt, AVG(sentiment) AS avg_sent
                    FROM signals_v2 WHERE id = ANY($1::bigint[]) AND country_code IS NOT NULL
                    GROUP BY country_code ORDER BY cnt DESC LIMIT 5
                    """, sample_ids, timeout=8) if sample_ids else []
                trend_row = {"recent": 0, "previous": 0}
        except Exception as db_err:
            return {"theme": theme_code, "insight": None, "error": "db_error",
                    "detail": str(db_err), "data_points": {}, "generated_at": generated_at}
    else:
      try:
          async with db.pool.acquire() as conn:
              # Aggregate stats
              stats_row = await conn.fetchrow(
                  f"""
                  SELECT
                      COUNT(*)                          AS total_signals,
                      COUNT(DISTINCT country_code)      AS country_count,
                      COUNT(DISTINCT source_name)       AS source_count,
                      AVG(sentiment)                    AS global_sentiment
                  FROM signals_v2
                  WHERE $1 = ANY(themes)
                    AND timestamp > NOW() - INTERVAL '{hours} hours'
                  """,
                  tc,
              )

              # Top 5 countries by volume
              country_rows = await conn.fetch(
                  f"""
                  SELECT country_code, COUNT(*) AS cnt, AVG(sentiment) AS avg_sent
                  FROM signals_v2
                  WHERE $1 = ANY(themes)
                    AND timestamp > NOW() - INTERVAL '{hours} hours'
                  GROUP BY country_code
                  ORDER BY cnt DESC
                  LIMIT 5
                  """,
                  tc,
              )

              # Volume trend: last 6h vs previous 6h
              trend_row = await conn.fetchrow(
                  """
                  SELECT
                      SUM(CASE WHEN timestamp > NOW() - INTERVAL '6 hours' THEN 1 ELSE 0 END)          AS recent,
                      SUM(CASE WHEN timestamp BETWEEN NOW() - INTERVAL '12 hours'
                                               AND NOW() - INTERVAL '6 hours'  THEN 1 ELSE 0 END)     AS previous
                  FROM signals_v2
                  WHERE $1 = ANY(themes)
                    AND timestamp > NOW() - INTERVAL '12 hours'
                  """,
                  tc,
              )
      except Exception as db_err:
          return {
              "theme": theme_code.upper(),
              "insight": None,
              "error": "db_error",
              "detail": str(db_err),
              "data_points": {},
              "generated_at": generated_at,
          }

    total_signals = int(stats_row["total_signals"] or 0)
    country_count = int(stats_row["country_count"] or 0)
    source_count = int(stats_row["source_count"] or 0)
    global_sentiment = float(stats_row["global_sentiment"] or 0.0)

    data_points = {
        "total_signals": total_signals,
        "country_count": country_count,
        "source_count": source_count,
    }

    # Format top countries string
    top_countries_parts = []
    for r in country_rows:
        cc = r["country_code"] or "??"
        cnt = int(r["cnt"])
        avg_s = float(r["avg_sent"] or 0.0)
        top_countries_parts.append(f"{cc} ({cnt} signals, {avg_s:+.1f} tone)")
    top_countries_formatted = ", ".join(top_countries_parts) if top_countries_parts else "N/A"

    # Trend description
    recent = int(trend_row["recent"] or 0)
    previous = int(trend_row["previous"] or 0)
    if previous == 0:
        trend_description = "accelerating (no data in previous 6h)" if recent > 0 else "no recent activity"
    else:
        ratio = recent / previous
        if ratio >= 1.5:
            trend_description = f"accelerating ({ratio:.1f}x vs previous 6h)"
        elif ratio <= 0.5:
            trend_description = f"declining ({ratio:.1f}x vs previous 6h)"
        else:
            trend_description = "stable"

    # --- LLM call ---
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    insight_provider = os.getenv("INSIGHT_PROVIDER", "anthropic").lower()
    theme_label = _clean_theme_label(theme_code)

    user_prompt = (
        f'Analyze the global media coverage for the topic "{theme_label}" over the last {hours} hours.\n\n'
        f"Data points to weave into your summary:\n"
        f"- Total volume: {total_signals} articles across {country_count} countries.\n"
        f"- Number of distinct sources: {source_count}\n"
        f"- Overall global tone (sentiment): {global_sentiment:+.1f} (where negative is bad/pessimistic, positive is good/optimistic)\n"
        f"- Key countries driving the coverage (with their specific tone): {top_countries_formatted}\n"
        f"- Current momentum: {trend_description}\n\n"
        "Write your 2-3 sentence summary now."
    )

    system_prompt = (
        "You are an intelligence analyst summarizing global media trends.\n"
        "Your goal is to provide a clear, concise, and highly readable summary of how a topic is being covered globally.\n"
        "Rules:\n"
        "1. Never use raw database taxonomy names (e.g., if the topic is 'Crisislex Crisislexrec', translate it naturally to 'crisis events' or 'emergencies').\n"
        "2. Do not write like a robot listing statistics. Weave the data (countries, sentiment, volume) into a fluid, human-readable narrative.\n"
        "3. Highlight interesting contrasts (e.g., if sentiment is negative in Russia but positive in the US, mention the regional split naturally).\n"
        "4. Keep it exactly 2-3 sentences. Be insightful, engaging, and professional.\n"
        "5. Never use em-dashes (—) or en-dashes. Rephrase with commas or separate sentences."
    )

    insight_text: Optional[str] = None

    # Ollama fallback path (optional, environment-controlled)
    if insight_provider == "ollama":
        ollama_host = os.getenv("OLLAMA_HOST")
        if ollama_host:
            try:
                ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{ollama_host.rstrip('/')}/api/chat",
                        json={
                            "model": ollama_model,
                            "stream": False,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                        },
                    )
                    resp.raise_for_status()
                    insight_text = resp.json()["message"]["content"].strip()
            except Exception as ollama_err:
                print(f"[insight] Ollama call failed: {ollama_err}")

    # Anthropic (Claude Haiku) — primary path
    if insight_text is None and anthropic_key:
        try:
            import anthropic

            async_client = anthropic.AsyncAnthropic(api_key=anthropic_key)
            response = await async_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            insight_text = next(
                (block.text for block in response.content if block.type == "text"),
                None,
            )
        except Exception as llm_err:
            err_msg = str(llm_err)
            print(f"[insight] Claude Haiku call failed: {err_msg}")
            error_code = "insight_no_credits" if "credit balance" in err_msg.lower() else "insight_unavailable"
            return {
                "theme": theme_code.upper(),
                "insight": None,
                "error": error_code,
                "data_points": data_points,
                "generated_at": generated_at,
            }

    if insight_text is None:
        # API key missing or provider skipped — return graceful fallback
        return {
            "theme": theme_code.upper(),
            "insight": None,
            "error": "insight_unavailable",
            "data_points": data_points,
            "generated_at": generated_at,
        }

    result = {
        "theme": theme_code.upper(),
        "insight": insight_text,
        "data_points": data_points,
        "cached": False,
        "generated_at": generated_at,
    }

    # --- Cache the result ---
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(cache_key, 900, json.dumps(result))
        except Exception:
            pass  # Best-effort caching

    return result


@router.get("/api/v2/theme/{theme_code}/spikes")
async def get_theme_spikes(
    theme_code: str,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(3, ge=1, le=10),
):
    """
    Return the top spike moments for a theme in the last N hours.
    Each spike includes the hour, signal count, % delta from prior hour,
    and the single article that contributed most (trigger event).
    Used to annotate NarrativeThreads sparklines.
    """
    import json as _json, traceback

    cache_key = f"spikes:{theme_code}:{hours}:{limit}"
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return _json.loads(cached)
        except Exception:
            pass

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 10000")

            # Hourly counts for this theme
            hourly = await conn.fetch("""
                SELECT
                    date_trunc('hour', timestamp) AS hour,
                    COUNT(*)                       AS count
                FROM signals_v2
                WHERE timestamp > NOW() - ($2 || ' hours')::INTERVAL
                  AND themes IS NOT NULL
                  AND $1 = ANY(themes)
                GROUP BY 1
                ORDER BY 1
            """, theme_code, str(hours))

            if len(hourly) < 2:
                return {"theme_code": theme_code, "spikes": []}

            # Compute delta vs previous hour; rank by absolute delta
            rows_with_delta = []
            for i in range(1, len(hourly)):
                prev = hourly[i - 1]["count"]
                curr = hourly[i]["count"]
                if prev > 0:
                    delta_pct = round((curr - prev) / prev * 100, 1)
                else:
                    delta_pct = 100.0 if curr > 0 else 0.0
                rows_with_delta.append({
                    "hour": hourly[i]["hour"],
                    "count": curr,
                    "prev_count": prev,
                    "delta_pct": delta_pct,
                })

            # Top spikes by absolute delta_pct (only positive — accelerating moments)
            top_spikes = sorted(
                [r for r in rows_with_delta if r["delta_pct"] > 0],
                key=lambda r: r["delta_pct"],
                reverse=True,
            )[:limit]

            # For each spike hour, find the single article with the most mentions
            # as a proxy for the trigger event
            spikes = []
            for spike in top_spikes:
                trigger = await conn.fetchrow("""
                    SELECT source_url AS url, source_name AS source, country_code, sentiment
                    FROM signals_v2
                    WHERE timestamp >= $1
                      AND timestamp < $1 + INTERVAL '1 hour'
                      AND themes IS NOT NULL
                      AND $2 = ANY(themes)
                      AND source_url IS NOT NULL
                    ORDER BY timestamp ASC
                    LIMIT 1
                """, spike["hour"], theme_code)

                spikes.append({
                    "hour": spike["hour"].isoformat(),
                    "count": spike["count"],
                    "prev_count": spike["prev_count"],
                    "delta_pct": spike["delta_pct"],
                    "trigger": {
                        "url": trigger["url"],
                        "source": trigger["source"],
                        "country_code": trigger["country_code"],
                        "sentiment": round(float(trigger["sentiment"] or 0), 3),
                    } if trigger else None,
                })

            result = {
                "theme_code": theme_code,
                "hours": hours,
                "spikes": spikes,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            if hasattr(app.state, "redis") and app.state.redis:
                try:
                    await app.state.redis.setex(cache_key, 300, _json.dumps(result, default=str))
                except Exception:
                    pass

            return result

    except Exception as e:
        traceback.print_exc()
        return {"theme_code": theme_code, "spikes": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Orbital Thread View (E2/L11 — spec docs/specs/2026-07-02-orbital-thread-view.md)
# ---------------------------------------------------------------------------

def _vector_text(values) -> str:
    """pgvector text input format for a python float sequence."""
    return "[" + ",".join(f"{float(v):.6f}" for v in values) + "]"


def _radial_drift(samples: list) -> float | None:
    """Semantic drift of a body: mean centroid-distance of its LATE half of
    signals minus its EARLY half (Pedro 2026-07-02 — the comet tail should
    mean "moving away from / toward the story", measured, not decorative).
    Positive = receding from the thread; negative = approaching. None when
    there are too few samples to split honestly."""
    if len(samples) < 4:
        return None
    ordered = sorted(samples, key=lambda p: p[0])
    half = len(ordered) // 2
    early = sum(d for _, d in ordered[:half]) / half
    late = sum(d for _, d in ordered[half:]) / (len(ordered) - half)
    return round(late - early, 5)


def build_orbital_bodies(rows, *, max_entities: int = 24, max_countries: int = 12) -> list:
    """Aggregate member-signal rows into orbital bodies (pure, testable).

    ``rows``: dicts with timestamp (datetime), country_code, persons (list),
    dist (float). Returns typed entity bodies + country bodies with per-body
    signal counts, presence window, raw timestamps, mean centroid distance,
    and radial drift (late-vs-early distance trend).
    """
    from app.services.subjects import classify_subject

    entities: dict = {}
    countries: dict = {}
    for r in rows:
        ts = r["timestamp"]
        dist = float(r["dist"])
        tone = float(r.get("sentiment") or 0)
        sid = r.get("id")
        cc = (r.get("country_code") or "").strip().upper()
        if cc:
            b = countries.setdefault(cc, {"n": 0, "dist_total": 0.0, "tone_total": 0.0, "timestamps": [], "samples": [], "signal_ids": set()})
            b["n"] += 1
            b["dist_total"] += dist
            b["tone_total"] += tone
            b["timestamps"].append(ts)
            b["samples"].append((ts, dist))
            if sid is not None:
                b["signal_ids"].add(sid)
        for person in (r.get("persons") or []):
            name = (person or "").strip()
            if not name:
                continue
            key = name.lower()
            b = entities.setdefault(key, {"label": name, "n": 0, "dist_total": 0.0, "tone_total": 0.0, "timestamps": [], "samples": [], "signal_ids": set()})
            b["n"] += 1
            b["dist_total"] += dist
            b["tone_total"] += tone
            b["timestamps"].append(ts)
            b["samples"].append((ts, dist))
            if sid is not None:
                b["signal_ids"].add(sid)

    bodies = []
    ranked_entities = sorted(entities.values(), key=lambda b: -b["n"])[:max_entities]
    for b in ranked_entities:
        subject_type = classify_subject(b["label"])
        if subject_type is None:
            continue
        stamps = sorted(b["timestamps"])
        bodies.append({
            "id": f"entity-{b['label'].lower()}",
            "label": b["label"],
            "type": subject_type,
            "n": b["n"],
            "dist": round(b["dist_total"] / b["n"], 5),
            "drift": _radial_drift(b["samples"]),
            "tone": round(b["tone_total"] / b["n"], 3),
            "first_seen": stamps[0].isoformat(),
            "last_seen": stamps[-1].isoformat(),
            "timestamps": [t.isoformat() for t in stamps],
            "_signal_ids": b["signal_ids"],
        })
    ranked_countries = sorted(countries.items(), key=lambda kv: -kv[1]["n"])[:max_countries]
    for cc, b in ranked_countries:
        stamps = sorted(b["timestamps"])
        bodies.append({
            "id": f"country-{cc}",
            "label": cc,
            "type": "country",
            "n": b["n"],
            "dist": round(b["dist_total"] / b["n"], 5),
            "drift": _radial_drift(b["samples"]),
            "tone": round(b["tone_total"] / b["n"], 3),
            "first_seen": stamps[0].isoformat(),
            "last_seen": stamps[-1].isoformat(),
            "timestamps": [t.isoformat() for t in stamps],
            "_signal_ids": b["signal_ids"],
        })

    # MOONS (Pedro 2026-07-02, spec 7b): a small ENTITY that appears almost
    # only inside a bigger entity's signals is its satellite — co-occurrence
    # measured on shared member signals, no fabricated physics. Countries
    # never become moons (a country is a stage, not a companion).
    entity_bodies = [b for b in bodies if b["type"] != "country"]
    for small in entity_bodies:
        if small["n"] > 6:
            continue
        best = None
        for big in entity_bodies:
            if big is small or big["n"] < max(4, small["n"] * 2):
                continue
            if not small["_signal_ids"]:
                continue
            overlap = len(small["_signal_ids"] & big["_signal_ids"]) / len(small["_signal_ids"])
            if overlap >= 0.75 and (best is None or big["n"] > best[1]["n"]):
                best = (overlap, big)
        if best:
            small["moon_of"] = best[1]["id"]
            small["moon_overlap"] = round(best[0], 3)
    for b in bodies:
        b.pop("_signal_ids", None)
    return bodies


@router.get("/api/v2/theme/{theme_code}/orbital")
async def get_theme_orbital(
    theme_code: str,
    hours: int = Query(168, ge=1, le=8760),
):
    """Orbital Thread View data: thread center + orbiting bodies with REAL
    semantic distance (member signal embeddings vs the topic centroid).
    Contract orbital-thread-v0; honest empties, never fabricated layout."""
    empty = {
        "contract": "orbital-thread-v0",
        "theme": theme_code,
        "hours": hours,
        "center": None,
        "bodies": [],
    }
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 15000")
            centroid_text: Optional[str] = None
            centroid_basis = "stored"
            center = None
            topic_id_text = theme_code.lower()

            if topic_id_text.startswith("dynamic-topic-") and topic_id_text[len("dynamic-topic-"):].isdigit():
                topic_row = await conn.fetchrow(
                    "SELECT id, label, category, crisis_relevant, centroid_vec"
                    " FROM dynamic_topics WHERE id = $1 AND state = 'active'",
                    int(topic_id_text[len("dynamic-topic-"):]),
                )
                if not topic_row:
                    return {**empty, "reason": "topic_not_found"}
                center = {
                    "label": topic_row["label"],
                    "category": topic_row["category"],
                    "crisis_relevant": bool(topic_row["crisis_relevant"])
                        if topic_row["crisis_relevant"] is not None else None,
                }
                if topic_row["centroid_vec"]:
                    centroid_text = _vector_text(topic_row["centroid_vec"])
            elif "-" in topic_id_text:
                # Thread ids may carry the '--cc' suffix — strip like the detail path.
                atlas_slug = topic_id_text.split("--")[0]
                atlas_row = await conn.fetchrow(
                    "SELECT slug, label, parent_domain FROM atlas_topics WHERE slug = $1",
                    atlas_slug,
                )
                if not atlas_row:
                    return {**empty, "reason": "topic_not_found"}
                topic_id_text = atlas_slug
                center = {
                    "label": atlas_row["label"],
                    "category": atlas_row["parent_domain"],
                    "crisis_relevant": None,
                }
            else:
                return {**empty, "reason": "unsupported_theme_kind"}

            # Window on assigned_at (carries source assignment time since the
            # F0.3 ETL fix) — atlas topics hold ALL-TIME members (3K+ ids), and
            # an unbounded set made the computed-centroid path take ~26s cold.
            member_ids = [
                r["signal_id"] for r in await conn.fetch(
                    f"""
                    SELECT DISTINCT signal_id FROM topic_members
                    WHERE topic_id = $1 AND role = 'evidence' AND signal_id IS NOT NULL
                      AND assigned_at > NOW() - INTERVAL '{int(hours)} hours'
                    """,
                    topic_id_text,
                )
            ]
            if not member_ids:
                # §I: a story keeps ITS OWN timeline — when the request window
                # has aged past every assignment (dt-981 went empty the night
                # its Jun-26 members crossed the 168h line), serve the most
                # recent members instead of an empty system. LIMIT keeps the
                # atlas perf bound (unbounded was the 26s cold path).
                member_ids = [
                    r["signal_id"] for r in await conn.fetch(
                        """
                        SELECT signal_id FROM (
                            SELECT DISTINCT ON (signal_id) signal_id, assigned_at
                            FROM topic_members
                            WHERE topic_id = $1 AND role = 'evidence' AND signal_id IS NOT NULL
                            ORDER BY signal_id, assigned_at DESC
                        ) m ORDER BY m.assigned_at DESC LIMIT 400
                        """,
                        topic_id_text,
                    )
                ]
            if not member_ids and topic_id_text.startswith("dynamic-topic-"):
                # topic_members is an ETL projection and can be mid-rebuild
                # (2026-07-03: the nightly pass left dt-981 at 0 rows). The
                # engine's own member record — sample_signal_ids via the
                # topic's clusters — is the same source the detail serves.
                member_ids = [
                    r["signal_id"] for r in await conn.fetch(
                        """
                        SELECT DISTINCT sid.signal_id
                        FROM dynamic_topic_members dtm
                        JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
                        LEFT JOIN LATERAL unnest(ec.sample_signal_ids) AS sid(signal_id) ON TRUE
                        WHERE dtm.dynamic_topic_id = $1 AND sid.signal_id IS NOT NULL
                        """,
                        int(topic_id_text[len("dynamic-topic-"):]),
                    )
                ]
            if not member_ids:
                return {**empty, "center": center, "reason": "no_members"}

            if centroid_text is None:
                centroid_basis = "computed"
                centroid_text = await conn.fetchval(
                    """
                    SELECT avg(vec::vector(768))::text FROM signal_embeddings
                    WHERE signal_id = ANY($1::bigint[])
                    """,
                    member_ids,
                )
                if not centroid_text:
                    return {**empty, "center": center, "reason": "no_embeddings"}

            rows = await conn.fetch(
                f"""
                SELECT s.id, s.timestamp, s.country_code, s.persons,
                       COALESCE(s.nlp_sentiment, s.sentiment) AS sentiment,
                       (se.vec::vector(768) <=> $2::vector(768)) AS dist
                FROM signals_v2 s
                JOIN signal_embeddings se ON se.signal_id = s.id
                WHERE s.id = ANY($1::bigint[])
                """,
                member_ids, centroid_text,
            )
            if not rows:
                return {**empty, "center": center, "reason": "no_embedded_members"}

            bodies = build_orbital_bodies([dict(r) for r in rows])
            stamps = sorted(r["timestamp"] for r in rows)
            return {
                "contract": "orbital-thread-v0",
                "theme": theme_code,
                "hours": hours,
                "centroid_basis": centroid_basis,
                "center": {
                    **(center or {}),
                    "member_count": len(rows),
                    "window": {
                        "start": stamps[0].isoformat(),
                        "end": stamps[-1].isoformat(),
                    },
                },
                "bodies": bodies,
            }
    except Exception as exc:
        logger.error("orbital view failed for %s: %s", theme_code, exc)
        return {**empty, "reason": "error"}
