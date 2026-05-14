from fastapi import APIRouter, Query
from app import db

router = APIRouter()

@router.get("/api/indicators/tooltips")
async def get_indicator_tooltips():
    """Return tooltip explanations for all trust indicators."""
    if not INDICATORS_AVAILABLE:
        return {"error": "Indicators module not available"}
    
    return {
        "source_diversity": DIVERSITY_TOOLTIP,
        "source_quality": QUALITY_TOOLTIP,
        "normalized_volume": VOLUME_TOOLTIP
    }


@router.get("/api/indicators/allowlist")
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


@router.get("/api/indicators/denylist")
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


@router.get("/api/indicators/country/{country_code}")
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
    
    async with db.pool.acquire() as conn:
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


