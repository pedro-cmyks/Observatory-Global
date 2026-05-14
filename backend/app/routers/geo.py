import os
import time
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from app import db
from app.main_v2 import app
from app.utils import _is_valid_person, _resolve_persons, extract_domain
from app.core.gdelt_taxonomy import classify_source
import httpx
import asyncio

router = APIRouter()

@router.get("/api/v2/heatmap")
async def get_heatmap(hours: int = Query(24, ge=1, le=8760)):
    """Deprecated - heatmap data now comes from nodes with glow effect."""
    return {
        "points": [],
        "count": 0,
        "message": "Heatmap deprecated, use nodes with glow effect"
    }

@router.get("/api/v2/flows")
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
        async with db.pool.acquire() as conn:
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

@router.get("/api/v2/country/{country_code}")
async def get_country_detail(country_code: str, hours: int = Query(24, ge=1, le=8760)):
    """Get detailed information for a specific country."""
    country_code = country_code.upper()
    
    async with db.pool.acquire() as conn:
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

        # Geo validation: what % of signals come from foreign-origin sources?
        geo_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE source_origin_country IS NOT NULL) AS known,
                COUNT(*) FILTER (WHERE source_origin_country IS NOT NULL
                                   AND source_origin_country != $1)       AS foreign_count
            FROM signals_v2
            WHERE country_code = $1
            AND timestamp > NOW() - INTERVAL '%s hours'
        """ % hours, country_code)
        known = int(geo_stats['known'] or 0)
        foreign_count = int(geo_stats['foreign_count'] or 0)
        foreign_source_pct = round(foreign_count / known * 100) if known > 50 else None

        return {
            "countryCode": country_code,
            "name": country_name,
            "totalSignals": int(stats['total_signals'] or 0),
            "sentiment": float(stats['sentiment'] or 0) / 10,
            "maxSentiment": float(stats['max_sentiment'] or 0) / 10,
            "minSentiment": float(stats['min_sentiment'] or 0) / 10,
            "themes": [{"name": t['theme'], "count": t['count']} for t in themes],
            "sources": [{"name": s['source_name'], "count": s['count']} for s in sources],
            "keyPersons": [{"name": p['person'], "count": p['count']} for p in persons],
            "foreignSourcePct": foreign_source_pct,
        }

def _build_theme_country_map(rows) -> list:
    """Group theme_country_hourly rows into [{theme, countries: [{code, name, count}]}]."""
    from collections import defaultdict
    grouped: dict = defaultdict(list)
    for r in rows:
        grouped[r['theme']].append({
            "code": r['country_code'],
            "name": r['country_name'] or r['country_code'],
            "count": int(r['cnt'])
        })
    return [
        {"theme": theme, "countries": countries[:4]}
        for theme, countries in grouped.items()
    ]


@router.get("/api/v2/conflict-markers")
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
        async with db.pool.acquire() as conn:
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

@router.get("/api/v2/acled")
async def get_acled_conflicts(
    country: Optional[str] = Query(None, description="Filter by country name"),
    days: int = Query(3, ge=1, le=30),
    limit: int = Query(500, ge=1, le=5000)
):
    """Get recent conflict events from ACLED."""
    try:
        async with db.pool.acquire() as conn:
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

@router.get("/api/v2/correlation")
async def get_correlation(
    mode: str = Query("country", description="mode: 'country' or 'theme'"),
    hours: int = Query(24, ge=1, le=8760),
    limit: int = Query(12, ge=2, le=30)
):
    """Get N*N correlation matrix (Jaccard similarity) for countries or themes."""
    from app.core.gdelt_taxonomy import get_theme_label
    import traceback
    
    try:
        async with db.pool.acquire() as conn:
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


@router.get("/api/v2/aircraft")
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


@router.get("/api/v2/vessels")
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
