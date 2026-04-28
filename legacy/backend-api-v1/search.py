"""Search API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import or_, func
from app.db.base import SessionLocal
from app.models.gdelt import GdeltSignal, SignalTheme, SignalEntity
from app.models.aggregates import Country

router = APIRouter()

@router.get("", response_model=Dict[str, Any])
async def search_signals(
    q: str = Query(..., description="Search query"),
    time_window: str = Query("24h", description="Time window (e.g., '1h', '6h', '24h', 'all')"),
    limit: int = Query(100, description="Max results", ge=1, le=500)
):
    """
    Search signals by theme, country, or entity name.
    
    Returns matching themes, entities (persons/orgs), and countries.
    """
    window_hours = {"1h": 1, "6h": 6, "12h": 12, "24h": 24, "all": None}.get(time_window, 24)
    
    db = SessionLocal()
    try:
        # Time filter for signals
        time_filter = None
        if window_hours is not None:
            window_start = datetime.utcnow() - timedelta(hours=window_hours)
            time_filter = GdeltSignal.timestamp >= window_start
        
        # Search in themes
        theme_query = db.query(
            SignalTheme.theme_code,
            func.count(SignalTheme.signal_id).label('signal_count'),
            func.sum(SignalTheme.theme_count).label('total_mentions')
        ).join(
            GdeltSignal, SignalTheme.signal_id == GdeltSignal.id
        ).filter(
            SignalTheme.theme_code.ilike(f"%{q}%")
        )
        
        if time_filter is not None:
            theme_query = theme_query.filter(time_filter)
        
        theme_matches = theme_query.group_by(SignalTheme.theme_code).order_by(
            func.count(SignalTheme.signal_id).desc()
        ).limit(limit).all()
        
        # Search in entities (persons, orgs)
        entity_query = db.query(
            SignalEntity.entity_name,
            SignalEntity.entity_type,
            func.count(SignalEntity.signal_id).label('signal_count')
        ).join(
            GdeltSignal, SignalEntity.signal_id == GdeltSignal.id
        ).filter(
            SignalEntity.entity_name.ilike(f"%{q}%")
        )
        
        if time_filter is not None:
            entity_query = entity_query.filter(time_filter)
        
        entity_matches = entity_query.group_by(
            SignalEntity.entity_name,
            SignalEntity.entity_type
        ).order_by(
            func.count(SignalEntity.signal_id).desc()
        ).limit(limit).all()
        
        # Search in countries
        country_matches = db.query(Country).filter(
            or_(
                Country.country_code.ilike(f"%{q}%"),
                Country.country_name.ilike(f"%{q}%")
            )
        ).limit(50).all()
        
        return {
            "query": q,
            "time_window": time_window,
            "results": {
                "themes": [
                    {
                        "code": t.theme_code,
                        "signal_count": t.signal_count,
                        "total_mentions": t.total_mentions or 0
                    }
                    for t in theme_matches
                ],
                "entities": [
                    {
                        "name": e.entity_name,
                        "type": e.entity_type,
                        "signal_count": e.signal_count
                    }
                    for e in entity_matches
                ],
                "countries": [
                    {
                        "code": c.country_code,
                        "name": c.country_name,
                        "lat": c.latitude,
                        "lon": c.longitude
                    }
                    for c in country_matches
                ]
            },
            "total_results": len(theme_matches) + len(entity_matches) + len(country_matches)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    finally:
        db.close()
