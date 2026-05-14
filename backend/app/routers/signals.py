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
    limit: int = Query(50, ge=1, le=500)
):
    """Get raw signals with filters and velocity calculation."""
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
        
        rows = await conn.fetch(f"""
            SELECT
                id,
                timestamp,
                country_code,
                source_name,
                source_url,
                headline,
                {sentiment_expr} AS sentiment,
                themes,
                persons,
                {nlp_persons_expr},
                {nlp_framing_expr}
            FROM signals_v2
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT {limit}
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
        
        return {
            "count": len(rows),
            "velocity": {
                "signals_per_minute": velocity,
                "delta": velocity_delta,
                "percentage_change": round(velocity_pct, 1)
            },
            "signals": [
                {
                    "id": r['id'],
                    "timestamp": r['timestamp'].isoformat(),
                    "country": r['country_code'],
                    "source": r['source_name'],
                    "url": r['source_url'],
                    "headline": r['headline'],
                    "sentiment": float(r['sentiment'] or 0),
                    "themes": r['themes'] or [],
                    "persons": _resolve_persons(r['nlp_persons'], r['persons']),
                    "framing": r['nlp_framing']
                }
                for r in rows
            ]
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

