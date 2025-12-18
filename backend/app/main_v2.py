"""
Observatory Global v2 - Simplified Backend API

NO Docker orchestration
NO custom aggregation code
Direct async PostgreSQL queries to v2 schema
Hot-reload enabled with uvicorn --reload
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from datetime import datetime
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

@app.get("/api/v2/nodes")
async def get_nodes(
    hours: int = Query(24, ge=1, le=168, description="Hours of data (1-168)"),
    focus_type: Optional[str] = Query(None, description="Focus type: theme, person, country, source"),
    focus_value: Optional[str] = Query(None, description="Value to focus on")
):
    """Get country nodes with aggregated stats. Supports focus filtering."""
    async with app.state.pool.acquire() as conn:
        
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
                return {"nodes": [], "count": 0, "hours": hours, "error": f"Unknown focus_type: {focus_type}"}
            
            # Query signals_v2 with focus filter
            rows = await conn.fetch(f"""
                WITH filtered AS (
                    SELECT 
                        country_code,
                        sentiment,
                        source_name
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '{hours} hours'
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
            """, filter_value)
        else:
            # Use materialized view for unfiltered queries (faster)
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
            """ % hours)
        
        if not rows:
            return {"nodes": [], "count": 0, "hours": hours, "focus_type": focus_type, "focus_value": focus_value}
        
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
            "hours": hours,
            "focus_type": focus_type,
            "focus_value": focus_value,
            "is_filtered": focus_type is not None
        }

@app.get("/api/v2/anomalies")
async def get_anomalies(
    hours: int = Query(24, ge=1, le=168),
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
                    c.signal_count,
                    COALESCE(b.avg_daily_signals, 50) as baseline_avg,
                    ROUND((c.signal_count::numeric / NULLIF(COALESCE(b.avg_daily_signals, 50) / 24 * $1, 0)), 2) as multiplier,
                    ROUND(((c.signal_count - COALESCE(b.avg_daily_signals, 50) / 24 * $1) / 
                           NULLIF(COALESCE(b.stddev_daily_signals, 25) / 24 * $1, 0))::numeric, 2) as zscore
                FROM current_counts c
                LEFT JOIN country_baseline_stats b ON c.country_code = b.country_code
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
async def get_heatmap(hours: int = Query(24, ge=1, le=168)):
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
    hours: int = Query(24, ge=1, le=168)
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
    hours: int = Query(24, ge=1, le=168)
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
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200)
):
    """Get raw signals with filters."""
    async with app.state.pool.acquire() as conn:
        conditions = ["timestamp > NOW() - INTERVAL '%s hours'" % hours]
        params = []
        param_count = 0
        
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
                timestamp,
                country_code,
                source_name,
                source_url,
                sentiment,
                themes
            FROM signals_v2
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT {limit}
        """, *params)
        
        return {
            "count": len(rows),
            "signals": [
                {
                    "timestamp": r['timestamp'].isoformat(),
                    "country": r['country_code'],
                    "source": r['source_name'],
                    "url": r['source_url'],
                    "sentiment": float(r['sentiment'] or 0),
                    "themes": r['themes'] or []
                }
                for r in rows
            ]
        }

@app.get("/api/v3/crisis/signals")
async def get_crisis_signals(
    hours: int = Query(24, ge=1, le=168),
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
async def get_crisis_summary(hours: int = Query(24, ge=1, le=168)):
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
    hours: int = Query(24, ge=1, le=168),
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
                        WHERE timestamp > NOW() - INTERVAL '{hours} hours'
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
                """ % hours)
            
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
async def get_country_detail(country_code: str, hours: int = Query(24, ge=1, le=168)):
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
        
        return {
            "countryCode": country_code,
            "totalSignals": int(stats['total_signals'] or 0),
            "sentiment": float(stats['sentiment'] or 0) / 10,
            "maxSentiment": float(stats['max_sentiment'] or 0) / 10,
            "minSentiment": float(stats['min_sentiment'] or 0) / 10,
            "themes": [{"name": t['theme'], "count": t['count']} for t in themes],
            "sources": [{"name": s['source_name'], "count": s['count']} for s in sources],
            "keyPersons": [{"name": p['person'], "count": p['count']} for p in persons]
        }

@app.get("/api/v2/briefing")
async def get_briefing(hours: int = Query(24, ge=1, le=168)):
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
    hours: int = Query(default=24, ge=1, le=168)
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
