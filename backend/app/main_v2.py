"""
Observatory Global v2 - Simplified Backend API

NO Docker orchestration
NO custom aggregation code
Direct async PostgreSQL queries to v2 schema
Hot-reload enabled with uvicorn --reload

SCHEMA SAFETY / TABLE MAPPINGS:
- /api/v2/trends, /api/v2/compare -> use signals_country_hourly, signals_theme_hourly, signals_source_hourly
- /api/v2/nodes (extended range)  -> uses country_daily_v2
- /api/v2/nodes (short range)     -> uses country_hourly_v2
- /api/v2/anomalies               -> uses country_baseline_stats
(Note: These tables DO exist in the live DB and are populated)
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from datetime import datetime, timezone
from typing import Optional
import os
import sys

# Add parent directory to path for indicator imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import indicator modules
try:
    from indicators.source_diversity import calculate_source_diversity, DIVERSITY_TOOLTIP
    from indicators.source_quality import calculate_source_quality, get_allowlist, get_denylist, QUALITY_TOOLTIP
    from indicators.normalized_volume import calculate_normalized_volume, VOLUME_TOOLTIP
    INDICATORS_AVAILABLE = True
except ImportError:
    INDICATORS_AVAILABLE = False


app = FastAPI(
    title="Observatory Global v2",
    description="Simplified real-time global narrative tracking",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory")

@app.on_event("startup")
async def startup():
    """Create async connection pool on startup."""
    app.state.pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    print(f"✅ Connected to database: {DATABASE_URL.split('@')[1]}")

@app.on_event("shutdown")
async def shutdown():
    """Close connection pool on shutdown."""
    await app.state.pool.close()

@app.get("/api/v2/stats")
async def get_system_stats():
    """
    System-wide database statistics.
    Shows total signals, time range, and ingestion health.
    """
    async with app.state.pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                COUNT(*) AS total_signals,
                MIN(timestamp) AS oldest_signal,
                MAX(timestamp) AS newest_signal,
                COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '1 hour') AS signals_1h,
                COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '24 hours') AS signals_24h,
                COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '7 days') AS signals_7d,
                COUNT(DISTINCT country_code) AS unique_countries,
                COUNT(DISTINCT source_name) AS unique_sources
            FROM signals_v2
        """)
        
        # Check recent ingestion health
        recent = await conn.fetchval("""
            SELECT COUNT(*) FROM signals_v2 
            WHERE timestamp > NOW() - INTERVAL '2 hours'
        """)
        
        ingestion_status = "healthy" if recent > 100 else "stalled" if recent == 0 else "low"
        
        return {
            "database": {
                "total_signals": row['total_signals'],
                "signals_1h": row['signals_1h'],
                "signals_24h": row['signals_24h'],
                "signals_7d": row['signals_7d'],
                "unique_countries": row['unique_countries'],
                "unique_sources": row['unique_sources'],
                "oldest_signal": row['oldest_signal'].isoformat() if row['oldest_signal'] else None,
                "newest_signal": row['newest_signal'].isoformat() if row['newest_signal'] else None
            },
            "ingestion": {
                "status": ingestion_status,
                "signals_last_2h": recent
            },
            "retention": {
                "policy": "90 days raw (configurable)",
                "note": "Check data_lifecycle_config table for settings"
            }
        }


@app.get("/api/v2/trends")
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
    async with app.state.pool.acquire() as conn:
        # Force daily bucket for longer ranges
        if bucket == "1h" and days > 7:
            bucket = "1d"
        
        bucket_interval = "hour" if bucket == "1h" else "day"
        
        if entity_type == "global":
            rows = await conn.fetch(f"""
                SELECT 
                    date_trunc('{bucket_interval}', bucket) AS time_bucket,
                    SUM(signal_count) AS signal_count,
                    ROUND(AVG(avg_sentiment)::numeric, 2) AS avg_sentiment,
                    SUM(unique_sources) AS unique_sources
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
                    ROUND(AVG(avg_sentiment)::numeric, 2) AS avg_sentiment,
                    SUM(unique_sources) AS unique_sources
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
                "unique_sources": row.get('unique_sources')
            }
            for row in rows
        ]
        
        return {
            "entity": {"type": entity_type, "value": entity_value},
            "window": {"days": days, "bucket": bucket},
            "data": data_points,
            "meta": {"points": len(data_points)}
        }


@app.get("/api/v2/compare")
async def compare_periods(
    entity_type: str = Query(..., description="Type: country, theme, or global"),
    entity_value: Optional[str] = Query(None, description="Value for entity"),
    window: str = Query("24h", description="Window size: 24h, 7d, etc"),
    baseline: str = Query("previous", description="Baseline: previous or Nd_ago")
):
    """
    Compare two time periods for trend analysis.
    Returns signal count, sentiment, and percent change.
    """
    from datetime import timedelta
    
    async with app.state.pool.acquire() as conn:
        # Parse window
        if window.endswith('h'):
            hours = int(window[:-1])
        elif window.endswith('d'):
            hours = int(window[:-1]) * 24
        else:
            hours = 24
        
        # Calculate time ranges using raw SQL
        if entity_type == "global":
            query = """
                SELECT 
                    SUM(signal_count) AS signals,
                    AVG(avg_sentiment) AS sentiment
                FROM signals_country_hourly
                WHERE bucket >= NOW() - ($1 * INTERVAL '1 hour')
                  AND bucket < NOW() - ($2 * INTERVAL '1 hour')
            """
            result_a = await conn.fetchrow(query, hours, 0)
            result_b = await conn.fetchrow(query, hours * 2, hours)
            
        elif entity_type == "country":
            query = """
                SELECT 
                    SUM(signal_count) AS signals,
                    AVG(avg_sentiment) AS sentiment
                FROM signals_country_hourly
                WHERE country_code = $1
                  AND bucket >= NOW() - ($2 * INTERVAL '1 hour')
                  AND bucket < NOW() - ($3 * INTERVAL '1 hour')
            """
            result_a = await conn.fetchrow(query, entity_value.upper(), hours, 0)
            result_b = await conn.fetchrow(query, entity_value.upper(), hours * 2, hours)
            
        elif entity_type == "theme":
            query = """
                SELECT 
                    SUM(signal_count) AS signals,
                    AVG(avg_sentiment) AS sentiment
                FROM signals_theme_hourly
                WHERE theme ILIKE $1
                  AND bucket >= NOW() - ($2 * INTERVAL '1 hour')
                  AND bucket < NOW() - ($3 * INTERVAL '1 hour')
            """
            result_a = await conn.fetchrow(query, f"%{entity_value}%", hours, 0)
            result_b = await conn.fetchrow(query, f"%{entity_value}%", hours * 2, hours)
        else:
            return {"error": f"Unknown entity_type: {entity_type}"}
        
        signals_a = result_a['signals'] or 0 if result_a else 0
        signals_b = result_b['signals'] or 0 if result_b else 0
        tone_a = float(result_a['sentiment']) if result_a and result_a['sentiment'] else 0
        tone_b = float(result_b['sentiment']) if result_b and result_b['sentiment'] else 0
        
        signals_delta = signals_a - signals_b
        signals_pct = ((signals_a - signals_b) / signals_b * 100) if signals_b > 0 else 0
        
        return {
            "entity": {"type": entity_type, "value": entity_value},
            "period_a": {"label": f"Last {window}", "signals": signals_a, "avg_sentiment": round(tone_a, 2)},
            "period_b": {"label": f"Previous {window}", "signals": signals_b, "avg_sentiment": round(tone_b, 2)},
            "delta": {
                "signals": signals_delta,
                "signals_pct": round(signals_pct, 1),
                "sentiment": round(tone_a - tone_b, 2)
            }
        }

@app.get("/api/v2/nodes")
async def get_nodes(
    hours: int = Query(24, ge=1, le=8760, description="Hours of data (1-168) - ignored if range is set"),
    time_range: Optional[str] = Query(None, alias="range", description="Time range: 24h, 1w, 1m, 3m, record"),
    focus_type: Optional[str] = Query(None, description="Focus type: theme, person, country, source"),
    focus_value: Optional[str] = Query(None, description="Value to focus on"),
    limit: int = Query(100, ge=1, le=200, description="Max nodes to return (1-200, capped at 100 by default)")
):
    """Get country nodes with aggregated stats. Supports focus filtering and extended time ranges."""
    async with app.state.pool.acquire() as conn:
        
        # Parse range parameter (takes precedence over hours)
        use_daily_rollup = False
        effective_hours = hours
        if time_range:
            range_map = {
                "24h": 24,
                "1w": 168,
                "1m": 720,    # 30 days
                "3m": 2160,   # 90 days
                "record": 8760  # ~1 year, will use all data
            }
            effective_hours = range_map.get(time_range, hours)
            # Use daily rollup for ranges > 168 hours (1 week)
            use_daily_rollup = effective_hours > 168
        
        # If focus is active, query signals_v2 directly with filtering
        if focus_type and focus_value:
            # Build focus filter based on type
            if focus_type == "theme":
                focus_filter = "$1 = ANY(themes)"
                filter_value = focus_value.upper()
            elif focus_type == "person":
                focus_filter = "EXISTS (SELECT 1 FROM unnest(persons) p WHERE LOWER(p) LIKE LOWER($1))"
                filter_value = f"%{focus_value}%"
            elif focus_type == "country":
                focus_filter = "country_code = $1"
                filter_value = focus_value.upper()
            elif focus_type == "source":
                focus_filter = "LOWER(source_name) LIKE LOWER($1)"
                filter_value = f"%{focus_value}%"
            else:
                return {"nodes": [], "count": 0, "hours": effective_hours, "error": f"Unknown focus_type: {focus_type}"}
            
            # Query signals_v2 with focus filter (limit to 168 hours for focus queries)
            query_hours = min(effective_hours, 168)
            # Enforce server-side cap of 100 nodes
            effective_limit = min(limit, 100)
            rows = await conn.fetch(f"""
                WITH filtered AS (
                    SELECT
                        country_code,
                        sentiment,
                        source_name
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '{query_hours} hours'
                      AND {focus_filter}
                )
                SELECT
                    f.country_code,
                    c.name,
                    c.latitude,
                    c.longitude,
                    COUNT(*) as total_signals,
                    AVG(f.sentiment) as sentiment,
                    COUNT(DISTINCT f.source_name) as unique_sources
                FROM filtered f
                LEFT JOIN countries_v2 c ON f.country_code = c.code
                GROUP BY f.country_code, c.name, c.latitude, c.longitude
                HAVING COUNT(*) > 0
                ORDER BY total_signals DESC
                LIMIT {effective_limit}
            """, filter_value)
        elif use_daily_rollup:
            # Use daily rollup for extended ranges (1m, 3m, record)
            days = effective_hours // 24
            # Enforce server-side cap of 100 nodes
            effective_limit = min(limit, 100)
            rows = await conn.fetch("""
                SELECT
                    d.country_code,
                    c.name,
                    c.latitude,
                    c.longitude,
                    SUM(d.signal_count) as total_signals,
                    AVG(d.avg_sentiment) as sentiment,
                    MAX(d.max_sentiment) as max_sentiment,
                    MIN(d.min_sentiment) as min_sentiment,
                    SUM(d.unique_sources) as unique_sources
                FROM country_daily_v2 d
                LEFT JOIN countries_v2 c ON d.country_code = c.code
                WHERE d.day > CURRENT_DATE - INTERVAL '%s days'
                GROUP BY d.country_code, c.name, c.latitude, c.longitude
                HAVING SUM(d.signal_count) > 0
                ORDER BY total_signals DESC
                LIMIT %s
            """ % (days, effective_limit))
        else:
            # Use hourly materialized view for short ranges (faster)
            # Enforce server-side cap of 100 nodes
            effective_limit = min(limit, 100)
            rows = await conn.fetch("""
                SELECT
                    h.country_code,
                    c.name,
                    c.latitude,
                    c.longitude,
                    SUM(h.signal_count) as total_signals,
                    AVG(h.avg_sentiment) as sentiment,
                    MAX(h.max_sentiment) as max_sentiment,
                    MIN(h.min_sentiment) as min_sentiment,
                    SUM(h.unique_sources) as unique_sources
                FROM country_hourly_v2 h
                LEFT JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - INTERVAL '%s hours'
                GROUP BY h.country_code, c.name, c.latitude, c.longitude
                HAVING SUM(h.signal_count) > 0
                ORDER BY total_signals DESC
                LIMIT %s
            """ % (effective_hours, effective_limit))
        
        if not rows:
            return {"nodes": [], "count": 0, "hours": effective_hours, "range": time_range, "focus_type": focus_type, "focus_value": focus_value}
        
        max_signals = max(float(r['total_signals']) for r in rows)
        
        nodes = []
        total_signals = 0
        for row in rows:
            if row['latitude'] and row['longitude']:
                signal_count = int(row['total_signals'])
                total_signals += signal_count
                nodes.append({
                    "id": row['country_code'],
                    "name": row['name'] or row['country_code'],
                    "lat": float(row['latitude']),
                    "lon": float(row['longitude']),
                    "intensity": float(row['total_signals']) / max_signals,
                    "sentiment": float(row['sentiment'] or 0) / 10,  # Normalize to -1 to 1
                    "signalCount": signal_count,
                    "sourceCount": int(row['unique_sources'] or 0)
                })
        
        return {
            "nodes": nodes,
            "count": len(nodes),
            "totalSignals": total_signals,
            "hours": effective_hours,
            "range": time_range,
            "focus_type": focus_type,
            "focus_value": focus_value,
            "is_filtered": focus_type is not None,
            "source": "daily_rollup" if use_daily_rollup else "hourly_rollup"
        }

@app.get("/api/v2/anomalies")
async def get_anomalies(
    hours: int = Query(24, ge=1, le=8760),
    limit: int = Query(10, ge=1, le=20)
):
    """
    Return top anomalous countries (activity significantly above baseline).
    Uses country_baseline_stats table for 7-day rolling baseline.
    """
    try:
        async with app.state.pool.acquire() as conn:
            rows = await conn.fetch("""
                WITH current_counts AS (
                    SELECT 
                        country_code,
                        COUNT(*) as signal_count
                    FROM signals_v2
                    WHERE timestamp > NOW() - ($1::int * INTERVAL '1 hour')
                    AND country_code IS NOT NULL
                    GROUP BY country_code
                    HAVING COUNT(*) >= 10
                )
                SELECT 
                    c.country_code,
                    co.name as country_name,
                    c.signal_count,
                    COALESCE(b.avg_daily_signals, 50) as baseline_avg,
                    ROUND((c.signal_count::numeric / NULLIF(COALESCE(b.avg_daily_signals, 50) / 24 * $1, 0)), 2) as multiplier,
                    ROUND(((c.signal_count - COALESCE(b.avg_daily_signals, 50) / 24 * $1) / 
                           NULLIF(COALESCE(b.stddev_daily_signals, 25) / 24 * $1, 0))::numeric, 2) as zscore
                FROM current_counts c
                LEFT JOIN country_baseline_stats b ON c.country_code = b.country_code
                LEFT JOIN countries_v2 co ON c.country_code = co.code
                WHERE (c.signal_count::numeric / NULLIF(COALESCE(b.avg_daily_signals, 50) / 24 * $1, 0)) > 1.2
                ORDER BY zscore DESC NULLS LAST
                LIMIT $2
            """, hours, limit)
            
            def classify_anomaly(multiplier, zscore):
                if multiplier is None or zscore is None:
                    return "normal"
                if zscore > 3 and multiplier > 2:
                    return "critical"
                if zscore > 2:
                    return "elevated"
                if zscore > 1:
                    return "notable"
                return "normal"
            
            anomalies = []
            for row in rows:
                multiplier = float(row['multiplier']) if row['multiplier'] else 0
                zscore = float(row['zscore']) if row['zscore'] else 0
                level = classify_anomaly(multiplier, zscore)
                
                anomalies.append({
                    "country_code": row['country_code'],
                    "country_name": row['country_name'] or row['country_code'],
                    "current_count": row['signal_count'],
                    "baseline_avg": float(row['baseline_avg']),
                    "multiplier": multiplier,
                    "zscore": zscore,
                    "level": level
                })
            
            # Determine overall severity
            critical_count = sum(1 for a in anomalies if a["level"] == "critical")
            elevated_count = sum(1 for a in anomalies if a["level"] == "elevated")
            
            overall = "normal"
            if critical_count > 0:
                overall = "critical"
            elif elevated_count > 0:
                overall = "elevated"
            elif len(anomalies) > 0:
                overall = "notable"
            
            return {
                "anomalies": anomalies,
                "overall_severity": overall,
                "meta": {
                    "time_window_hours": hours,
                    "baseline_window_days": 7,
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
    except Exception as e:
        print(f"Error in anomalies endpoint: {e}")
        import traceback
        traceback.print_exc()
        return {"anomalies": [], "overall_severity": "normal", "error": str(e)}

@app.get("/api/v2/heatmap")
async def get_heatmap(hours: int = Query(24, ge=1, le=8760)):
    """Deprecated - heatmap data now comes from nodes with glow effect."""
    return {
        "points": [],
        "count": 0,
        "message": "Heatmap deprecated, use nodes with glow effect"
    }

@app.get("/api/v2/search")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    hours: int = Query(168, ge=1, le=720)
):
    """Search across themes, countries, sources, and persons."""
    query = q.lower().strip()
    
    async with app.state.pool.acquire() as conn:
        # Search in themes
        theme_results = await conn.fetch("""
            SELECT 
                unnest(themes) as theme,
                country_code,
                COUNT(*) as count
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            AND LOWER(array_to_string(themes, ' ')) LIKE $1
            GROUP BY theme, country_code
            ORDER BY count DESC
            LIMIT 20
        """ % hours, f'%{query}%')
        
        # Search in sources
        source_results = await conn.fetch("""
            SELECT 
                source_name,
                country_code,
                COUNT(*) as count
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            AND LOWER(source_name) LIKE $1
            GROUP BY source_name, country_code
            ORDER BY count DESC
            LIMIT 10
        """ % hours, f'%{query}%')
        
        # Search countries by name
        country_results = await conn.fetch("""
            SELECT code, name, latitude, longitude
            FROM countries_v2
            WHERE LOWER(name) LIKE $1 OR LOWER(code) LIKE $1
            LIMIT 10
        """, f'%{query}%')
        
        # Search in persons
        person_results = await conn.fetch("""
            SELECT 
                unnest(persons) as person,
                country_code,
                COUNT(*) as count
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            AND LOWER(array_to_string(persons, ' ')) LIKE $1
            GROUP BY person, country_code
            ORDER BY count DESC
            LIMIT 10
        """ % hours, f'%{query}%')
        
        return {
            "query": q,
            "themes": [{"theme": r['theme'], "country": r['country_code'], "count": int(r['count'])} for r in theme_results],
            "sources": [{"source": r['source_name'], "country": r['country_code'], "count": int(r['count'])} for r in source_results],
            "countries": [{"code": r['code'], "name": r['name']} for r in country_results],
            "persons": [{"person": r['person'], "country": r['country_code'], "count": int(r['count'])} for r in person_results]
        }

@app.get("/api/v2/focus")
async def get_focus_data(
    focus_type: str = Query(..., description="Type: theme, person, country, source"),
    value: str = Query(..., description="Value to focus on"),
    hours: int = Query(24, ge=1, le=8760)
):
    """
    Get filtered data for Focus Mode.
    Returns nodes, related topics, and top sources matching the focus.
    """
    async with app.state.pool.acquire() as conn:
        # Build WHERE clause based on focus type
        if focus_type == "theme":
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
                timestamp
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
              AND source_url IS NOT NULL
            ORDER BY LEFT(source_url, 100), timestamp DESC
            LIMIT 10
        """, filter_value)
        
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
                "generated_at": datetime.utcnow().isoformat()
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
                    "source": r['source_name'],
                    "count": int(r['count']),
                    "avg_sentiment": float(r['avg_sentiment'] or 0)
                }
                for r in sources
            ],
            "headlines": [
                {
                    "url": r['source_url'],
                    "source": r['source_name'],
                    "time": r['timestamp'].isoformat() if r['timestamp'] else None
                }
                for r in headlines
            ]
        }

@app.get("/api/v2/theme/{theme_code}")
async def get_theme_details(
    theme_code: str,
    country_code: str = Query(None, description="Filter by country"),
    hours: int = Query(24, ge=1, le=8760)
):
    """Get detailed information about a theme including rich context."""
    try:
        async with app.state.pool.acquire() as conn:
            # Build WHERE clause based on filters
            where_conditions = [
                "$1 = ANY(themes)",
                f"timestamp > NOW() - INTERVAL '{hours} hours'"
            ]
            params = [theme_code.upper()]
            
            if country_code:
                where_conditions.append("country_code = $2")
                params.append(country_code.upper())
            
            where_clause = " AND ".join(where_conditions)
            
            # Get signals
            signals = await conn.fetch(f"""
                SELECT 
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
            
            # Get timeline
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
            
            # Get country breakdown
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
            
            # Get related themes (co-occurrence)
            related_themes_data = await conn.fetch(f"""
                SELECT 
                    unnest(themes) as related_theme,
                    COUNT(*) as count
                FROM signals_v2
                WHERE $1 = ANY(themes)
                AND timestamp > NOW() - INTERVAL '{hours} hours'
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
                LIMIT 10
            """, *params)
            
            # Calculate summary stats
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
                for p in sorted(person_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            return {
                "theme": theme_code,
                "country": country_code,
                "hours": hours,
                "total": total,
                "avgSentiment": round(avg_sentiment, 3),
                "signals": [
                    {
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
                "countryBreakdown": [
                    {"code": r['country_code'], "count": int(r['count']), "sentiment": float(r['avg_sentiment'] or 0)}
                    for r in country_breakdown
                ],
                "relatedThemes": related_themes,
                "topSources": [
                    {"name": r['source_name'], "count": int(r['count']), "sentiment": float(r['avg_sentiment'] or 0)}
                    for r in top_sources
                ],
                "topPersons": top_persons,
                "timeline": [
                    {"hour": t['hour'].isoformat(), "count": int(t['count']), "sentiment": float(t['avg_sentiment'] or 0)}
                    for t in timeline
                ]
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
            "error": str(e)
        }

@app.get("/api/v2/signals")
async def get_signals(
    country_code: str = Query(None),
    theme: str = Query(None),
    hours: int = Query(24, ge=1, le=8760),
    since: Optional[datetime] = Query(None, description="Fetch signals since this timestamp"),
    limit: int = Query(50, ge=1, le=500)
):
    """Get raw signals with filters and velocity calculation."""
    async with app.state.pool.acquire() as conn:
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
        
        if theme:
            param_count += 1
            conditions.append(f"${param_count} = ANY(themes)")
            params.append(theme.upper())
        
        where_clause = " AND ".join(conditions)
        
        rows = await conn.fetch(f"""
            SELECT 
                id,
                timestamp,
                country_code,
                source_name,
                source_url,
                headline,
                sentiment,
                themes
            FROM signals_v2
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT {limit}
        """, *params)
        
        # Calculate velocity
        vel_last = await conn.fetchval(f"""
            SELECT COUNT(*) FROM signals_v2 
            WHERE {where_clause} AND timestamp > NOW() - INTERVAL '1 minute'
        """, *params)
        
        vel_prev = await conn.fetchval(f"""
            SELECT COUNT(*) FROM signals_v2 
            WHERE {where_clause} AND timestamp > NOW() - INTERVAL '2 minutes' AND timestamp <= NOW() - INTERVAL '1 minute'
        """, *params)
        
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
                    "themes": r['themes'] or []
                }
                for r in rows
            ]
        }

@app.get("/api/v3/crisis/signals")
async def get_crisis_signals(
    hours: int = Query(24, ge=1, le=8760),
    country: str = Query(None),
    severity: str = Query(None),
    event_type: str = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    """Get crisis-related signals only with filtering options."""
    async with app.state.pool.acquire() as conn:
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

@app.get("/api/v3/crisis/summary")
async def get_crisis_summary(hours: int = Query(24, ge=1, le=8760)):
    """Get summary statistics for crisis signals."""
    async with app.state.pool.acquire() as conn:
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

@app.get("/api/v2/flows")
async def get_flows(
    hours: int = Query(24, ge=1, le=8760, description="Hours (ignored if range set)"),
    time_range: Optional[str] = Query(None, alias="range", description="Time range: 24h, 1w, 1m, 3m, record"),
    focus_type: Optional[str] = Query(None, description="Focus type: theme, person, country, source"),
    focus_value: Optional[str] = Query(None, description="Value to focus on")
):
    """
    Calculate flows based on theme co-occurrence between countries.
    Two countries are connected if they share significant theme overlap.
    Supports focus filtering to show flows only for focused signals.
    """
    try:
        async with app.state.pool.acquire() as conn:
            # Parse range parameter (takes precedence over hours)
            effective_hours = hours
            if time_range:
                range_map = {
                    "1h": 1, "6h": 6, "12h": 12, # Future proofing
                    "24h": 24,
                    "1w": 168,
                    "1m": 720,    # 30 days
                    "3m": 2160,   # 90 days
                    "record": 8760  # ~1 year
                }
                effective_hours = range_map.get(time_range, hours)

            # Build focus filter if provided
            focus_filter = ""
            filter_value = None
            if focus_type and focus_value:
                if focus_type == "theme":
                    focus_filter = "AND $1 = ANY(themes)"
                    filter_value = focus_value.upper()
                elif focus_type == "person":
                    focus_filter = "AND EXISTS (SELECT 1 FROM unnest(persons) p WHERE LOWER(p) LIKE LOWER($1))"
                    filter_value = f"%{focus_value}%"
                elif focus_type == "country":
                    focus_filter = "AND country_code = $1"
                    filter_value = focus_value.upper()
                elif focus_type == "source":
                    focus_filter = "AND LOWER(source_name) LIKE LOWER($1)"
                    filter_value = f"%{focus_value}%"
            
            # Get theme vectors for each country
            if filter_value:
                country_themes = await conn.fetch(f"""
                    WITH theme_counts AS (
                        SELECT 
                            country_code,
                            unnest(themes) as theme,
                            COUNT(*) as cnt
                        FROM signals_v2
                        WHERE timestamp > NOW() - INTERVAL '{effective_hours} hours'
                        AND themes IS NOT NULL AND array_length(themes, 1) > 0
                        {focus_filter}
                        GROUP BY country_code, theme
                        HAVING COUNT(*) >= 2
                    )
                    SELECT 
                        country_code,
                        array_agg(theme ORDER BY cnt DESC) as themes,
                        SUM(cnt) as total
                    FROM theme_counts
                    GROUP BY country_code
                    HAVING SUM(cnt) >= 3
                """, filter_value)
            else:
                country_themes = await conn.fetch("""
                    WITH theme_counts AS (
                        SELECT 
                            country_code,
                            unnest(themes) as theme,
                            COUNT(*) as cnt
                        FROM signals_v2
                        WHERE timestamp > NOW() - INTERVAL '%s hours'
                        AND themes IS NOT NULL AND array_length(themes, 1) > 0
                        GROUP BY country_code, theme
                        HAVING COUNT(*) >= 2
                    )
                    SELECT 
                        country_code,
                        array_agg(theme ORDER BY cnt DESC) as themes,
                        SUM(cnt) as total
                    FROM theme_counts
                    GROUP BY country_code
                    HAVING SUM(cnt) >= 5
                """ % effective_hours)
            
            # Get coordinates
            coords = {r['code']: (float(r['longitude']), float(r['latitude'])) 
                      for r in await conn.fetch(
                          "SELECT code, latitude, longitude FROM countries_v2 WHERE latitude IS NOT NULL"
                      )}
            
            flows = []
            countries = list(country_themes)
            
            # Calculate Jaccard similarity between all pairs
            for i in range(len(countries)):
                for j in range(i + 1, len(countries)):
                    c1, c2 = countries[i], countries[j]
                    code1, code2 = c1['country_code'], c2['country_code']
                    
                    if code1 not in coords or code2 not in coords:
                        continue
                    
                    # Get top themes for each
                    themes1 = set(c1['themes'][:30])
                    themes2 = set(c2['themes'][:30])
                    
                    # Jaccard similarity
                    intersection = themes1 & themes2
                    union = themes1 | themes2
                    
                    if len(union) == 0:
                        continue
                        
                    similarity = len(intersection) / len(union)
                    
                    # Only create flow if significant overlap (>20% themes shared)
                    if similarity >= 0.2 and len(intersection) >= 3:
                        # Strength based on similarity AND volume
                        strength = similarity * min(int(c1['total']), int(c2['total'])) / 10
                        
                        flows.append({
                            "source": list(coords[code1]),
                            "target": list(coords[code2]),
                            "sourceCountry": code1,
                            "targetCountry": code2,
                            "strength": round(strength, 2),
                            "similarity": round(similarity, 3),
                            "sharedThemes": list(intersection)[:5],
                            "sharedCount": len(intersection)
                        })
            
            # Sort by strength and return top flows
            flows.sort(key=lambda x: x['strength'], reverse=True)
            
            return {"flows": flows[:100], "total": len(flows)}
    except Exception as e:
        # Log error but don't crash - return empty flows
        print(f"Error in flows endpoint: {e}")
        import traceback
        traceback.print_exc()
        return {"flows": [], "total": 0, "error": str(e)}

@app.get("/api/v2/country/{country_code}")
async def get_country_detail(country_code: str, hours: int = Query(24, ge=1, le=8760)):
    """Get detailed information for a specific country."""
    country_code = country_code.upper()
    
    async with app.state.pool.acquire() as conn:
        # Basic stats from materialized view
        stats = await conn.fetchrow("""
            SELECT 
                SUM(signal_count) as total_signals,
                AVG(avg_sentiment) as sentiment,
                MAX(max_sentiment) as max_sentiment,
                MIN(min_sentiment) as min_sentiment
            FROM country_hourly_v2
            WHERE country_code = $1
            AND hour > NOW() - INTERVAL '%s hours'
        """ % hours, country_code)
        
        if not stats or not stats['total_signals']:
            raise HTTPException(status_code=404, detail=f"No data for country {country_code}")
        
        # Top themes (from array aggregation)
        themes = await conn.fetch("""
            SELECT unnest(themes) as theme, COUNT(*) as count
            FROM signals_v2
            WHERE country_code = $1
            AND timestamp > NOW() - INTERVAL '%s hours'
            AND themes IS NOT NULL
            GROUP BY theme
            ORDER BY count DESC
            LIMIT 10
        """ % hours, country_code)
        
        # Top sources
        sources = await conn.fetch("""
            SELECT source_name, COUNT(*) as count
            FROM signals_v2
            WHERE country_code = $1
            AND timestamp > NOW() - INTERVAL '%s hours'
            AND source_name IS NOT NULL
            GROUP BY source_name
            ORDER BY count DESC
            LIMIT 20
        """ % hours, country_code)
        
        # Key persons
        persons = await conn.fetch("""
            SELECT unnest(persons) as person, COUNT(*) as count
            FROM signals_v2
            WHERE country_code = $1
            AND timestamp > NOW() - INTERVAL '%s hours'
            AND persons IS NOT NULL
            GROUP BY person
            ORDER BY count DESC
            LIMIT 10
        """ % hours, country_code)
        
        # Determine country name
        country_record = await conn.fetchrow(
            "SELECT name FROM countries_v2 WHERE code = $1", country_code
        )
        country_name = country_record['name'] if country_record else country_code
        
        return {
            "countryCode": country_code,
            "name": country_name,
            "totalSignals": int(stats['total_signals'] or 0),
            "sentiment": float(stats['sentiment'] or 0) / 10,
            "maxSentiment": float(stats['max_sentiment'] or 0) / 10,
            "minSentiment": float(stats['min_sentiment'] or 0) / 10,
            "themes": [{"name": t['theme'], "count": t['count']} for t in themes],
            "sources": [{"name": s['source_name'], "count": s['count']} for s in sources],
            "keyPersons": [{"name": p['person'], "count": p['count']} for p in persons]
        }

@app.get("/api/v2/briefing")
async def get_briefing(hours: int = Query(24, ge=1, le=8760)):
    """Get morning briefing summary."""
    async with app.state.pool.acquire() as conn:
        # Top countries by activity
        top_countries = await conn.fetch("""
            SELECT 
                s.country_code,
                c.name,
                COUNT(*) as total,
                AVG(s.sentiment) as sentiment
            FROM signals_v2 s
            JOIN countries_v2 c ON s.country_code = c.code
            WHERE s.timestamp > NOW() - INTERVAL '%s hours'
            GROUP BY s.country_code, c.name
            ORDER BY total DESC
            LIMIT 10
        """ % hours)
        
        # Most negative sentiment
        negative_sentiment = await conn.fetch("""
            SELECT 
                s.country_code,
                c.name,
                AVG(s.sentiment) as sentiment,
                COUNT(*) as total
            FROM signals_v2 s
            JOIN countries_v2 c ON s.country_code = c.code
            WHERE s.timestamp > NOW() - INTERVAL '%s hours'
            GROUP BY s.country_code, c.name
            HAVING COUNT(*) > 10
            ORDER BY sentiment ASC
            LIMIT 10
        """ % hours)
        
        # Most positive sentiment
        positive_sentiment = await conn.fetch("""
            SELECT 
                s.country_code,
                c.name,
                AVG(s.sentiment) as sentiment,
                COUNT(*) as total
            FROM signals_v2 s
            JOIN countries_v2 c ON s.country_code = c.code
            WHERE s.timestamp > NOW() - INTERVAL '%s hours'
            GROUP BY s.country_code, c.name
            HAVING COUNT(*) > 10
            ORDER BY sentiment DESC
            LIMIT 10
        """ % hours)
        
        # Top themes globally
        top_themes = await conn.fetch("""
            SELECT 
                unnest(themes) as theme,
                COUNT(*) as count
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            GROUP BY theme
            ORDER BY count DESC
            LIMIT 10
        """ % hours)
        
        # Top sources
        top_sources = await conn.fetch("""
            SELECT 
                source_name,
                COUNT(*) as count
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            AND source_name IS NOT NULL
            GROUP BY source_name
            ORDER BY count DESC
            LIMIT 5
        """ % hours)
        
        # Overall stats
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_signals,
                COUNT(DISTINCT country_code) as countries,
                COUNT(DISTINCT source_name) as sources,
                AVG(sentiment) as avg_sentiment
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '%s hours'
        """ % hours)
        
        return {
            "period_hours": hours,
            "generated_at": datetime.utcnow().isoformat(),
            "stats": {
                "total_signals": stats['total_signals'] or 0,
                "countries": stats['countries'] or 0,
                "sources": stats['sources'] or 0,
                "avg_sentiment": float(stats['avg_sentiment'] or 0)
            },
            "top_countries": [
                {"code": r['country_code'], "name": r['name'], "signals": r['total'], "sentiment": float(r['sentiment'] or 0)}
                for r in top_countries
            ],
            "negative_sentiment": [
                {"code": r['country_code'], "name": r['name'], "sentiment": float(r['sentiment'] or 0), "signals": r['total']}
                for r in negative_sentiment
            ],
            "positive_sentiment": [
                {"code": r['country_code'], "name": r['name'], "sentiment": float(r['sentiment'] or 0), "signals": r['total']}
                for r in positive_sentiment
            ],
            "top_themes": [
                {"theme": r['theme'], "count": r['count']}
                for r in top_themes
            ],
            "top_sources": [
                {"source": r['source_name'], "count": r['count']}
                for r in top_sources
            ]
        }


# =============================================================================
# TRUST INDICATORS API (v3)
# =============================================================================

@app.get("/api/indicators/tooltips")
async def get_indicator_tooltips():
    """Return tooltip explanations for all trust indicators."""
    if not INDICATORS_AVAILABLE:
        return {"error": "Indicators module not available"}
    
    return {
        "source_diversity": DIVERSITY_TOOLTIP,
        "source_quality": QUALITY_TOOLTIP,
        "normalized_volume": VOLUME_TOOLTIP
    }


@app.get("/api/indicators/allowlist")
async def get_quality_allowlist():
    """Return the current source quality allowlist for transparency."""
    if not INDICATORS_AVAILABLE:
        return {"error": "Indicators module not available"}
    
    sources = get_allowlist()
    return {
        "count": len(sources),
        "sources": sources,
        "description": "Major wire services and established news outlets with editorial standards."
    }


@app.get("/api/indicators/denylist")
async def get_quality_denylist():
    """Return the current source quality denylist for transparency."""
    if not INDICATORS_AVAILABLE:
        return {"error": "Indicators module not available"}
    
    sources = get_denylist()
    return {
        "count": len(sources),
        "sources": sources,
        "description": "Sources with documented reliability issues."
    }


@app.get("/api/indicators/country/{country_code}")
async def get_country_indicators(
    country_code: str,
    hours: int = Query(default=720, ge=1, le=8760)
):
    """
    Get all trust indicators for a country in a time window.
    
    Returns diversity, quality, and volume metrics.
    """
    if not INDICATORS_AVAILABLE:
        return {"error": "Indicators module not available"}
    
    async with app.state.pool.acquire() as conn:
        # Get source domains for diversity and quality
        source_rows = await conn.fetch("""
            SELECT source_name
            FROM signals_v2
            WHERE country_code = $1
            AND timestamp > NOW() - INTERVAL '%s hours'
            AND source_name IS NOT NULL
        """ % hours, country_code.upper())
        
        domains = [r['source_name'] for r in source_rows]
        
        if not domains:
            return {
                "country_code": country_code.upper(),
                "hours": hours,
                "signal_count": 0,
                "error": f"No signals found for {country_code} in last {hours} hours"
            }
        
        # Calculate diversity and quality
        diversity = calculate_source_diversity(domains)
        quality = calculate_source_quality(domains)
        
        # Get volume baseline (7-day rolling)
        volume_data = await conn.fetchrow("""
            WITH current_period AS (
                SELECT COUNT(*) as current_count
                FROM signals_v2
                WHERE country_code = $1
                AND timestamp > NOW() - INTERVAL '%s hours'
            ),
            baseline_data AS (
                SELECT 
                    date_trunc('day', timestamp) as day,
                    COUNT(*) as day_count
                FROM signals_v2
                WHERE country_code = $1
                AND timestamp > NOW() - INTERVAL '7 days'
                AND timestamp <= NOW() - INTERVAL '%s hours'
                GROUP BY day
            )
            SELECT 
                (SELECT current_count FROM current_period) as current_count,
                AVG(day_count) as baseline_avg,
                COALESCE(STDDEV(day_count), 0) as baseline_stddev
            FROM baseline_data
        """ % (hours, hours), country_code.upper())
        
        current_count = volume_data['current_count'] or 0
        baseline_avg = float(volume_data['baseline_avg'] or 0)
        baseline_stddev = float(volume_data['baseline_stddev'] or 0)
        
        # Scale baseline to match hours parameter
        hours_ratio = hours / 24
        baseline_avg_scaled = baseline_avg * hours_ratio
        baseline_stddev_scaled = baseline_stddev * hours_ratio
        
        volume = calculate_normalized_volume(
            current_count,
            baseline_avg_scaled,
            baseline_stddev_scaled
        )
        
        return {
            "country_code": country_code.upper(),
            "hours": hours,
            "signal_count": current_count,
            "diversity": diversity,
            "quality": quality,
            "volume": volume
        }


@app.get("/health")
async def health():
    """
    Health check endpoint with database connectivity and ingestion metrics.
    
    Returns:
        - status: 'healthy', 'degraded', or 'error'
        - db_ok: database connectivity status
        - last_ingest_ts: timestamp of most recent signal
        - ingest_lag_minutes: minutes since last ingestion
        - rows_ingested_last_15m: signals ingested in last 15 minutes
        - error_count_last_15m: placeholder for error tracking
    """
    try:
        async with app.state.pool.acquire() as conn:
            # Check DB connectivity
            db_ok = True
            try:
                await conn.fetchval("SELECT 1")
            except Exception:
                db_ok = False
            
            # Get ingestion metrics
            result = await conn.fetchrow("""
                SELECT 
                    MAX(timestamp) as last_ts,
                    COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '15 minutes') as rows_15m,
                    COUNT(*) as total_signals
                FROM signals_v2
            """)
            
            last_ingest_ts = result['last_ts'] if result else None
            rows_ingested_last_15m = result['rows_15m'] if result else 0
            total_signals = result['total_signals'] if result else 0
            
            # Calculate lag
            ingest_lag_minutes = None
            if last_ingest_ts:
                ingest_lag_minutes = (datetime.utcnow() - last_ingest_ts.replace(tzinfo=None)).total_seconds() / 60
            
            # Determine status
            # Healthy: DB OK and ingestion within 30 minutes
            # Degraded: DB OK but ingestion stale (>30 min lag)
            # Error: DB not OK
            if not db_ok:
                status = "error"
            elif ingest_lag_minutes is None or ingest_lag_minutes > 30:
                status = "degraded"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "db_ok": db_ok,
                "timestamp": datetime.utcnow().isoformat(),
                "last_ingest_ts": last_ingest_ts.isoformat() if last_ingest_ts else None,
                "ingest_lag_minutes": round(ingest_lag_minutes, 1) if ingest_lag_minutes else None,
                "rows_ingested_last_15m": rows_ingested_last_15m,
                "total_signals": total_signals,
                "error_count_last_15m": 0  # TODO: implement error tracking table
            }
    except Exception as e:
        return {
            "status": "error",
            "db_ok": False,
            "timestamp": datetime.utcnow().isoformat(),
            "message": str(e),
            "last_ingest_ts": None,
            "ingest_lag_minutes": None,
            "rows_ingested_last_15m": 0,
            "total_signals": 0,
            "error_count_last_15m": 0
        }


@app.get("/api/v2/narratives")
async def get_narratives(hours: int = Query(24, ge=1, le=8760), limit: int = Query(5, ge=1, le=20)):
    """Get top narrative threads with spread and velocity data."""
    from app.core.gdelt_taxonomy import get_theme_label
    import traceback
    
    try:
        async with app.state.pool.acquire() as conn:
            # Count total active countries in this window for spread_pct denominator
            total_active = await conn.fetchval("""
                SELECT COUNT(DISTINCT country_code)
                FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '%s hours'
            """ % hours)
            total_active = max(total_active or 1, 1)
            
            # Get top N themes by signal count
            top_themes = await conn.fetch("""
                SELECT 
                    unnest(themes) as theme,
                    COUNT(*) as signal_count,
                    COUNT(DISTINCT country_code) as country_count,
                    COUNT(DISTINCT source_name) as source_count,
                    MIN(timestamp) as first_seen
                FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                AND themes IS NOT NULL
                GROUP BY theme
                ORDER BY signal_count DESC
                LIMIT %s
            """ % (hours, limit))
            
            narratives = []
            for t in top_themes:
                theme_code = t['theme']
                
                # Velocity: last hour vs previous hour
                last_hour = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '1 hour'
                    AND themes IS NOT NULL
                    AND $1 = ANY(themes)
                """, theme_code)
                last_hour = last_hour or 0
                
                prev_hour = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '2 hours'
                    AND timestamp <= NOW() - INTERVAL '1 hour'
                    AND themes IS NOT NULL
                    AND $1 = ANY(themes)
                """, theme_code)
                prev_hour = prev_hour or 0
                
                # Determine trend
                if prev_hour > 0 and last_hour > prev_hour * 1.2:
                    trend = "accelerating"
                elif prev_hour > 0 and last_hour < prev_hour * 0.8:
                    trend = "fading"
                else:
                    trend = "stable"
                
                # Hourly timeline (last 24 data points or less)
                timeline_hours = min(hours, 24)
                timeline = await conn.fetch("""
                    SELECT 
                        date_trunc('hour', timestamp) as hour,
                        COUNT(*) as count
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    AND themes IS NOT NULL
                    AND $1 = ANY(themes)
                    GROUP BY hour
                    ORDER BY hour ASC
                """ % timeline_hours, theme_code)
                
                hourly_timeline = [
                    {"hour": r['hour'].strftime('%H:%M'), "count": int(r['count'])}
                    for r in timeline
                ]
                
                # Top 3 countries
                top_countries_rows = await conn.fetch("""
                    SELECT country_code, COUNT(*) as cnt
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    AND themes IS NOT NULL
                    AND $1 = ANY(themes)
                    GROUP BY country_code
                    ORDER BY cnt DESC
                    LIMIT 3
                """ % hours, theme_code)
                top_countries = [r['country_code'] for r in top_countries_rows]
                
                spread_pct = round((t['country_count'] / total_active) * 100, 1)
                
                narratives.append({
                    "theme_code": theme_code,
                    "label": get_theme_label(theme_code),
                    "signal_count": int(t['signal_count']),
                    "country_count": int(t['country_count']),
                    "source_count": int(t['source_count']),
                    "first_seen": t['first_seen'].isoformat() if t['first_seen'] else None,
                    "velocity": int(last_hour),
                    "trend": trend,
                    "spread_pct": spread_pct,
                    "hourly_timeline": hourly_timeline,
                    "top_countries": top_countries
                })
            
            return {
                "narratives": narratives,
                "hours": hours,
                "total_active_countries": int(total_active),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        traceback.print_exc()
        return {"narratives": [], "hours": hours, "error": str(e)}

@app.get("/api/v2/correlation")
async def get_correlation(
    mode: str = Query("country", description="mode: 'country' or 'theme'"),
    hours: int = Query(24, ge=1, le=8760),
    limit: int = Query(12, ge=2, le=30)
):
    """Get N*N correlation matrix (Jaccard similarity) for countries or themes."""
    from app.core.gdelt_taxonomy import get_theme_label
    import traceback
    
    try:
        async with app.state.pool.acquire() as conn:
            if mode == "theme":
                # 1. Top themes by signal count
                top_themes = await conn.fetch("""
                    SELECT unnest(themes) as theme, COUNT(*) as cnt
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    AND themes IS NOT NULL
                    GROUP BY theme
                    ORDER BY cnt DESC
                    LIMIT %s
                """ % (hours, limit))
                
                theme_codes = [r['theme'] for r in top_themes]
                theme_counts = {r['theme']: r['cnt'] for r in top_themes}
                
                if not theme_codes:
                    return {"mode": mode, "entities": [], "entity_names": {}, "matrix": [], "hours": hours}
                
                # 2. Get exact intersection counts via LATERAL-like self cross
                intersections = await conn.fetch("""
                    SELECT t1.theme as theme1, t2.theme as theme2, COUNT(*) as intersection_count
                    FROM signals_v2 s, unnest(s.themes) as t1(theme), unnest(s.themes) as t2(theme)
                    WHERE s.timestamp > NOW() - INTERVAL '%s hours'
                    AND t1.theme = ANY($1) AND t2.theme = ANY($1)
                    GROUP BY t1.theme, t2.theme
                """ % hours, theme_codes)
                
                intersect_map = {}
                for r in intersections:
                    t1, t2 = r['theme1'], r['theme2']
                    if t1 not in intersect_map: intersect_map[t1] = {}
                    intersect_map[t1][t2] = r['intersection_count']
                
                # 3. Build Matrix
                N = len(theme_codes)
                matrix = [[0.0 for _ in range(N)] for _ in range(N)]
                entity_names = {t: get_theme_label(t) for t in theme_codes}
                
                for i in range(N):
                    t1 = theme_codes[i]
                    c1 = theme_counts[t1]
                    for j in range(i, N):
                        t2 = theme_codes[j]
                        if i == j:
                            matrix[i][j] = 1.0
                        else:
                            c2 = theme_counts[t2]
                            int_cnt = intersect_map.get(t1, {}).get(t2, 0)
                            union = c1 + c2 - int_cnt
                            jaccard = round((int_cnt / union) if union > 0 else 0.0, 3)
                            matrix[i][j] = jaccard
                            matrix[j][i] = jaccard
                
                return {
                    "mode": mode,
                    "entities": theme_codes,
                    "entity_names": entity_names,
                    "matrix": matrix,
                    "hours": hours
                }
                
            else: # mode == "country"
                # 1. Top countries by signal count
                top_countries = await conn.fetch("""
                    SELECT country_code, COUNT(*) as cnt
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    GROUP BY country_code
                    ORDER BY cnt DESC
                    LIMIT %s
                """ % (hours, limit))
                
                country_codes = [r['country_code'] for r in top_countries]
                
                if not country_codes:
                    return {"mode": mode, "entities": [], "entity_names": {}, "matrix": [], "hours": hours}
                
                # Resolve proper names
                names_res = await conn.fetch("""
                    SELECT code, name FROM countries_v2 WHERE code = ANY($1)
                """, country_codes)
                entity_names = {r['code']: (r['name'] or r['code']) for r in names_res}
                for code in country_codes:
                    if code not in entity_names:
                        entity_names[code] = code
                
                # 2. Get themes per country
                country_themes_rows = await conn.fetch("""
                    SELECT country_code, unnest(themes) as theme
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    AND country_code = ANY($1)
                    AND themes IS NOT NULL
                """ % hours, country_codes)
                
                country_themes = {c: set() for c in country_codes}
                for r in country_themes_rows:
                    country_themes[r['country_code']].add(r['theme'])
                
                # 3. Build Matrix
                N = len(country_codes)
                matrix = [[0.0 for _ in range(N)] for _ in range(N)]
                
                for i in range(N):
                    c1 = country_codes[i]
                    t1_set = country_themes[c1]
                    for j in range(i, N):
                        c2 = country_codes[j]
                        if i == j:
                            matrix[i][j] = 1.0
                        else:
                            t2_set = country_themes[c2]
                            intersection = t1_set & t2_set
                            union = t1_set | t2_set
                            jaccard = round((len(intersection) / len(union)) if len(union) > 0 else 0.0, 3)
                            matrix[i][j] = jaccard
                            matrix[j][i] = jaccard
                
                return {
                    "mode": mode,
                    "entities": country_codes,
                    "entity_names": entity_names,
                    "matrix": matrix,
                    "hours": hours
                }
                
    except Exception as e:
        traceback.print_exc()
        return {"mode": mode, "error": str(e)}

@app.get("/")
async def root():
    """API root with available endpoints."""
    return {
        "name": "Observatory Global v2",
        "version": "2.0.0",
        "endpoints": {
            "nodes": "/api/v2/nodes?hours=24",
            "heatmap": "/api/v2/heatmap?hours=24",
            "flows": "/api/v2/flows?hours=24",
            "country": "/api/v2/country/{code}?hours=24",
            "health": "/health"
        },
        "docs": "/docs"
    }
