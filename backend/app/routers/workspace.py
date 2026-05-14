from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query
from app import db
from app.utils import extract_domain
from app.core.gdelt_taxonomy import classify_source

router = APIRouter()

@router.get("/api/v2/compare")
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
    
    async with db.pool.acquire() as conn:
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

# Static fallback coordinates for countries that may have NULL in countries_v2.
# Used when the DB LEFT JOIN returns no lat/lon (countries added dynamically via update_countries).
_COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "US": (38.0, -97.0), "GB": (54.0, -2.0), "DE": (51.0, 10.0), "FR": (46.0, 2.0),
    "CN": (35.0, 105.0), "RU": (60.0, 100.0), "IN": (20.0, 77.0), "BR": (-10.0, -55.0),
    "JP": (36.0, 138.0), "AU": (-25.0, 133.0), "CA": (56.0, -96.0), "MX": (23.0, -102.0),
    "KR": (36.0, 128.0), "IT": (42.0, 12.0), "ES": (40.0, -4.0), "SA": (24.0, 45.0),
    "TR": (39.0, 35.0), "AR": (-34.0, -64.0), "ZA": (-29.0, 25.0), "EG": (27.0, 30.0),
    "NG": (10.0, 8.0), "PK": (30.0, 70.0), "UA": (49.0, 32.0), "IL": (31.5, 35.0),
    "IR": (32.0, 53.0), "PL": (52.0, 20.0), "NL": (52.0, 5.0), "SE": (62.0, 15.0),
    "NO": (62.0, 8.0), "CH": (47.0, 8.0), "BE": (50.0, 4.0), "AT": (47.0, 14.0),
    "AE": (24.0, 54.0), "TH": (15.0, 101.0), "ID": (-2.0, 118.0), "MY": (2.5, 112.0),
    "PH": (13.0, 122.0), "VN": (16.0, 108.0), "BD": (24.0, 90.0), "MM": (17.0, 96.0),
    "IQ": (33.0, 44.0), "SY": (35.0, 38.0), "JO": (31.0, 36.0), "LB": (33.9, 35.5),
    "KW": (29.5, 47.5), "QA": (25.3, 51.2), "BH": (26.0, 50.6), "OM": (21.0, 57.0),
    "YE": (15.0, 48.0), "PS": (31.5, 35.0), "AF": (33.0, 65.0), "NP": (28.0, 84.0),
    "LK": (7.0, 81.0), "TW": (23.7, 121.0), "SG": (1.4, 103.8), "KZ": (48.0, 68.0),
    "UZ": (41.0, 64.0), "KE": (-1.0, 38.0), "TZ": (-6.0, 35.0), "ET": (9.0, 40.0),
    "GH": (8.0, -2.0), "CM": (3.8, 11.5), "CI": (7.5, -5.5), "SN": (14.5, -14.5),
    "ML": (17.0, -4.0), "MR": (20.0, -12.0), "AO": (-12.0, 18.0), "MZ": (-18.0, 35.0),
    "ZM": (-14.0, 27.0), "RW": (-2.0, 30.0), "DZ": (28.0, 2.0), "MA": (32.0, -5.0),
    "LY": (27.0, 17.0), "SO": (10.0, 49.0), "SD": (15.0, 30.0), "TN": (34.0, 9.0),
    "PT": (39.5, -8.0), "GR": (39.0, 22.0), "CZ": (49.8, 15.5), "HU": (47.0, 19.0),
    "RO": (46.0, 25.0), "BG": (43.0, 25.0), "HR": (45.0, 16.0), "RS": (44.0, 21.0),
    "SK": (48.7, 19.5), "FI": (62.0, 26.0), "DK": (56.0, 10.0), "IE": (53.0, -8.0),
    "EE": (59.0, 25.0), "LV": (57.0, 25.0), "LT": (56.0, 24.0), "BY": (53.0, 28.0),
    "MD": (47.0, 29.0), "GE": (42.0, 44.0), "AM": (40.0, 45.0), "AZ": (40.5, 47.5),
    "TM": (40.0, 60.0), "TJ": (39.0, 71.0), "KG": (41.0, 75.0), "MN": (46.0, 105.0),
    "KP": (40.0, 127.0), "KH": (12.5, 105.0), "LA": (18.0, 103.0), "BN": (4.5, 114.7),
    "TL": (-8.8, 125.7), "PG": (-6.0, 147.0), "NZ": (-41.0, 174.0), "FJ": (-18.0, 178.0),
    "CL": (-30.0, -71.0), "CO": (4.0, -72.0), "PE": (-10.0, -76.0), "VE": (8.0, -66.0),
    "EC": (-2.0, -78.0), "BO": (-17.0, -65.0), "PY": (-23.0, -58.0), "UY": (-33.0, -56.0),
    "GT": (15.0, -90.0), "CU": (22.0, -80.0), "DO": (19.0, -70.7), "HT": (19.0, -72.3),
    "CR": (10.0, -84.0), "PA": (9.0, -80.0), "HN": (15.0, -87.0), "NI": (13.0, -85.0),
    "SV": (13.7, -89.0), "JM": (18.0, -77.3), "TT": (10.7, -61.2), "GY": (5.0, -59.0),
    "SR": (4.0, -56.0), "BI": (-3.0, 30.0), "MW": (-13.5, 34.0), "ZW": (-20.0, 30.0),
    "BW": (-22.0, 24.0), "NA": (-22.0, 17.0), "LS": (-29.5, 28.3), "SZ": (-26.5, 31.5),
    "MG": (-20.0, 47.0), "TG": (8.0, 1.0), "BJ": (9.3, 2.3), "BF": (13.0, -2.0),
    "GN": (11.0, -11.0), "SL": (8.5, -12.0), "LR": (6.5, -9.5), "GW": (12.0, -15.0),
    "GM": (13.5, -15.0), "CV": (16.0, -24.0), "CF": (7.0, 21.0), "CG": (-1.0, 15.0),
    "CD": (-4.0, 25.0), "GA": (-1.0, 12.0), "GQ": (2.0, 10.0), "SS": (4.0, 31.0),
    "ER": (15.0, 39.0), "DJ": (11.5, 43.0), "UG": (1.0, 32.0), "KM": (-11.7, 43.3),
    "SC": (-4.7, 55.5), "MU": (-20.3, 57.5), "RE": (-21.1, 55.5),
    "PW": (7.5, 134.6), "FM": (7.0, 158.0), "MH": (9.0, 168.0), "NR": (-0.5, 166.9),
    "WS": (-13.8, -172.1), "TO": (-20.0, -175.0), "VU": (-16.0, 167.0), "SB": (-8.0, 157.0),
    "LU": (49.8, 6.1), "CY": (35.0, 33.0), "MT": (35.9, 14.5), "IS": (65.0, -18.0),
    "AL": (41.0, 20.0), "MK": (41.6, 21.7), "ME": (42.5, 19.3), "BA": (44.0, 17.0),
    "SI": (46.1, 14.8), "LI": (47.1, 9.5), "MC": (43.7, 7.4), "SM": (43.9, 12.5),
    "AD": (42.5, 1.5), "VA": (41.9, 12.4),
}

@router.get("/api/v2/nodes")
async def get_nodes(
    hours: int = Query(24, ge=1, le=8760, description="Hours of data (1-168) - ignored if range is set"),
    time_range: Optional[str] = Query(None, alias="range", description="Time range: 24h, 1w, 1m, 3m, record"),
    focus_type: Optional[str] = Query(None, description="Focus type: theme, person, country, source"),
    focus_value: Optional[str] = Query(None, description="Value to focus on"),
    countries: Optional[str] = Query(None, description="Comma-separated country codes to filter (e.g. IR,AE,OM)"),
    limit: int = Query(217, ge=1, le=250, description="Max nodes to return"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to return")
):
    """Get country nodes with aggregated stats. Supports focus filtering, country filtering, and extended time ranges."""
    # Parse countries filter into a set for post-query filtering
    country_filter_set = None
    if countries:
        country_filter_set = set(c.strip().upper() for c in countries.split(',') if c.strip())

    try:
        async with db.pool.acquire() as conn:
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
                effective_limit = min(limit, 217)
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
                # If daily rollup is empty (table not yet populated), fall back to hourly
                if not rows:
                    fallback_hours = min(effective_hours, 168)
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
                    """ % (fallback_hours, effective_limit), timeout=10.0)
            else:
                # Use hourly materialized view for short ranges (faster)
                effective_limit = min(limit, 217)
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

            # Fetch per-country baselines for z-score heat (non-focus queries only — focus queries
            # are already filtered so relative deviation vs global baseline is less meaningful)
            baselines: dict[str, tuple[float, float]] = {}
            if not (focus_type and focus_value):
                country_codes = [r['country_code'] for r in rows if r['country_code']]
                if country_codes:
                    baseline_rows = await conn.fetch("""
                        SELECT country_code, avg_daily_signals, stddev_daily_signals
                        FROM country_baseline_stats
                        WHERE country_code = ANY($1::text[])
                    """, country_codes, timeout=3.0)
                    for br in baseline_rows:
                        avg = float(br['avg_daily_signals'] or 0)
                        std = float(br['stddev_daily_signals'] or avg * 0.3 or 1)
                        baselines[br['country_code']] = (avg, std)

            def _heat(country_code: str, current: float) -> tuple[float, str]:
                """Return (heat [0-1], anomaly_level) using z-score vs baseline.
                Falls back to intensity-based heat when no baseline exists."""
                if country_code not in baselines:
                    return float(current) / max_signals, "normal"
                avg_daily, std_daily = baselines[country_code]
                window_hours = float(effective_hours)
                expected = (avg_daily / 24.0) * window_hours
                stddev = (std_daily / 24.0) * window_hours
                if stddev <= 0:
                    return float(current) / max_signals, "normal"
                zscore = (current - expected) / stddev
                multiplier = current / expected if expected > 0 else 1.0
                if zscore > 4 and multiplier > 3:
                    level = "critical"
                elif zscore > 2.5 or multiplier > 2:
                    level = "elevated"
                elif zscore > 1.5 and multiplier > 1.5:
                    level = "notable"
                else:
                    level = "normal"
                # Clamp z-score to [0, 1]: z=3 → heat=1.0 (fully red)
                heat = max(0.0, min(1.0, zscore / 3.0))
                return heat, level

            nodes = []
            total_signals = 0
            for row in rows:
                # Use DB coords first, fall back to static dict for countries with NULL coords
                lat = row['latitude']
                lon = row['longitude']
                if lat is None or lon is None:
                    code = row['country_code']
                    if code in _COUNTRY_COORDS:
                        lat, lon = _COUNTRY_COORDS[code]
                if lat is None or lon is None:
                    continue
                signal_count = int(row['total_signals'])
                total_signals += signal_count
                heat_val, anomaly_level = _heat(row['country_code'], float(signal_count))
                nodes.append({
                    "id": row['country_code'],
                    "name": row['name'] or row['country_code'],
                    "lat": float(lat),
                    "lon": float(lon),
                    "intensity": float(row['total_signals']) / max_signals,
                    "heat": heat_val,
                    "anomalyLevel": anomaly_level,
                    "sentiment": float(row['sentiment'] or 0) / 10,
                    "signalCount": signal_count,
                    "sourceCount": int(row['unique_sources'] or 0)
                })
            # Rank countries by baseline deviation first. Raw signal volume remains
            # evidence/confidence, but should not make high-volume countries look
            # inherently more important than countries with unusual activity.
            nodes.sort(key=lambda x: (x.get("heat") or 0, x["signalCount"]), reverse=True)

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

@router.get("/api/v2/anomalies")
async def get_anomalies(
    hours: int = Query(24, ge=1, le=8760),
    limit: int = Query(10, ge=1, le=20)
):
    """
    Return top anomalous countries (activity significantly above baseline).
    Uses country_baseline_stats table for 7-day rolling baseline.
    """
    try:
        async with db.pool.acquire() as conn:
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
                    "active_countries": int((total_stats['active_countries'] if total_stats else 0) or 0),
                    "total_signals_24h": int((total_stats['total_signals'] if total_stats else 0) or 0)
                }
            }
    except Exception as e:
        print(f"Error in anomalies endpoint: {e}")
        import traceback
        traceback.print_exc()
        return {"anomalies": [], "overall_severity": "normal", "error": str(e)}

@router.get("/api/v2/anomalies/themes")
async def get_theme_anomalies(
    hours: int = Query(24, ge=1, le=8760),
    limit: int = Query(5, ge=1, le=20)
):
    """
    Return top anomalous themes globally based on volume spikes.
    Compares current signals against theme_daily_v2 7-day rolling baseline.
    """
    try:
        async with db.pool.acquire() as conn:
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


@router.get("/api/v2/source/{domain:path}/profile")
async def get_source_profile(
    domain: str,
    hours: int = Query(24, ge=1, le=8760, description="Hours of data (1-168)")
):
    """Get the bias profile, top themes, and countries covered by a specific news source."""
    async with db.pool.acquire() as conn:
        # We need to URL-decode the domain just in case
        import urllib.parse
        clean_domain = urllib.parse.unquote(domain).strip()

        # 1. Overall stats
        stats_query = """
            SELECT 
                COUNT(*) as total_signals,
                AVG(sentiment) as avg_sentiment,
                COUNT(DISTINCT country_code) as total_countries
            FROM signals_v2
            WHERE source_name ILIKE $1
              AND timestamp > NOW() - ($2 * INTERVAL '1 hour')
        """
        stats = await conn.fetchrow(stats_query, f"%{clean_domain}%", hours)
        
        if not stats or not stats['total_signals'] or stats['total_signals'] == 0:
            return {"error": "Source not found or no data in time range", "source": clean_domain}

        # 2. Top themes
        themes_query = """
            SELECT 
                unnest(themes) as theme,
                COUNT(*) as signal_count,
                ROUND(AVG(sentiment)::numeric, 2) as avg_sentiment
            FROM signals_v2
            WHERE source_name ILIKE $1
              AND timestamp > NOW() - ($2 * INTERVAL '1 hour')
              AND themes IS NOT NULL AND array_length(themes, 1) > 0
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 10
        """
        themes_rows = await conn.fetch(themes_query, f"%{clean_domain}%", hours)

        # 3. Top countries
        countries_query = """
            SELECT 
                country_code,
                COUNT(*) as signal_count,
                ROUND(AVG(sentiment)::numeric, 2) as avg_sentiment
            FROM signals_v2
            WHERE source_name ILIKE $1
              AND timestamp > NOW() - ($2 * INTERVAL '1 hour')
              AND country_code IS NOT NULL
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 10
        """
        countries_rows = await conn.fetch(countries_query, f"%{clean_domain}%", hours)

        # 4. Volume over time
        # For small hours, bucket by hour, else by day
        bucket_interval = 'hour' if hours <= 72 else 'day'
        timeline_query = f"""
            SELECT 
                date_trunc('{bucket_interval}', bucket) as time_bucket,
                SUM(signal_count) as signal_count,
                ROUND(AVG(avg_sentiment)::numeric, 2) as avg_sentiment
            FROM signals_source_hourly
            WHERE source_name ILIKE $1
              AND bucket > NOW() - ($2 * INTERVAL '1 hour')
            GROUP BY 1
            ORDER BY 1 ASC
        """
        timeline_rows = await conn.fetch(timeline_query, f"%{clean_domain}%", hours)

        return {
            "source": clean_domain,
            "summary": {
                "total_signals": stats['total_signals'],
                "avg_sentiment": round(float(stats['avg_sentiment'] or 0), 2),
                "total_countries": stats['total_countries'],
            },
            "top_themes": [
                {
                    "theme": r['theme'],
                    "count": r['signal_count'],
                    "sentiment": float(r['avg_sentiment']) if r['avg_sentiment'] else 0
                } for r in themes_rows
            ],
            "top_countries": [
                {
                    "country_code": r['country_code'],
                    "count": r['signal_count'],
                    "sentiment": float(r['avg_sentiment']) if r['avg_sentiment'] else 0
                } for r in countries_rows
            ],
            "timeline": [
                {
                    "time": r['time_bucket'].isoformat() if r['time_bucket'] else None,
                    "count": r['signal_count'],
                    "sentiment": float(r['avg_sentiment']) if r['avg_sentiment'] else 0
                } for r in timeline_rows
            ]
        }
