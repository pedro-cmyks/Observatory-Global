"""Heatmap API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, select
from app.db.base import SessionLocal
from app.models.gdelt import GdeltSignal, SignalTheme
from app.models.aggregates import ThemeAggregation1h, Country

router = APIRouter()

@router.get("", response_model=Dict[str, Any])
async def get_heatmap(
    time_window: str = Query("1h", description="Time window (e.g., '1h', '6h', '24h')"),
    theme: Optional[str] = Query(None, description="Filter by theme"),
):
    """
    Returns heatmap points for geographic visualization.
    """
    window_hours = {"1h": 1, "6h": 6, "12h": 12, "24h": 24, "all": None}.get(time_window, 1)
    
    db = SessionLocal()
    try:
        # Query raw signals for precise location data
        query = select(
            GdeltSignal.latitude,
            GdeltSignal.longitude,
            GdeltSignal.country_code,
            func.count(GdeltSignal.id).label('event_count')
        ).join(
            Country, GdeltSignal.country_code == Country.country_code
        ).where(
            GdeltSignal.latitude.isnot(None),
            GdeltSignal.longitude.isnot(None),
            # Filter out suspicious coordinates (too far from country centroid)
            # Heuristic: Lat diff < 30, Lon diff < 50 (covers most large countries)
            func.abs(GdeltSignal.latitude - Country.latitude) < 30,
            func.abs(GdeltSignal.longitude - Country.longitude) < 50
        )
        
        if window_hours is not None:
            window_start = datetime.utcnow() - timedelta(hours=window_hours)
            query = query.where(GdeltSignal.timestamp >= window_start)
            
        if theme:
            # Join with SignalTheme if filtering by theme
            query = query.join(SignalTheme, GdeltSignal.id == SignalTheme.signal_id)
            query = query.where(SignalTheme.theme_code.ilike(f'%{theme}%'))
            
        stmt = query.group_by(
            GdeltSignal.latitude,
            GdeltSignal.longitude,
            GdeltSignal.country_code
        )
        
        results = db.execute(stmt).all()
        
        # Normalize intensity (0-1 scale)
        max_count = max([r.event_count for r in results], default=1)
        
        points = [
            {
                "lat": r.latitude,
                "lon": r.longitude,
                "intensity": min(r.event_count / max_count, 1.0),
                "country": r.country_code
            }
            for r in results
        ]
        
        return {
            "points": points,
            "metadata": {
                "time_window": time_window,
                "point_count": len(points),
                "max_intensity": 1.0,
                "source": "database"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
