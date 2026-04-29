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
import httpx
import asyncio
import time
import json

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
except ImportError:
    pass

# Add parent directory to path for indicator imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from urllib.parse import urlparse

def extract_domain(source_url: str) -> str:
    if not source_url:
        return "Unknown"
    try:
        parsed = urlparse(source_url if source_url.startswith('http') else f'http://{source_url}')
        domain = parsed.netloc or parsed.path
        return domain.replace('www.', '').split('/')[0] or source_url[:30]
    except (ValueError, AttributeError):
        return source_url[:30]

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
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

@app.on_event("startup")
async def startup():
    """Create async connection pool on startup, with retry for connection saturation."""
    for attempt in range(10):
        try:
            app.state.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
            print(f"✅ Connected to database: {DATABASE_URL.split('@')[1]}")
            break
        except Exception as e:
            if attempt < 9:
                wait = (attempt + 1) * 5
                print(f"⚠️  DB connect attempt {attempt+1} failed ({e}), retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"❌ DB connect failed after 10 attempts: {e}")
                raise

    # Optional Redis connection for caching
    try:
        import redis.asyncio as aioredis
        app.state.redis = await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await app.state.redis.ping()
        print(f"✅ Connected to Redis: {REDIS_URL}")
    except Exception as e:
        print(f"⚠️  Redis unavailable (caching disabled): {e}")
        app.state.redis = None

    # AISStream background task for maritime vessel tracking
    app.state.aisstream_task = asyncio.create_task(_aisstream_background())

@app.on_event("shutdown")
async def shutdown():
    """Close connection pool on shutdown."""
    await app.state.pool.close()
    if hasattr(app.state, "redis") and app.state.redis:
        await app.state.redis.close()

@app.get("/api/v2/stats")
async def get_system_stats():
    """
    System-wide database statistics.
    Shows total signals, time range, and ingestion health.
    """
    async with app.state.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 5000")
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
    countries: Optional[str] = Query(None, description="Comma-separated country codes to filter (e.g. IR,AE,OM)"),
    limit: int = Query(80, ge=1, le=200, description="Max nodes to return"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to return")
):
    """Get country nodes with aggregated stats. Supports focus filtering, country filtering, and extended time ranges."""
    # Parse countries filter into a set for post-query filtering
    country_filter_set = None
    if countries:
        country_filter_set = set(c.strip().upper() for c in countries.split(',') if c.strip())

    try:
        async with app.state.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 10000")

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
                # Enforce server-side cap
                effective_limit = min(limit, 80)
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
                """, filter_value, timeout=10.0)
            elif use_daily_rollup:
                # Use daily rollup for extended ranges (1m, 3m, record)
                days = effective_hours // 24
                # Enforce server-side cap
                effective_limit = min(limit, 80)
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
                """ % (days, effective_limit), timeout=10.0)
            else:
                # Use hourly materialized view for short ranges (faster)
                # Enforce server-side cap
                effective_limit = min(limit, 80)
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
                """ % (effective_hours, effective_limit), timeout=10.0)

            if not rows:
                return {"nodes": [], "count": 0, "hours": effective_hours, "range": time_range, "focus_type": focus_type, "focus_value": focus_value}

            # Apply countries filter if provided (post-query for compatibility with all query paths)
            if country_filter_set:
                rows = [r for r in rows if r['country_code'] in country_filter_set]
                if not rows:
                    return {"nodes": [], "count": 0, "hours": effective_hours, "range": time_range, "countries": countries}

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
            # Sort by total_signals DESC and slice top 80 to guarantee no bloated payloads
            nodes.sort(key=lambda x: x["signalCount"], reverse=True)
            if len(nodes) > 80:
                nodes = nodes[:80]

            allowed_fields = None
            if fields:
                allowed_fields = set(f.strip() for f in fields.split(','))

            if allowed_fields:
                nodes = [{k: v for k, v in n.items() if k in allowed_fields} for n in nodes]

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
    except Exception as e:
        return {"nodes": [], "count": 0, "error": str(e), "hours": hours}

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
            await conn.execute("SET statement_timeout = 8000")
            # Use country_hourly_v2 materialized view for both current window and baseline
            # This avoids scanning raw signals_v2 (which has 240K+ rows/day)
            rows = await conn.fetch("""
                WITH current_window AS (
                    SELECT
                        country_code,
                        SUM(signal_count) as signal_count
                    FROM country_hourly_v2
                    WHERE hour > NOW() - ($1::int * INTERVAL '1 hour')
                    GROUP BY country_code
                    HAVING SUM(signal_count) >= 5
                ),
                daily_history AS (
                    SELECT
                        country_code,
                        DATE_TRUNC('day', hour) as day,
                        SUM(signal_count) as daily_count
                    FROM country_hourly_v2
                    WHERE hour > NOW() - INTERVAL '8 days'
                    AND hour <= NOW() - ($1::int * INTERVAL '1 hour')
                    GROUP BY country_code, DATE_TRUNC('day', hour)
                ),
                baseline AS (
                    SELECT
                        country_code,
                        COUNT(*) as days_observed,
                        AVG(daily_count) as avg_daily,
                        STDDEV(daily_count) as stddev_daily
                    FROM daily_history
                    GROUP BY country_code
                    HAVING COUNT(*) >= 1
                )
                SELECT
                    c.country_code,
                    co.name as country_name,
                    c.signal_count,
                    b.avg_daily as baseline_avg,
                    b.days_observed,
                    ROUND((c.signal_count::numeric / NULLIF(b.avg_daily / 24.0 * $1, 0)), 2) as multiplier,
                    ROUND(((c.signal_count - b.avg_daily / 24.0 * $1) /
                           NULLIF(COALESCE(b.stddev_daily, b.avg_daily * 0.3) / 24.0 * $1, 0))::numeric, 2) as zscore
                FROM current_window c
                JOIN baseline b ON c.country_code = b.country_code
                LEFT JOIN countries_v2 co ON c.country_code = co.code
                ORDER BY zscore DESC NULLS LAST
                LIMIT $2
            """, hours, limit * 2, timeout=8.0)

            # Fetch total system stats using materialized view
            total_stats = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT country_code) as active_countries,
                    SUM(signal_count) as total_signals
                FROM country_hourly_v2
                WHERE hour > NOW() - INTERVAL '24 hours'
            """, timeout=5.0)
            
            def classify_anomaly(multiplier, zscore):
                if multiplier is None or zscore is None:
                    return "normal"
                if zscore > 4 and multiplier > 3:
                    return "critical"
                if zscore > 2.5 or multiplier > 2:
                    return "elevated"
                if zscore > 1.5 and multiplier > 1.5:
                    return "notable"
                return "normal"

            anomalies = []
            near_misses = []
            
            for row in rows:
                multiplier = float(row['multiplier']) if row['multiplier'] else 0
                zscore = float(row['zscore']) if row['zscore'] else 0
                level = classify_anomaly(multiplier, zscore)

                item = {
                    "country_code": row['country_code'],
                    "country_name": row['country_name'] or row['country_code'],
                    "current_count": int(row['signal_count']),
                    "baseline_avg": round(float(row['baseline_avg']), 1),
                    "days_observed": int(row['days_observed']),
                    "multiplier": multiplier,
                    "zscore": zscore,
                    "level": level
                }
                
                if level != "normal":
                    if len(anomalies) < limit:
                        anomalies.append(item)
                else:
                    if multiplier > 1.0 and len(near_misses) < 3:
                        near_misses.append(item)
            
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
                "near_misses": near_misses,
                "overall_severity": overall,
                "meta": {
                    "time_window_hours": hours,
                    "baseline_window_days": 7,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "active_countries": int(total_stats['active_countries']) if total_stats else 0,
                    "total_signals_24h": int(total_stats['total_signals']) if total_stats else 0
                }
            }
    except Exception as e:
        print(f"Error in anomalies endpoint: {e}")
        import traceback
        traceback.print_exc()
        return {"anomalies": [], "overall_severity": "normal", "error": str(e)}

@app.get("/api/v2/anomalies/themes")
async def get_theme_anomalies(
    hours: int = Query(24, ge=1, le=8760),
    limit: int = Query(5, ge=1, le=20)
):
    """
    Return top anomalous themes globally based on volume spikes.
    Compares current signals against theme_daily_v2 7-day rolling baseline.
    """
    try:
        async with app.state.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 8000")
            rows = await conn.fetch("""
                WITH current_window AS (
                    SELECT unnest(themes) as theme, COUNT(*) as signal_count
                    FROM signals_v2
                    WHERE timestamp > NOW() - ($1::int * INTERVAL '1 hour')
                    GROUP BY 1
                    HAVING COUNT(*) >= 10
                ),
                baseline AS (
                    SELECT theme, AVG(signal_count) as avg_daily, STDDEV(signal_count) as stddev_daily
                    FROM theme_daily_v2
                    WHERE day > CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY 1
                )
                SELECT
                    c.theme,
                    c.signal_count,
                    b.avg_daily as baseline_avg,
                    ROUND((c.signal_count::numeric / NULLIF(b.avg_daily / 24.0 * $1, 0)), 2) as multiplier,
                    ROUND(((c.signal_count - b.avg_daily / 24.0 * $1) /
                           NULLIF(COALESCE(b.stddev_daily, b.avg_daily * 0.3) / 24.0 * $1, 0))::numeric, 2) as zscore
                FROM current_window c
                JOIN baseline b ON c.theme = b.theme
                WHERE ((c.signal_count - b.avg_daily / 24.0 * $1) / NULLIF(COALESCE(b.stddev_daily, b.avg_daily * 0.3) / 24.0 * $1, 0)) > 1.5
                ORDER BY zscore DESC NULLS LAST
                LIMIT $2
            """, hours, limit, timeout=8.0)
            
            anomalies = []
            for row in rows:
                multiplier = float(row['multiplier']) if row['multiplier'] else 0
                zscore = float(row['zscore']) if row['zscore'] else 0
                
                anomalies.append({
                    "theme": row['theme'],
                    "current_count": int(row['signal_count']),
                    "baseline_avg": round(float(row['baseline_avg']), 1),
                    "multiplier": multiplier,
                    "zscore": zscore
                })
            
            return {
                "theme_anomalies": anomalies,
                "meta": {
                    "time_window_hours": hours,
                    "baseline_window_days": 7,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            }
    except Exception as e:
        print(f"Error in theme anomalies endpoint: {e}")
        return {"theme_anomalies": [], "error": str(e)}


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
    """Search across themes, countries, and persons. Returns top_countries per result for map fly-to."""
    query = q.lower().strip()
    cache_key = f"search:{query}:{hours}"
    if app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    async with app.state.pool.acquire() as conn:
        # Themes — grouped with top 3 countries each
        # Exclude pure taxonomy prefixes (TAX_WORLDFISH, TAX_WORLDLANGUAGES, etc.) that
        # match on biological/language names and produce misleading results
        theme_rows = await conn.fetch("""
            WITH matches AS (
                SELECT unnest(themes) as theme, country_code, COUNT(*) as cnt
                FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                  AND LOWER(array_to_string(themes, ' ')) LIKE $1
                GROUP BY theme, country_code
                HAVING COUNT(*) >= 2
            ),
            filtered AS (
                SELECT * FROM matches
                WHERE theme NOT LIKE 'TAX_%%'
                  AND theme NOT LIKE 'WORLDLANGUAGES_%%'
            ),
            totals AS (
                SELECT theme, SUM(cnt) as total_signals
                FROM filtered GROUP BY theme
                ORDER BY total_signals DESC LIMIT 10
            ),
            ranked AS (
                SELECT m.theme, m.country_code, m.cnt,
                       ROW_NUMBER() OVER (PARTITION BY m.theme ORDER BY m.cnt DESC) as rn
                FROM filtered m JOIN totals t ON t.theme = m.theme
            )
            SELECT
                t.theme,
                t.total_signals,
                array_agg(r.country_code ORDER BY r.rn) FILTER (WHERE r.rn <= 3) as top_codes,
                array_agg(r.cnt::int ORDER BY r.rn)     FILTER (WHERE r.rn <= 3) as top_counts,
                array_agg(COALESCE(c.name, r.country_code) ORDER BY r.rn) FILTER (WHERE r.rn <= 3) as top_names
            FROM totals t
            JOIN ranked r ON r.theme = t.theme AND r.rn <= 3
            LEFT JOIN countries_v2 c ON c.code = r.country_code
            GROUP BY t.theme, t.total_signals
            ORDER BY t.total_signals DESC
        """ % hours, f'%{query}%')

        # Persons — same grouping pattern
        person_rows = await conn.fetch("""
            WITH matches AS (
                SELECT unnest(persons) as person, country_code, COUNT(*) as cnt
                FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                  AND persons IS NOT NULL AND array_length(persons, 1) > 0
                  AND LOWER(array_to_string(persons, ' ')) LIKE $1
                GROUP BY person, country_code
                HAVING COUNT(*) >= 2
            ),
            totals AS (
                SELECT person, SUM(cnt) as total_signals
                FROM matches GROUP BY person
                ORDER BY total_signals DESC LIMIT 8
            ),
            ranked AS (
                SELECT m.person, m.country_code, m.cnt,
                       ROW_NUMBER() OVER (PARTITION BY m.person ORDER BY m.cnt DESC) as rn
                FROM matches m JOIN totals t ON t.person = m.person
            )
            SELECT
                t.person,
                t.total_signals,
                array_agg(r.country_code ORDER BY r.rn) FILTER (WHERE r.rn <= 3) as top_codes,
                array_agg(r.cnt::int ORDER BY r.rn)     FILTER (WHERE r.rn <= 3) as top_counts,
                array_agg(COALESCE(c.name, r.country_code) ORDER BY r.rn) FILTER (WHERE r.rn <= 3) as top_names
            FROM totals t
            JOIN ranked r ON r.person = t.person AND r.rn <= 3
            LEFT JOIN countries_v2 c ON c.code = r.country_code
            GROUP BY t.person, t.total_signals
            ORDER BY t.total_signals DESC
        """ % hours, f'%{query}%')

        # Countries — simple name/code match
        country_rows = await conn.fetch("""
            SELECT code, name FROM countries_v2
            WHERE LOWER(name) LIKE $1 OR LOWER(code) LIKE $1
            LIMIT 8
        """, f'%{query}%')

        def build_top_countries(codes, names, counts):
            if not codes:
                return []
            return [
                {"code": codes[i], "name": names[i], "count": counts[i]}
                for i in range(len(codes))
            ]

        result = {
            "query": q,
            "themes": [
                {
                    "theme": r['theme'],
                    "total_signals": int(r['total_signals']),
                    "top_countries": build_top_countries(r['top_codes'], r['top_names'], r['top_counts'])
                }
                for r in theme_rows
            ],
            "persons": [
                {
                    "person": r['person'],
                    "total_signals": int(r['total_signals']),
                    "top_countries": build_top_countries(r['top_codes'], r['top_names'], r['top_counts'])
                }
                for r in person_rows
            ],
            "countries": [{"code": r['code'], "name": r['name']} for r in country_rows],
        }

    if app.state.redis:
        try:
            await app.state.redis.setex(cache_key, 120, json.dumps(result))
        except Exception:
            pass

    return result

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
                  AND s.timestamp > NOW() - INTERVAL '{hours} hours'
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
                          AND timestamp > NOW() - INTERVAL '{hours} hours'
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
                    {"name": extract_domain(r['source_name']), "count": int(r['count']), "sentiment": float(r['avg_sentiment'] or 0)}
                    for r in top_sources
                ],
                "topPersons": top_persons,
                "timeline": [
                    {"hour": t['hour'].isoformat(), "count": int(t['count']), "sentiment": float(t['avg_sentiment'] or 0)}
                    for t in timeline
                ],
                "countryFraming": country_framing
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
    for prefix in ("WB_", "TAX_", "GDELT_"):
        if label.startswith(prefix):
            # Also strip the numeric segment that follows e.g. WB_475_
            parts = label.split("_", 2)
            label = parts[-1] if len(parts) >= 2 else label
            break
    # Remove any remaining leading numeric segment (e.g. "475_DIGITAL" → "DIGITAL")
    parts = label.split("_", 1)
    if parts[0].isdigit() and len(parts) == 2:
        label = parts[1]
    return label.replace("_", " ").title()


@app.get("/api/v2/theme/{theme_code}/insight")
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
    try:
        async with app.state.pool.acquire() as conn:
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
        "4. Keep it exactly 2-3 sentences. Be insightful, engaging, and professional."
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


@app.get("/api/v2/signals")
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
    async with app.state.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 10000")
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
                sentiment,
                themes,
                persons
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
                    "persons": (r['persons'] or [])[:3]
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
    import json as _json
    cache_key = f"flows:{time_range or hours}:{focus_type}:{focus_value}"
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return _json.loads(cached)
        except Exception:
            pass

    try:
        async with app.state.pool.acquire() as conn:
            # 20s cap: slow unnest query must not hold connections indefinitely
            await conn.execute("SET statement_timeout = 20000")
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
            # Cap the scan window for the unnest query: 6h max prevents full-table scans
            query_hours = min(effective_hours, 6)

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
            
            # Get theme vectors for each country (capped at 6h to prevent full-table scans)
            if filter_value:
                country_themes = await conn.fetch(f"""
                    WITH theme_counts AS (
                        SELECT
                            country_code,
                            unnest(themes) as theme,
                            COUNT(*) as cnt
                        FROM signals_v2
                        WHERE timestamp > NOW() - INTERVAL '{query_hours} hours'
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
                """ % query_hours)
            
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

            result = {"flows": flows[:100], "total": len(flows)}
            if hasattr(app.state, "redis") and app.state.redis:
                try:
                    await app.state.redis.setex(cache_key, 300, _json.dumps(result))
                except Exception:
                    pass
            return result
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
        await conn.execute("SET statement_timeout = 8000")
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
            "generated_at": datetime.now(timezone.utc).isoformat(),
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
                {"source": extract_domain(r['source_name']), "count": r['count']}
                for r in top_sources
            ]
        }


@app.get("/api/v2/briefing/insight")
async def get_briefing_insight(hours: int = Query(24, ge=1, le=8760)):
    """AI meta-summary of the global news landscape for the current time window."""
    cache_key = f"briefing_insight:{hours}"
    generated_at = datetime.now(timezone.utc).isoformat()

    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached_raw = await app.state.redis.get(cache_key)
            if cached_raw:
                data = json.loads(cached_raw)
                data["cached"] = True
                return data
        except Exception:
            pass

    try:
        async with app.state.pool.acquire() as conn:
            stats = await conn.fetchrow(f"""
                SELECT COUNT(*) as total, COUNT(DISTINCT country_code) as countries,
                       AVG(sentiment) as avg_sent
                FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '{hours} hours'
            """)
            top_themes = await conn.fetch(f"""
                SELECT unnest(themes) as theme, COUNT(*) as cnt
                FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '{hours} hours'
                GROUP BY theme ORDER BY cnt DESC LIMIT 5
            """)
            top_countries = await conn.fetch(f"""
                SELECT s.country_code, co.name, COUNT(*) as cnt, AVG(s.sentiment) as avg_s
                FROM signals_v2 s LEFT JOIN countries_v2 co ON s.country_code = co.code
                WHERE s.timestamp > NOW() - INTERVAL '{hours} hours'
                GROUP BY s.country_code, co.name ORDER BY cnt DESC LIMIT 5
            """)
    except Exception as e:
        return {"insight": None, "error": "db_error", "generated_at": generated_at}

    total = int(stats["total"] or 0)
    countries = int(stats["countries"] or 0)
    avg_sent = float(stats["avg_sent"] or 0)
    themes_str = ", ".join([_clean_theme_label(r["theme"]) for r in top_themes])
    countries_str = ", ".join([
        f"{r['name'] or r['country_code']} ({int(r['cnt'])} signals, {float(r['avg_s'] or 0):+.1f})"
        for r in top_countries
    ])

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return {"insight": None, "error": "insight_unavailable", "generated_at": generated_at}

    user_prompt = (
        f"Summarize the global information landscape over the last {hours} hours.\n"
        f"- Total coverage: {total:,} articles across {countries} countries\n"
        f"- Global sentiment: {avg_sent:+.1f} (negative = concern/crisis, positive = stability/progress)\n"
        f"- Dominant topics: {themes_str}\n"
        f"- Most-covered countries (with their tone): {countries_str}\n\n"
        "Write 2-3 sentences describing what the world's media is focused on right now, "
        "what emotional tenor dominates, and any notable geographic patterns in coverage."
    )
    system_prompt = (
        "You are an intelligence analyst giving a morning media briefing. "
        "Describe what the world's press is covering and how, using the data provided. "
        "Be concise, neutral, and analytical. No markdown, no bullet points — flowing prose only."
    )

    try:
        import anthropic as _anthropic
        client = _anthropic.AsyncAnthropic(api_key=anthropic_key)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        insight_text = next((b.text for b in response.content if b.type == "text"), None)
    except Exception as e:
        err = str(e)
        code = "insight_no_credits" if "credit balance" in err.lower() else "insight_unavailable"
        return {"insight": None, "error": code, "generated_at": generated_at}

    result = {"insight": insight_text, "generated_at": generated_at, "cached": False}
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(cache_key, 1800, json.dumps(result))
        except Exception:
            pass
    return result


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
        
        domains = [extract_domain(r['source_name']) for r in source_rows]
        
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
        async with app.state.pool.acquire(timeout=5) as conn:
            await conn.execute("SET statement_timeout = 5000")
            db_ok = True
            try:
                await conn.fetchval("SELECT 1", timeout=3.0)
            except Exception:
                db_ok = False

            # Use materialized view only — instant, no full-table scan of signals_v2
            result = await conn.fetchrow("""
                SELECT
                    MAX(hour) as last_ts,
                    SUM(signal_count) FILTER (WHERE hour >= NOW() - INTERVAL '1 hour') as rows_15m,
                    SUM(signal_count) as total_signals
                FROM country_hourly_v2
            """, timeout=5.0)

            last_ingest_ts = result['last_ts'] if result else None
            rows_ingested_last_15m = int(result['rows_15m'] or 0) if result else 0
            total_signals = int(result['total_signals'] or 0) if result else 0

            ingest_lag_minutes = None
            if last_ingest_ts:
                ts = last_ingest_ts.replace(tzinfo=timezone.utc) if last_ingest_ts.tzinfo is None else last_ingest_ts
                ingest_lag_minutes = (datetime.now(timezone.utc) - ts).total_seconds() / 60

            if not db_ok:
                status = "error"
            elif ingest_lag_minutes is None or ingest_lag_minutes > 90:
                status = "degraded"
            else:
                status = "healthy"

            return {
                "status": status,
                "db_ok": db_ok,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "last_ingest_ts": last_ingest_ts.isoformat() if last_ingest_ts else None,
                "ingest_lag_minutes": round(ingest_lag_minutes, 1) if ingest_lag_minutes else None,
                "rows_ingested_last_15m": rows_ingested_last_15m,
                "total_signals": total_signals,
                "error_count_last_15m": 0
            }
    except asyncio.TimeoutError:
        return {
            "status": "degraded",
            "db_ok": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "pool busy",
            "last_ingest_ts": None,
            "ingest_lag_minutes": None,
            "rows_ingested_last_15m": 0,
            "total_signals": 0,
            "error_count_last_15m": 0
        }
    except Exception as e:
        return {
            "status": "error",
            "db_ok": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": str(e),
            "last_ingest_ts": None,
            "ingest_lag_minutes": None,
            "rows_ingested_last_15m": 0,
            "total_signals": 0,
            "error_count_last_15m": 0
        }

# =============================================================================
# GOOGLE TRENDS API
# =============================================================================

@app.get("/api/v2/trends/search")
async def get_trending_searches(
    country_code: Optional[str] = Query(None, description="ISO 2-letter country code"),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=50)
):
    """Get trending Google searches for a country or globally."""
    try:
        async with app.state.pool.acquire() as conn:
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


@app.get("/api/v2/trends/match")
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
        async with app.state.pool.acquire() as conn:
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

@app.get("/api/v2/wiki/top")
async def get_wiki_top_articles(
    country_code: Optional[str] = Query(None, description="ISO 2-letter country code"),
    days: int = Query(1, ge=1, le=7),
    limit: int = Query(15, ge=1, le=50)
):
    """Get top Wikipedia articles by pageviews for a country or globally."""
    try:
        async with app.state.pool.acquire() as conn:
            if country_code:
                rows = await conn.fetch("""
                    SELECT article_title, views, rank, language, fetch_date
                    FROM wiki_pageviews_v2
                    WHERE country_code = $1
                    AND fetch_date >= CURRENT_DATE - $2::int
                    ORDER BY views DESC
                    LIMIT $3
                """, country_code.upper(), days, limit)
            else:
                # Global aggregate: sum views across all countries
                rows = await conn.fetch("""
                    SELECT article_title, SUM(views) as views, MIN(rank) as rank,
                           COUNT(DISTINCT country_code) as country_count
                    FROM wiki_pageviews_v2
                    WHERE fetch_date >= CURRENT_DATE - $1::int
                    GROUP BY article_title
                    ORDER BY views DESC
                    LIMIT $2
                """, days, limit)

            return {
                "articles": [
                    {
                        "title": r['article_title'],
                        "views": r['views'],
                        "rank": r['rank'],
                        "language": r.get('language'),
                        "country_count": r.get('country_count'),
                    }
                    for r in rows
                ],
                "country_code": country_code,
                "days": days,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        return {"articles": [], "error": str(e)}


@app.get("/api/v2/wiki/match")
async def get_wiki_theme_match(
    theme: str = Query(..., description="GDELT theme code to check against Wikipedia activity"),
    days: int = Query(1, ge=1, le=7)
):
    """Check if a GDELT theme matches any spiking Wikipedia articles.
    Returns matching articles and view counts — useful for 'wiki activity' badges.
    """
    from app.core.gdelt_taxonomy import get_theme_label

    label = get_theme_label(theme).lower()
    theme_words = [w for w in label.split() if len(w) > 3]

    if not theme_words:
        return {"matches": [], "theme": theme, "has_wiki_activity": False}

    try:
        async with app.state.pool.acquire() as conn:
            conditions = " OR ".join([f"LOWER(article_title) LIKE '%' || ${i+1} || '%'" for i in range(len(theme_words))])
            query = f"""
                SELECT article_title, SUM(views) as views, COUNT(DISTINCT country_code) as country_count
                FROM wiki_pageviews_v2
                WHERE fetch_date >= CURRENT_DATE - ('{days} days')::INTERVAL
                AND ({conditions})
                GROUP BY article_title
                ORDER BY views DESC
                LIMIT 5
            """
            rows = await conn.fetch(query, *theme_words)

            matches = [
                {
                    "title": r['article_title'],
                    "views": r['views'],
                    "country_count": r['country_count'],
                }
                for r in rows
            ]

            return {
                "matches": matches,
                "theme": theme,
                "theme_label": get_theme_label(theme),
                "has_wiki_activity": len(matches) > 0,
                "total_views": sum(m['views'] for m in matches),
            }
    except Exception as e:
        return {"matches": [], "theme": theme, "has_wiki_activity": False, "error": str(e)}


# =============================================================================
# GDELT EVENTS API
# =============================================================================

@app.get("/api/v2/events")
async def get_events(
    country_code: Optional[str] = Query(None, description="Filter by action country code"),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200)
):
    """Get recent structured geopolitical events (CAMEO)."""
    from app.core.cameo_taxonomy import get_cameo_label, get_quad_class_label

    try:
        async with app.state.pool.acquire() as conn:
            if country_code:
                query = """
                    SELECT * FROM events_v2
                    WHERE action_country_code = $1
                    AND timestamp > NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC
                    LIMIT %s
                """ % (hours, limit)
                rows = await conn.fetch(query, country_code.upper())
            else:
                query = """
                    SELECT * FROM events_v2
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC
                    LIMIT %s
                """ % (hours, limit)
                rows = await conn.fetch(query)

            events = []
            for r in rows:
                events.append({
                    "id": r['global_event_id'],
                    "timestamp": r['timestamp'].isoformat() if r['timestamp'] else None,
                    "action": {
                        "code": r['event_code'],
                        "label": get_cameo_label(r['event_code']),
                        "quad_class": r['quad_class'],
                        "quad_label": get_quad_class_label(r['quad_class']),
                        "goldstein_scale": float(r['goldstein_scale']) if r['goldstein_scale'] else None,
                        "is_root": r['is_root_event']
                    },
                    "actor1": {
                        "name": r['actor1_name'],
                        "country_code": r['actor1_country_code']
                    } if r['actor1_name'] or r['actor1_country_code'] else None,
                    "actor2": {
                        "name": r['actor2_name'],
                        "country_code": r['actor2_country_code']
                    } if r['actor2_name'] or r['actor2_country_code'] else None,
                    "location": {
                        "name": r['action_location_name'],
                        "country_code": r['action_country_code'],
                        "latitude": float(r['latitude']) if r['latitude'] else None,
                        "longitude": float(r['longitude']) if r['longitude'] else None
                    },
                    "meta": {
                        "mentions": r['num_mentions'],
                        "avg_tone": float(r['avg_tone']) if r['avg_tone'] else None,
                        "source_url": r['source_url']
                    }
                })

            return {
                "events": events,
                "country_code": country_code,
                "hours": hours,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        return {"events": [], "error": str(e)}


@app.get("/api/v2/events/clusters")
async def get_event_clusters(
    hours: int = Query(24, ge=1, le=168),
    quad_class: Optional[int] = Query(None, description="Filter: 1=Verbal Coop 2=Material Coop 3=Verbal Conflict 4=Material Conflict"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Cluster GDELT Events by country + quad_class for the given window.
    Returns the hottest conflict/cooperation clusters with actor pairs,
    Goldstein score, and event type breakdown.
    """
    from app.core.cameo_taxonomy import get_cameo_label, get_quad_class_label

    try:
        async with app.state.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 10000")

            quad_filter = "AND quad_class = $2" if quad_class else ""
            params = [str(hours)]
            if quad_class:
                params.append(quad_class)

            rows = await conn.fetch(f"""
                SELECT
                    action_country_code                             AS country,
                    quad_class,
                    COUNT(*)                                        AS event_count,
                    ROUND(AVG(goldstein_scale)::numeric, 2)        AS avg_goldstein,
                    SUM(num_mentions)                               AS total_mentions,
                    MIN(timestamp)                                  AS first_seen,
                    MAX(timestamp)                                  AS last_seen,
                    AVG(latitude)                                   AS center_lat,
                    AVG(longitude)                                  AS center_lon,
                    ARRAY_AGG(DISTINCT event_root_code)
                        FILTER (WHERE event_root_code IS NOT NULL)  AS root_codes,
                    -- Top actor pair by co-occurrence count
                    MODE() WITHIN GROUP (ORDER BY actor1_country_code) AS top_actor1,
                    MODE() WITHIN GROUP (ORDER BY actor2_country_code) AS top_actor2
                FROM events_v2
                WHERE timestamp > NOW() - ($1 || ' hours')::INTERVAL
                  AND action_country_code IS NOT NULL
                  {quad_filter}
                GROUP BY action_country_code, quad_class
                HAVING COUNT(*) >= 3
                ORDER BY event_count DESC, avg_goldstein ASC
                LIMIT {limit}
            """, *params)

            clusters = []
            for r in rows:
                root_labels = [get_cameo_label(c) for c in (r["root_codes"] or []) if c]
                clusters.append({
                    "country": r["country"],
                    "quad_class": r["quad_class"],
                    "quad_label": get_quad_class_label(r["quad_class"]),
                    "event_count": int(r["event_count"]),
                    "avg_goldstein": float(r["avg_goldstein"] or 0),
                    "total_mentions": int(r["total_mentions"] or 0),
                    "first_seen": r["first_seen"].isoformat() if r["first_seen"] else None,
                    "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
                    "center": {
                        "lat": float(r["center_lat"]) if r["center_lat"] else None,
                        "lon": float(r["center_lon"]) if r["center_lon"] else None,
                    },
                    "event_types": root_labels[:5],
                    "top_actors": {
                        "actor1_country": r["top_actor1"],
                        "actor2_country": r["top_actor2"],
                    },
                    # Intensity 0–1 for frontend sizing: Goldstein -10 → 1.0, 0 → 0.5, +10 → 0.0
                    "intensity": round(max(0, min(1, (0 - float(r["avg_goldstein"] or 0)) / 10 + 0.5)), 2),
                })

            return {
                "clusters": clusters,
                "hours": hours,
                "total": len(clusters),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        return {"clusters": [], "error": str(e)}


@app.get("/api/v2/conflict-markers")
async def get_conflict_markers(
    days: int = Query(3, ge=1, le=30),
    limit: int = Query(200, ge=1, le=2000)
):
    """
    Returns conflict markers for the map.
    Priority: ACLED verified events (if configured).
    Fallback: GDELT Events quad_class=4 (Material Conflict) with Goldstein < -3.
    Frontend can render both the same way.
    """
    from app.services.ingest_acled import ACLED_API_KEY

    try:
        async with app.state.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 8000")

            # Try ACLED first (cast days to int to avoid asyncpg int8 vs int4 mismatch)
            acled_count = await conn.fetchval(
                "SELECT COUNT(*) FROM acled_conflicts_v2 WHERE event_date >= CURRENT_DATE - $1::int", days)

            if acled_count and acled_count > 0:
                rows = await conn.fetch("""
                    SELECT event_id_cnty, event_date, event_type, sub_event_type,
                           actor1, actor2, country, region, location,
                           latitude, longitude, fatalities, notes, source
                    FROM acled_conflicts_v2
                    WHERE event_date >= CURRENT_DATE - $1::int
                    ORDER BY event_date DESC
                    LIMIT $2
                """, days, limit)
                markers = [{
                    "id": r["event_id_cnty"],
                    "source": "acled",
                    "date": r["event_date"].isoformat() if r["event_date"] else None,
                    "type": r["event_type"],
                    "sub_type": r["sub_event_type"],
                    "actors": {"actor1": r["actor1"], "actor2": r["actor2"]},
                    "location": {
                        "country": r["country"], "name": r["location"],
                        "latitude": float(r["latitude"]) if r["latitude"] else None,
                        "longitude": float(r["longitude"]) if r["longitude"] else None,
                    },
                    "fatalities": r["fatalities"] or 0,
                    "severity": "verified",
                } for r in rows]
                return {"markers": markers, "source": "acled", "count": len(markers)}

            # Fallback: GDELT Events Material Conflict (quad_class=4, Goldstein < -3)
            rows = await conn.fetch("""
                SELECT global_event_id, timestamp, event_code, event_root_code,
                       actor1_name, actor1_country_code, actor2_name, actor2_country_code,
                       action_country_code, action_location_name,
                       latitude, longitude, goldstein_scale, num_mentions, avg_tone
                FROM events_v2
                WHERE timestamp > NOW() - ($1 || ' days')::INTERVAL
                  AND quad_class = 4
                  AND goldstein_scale < -3
                  AND latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY timestamp DESC, num_mentions DESC
                LIMIT $2
            """, str(days), limit)

            from app.core.cameo_taxonomy import get_cameo_label
            markers = [{
                "id": str(r["global_event_id"]),
                "source": "gdelt_events",
                "date": r["timestamp"].isoformat() if r["timestamp"] else None,
                "type": get_cameo_label(r["event_code"]),
                "sub_type": r["event_root_code"],
                "actors": {
                    "actor1": r["actor1_name"] or r["actor1_country_code"],
                    "actor2": r["actor2_name"] or r["actor2_country_code"],
                },
                "location": {
                    "country": r["action_country_code"], "name": r["action_location_name"],
                    "latitude": float(r["latitude"]) if r["latitude"] else None,
                    "longitude": float(r["longitude"]) if r["longitude"] else None,
                },
                "fatalities": 0,
                "severity": "inferred",
                "goldstein": float(r["goldstein_scale"]) if r["goldstein_scale"] else None,
                "mentions": r["num_mentions"] or 0,
            } for r in rows]
            return {"markers": markers, "source": "gdelt_events_fallback", "count": len(markers)}

    except Exception as e:
        return {"markers": [], "error": str(e)}


# =============================================================================
# ACLED CONFLICT API
# =============================================================================

@app.get("/api/v2/acled")
async def get_acled_conflicts(
    country: Optional[str] = Query(None, description="Filter by country name"),
    days: int = Query(3, ge=1, le=30),
    limit: int = Query(500, ge=1, le=5000)
):
    """Get recent conflict events from ACLED."""
    try:
        async with app.state.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 8000")
            if country:
                query = """
                    SELECT * FROM acled_conflicts_v2
                    WHERE country ILIKE $1
                    AND event_date >= CURRENT_DATE - ($2 || ' days')::INTERVAL
                    ORDER BY event_date DESC
                    LIMIT $3
                """
                rows = await conn.fetch(query, f"%{country}%", str(days), limit)
            else:
                query = """
                    SELECT * FROM acled_conflicts_v2
                    WHERE event_date >= CURRENT_DATE - ($1 || ' days')::INTERVAL
                    ORDER BY event_date DESC
                    LIMIT $2
                """
                rows = await conn.fetch(query, str(days), limit)

            conflicts = []
            for r in rows:
                conflicts.append({
                    "id": r['event_id_cnty'],
                    "date": r['event_date'].isoformat() if r['event_date'] else None,
                    "type": r['event_type'],
                    "sub_type": r['sub_event_type'],
                    "actors": {
                        "actor1": r['actor1'],
                        "actor2": r['actor2']
                    },
                    "location": {
                        "country": r['country'],
                        "region": r['region'],
                        "name": r['location'],
                        "latitude": float(r['latitude']) if r['latitude'] else None,
                        "longitude": float(r['longitude']) if r['longitude'] else None
                    },
                    "fatalities": r['fatalities'],
                    "notes": r['notes'],
                    "source": r['source']
                })

            return {
                "conflicts": conflicts,
                "count": len(conflicts),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        return {"conflicts": [], "error": str(e)}

@app.get("/api/v2/narratives")
async def get_narratives(hours: int = Query(24, ge=1, le=8760), limit: int = Query(5, ge=1, le=20)):
    """Get top narrative threads. Cached 5 min in Redis."""
    from app.core.gdelt_taxonomy import get_theme_label
    import traceback, json as _json

    cache_key = f"narratives:{hours}:{limit}"
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return _json.loads(cached)
        except Exception:
            pass

    try:
        async with app.state.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 20000")
            timeline_hours = min(hours, 24)

            # Phase 1: Get top themes from pre-aggregated table (instant, any window)
            top_rows = await conn.fetch("""
                SELECT
                    theme,
                    SUM(signal_count)   AS signal_count,
                    SUM(country_count)  AS country_count,
                    SUM(source_count)   AS source_count,
                    AVG(avg_sentiment)  AS avg_sentiment
                FROM theme_hourly_v2
                WHERE hour > NOW() - ($1 || ' hours')::INTERVAL
                GROUP BY theme
                ORDER BY signal_count DESC
                LIMIT $2
            """, str(hours), limit)

            if not top_rows:
                return {"narratives": [], "hours": hours,
                        "total_active_countries": 0,
                        "generated_at": datetime.now(timezone.utc).isoformat()}

            top_themes = [r["theme"] for r in top_rows]

            # Phase 2: Velocity + timeline + countries — scoped to top themes only
            # GIN index on signals_v2.themes makes this fast even at 24h
            rows = await conn.fetch("""
                WITH
                total_active AS (
                    SELECT COUNT(DISTINCT country_code) AS cnt
                    FROM signals_v2
                    WHERE timestamp > NOW() - ($2 || ' hours')::INTERVAL
                ),
                filtered AS (
                    SELECT country_code, themes, timestamp
                    FROM signals_v2
                    WHERE timestamp > NOW() - ($2 || ' hours')::INTERVAL
                      AND themes IS NOT NULL
                      AND themes && $1::text[]
                ),
                velocity AS (
                    SELECT
                        unnest(themes) AS theme,
                        COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '1 hour') AS last_hour,
                        COUNT(*) FILTER (WHERE timestamp <= NOW() - INTERVAL '1 hour'
                                          AND timestamp > NOW() - INTERVAL '2 hours') AS prev_hour
                    FROM filtered
                    GROUP BY 1
                ),
                tl_base AS (
                    SELECT unnest(themes) AS theme, date_trunc('hour', timestamp) AS hour, COUNT(*) AS cnt
                    FROM filtered
                    WHERE timestamp > NOW() - ($3 || ' hours')::INTERVAL
                    GROUP BY 1, 2
                ),
                timeline AS (
                    SELECT theme,
                        JSON_AGG(JSON_BUILD_OBJECT('hour', TO_CHAR(hour, 'HH24:MI'), 'count', cnt)
                                 ORDER BY hour) AS tl
                    FROM tl_base WHERE theme = ANY($1::text[]) GROUP BY theme
                ),
                ctry_base AS (
                    SELECT unnest(themes) AS theme, country_code, COUNT(*) AS cnt
                    FROM filtered GROUP BY 1, 2
                ),
                top_ctry AS (
                    SELECT theme, ARRAY_AGG(country_code ORDER BY cnt DESC) AS countries
                    FROM (
                        SELECT *, ROW_NUMBER() OVER (PARTITION BY theme ORDER BY cnt DESC) AS rn
                        FROM ctry_base WHERE theme = ANY($1::text[])
                    ) r WHERE rn <= 3
                    GROUP BY theme
                ),
                first_seen AS (
                    SELECT unnest(themes) AS theme, MIN(timestamp) AS first_seen
                    FROM filtered GROUP BY 1
                )
                SELECT
                    (SELECT cnt FROM total_active) AS total_active,
                    v.theme,
                    COALESCE(v.last_hour, 0)   AS last_hour,
                    COALESCE(v.prev_hour, 0)   AS prev_hour,
                    COALESCE(tc.countries, '{}') AS top_countries,
                    COALESCE(tl.tl::text, '[]') AS hourly_timeline,
                    fs.first_seen
                FROM (SELECT DISTINCT unnest($1::text[]) AS theme) base
                LEFT JOIN velocity v    ON v.theme = base.theme
                LEFT JOIN top_ctry tc   ON tc.theme = base.theme
                LEFT JOIN timeline tl   ON tl.theme = base.theme
                LEFT JOIN first_seen fs ON fs.theme = base.theme
            """, top_themes, str(hours), str(timeline_hours))

            total_active = max(int((rows[0]["total_active"] if rows else None) or 1), 1)

            # Merge: top_rows has counts, rows has velocity/timeline/countries
            detail_by_theme = {r["theme"]: r for r in rows}
            theme_codes = [r["theme"] for r in top_rows]

            # Top persons — scoped to top themes, GIN-indexed lookup
            persons_map: dict = {tc: [] for tc in theme_codes}
            try:
                p_rows = await conn.fetch("""
                    SELECT theme, ARRAY_AGG(person ORDER BY cnt DESC) AS persons
                    FROM (
                        SELECT unnest(themes) AS theme, unnest(persons) AS person, COUNT(*) AS cnt
                        FROM signals_v2
                        WHERE timestamp > NOW() - ($1 || ' hours')::INTERVAL
                          AND themes IS NOT NULL AND persons IS NOT NULL
                          AND themes && $2
                        GROUP BY 1, 2
                    ) sub
                    WHERE person IS NOT NULL AND person != ''
                      AND theme = ANY($2)
                    GROUP BY theme
                """, str(min(hours, 6)), theme_codes)
                for pr in p_rows:
                    persons_map[pr["theme"]] = (pr["persons"] or [])[:3]
            except Exception:
                pass

            # Batch enrich with Trends + Wiki flags (non-fatal if tables empty)
            trends_flags: dict = {tc: False for tc in theme_codes}
            wiki_flags: dict = {tc: False for tc in theme_codes}
            try:
                theme_word_map: dict = {}
                for tc in theme_codes:
                    label = get_theme_label(tc).lower()
                    words = [w for w in label.split() if len(w) > 3]
                    if words:
                        theme_word_map[tc] = words

                if theme_word_map:
                    all_words = list({w for ws in theme_word_map.values() for w in ws})

                    trend_rows = await conn.fetch("""
                        SELECT DISTINCT LOWER(keyword) AS kw
                        FROM trends_v2
                        WHERE timestamp > NOW() - INTERVAL '48 hours'
                          AND LOWER(keyword) LIKE ANY(
                              SELECT '%' || w || '%' FROM unnest($1::text[]) w
                          )
                        LIMIT 100
                    """, all_words)
                    matched_kws = {r["kw"] for r in trend_rows}
                    for tc, words in theme_word_map.items():
                        if any(any(w in kw for kw in matched_kws) for w in words):
                            trends_flags[tc] = True

                    wiki_rows = await conn.fetch("""
                        SELECT DISTINCT LOWER(article_title) AS title
                        FROM wiki_pageviews_v2
                        WHERE fetch_date >= CURRENT_DATE - 3
                          AND LOWER(article_title) LIKE ANY(
                              SELECT '%' || w || '%' FROM unnest($1::text[]) w
                          )
                        LIMIT 100
                    """, all_words)
                    matched_titles = {r["title"] for r in wiki_rows}
                    for tc, words in theme_word_map.items():
                        if any(any(w in title for title in matched_titles) for w in words):
                            wiki_flags[tc] = True
            except Exception:
                pass

            narratives = []
            for tr in top_rows:
                tc = tr["theme"]
                det = detail_by_theme.get(tc, {})
                last_h = int((det.get("last_hour") or 0))
                prev_h = int((det.get("prev_hour") or 0))
                if prev_h > 0 and last_h > prev_h * 1.2:
                    trend = "accelerating"
                elif prev_h > 0 and last_h < prev_h * 0.8:
                    trend = "fading"
                else:
                    trend = "stable"

                tl_raw = det.get("hourly_timeline", "[]")
                try:
                    hourly_timeline = _json.loads(tl_raw) if isinstance(tl_raw, str) else tl_raw
                except Exception:
                    hourly_timeline = []

                first_seen_val = det.get("first_seen")

                narratives.append({
                    "theme_code": tc,
                    "label": get_theme_label(tc),
                    "signal_count": int(tr["signal_count"]),
                    "country_count": int(tr["country_count"]),
                    "source_count": int(tr["source_count"]),
                    "first_seen": first_seen_val.isoformat() if first_seen_val else None,
                    "velocity": last_h,
                    "trend": trend,
                    "spread_pct": round((int(tr["country_count"]) / total_active) * 100, 1),
                    "avg_sentiment": round(float(tr["avg_sentiment"] or 0), 2),
                    "top_persons": persons_map.get(tc, []),
                    "hourly_timeline": hourly_timeline or [],
                    "top_countries": list((det.get("top_countries") or [])),
                    "has_public_interest": trends_flags.get(tc, False),
                    "trending_keywords": [],
                    "has_wiki_activity": wiki_flags.get(tc, False),
                    "wiki_views": 0,
                })

            result = {
                "narratives": narratives,
                "hours": hours,
                "total_active_countries": total_active,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            if hasattr(app.state, "redis") and app.state.redis:
                try:
                    await app.state.redis.setex(cache_key, 300, _json.dumps(result))
                except Exception:
                    pass
            return result
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
            await conn.execute("SET statement_timeout = 20000")
            # Cap the scan window to prevent full-table scans
            hours = min(hours, 6)
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

# =============================================================================
# AIRCRAFT TRACKING (OpenSky Network – OAuth2 client_credentials)
# =============================================================================

# Aircraft callsign classification
# Military: known NATO/country prefixes; Government: VIP/state flights
_MIL_PREFIXES = {
    # US military
    "RCH", "PAT", "REACH", "DUKE", "VALOR", "ZEUS", "TOPCAT",
    "VENUS", "NAVY", "USAF", "ARMY",
    # UK
    "RAF", "RRR",
    # Germany
    "GAF", "GAFMED",
    # France
    "FAF", "CTM",
    # Israel
    "IAF",
    # NATO
    "NATO", "NATOEX",
    # Russia
    "RFF",
    # Other common military
    "MAGMA", "COBRA", "VIPER", "GHOST",
}
_GOV_PREFIXES = {"SAM", "AF1", "AF2", "EXEC", "VENUS0", "SPAR", "CAPS", "IRON"}
_ICAO24_MIL_RANGES = {
    # US DoD range AE0000–AFFFFF (partial)
    "ae", "af",
    # UK military 43
    "43",
}

def _classify_aircraft(callsign: str, icao24: str) -> str:
    cs = callsign.upper().strip()
    prefix4 = cs[:4]
    prefix3 = cs[:3]
    prefix2 = cs[:2]
    if prefix3 in _MIL_PREFIXES or prefix4 in _MIL_PREFIXES or prefix2 in _MIL_PREFIXES:
        return "military"
    if prefix3 in _GOV_PREFIXES or prefix4 in _GOV_PREFIXES:
        return "government"
    # ICAO24 hex range heuristic
    if icao24[:2].lower() in _ICAO24_MIL_RANGES:
        return "military"
    # Commercial: typical 3-letter ICAO airline code followed by digits
    import re as _re
    if _re.match(r'^[A-Z]{2,3}\d', cs):
        return "commercial"
    return "private"


# Global cache for aircraft tracking (60 second TTL)
AIRCRAFT_CACHE: dict = {
    "timestamp": 0,
    "data": []
}
_OPENSKY_RETRY_AFTER: float = 0  # epoch seconds; don't retry OpenSky until this time

# OAuth2 token cache (tokens last ~30 min; we refresh at 25 min)
_OPENSKY_TOKEN_CACHE: dict = {
    "access_token": "",
    "expires_at": 0
}

OPENSKY_CLIENT_ID = os.getenv("OPENSKY_CLIENT_ID", "")
OPENSKY_CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET", "")
OPENSKY_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
OPENSKY_API_URL = "https://opensky-network.org/api/states/all"


async def _get_opensky_token() -> str | None:
    """
    Exchange client_id / client_secret for a Bearer token via
    the OAuth2 client_credentials grant. Caches the token for 25 min.
    Returns None when credentials are not configured.
    """
    if not OPENSKY_CLIENT_ID or not OPENSKY_CLIENT_SECRET:
        return None

    now = time.time()
    if _OPENSKY_TOKEN_CACHE["access_token"] and now < _OPENSKY_TOKEN_CACHE["expires_at"]:
        return _OPENSKY_TOKEN_CACHE["access_token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OPENSKY_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": OPENSKY_CLIENT_ID,
                "client_secret": OPENSKY_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        if resp.status_code != 200:
            print(f"[OpenSky] Token exchange failed: {resp.status_code} – {resp.text[:300]}")
            return None

        body = resp.json()
        token = body.get("access_token", "")
        expires_in = body.get("expires_in", 1800)  # default 30 min
        _OPENSKY_TOKEN_CACHE["access_token"] = token
        _OPENSKY_TOKEN_CACHE["expires_at"] = now + expires_in - 300  # refresh 5 min early
        print(f"[OpenSky] Got token, expires in {expires_in}s")
        return token


@app.get("/api/v2/aircraft")
async def get_aircraft_positions():
    """
    Proxy to OpenSky Network for live aircraft positions.
    Uses OAuth2 Bearer tokens (client_credentials grant).
    Limits to top 2000 aircraft sorted by altitude.
    Polls at most once every 60 seconds; falls back to cache up to 30 min old.
    Never returns fake/simulated data.
    """
    global AIRCRAFT_CACHE, _OPENSKY_RETRY_AFTER
    current_time = time.time()

    # ── Hard backoff: don't hit OpenSky until retry window expires ──────
    if current_time < _OPENSKY_RETRY_AFTER:
        if AIRCRAFT_CACHE["data"]:
            age_mins = round((current_time - AIRCRAFT_CACHE["timestamp"]) / 60, 1)
            return {"aircraft": AIRCRAFT_CACHE["data"], "cached": True, "cache_age_minutes": age_mins}
        return {"aircraft": [], "cached": False, "message": "Aircraft data temporarily unavailable (rate limited)"}

    # ── Soft rate-limit: max one poll every 60 s ─────────────────────
    if current_time - AIRCRAFT_CACHE["timestamp"] < 60 and AIRCRAFT_CACHE["data"]:
        age_mins = round((current_time - AIRCRAFT_CACHE["timestamp"]) / 60, 1)
        return {"aircraft": AIRCRAFT_CACHE["data"], "cached": True, "cache_age_minutes": age_mins}

    try:
        # Get OAuth2 token (or None for anonymous)
        token = await _get_opensky_token()
        headers: dict = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                OPENSKY_API_URL,
                headers=headers,
                timeout=15.0,
            )
            if resp.status_code != 200:
                raise Exception(f"OpenSky API returned {resp.status_code}: {resp.text[:200]}")

            data = resp.json()
            states = data.get("states", [])

            aircraft_list = []
            for state in states:
                # State vector indices: 0=icao24, 1=callsign, 2=origin_country,
                # 5=longitude, 6=latitude, 7=baro_altitude, 8=on_ground, 10=true_track
                lon = state[5]
                lat = state[6]
                on_ground = state[8]
                alt = state[7]

                # Skip ground aircraft and invalid positions
                if on_ground or lon is None or lat is None or alt is None:
                    continue

                callsign = (state[1] or "").strip() or "Unknown"
                aircraft_list.append({
                    "icao24": state[0],
                    "callsign": callsign,
                    "origin_country": state[2],
                    "longitude": lon,
                    "latitude": lat,
                    "baro_altitude": alt,
                    "true_track": state[10],
                    "category": _classify_aircraft(callsign, state[0] or ""),
                })

            # Top 2000 by altitude
            aircraft_list.sort(key=lambda x: x["baro_altitude"], reverse=True)
            top_aircraft = aircraft_list[:2000]

            AIRCRAFT_CACHE["timestamp"] = current_time
            AIRCRAFT_CACHE["data"] = top_aircraft
            print(f"[OpenSky] Fetched {len(top_aircraft)} aircraft (of {len(aircraft_list)} airborne)")
            return {"aircraft": top_aircraft, "cached": False, "message": "Live"}

    except Exception as e:
        print(f"[OpenSky] Error: {e}")
        # Back off 5 minutes on any error so we stop hammering OpenSky
        _OPENSKY_RETRY_AFTER = current_time + 300
        # Graceful degradation: serve stale cache up to 30 min
        cache_age_seconds = current_time - AIRCRAFT_CACHE["timestamp"]
        if AIRCRAFT_CACHE["data"] and cache_age_seconds < 1800:
            age_mins = round(cache_age_seconds / 60, 1)
            return {
                "aircraft": AIRCRAFT_CACHE["data"],
                "cached": True,
                "cache_age_minutes": age_mins,
                "message": f"Using cached data ({age_mins}m old) – API error: {e}",
            }

        # No usable cache – return empty, never fake data
        return {"aircraft": [], "cached": False, "message": f"Aircraft data temporarily unavailable: {e}"}


# ─────────────────────────────────────────────────────────────────────────────
# Maritime vessel tracking via AISStream WebSocket
# ─────────────────────────────────────────────────────────────────────────────

AISSTREAM_API_KEY = os.getenv("AISSTREAM_API_KEY", "")

# Vessels keyed by MMSI; entries expire after 10 minutes of no update
VESSEL_CACHE: dict = {
    "vessels": {},
    "last_cleanup": 0.0,
    "connected": False,
    "msgs_received": 0,
    "msgs_filtered": 0,
}

# Bounding boxes for geopolitically significant maritime chokepoints
# Format: [[min_lat, min_lon], [max_lat, max_lon]]
CHOKEPOINT_BBOXES = [
    [[25.8, 55.8], [27.2, 57.5]],    # Strait of Hormuz
    [[40.5, 28.5], [41.5, 29.8]],    # Bosphorus
    [[11.0, 42.0], [14.0, 45.0]],    # Bab-el-Mandeb (Red Sea south)
    [[29.5, 31.8], [31.5, 33.0]],    # Suez Canal
    [[1.0, 99.5],  [5.5, 104.5]],    # Strait of Malacca
    [[22.0, 119.0],[26.5, 122.0]],   # Taiwan Strait
    [[8.0, -81.0], [10.0, -79.0]],   # Panama Canal
    [[-35.5, 17.5],[-32.0, 20.5]],   # Cape of Good Hope
    [[50.0, -2.5], [52.0, 2.5]],     # English Channel
    [[3.0, 109.0], [10.0, 117.0]],   # South China Sea core
]

# Nav status codes we treat as "underway"
_UNDERWAY_STATUS = {0, 8, 15}

async def _aisstream_background():
    """
    Persistent WebSocket connection to AISStream.io for vessel positions near
    geopolitical chokepoints. Runs as a background asyncio task.
    Gracefully does nothing when AISSTREAM_API_KEY is not set.
    """
    import aiohttp

    if not AISSTREAM_API_KEY:
        print("[AISStream] No API key set — vessel layer disabled (set AISSTREAM_API_KEY)")
        return

    RETRY_DELAY = 30
    while True:
        try:
            VESSEL_CACHE["connected"] = False
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    "wss://stream.aisstream.io/v0/stream",
                    # No heartbeat — AISStream manages its own ping/pong
                ) as ws:
                    sub = json.dumps({
                        "APIKey": AISSTREAM_API_KEY,
                        "BoundingBoxes": CHOKEPOINT_BBOXES,
                        "FilterMessageTypes": ["PositionReport"],
                    })
                    await ws.send_str(sub)
                    VESSEL_CACHE["connected"] = True
                    print(f"[AISStream] Connected, subscription sent ({len(CHOKEPOINT_BBOXES)} bboxes)")

                    async for msg in ws:
                        if msg.type in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                            VESSEL_CACHE["msgs_received"] += 1
                            raw = msg.data if msg.type == aiohttp.WSMsgType.TEXT else msg.data.decode("utf-8", errors="replace")

                            try:
                                data = json.loads(raw)
                            except Exception:
                                continue

                            msg_type = data.get("MessageType") or data.get("message_type") or ""
                            if msg_type != "PositionReport":
                                VESSEL_CACHE["msgs_filtered"] += 1
                                continue

                            meta = data.get("MetaData", {})
                            pos = data.get("Message", {}).get("PositionReport", {})

                            mmsi = str(meta.get("MMSI") or "")
                            lat = meta.get("latitude")
                            lon = meta.get("longitude")
                            if not mmsi or lat is None or lon is None:
                                VESSEL_CACHE["msgs_filtered"] += 1
                                continue

                            nav_status = pos.get("NavigationalStatus", 15)
                            speed = float(pos.get("Sog") or 0)

                            VESSEL_CACHE["vessels"][mmsi] = {
                                "mmsi": mmsi,
                                "name": (meta.get("ShipName") or "").strip() or "Unknown",
                                "latitude": lat,
                                "longitude": lon,
                                "speed": round(speed, 1),
                                "heading": pos.get("TrueHeading") or pos.get("Cog") or 0,
                                "nav_status": nav_status,
                                "ts": time.time(),
                            }

                            # Periodic cleanup: drop entries > 10 min old
                            now = time.time()
                            if now - VESSEL_CACHE["last_cleanup"] > 120:
                                VESSEL_CACHE["vessels"] = {
                                    k: v for k, v in VESSEL_CACHE["vessels"].items()
                                    if now - v["ts"] < 600
                                }
                                VESSEL_CACHE["last_cleanup"] = now
                                print(f"[AISStream] vessels={len(VESSEL_CACHE['vessels'])} msgs_rcvd={VESSEL_CACHE['msgs_received']} filtered={VESSEL_CACHE['msgs_filtered']}")

                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break

        except Exception as e:
            VESSEL_CACHE["connected"] = False
            print(f"[AISStream] Connection error: {e} — retrying in {RETRY_DELAY}s")

        await asyncio.sleep(RETRY_DELAY)


@app.get("/api/v2/vessels")
async def get_vessels():
    """
    Return current vessel positions near geopolitical chokepoints.
    Data comes from the AISStream WebSocket background task.
    Returns empty list (not fake data) when API key is not configured.
    """
    if not AISSTREAM_API_KEY:
        return {
            "vessels": [],
            "count": 0,
            "connected": False,
            "message": "Vessel tracking not configured (AISSTREAM_API_KEY not set)",
        }

    vessels = list(VESSEL_CACHE["vessels"].values())
    return {
        "vessels": vessels,
        "count": len(vessels),
        "connected": VESSEL_CACHE["connected"],
        "msgs_received": VESSEL_CACHE["msgs_received"],
        "msgs_filtered": VESSEL_CACHE["msgs_filtered"],
        "message": "Live" if VESSEL_CACHE["connected"] else "Connecting...",
    }
