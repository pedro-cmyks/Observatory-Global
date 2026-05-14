from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query
from app import db

router = APIRouter()

@router.get("/api/v2/events")
async def get_events(
    country_code: Optional[str] = Query(None, description="Filter by action country code"),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200)
):
    """Get recent structured geopolitical events (CAMEO)."""
    from app.core.cameo_taxonomy import get_cameo_label, get_quad_class_label

    try:
        async with db.pool.acquire() as conn:
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


@router.get("/api/v2/events/clusters")
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
        async with db.pool.acquire() as conn:
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


