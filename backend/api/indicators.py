"""
Trust Indicators API Endpoints

Provides endpoints for:
- Tooltips/documentation for all indicators
- Country-specific indicator calculations
- Allowlist/denylist transparency
"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
import asyncpg

from indicators.source_diversity import (
    calculate_source_diversity,
    DIVERSITY_TOOLTIP
)
from indicators.source_quality import (
    calculate_source_quality,
    get_allowlist,
    get_denylist,
    QUALITY_TOOLTIP
)
from indicators.normalized_volume import (
    calculate_normalized_volume,
    VOLUME_TOOLTIP
)


router = APIRouter(prefix="/api/indicators", tags=["indicators"])


@router.get("/tooltips")
async def get_tooltips():
    """
    Return tooltip explanations for all trust indicators.
    
    Use these for displaying help text in the UI.
    """
    return {
        "source_diversity": DIVERSITY_TOOLTIP,
        "source_quality": QUALITY_TOOLTIP,
        "normalized_volume": VOLUME_TOOLTIP
    }


@router.get("/allowlist")
async def get_quality_allowlist():
    """
    Return the current source quality allowlist.
    
    Transparency endpoint - shows which sources are considered 'verified'.
    """
    sources = get_allowlist()
    return {
        "count": len(sources),
        "sources": sources,
        "description": "Major wire services and established news outlets with editorial standards."
    }


@router.get("/denylist")
async def get_quality_denylist():
    """
    Return the current source quality denylist.
    
    Transparency endpoint - shows which sources are flagged.
    """
    sources = get_denylist()
    return {
        "count": len(sources),
        "sources": sources,
        "description": "Sources with documented reliability issues. List is minimal and evidence-based."
    }


async def get_country_indicators_impl(
    country_code: str,
    hours: int,
    pool: asyncpg.Pool
) -> dict:
    """
    Calculate all indicators for a country in a time window.
    
    This is the implementation that can be called from main_v2.py.
    """
    async with pool.acquire() as conn:
        # Get source domains for diversity and quality
        source_rows = await conn.fetch("""
            SELECT source_name
            FROM signals_v2
            WHERE country_code = $1
            AND timestamp > NOW() - INTERVAL '%s hours'
            AND source_name IS NOT NULL
        """ % hours, country_code.upper())
        
        domains = [r['source_name'] for r in source_rows]
        
        # Calculate diversity and quality
        diversity = calculate_source_diversity(domains)
        quality = calculate_source_quality(domains)
        
        # Get volume baseline (7-day rolling for same hour-of-day)
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
        
        # Adjust baseline to match the hours parameter
        # (baseline is per-day, need to scale to hours window)
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


# Note: This router needs to be included in main_v2.py
# Example: app.include_router(indicators_router)
