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
async def get_nodes(hours: int = Query(24, ge=1, le=168, description="Hours of data (1-168)")):
    """Get country nodes with aggregated stats from materialized view."""
    async with app.state.pool.acquire() as conn:
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
            return {"nodes": [], "count": 0, "hours": hours}
        
        max_signals = max(float(r['total_signals']) for r in rows)
        
        nodes = []
        for row in rows:
            if row['latitude'] and row['longitude']:
                nodes.append({
                    "id": row['country_code'],
                    "name": row['name'] or row['country_code'],
                    "lat": float(row['latitude']),
                    "lon": float(row['longitude']),
                    "intensity": float(row['total_signals']) / max_signals,
                    "sentiment": float(row['sentiment'] or 0) / 10,  # Normalize to -1 to 1
                    "signalCount": int(row['total_signals']),
                    "sourceCount": int(row['unique_sources'] or 0)
                })
        
        return {"nodes": nodes, "count": len(nodes), "hours": hours}

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

@app.get("/api/v2/theme/{theme_code}")
async def get_theme_details(
    theme_code: str,
    country_code: str = Query(None, description="Filter by country"),
    hours: int = Query(24, ge=1, le=168)
):
    """Get detailed signals for a specific theme."""
    async with app.state.pool.acquire() as conn:
        # Base query
        query = """
            SELECT 
                timestamp,
                country_code,
                source_name,
                source_url,
                sentiment,
                themes,
                persons
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            AND $1 = ANY(themes)
        """ % hours
        
        params = [theme_code.upper()]
        
        if country_code:
            query += " AND country_code = $2"
            params.append(country_code.upper())
        
        query += " ORDER BY timestamp DESC LIMIT 50"
        
        rows = await conn.fetch(query, *params)
        
        # Get timeline data (hourly counts)
        timeline_query = """
            SELECT 
                date_trunc('hour', timestamp) as hour,
                COUNT(*) as count,
                AVG(sentiment) as avg_sentiment
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            AND $1 = ANY(themes)
        """ % hours
        
        if country_code:
            timeline_query += " AND country_code = $2"
            
        timeline_query += " GROUP BY hour ORDER BY hour"
        
        timeline = await conn.fetch(timeline_query, *params)
        
        return {
            "theme": theme_code,
            "country": country_code,
            "total": len(rows),
            "signals": [
                {
                    "timestamp": r['timestamp'].isoformat(),
                    "country": r['country_code'],
                    "source": r['source_name'],
                    "url": r['source_url'],
                    "sentiment": float(r['sentiment'] or 0),
                    "otherThemes": [t for t in (r['themes'] or []) if t != theme_code.upper()][:3],
                    "persons": (r['persons'] or [])[:3]
                }
                for r in rows
            ],
            "timeline": [
                {
                    "hour": t['hour'].isoformat(),
                    "count": int(t['count']),
                    "sentiment": float(t['avg_sentiment'] or 0)
                }
                for t in timeline
            ]
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

@app.get("/api/v2/flows")
async def get_flows(hours: int = Query(24, ge=1, le=168)):
    """Generate information flows between active countries with shared themes."""
    async with app.state.pool.acquire() as conn:
        # Get top countries
        top_countries = await conn.fetch("""
            SELECT 
                country_code,
                COUNT(*) as signal_count
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            GROUP BY country_code
            ORDER BY signal_count DESC
            LIMIT 15
        """ % hours)
        
        if len(top_countries) < 2:
            return {"flows": [], "count": 0}
        
        # Get coordinates
        country_codes = [r['country_code'] for r in top_countries]
        coords = await conn.fetch("""
            SELECT code, latitude, longitude
            FROM countries_v2
            WHERE code = ANY($1) AND latitude IS NOT NULL
        """, country_codes)
        coord_map = {r['code']: (float(r['longitude']), float(r['latitude'])) for r in coords}
        
        # Create flows between top countries
        flows = []
        for i, c1 in enumerate(top_countries):
            # Connect each country to 2-3 others
            for c2 in top_countries[i+1:i+4]:
                if c1['country_code'] != c2['country_code']:
                    code1 = c1['country_code']
                    code2 = c2['country_code']
                    
                    if code1 in coord_map and code2 in coord_map:
                        strength = min(c1['signal_count'], c2['signal_count'])
                        flows.append({
                            "source": list(coord_map[code1]),
                            "target": list(coord_map[code2]),
                            "sourceCountry": code1,
                            "targetCountry": code2,
                            "strength": float(strength),
                            "sharedThemes": []
                        })
        
        return {"flows": flows, "count": len(flows)}

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
            LIMIT 5
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
            LIMIT 5
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
            LIMIT 5
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


@app.get("/health")
async def health():
    """Health check endpoint with database connectivity test."""
    try:
        async with app.state.pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM signals_v2")
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "totalSignals": result
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "message": str(e)
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
