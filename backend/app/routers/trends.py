from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query
from app import db

router = APIRouter()

@router.get("/api/v2/trends")
async def get_trends(
    entity_type: str = Query(..., description="Type: country, theme, source, or global"),
    entity_value: Optional[str] = Query(None, description="Value for the entity type"),
    days: int = Query(7, ge=1, le=90, description="Days of history"),
    bucket: str = Query("1d", description="Bucket size: 1h or 1d")
):
    """
    Return time series trend data from pre-computed hourly aggregates.
    Much faster than querying raw signals for historical analysis.
    """
    async with db.pool.acquire() as conn:
        # Force daily bucket for longer ranges
        if bucket == "1h" and days > 7:
            bucket = "1d"
        
        bucket_interval = "hour" if bucket == "1h" else "day"
        
        if entity_type == "global":
            rows = await conn.fetch(f"""
                SELECT
                    date_trunc('{bucket_interval}', bucket) AS time_bucket,
                    SUM(signal_count) AS signal_count,
                    ROUND(AVG(avg_sentiment)::numeric, 2) AS avg_sentiment
                FROM signals_country_hourly
                WHERE bucket > NOW() - ($1 * INTERVAL '1 day')
                GROUP BY 1
                ORDER BY 1 ASC
            """, days)

        elif entity_type == "country":
            if not entity_value:
                return {"error": "entity_value required for country trends"}
            rows = await conn.fetch(f"""
                SELECT
                    date_trunc('{bucket_interval}', bucket) AS time_bucket,
                    SUM(signal_count) AS signal_count,
                    ROUND(AVG(avg_sentiment)::numeric, 2) AS avg_sentiment
                FROM signals_country_hourly
                WHERE country_code = $1
                  AND bucket > NOW() - ($2 * INTERVAL '1 day')
                GROUP BY 1
                ORDER BY 1 ASC
            """, entity_value.upper(), days)
            
        elif entity_type == "theme":
            if not entity_value:
                return {"error": "entity_value required for theme trends"}
            rows = await conn.fetch(f"""
                SELECT 
                    date_trunc('{bucket_interval}', bucket) AS time_bucket,
                    SUM(signal_count) AS signal_count,
                    ROUND(AVG(avg_sentiment)::numeric, 2) AS avg_sentiment
                FROM signals_theme_hourly
                WHERE theme ILIKE $1
                  AND bucket > NOW() - ($2 * INTERVAL '1 day')
                GROUP BY 1
                ORDER BY 1 ASC
            """, f"%{entity_value}%", days)
            
        elif entity_type == "source":
            if not entity_value:
                return {"error": "entity_value required for source trends"}
            rows = await conn.fetch(f"""
                SELECT 
                    date_trunc('{bucket_interval}', bucket) AS time_bucket,
                    SUM(signal_count) AS signal_count,
                    ROUND(AVG(avg_sentiment)::numeric, 2) AS avg_sentiment
                FROM signals_source_hourly
                WHERE source_name ILIKE $1
                  AND bucket > NOW() - ($2 * INTERVAL '1 day')
                GROUP BY 1
                ORDER BY 1 ASC
            """, f"%{entity_value}%", days)
        else:
            return {"error": f"Unknown entity_type: {entity_type}"}
        
        data_points = [
            {
                "time": row['time_bucket'].isoformat() if row['time_bucket'] else None,
                "signal_count": row['signal_count'] or 0,
                "avg_sentiment": float(row['avg_sentiment']) if row['avg_sentiment'] else 0,
            }
            for row in rows
        ]
        
        return {
            "entity": {"type": entity_type, "value": entity_value},
            "window": {"days": days, "bucket": bucket},
            "data": data_points,
            "meta": {"points": len(data_points)}
        }


@router.get("/api/v2/trends/search")
async def get_trending_searches(
    country_code: Optional[str] = Query(None, description="ISO 2-letter country code"),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=50)
):
    """Get trending Google searches for a country or globally."""
    try:
        async with db.pool.acquire() as conn:
            if country_code:
                rows = await conn.fetch("""
                    SELECT keyword, rank, approximate_volume, timestamp, country_code
                    FROM trends_v2
                    WHERE country_code = $1
                    AND timestamp > NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC, rank ASC
                    LIMIT %s
                """ % (hours, limit), country_code.upper())
            else:
                # Global: group by keyword, count how many countries have it
                rows = await conn.fetch("""
                    SELECT keyword, MIN(rank) as rank, COUNT(DISTINCT country_code) as country_count,
                           MAX(timestamp) as timestamp
                    FROM trends_v2
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    GROUP BY keyword
                    ORDER BY country_count DESC, rank ASC
                    LIMIT %s
                """ % (hours, limit))

            return {
                "trending": [
                    {
                        "keyword": r['keyword'],
                        "rank": r['rank'],
                        "country_code": r.get('country_code'),
                        "country_count": r.get('country_count'),
                        "timestamp": r['timestamp'].isoformat() if r['timestamp'] else None,
                    }
                    for r in rows
                ],
                "country_code": country_code,
                "hours": hours,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        return {"trending": [], "error": str(e)}


@router.get("/api/v2/trends/match")
async def get_trends_theme_match(
    theme: str = Query(..., description="GDELT theme code to check against trending searches"),
    hours: int = Query(24, ge=1, le=168)
):
    """Check if a GDELT theme matches any current Google trending searches.
    Returns matching keywords and their countries — useful for 'public interest' badges.
    """
    from app.core.gdelt_taxonomy import get_theme_label

    label = get_theme_label(theme).lower()
    # Extract meaningful words from theme label (skip short words)
    theme_words = [w for w in label.split() if len(w) > 3]

    if not theme_words:
        return {"matches": [], "theme": theme, "has_public_interest": False}

    try:
        async with db.pool.acquire() as conn:
            # Build ILIKE conditions for each theme word
            conditions = " OR ".join([f"LOWER(keyword) LIKE '%' || ${i+1} || '%'" for i in range(len(theme_words))])
            query = f"""
                SELECT keyword, country_code, rank, timestamp
                FROM trends_v2
                WHERE timestamp > NOW() - INTERVAL '{hours} hours'
                AND ({conditions})
                ORDER BY rank ASC
                LIMIT 10
            """
            rows = await conn.fetch(query, *theme_words)

            matches = [
                {
                    "keyword": r['keyword'],
                    "country_code": r['country_code'],
                    "rank": r['rank'],
                }
                for r in rows
            ]

            return {
                "matches": matches,
                "theme": theme,
                "theme_label": get_theme_label(theme),
                "has_public_interest": len(matches) > 0,
                "country_count": len(set(m['country_code'] for m in matches)),
            }
    except Exception as e:
        return {"matches": [], "theme": theme, "has_public_interest": False, "error": str(e)}


# =============================================================================
# WIKIPEDIA PAGEVIEWS API
# =============================================================================

