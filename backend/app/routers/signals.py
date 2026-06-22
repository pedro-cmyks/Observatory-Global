from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query
from app import db
from app.utils import _resolve_persons, extract_domain

router = APIRouter()

@router.get("/api/v2/signals")
async def get_signals(
    country_code: str = Query(None),
    countries: Optional[str] = Query(None, description="Comma-separated country codes (e.g. IR,AE,OM)"),
    theme: str = Query(None),
    person: str = Query(None),
    hours: int = Query(24, ge=1, le=8760),
    since: Optional[datetime] = Query(None, description="Fetch signals since this timestamp"),
    limit: int = Query(50, ge=1, le=500),
    lane: Optional[str] = Query(None, description="Filter to a stream lane: analyst|sports|entertainment|general"),
    sort: str = Query("recent", description="recent | relevance (analyst-grade ranking)"),
):
    """Get raw signals with filters and velocity calculation.

    Each signal carries a ``lane`` (analyst|sports|entertainment|general) and a
    0..1 ``relevanceScore`` so the Signal Stream can promote analyst-grade items
    and separate sports/entertainment noise (#177). ``lane`` filters the result;
    ``sort=relevance`` ranks by relevance score then recency.
    """
    from app.services.stream_relevance import score_stream_signal
    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 10000")
        has_nlp_columns = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'signals_v2'
                  AND column_name = 'nlp_sentiment'
            )
        """)
        sentiment_expr = "COALESCE(nlp_sentiment, sentiment)" if has_nlp_columns else "sentiment"
        nlp_persons_expr = "nlp_persons" if has_nlp_columns else "NULL::jsonb AS nlp_persons"
        nlp_framing_expr = "nlp_framing" if has_nlp_columns else "NULL::text AS nlp_framing"
        conditions = ["timestamp > NOW() - INTERVAL '%s hours'" % hours]
        params = []
        param_count = 0

        if since:
            param_count += 1
            conditions.append(f"timestamp > ${param_count}")
            params.append(since)

        if country_code:
            param_count += 1
            conditions.append(f"country_code = ${param_count}")
            params.append(country_code.upper())

        if countries and not country_code:
            codes = [c.strip().upper() for c in countries.split(',') if c.strip()]
            if codes:
                param_count += 1
                conditions.append(f"country_code = ANY(${param_count})")
                params.append(codes)

        if theme:
            param_count += 1
            conditions.append(f"${param_count} = ANY(themes)")
            params.append(theme.upper())

        if person:
            param_count += 1
            conditions.append(f"EXISTS (SELECT 1 FROM unnest(persons) p WHERE LOWER(p) LIKE LOWER(${param_count}))")
            params.append(f"%{person}%")
        
        where_clause = " AND ".join(conditions)

        # When ranking or filtering by lane, classification happens in Python
        # after the fetch, so pull a wider window to give the lane material.
        fetch_limit = max(limit, 200) if (lane or sort == "relevance") else limit

        rows = await conn.fetch(f"""
            SELECT
                id,
                timestamp,
                country_code,
                source_name,
                source_url,
                headline,
                snippet,
                source_lang,
                {sentiment_expr} AS sentiment,
                themes,
                persons,
                {nlp_persons_expr},
                {nlp_framing_expr}
            FROM signals_v2
            WHERE {where_clause}
            -- Prefer information-rich signals in the stream (has body snippet,
            -- named people, themes) over bare ones, then most recent first.
            -- Display ordering only — does not affect any counts/heat/metrics.
            ORDER BY (
                (snippet IS NOT NULL AND snippet <> '')::int
                + (array_length(persons, 1) IS NOT NULL)::int
                + (array_length(themes, 1) IS NOT NULL)::int
            ) DESC, timestamp DESC
            LIMIT {fetch_limit}
        """, *params, timeout=8.0)

        # Calculate velocity
        vel_last = await conn.fetchval(f"""
            SELECT COUNT(*) FROM signals_v2
            WHERE {where_clause} AND timestamp > NOW() - INTERVAL '1 minute'
        """, *params, timeout=5.0)

        vel_prev = await conn.fetchval(f"""
            SELECT COUNT(*) FROM signals_v2
            WHERE {where_clause} AND timestamp > NOW() - INTERVAL '2 minutes' AND timestamp <= NOW() - INTERVAL '1 minute'
        """, *params, timeout=5.0)
        
        velocity = vel_last or 0
        velocity_delta = (vel_last or 0) - (vel_prev or 0)
        velocity_pct = ((vel_last or 0) - (vel_prev or 0)) / (vel_prev or 1) * 100
        
        signals = []
        for r in rows:
            themes = r['themes'] or []
            relevance = score_stream_signal(themes, r['headline'])
            signals.append({
                "id": r['id'],
                "timestamp": r['timestamp'].isoformat(),
                "country": r['country_code'],
                "source": r['source_name'],
                "url": r['source_url'],
                "headline": r['headline'],
                "snippet": r['snippet'],
                "source_lang": (r['source_lang'] or '').strip() or None,
                "sentiment": float(r['sentiment'] or 0),
                "themes": themes,
                "persons": _resolve_persons(r['nlp_persons'], r['persons']),
                "framing": r['nlp_framing'],
                "lane": relevance["lane"],
                "relevanceScore": relevance["relevanceScore"],
            })

        if lane:
            signals = [s for s in signals if s["lane"] == lane.lower()]

        if sort == "relevance":
            signals.sort(key=lambda s: (s["relevanceScore"], s["timestamp"]), reverse=True)

        signals = signals[:limit]

        return {
            "count": len(signals),
            "velocity": {
                "signals_per_minute": velocity,
                "delta": velocity_delta,
                "percentage_change": round(velocity_pct, 1)
            },
            "signals": signals
        }

@router.get("/api/v3/crisis/signals")
async def get_crisis_signals(
    hours: int = Query(24, ge=1, le=8760),
    country: str = Query(None),
    severity: str = Query(None),
    event_type: str = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    """Get crisis-related signals only with filtering options."""
    async with db.pool.acquire() as conn:
        conditions = [
            "is_crisis = TRUE",
            f"timestamp > NOW() - INTERVAL '{hours} hours'"
        ]
        params = []
        
        if country:
            params.append(country.upper())
            conditions.append(f"country_code = ${len(params)}")
        
        if severity:
            params.append(severity.lower())
            conditions.append(f"severity = ${len(params)}")
        
        if event_type:
            params.append(event_type.lower())
            conditions.append(f"event_type = ${len(params)}")
        
        where_clause = " AND ".join(conditions)
        
        rows = await conn.fetch(f"""
            SELECT 
                id, timestamp, country_code, sentiment,
                source_name, source_url, crisis_themes,
                severity, event_type, crisis_score
            FROM signals_v2
            WHERE {where_clause}
            ORDER BY 
                CASE severity 
                    WHEN 'critical' THEN 1 
                    WHEN 'high' THEN 2 
                    WHEN 'medium' THEN 3 
                    ELSE 4 
                END,
                timestamp DESC
            LIMIT {limit}
        """, *params)
        
        return {
            "signals": [
                {
                    **dict(r),
                    "timestamp": r['timestamp'].isoformat(),
                }
                for r in rows
            ],
            "count": len(rows),
            "filters": {
                "hours": hours, 
                "country": country, 
                "severity": severity,
                "event_type": event_type
            }
        }

@router.get("/api/v3/crisis/summary")
async def get_crisis_summary(hours: int = Query(24, ge=1, le=8760)):
    """Get summary statistics for crisis signals."""
    async with db.pool.acquire() as conn:
        # Overall stats
        stats = await conn.fetchrow(f"""
            SELECT 
                COUNT(*) as total_signals,
                COUNT(*) FILTER (WHERE is_crisis) as crisis_signals,
                COUNT(DISTINCT country_code) FILTER (WHERE is_crisis) as countries_affected,
                COUNT(DISTINCT source_name) FILTER (WHERE is_crisis) as sources_reporting,
                AVG(crisis_score) FILTER (WHERE is_crisis) as avg_crisis_score
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
        """)
        
        # By severity
        by_severity = await conn.fetch(f"""
            SELECT severity, COUNT(*) as count, AVG(sentiment) as avg_sentiment
            FROM signals_v2
            WHERE is_crisis = TRUE AND timestamp > NOW() - INTERVAL '{hours} hours'
            GROUP BY severity
            ORDER BY 
                CASE severity 
                    WHEN 'critical' THEN 1 
                    WHEN 'high' THEN 2 
                    WHEN 'medium' THEN 3 
                    ELSE 4 
                END
        """)
        
        # By event type
        by_type = await conn.fetch(f"""
            SELECT event_type, COUNT(*) as count, AVG(sentiment) as avg_sentiment
            FROM signals_v2
            WHERE is_crisis = TRUE AND timestamp > NOW() - INTERVAL '{hours} hours'
            GROUP BY event_type
            ORDER BY count DESC
        """)
        
        # Top countries with crises
        top_countries = await conn.fetch(f"""
            SELECT 
                country_code, 
                COUNT(*) as count, 
                AVG(crisis_score) as avg_score,
                AVG(sentiment) as avg_sentiment
            FROM signals_v2
            WHERE is_crisis = TRUE AND timestamp > NOW() - INTERVAL '{hours} hours'
            GROUP BY country_code
            ORDER BY count DESC
            LIMIT 10
        """)
        
        return {
            "period_hours": hours,
            "totals": dict(stats),
            "by_severity": [
                {
                    **dict(r), 
                    "avg_sentiment": float(r['avg_sentiment'] or 0)
                } 
                for r in by_severity
            ],
            "by_event_type": [
                {
                    **dict(r),
                    "avg_sentiment": float(r['avg_sentiment'] or 0)
                }
                for r in by_type
            ],
            "top_countries": [
                {
                    **dict(r), 
                    "avg_score": float(r['avg_score'] or 0),
                    "avg_sentiment": float(r['avg_sentiment'] or 0)
                }
                for r in top_countries
            ]
        }



@router.get("/api/v2/signal/{signal_id}/context")
async def get_signal_context(
    signal_id: int,
    hours: int = Query(168, ge=1, le=8760),
    neighbors: int = Query(4, ge=1, le=10),
):
    """Per-signal narrative context (#228 §2.3 SignalDetail rebuild).

    Returns the Narrative Threads this signal is assigned to (the product
    story model — primary) and semantically-nearest signals from the
    persisted embedding corpus (labeled, gate-status-tagged — replaces the
    old 'related by any shared GDELT theme' heuristic that connected a
    Pakistan mosque blast to an Illinois tornado via 'Disaster Fire').

    Uses the signal's OWN stored embedding (mig 054), so no embed-service
    round trip: signals not yet embedded return neighbors=[] with a note.
    """
    from app.services.research_semantic import is_junk_headline
    import html as _html

    if db.pool is None:
        return {"signal_id": signal_id, "threads": [], "semantic_neighbors": [],
                "notes": ["database unavailable"]}

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 8000")

        threads = await conn.fetch(
            """
            SELECT t.slug, t.label, a.gate_kept, a.gate_score
            FROM signal_topic_assignments a
            JOIN atlas_topics t ON t.id = a.topic_id
            WHERE a.signal_id = $1
              AND a.method = 'lexicon'
              AND a.model_version = 'theme-hint-lex-v2'
            ORDER BY a.gate_score DESC NULLS LAST
            LIMIT 5
            """,
            signal_id,
        )

        notes: list[str] = []
        neighbor_rows: list = []
        # Fetch the vector first and pass it back as a constant: the HNSW
        # index only serves `vec <=> $const` — ordering by a joined column
        # (me.vec) forces a sequential scan over the whole corpus and blows
        # the statement timeout.
        own_vec = await conn.fetchval(
            "SELECT vec::text FROM signal_embeddings WHERE signal_id = $1",
            signal_id,
        )
        if own_vec:
            neighbor_rows = await conn.fetch(
                f"""
                SELECT s.id, s.headline, s.country_code, s.source_name,
                       s.source_url, s.timestamp,
                       1 - (e.vec <=> $2::halfvec) AS similarity,
                       EXISTS (SELECT 1 FROM signal_topic_assignments sta
                               WHERE sta.signal_id = s.id) AS has_topic
                FROM signal_embeddings e
                JOIN signals_v2 s ON s.id = e.signal_id
                WHERE e.signal_id <> $1
                  AND s.timestamp > NOW() - INTERVAL '{int(hours)} hours'
                ORDER BY e.vec <=> $2::halfvec
                LIMIT {int(neighbors * 4)}
                """,
                signal_id,
                own_vec,
            )
        else:
            notes.append("signal not embedded yet; semantic neighbors unavailable")

        own_headline = await conn.fetchval(
            "SELECT headline FROM signals_v2 WHERE id = $1", signal_id,
        )

    own_key = _html.unescape(own_headline or "").strip().lower()
    seen = {own_key} if own_key else set()
    semantic_neighbors = []
    for r in neighbor_rows:
        sim = float(r["similarity"])
        if sim < 0.60:  # context view: looser than evidence retrieval (0.84),
            continue    # but everything below carries its similarity visibly
        headline = _html.unescape(r["headline"] or "")
        if is_junk_headline(headline):
            continue
        key = headline.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        semantic_neighbors.append({
            "signal_id": int(r["id"]),
            "headline": headline,
            "country_code": r["country_code"],
            "source": r["source_name"],
            "url": r["source_url"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
            "similarity": round(sim, 4),
            "gate_status": "assigned" if r["has_topic"] else "below_gate",
        })
        if len(semantic_neighbors) >= neighbors:
            break

    return {
        "signal_id": signal_id,
        "threads": [
            {
                "slug": t["slug"],
                "label": t["label"],
                "gate_kept": bool(t["gate_kept"]) if t["gate_kept"] is not None else None,
                "gate_score": float(t["gate_score"]) if t["gate_score"] is not None else None,
            }
            for t in threads
        ],
        "semantic_neighbors": semantic_neighbors,
        "match_basis": "signal_embedding",
        "notes": notes,
    }
