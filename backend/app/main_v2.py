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
    """Get signal points for heatmap layer (GPU filtered)."""
    # More points for shorter windows to ensure visibility
    limit = 10000 if hours <= 24 else 5000
    
    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT latitude, longitude, sentiment
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            AND latitude IS NOT NULL 
            AND longitude IS NOT NULL
            LIMIT %s
        """ % (hours, limit))
        
        return {
            "points": [
                {
                    "lat": float(r['latitude']),
                    "lon": float(r['longitude']),
                    "weight": 1 + abs(float(r['sentiment'] or 0)) / 5
                }
                for r in rows
            ],
            "count": len(rows),
            "hours": hours
        }

@app.get("/api/v2/flows")
async def get_flows(hours: int = Query(24, ge=1, le=168)):
    """Get information flows between top countries."""
    async with app.state.pool.acquire() as conn:
        # Create flows from top countries to their neighbors
        rows = await conn.fetch("""
            WITH top_countries AS (
                SELECT country_code, SUM(signal_count) as total
                FROM country_hourly_v2
                WHERE hour > NOW() - INTERVAL '%s hours'
                GROUP BY country_code
                ORDER BY total DESC
                LIMIT 10
            )
            SELECT 
                t.country_code as source,
                c1.latitude as source_lat,
                c1.longitude as source_lon,
                o.country_code as target,
                c2.latitude as target_lat,
                c2.longitude as target_lon,
                LEAST(t.total, o.total) as strength
            FROM top_countries t
            CROSS JOIN LATERAL (
                SELECT country_code, SUM(signal_count) as total
                FROM country_hourly_v2
                WHERE hour > NOW() - INTERVAL '%s hours'
                AND country_code != t.country_code
                GROUP BY country_code
                ORDER BY total DESC
                LIMIT 3
            ) o
            LEFT JOIN countries_v2 c1 ON t.country_code = c1.code
            LEFT JOIN countries_v2 c2 ON o.country_code = c2.code
            WHERE c1.latitude IS NOT NULL AND c2.latitude IS NOT NULL
        """ % (hours, hours))
        
        flows = []
        for r in rows:
            flows.append({
                "source": [float(r['source_lon']), float(r['source_lat'])],
                "target": [float(r['target_lon']), float(r['target_lat'])],
                "sourceCountry": r['source'],
                "targetCountry": r['target'],
                "strength": int(r['strength'])
            })
        
        return {"flows": flows, "count": len(flows), "hours": hours}

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
