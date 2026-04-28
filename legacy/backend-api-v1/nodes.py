"""Nodes API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, select, desc
from app.db.base import SessionLocal
from app.models.aggregates import ThemeAggregation1h, Country

router = APIRouter()

def normalize_sentiment(gdelt_tone):
    """
    GDELT AvgTone typically ranges from -10 to +10.
    Normalize to -1 to +1 for frontend.
    """
    if gdelt_tone is None:
        return 0
    return max(min(gdelt_tone / 10, 1.0), -1.0)

@router.get("", response_model=Dict[str, Any])
async def get_nodes(
    time_window: str = Query("1h", description="Time window (e.g., '1h', '6h', '24h')")
):
    """
    Returns country nodes with intensity and metadata.
    """
    window_hours = {"1h": 1, "6h": 6, "12h": 12, "24h": 24, "all": None}.get(time_window, 1)
    
    db = SessionLocal()
    try:
        # Aggregate by country
        query = select(
            ThemeAggregation1h.country_code,
            func.sum(ThemeAggregation1h.signal_count).label('total_events'),
            func.sum(ThemeAggregation1h.total_theme_mentions).label('total_mentions'),
            func.avg(ThemeAggregation1h.avg_tone).label('avg_tone')
        )
        
        if window_hours is not None:
            window_start = datetime.utcnow() - timedelta(hours=window_hours)
            query = query.where(ThemeAggregation1h.hour_bucket >= window_start)
            
        stmt = query.group_by(
            ThemeAggregation1h.country_code
        )
        
        country_stats = db.execute(stmt).all()
        
        max_events = max([c.total_events for c in country_stats], default=1)
        
        nodes = []
        for stat in country_stats:
            # Get top 3 themes for this country
            top_themes_query = select(
                ThemeAggregation1h.theme_code,
                func.sum(ThemeAggregation1h.signal_count).label('count')
            ).where(
                ThemeAggregation1h.country_code == stat.country_code
            )
            
            if window_hours is not None:
                top_themes_query = top_themes_query.where(ThemeAggregation1h.hour_bucket >= window_start)
                
            top_themes_stmt = top_themes_query.group_by(
                ThemeAggregation1h.theme_code
            ).order_by(
                desc('count')
            ).limit(3)
            
            top_themes = db.execute(top_themes_stmt).all()
            
            # Get country centroid
            country = db.query(Country).filter(Country.country_code == stat.country_code).first()
            
            node_data = {
                "country_code": stat.country_code,
                "country_name": country.country_name if country else stat.country_code,
                "lat": country.latitude if country else 0,
                "lon": country.longitude if country else 0,
                "intensity": min(stat.total_events / max_events, 1.0),
                "sentiment": round(normalize_sentiment(stat.avg_tone), 2),
                "event_count": stat.total_events,
                "top_themes": [{"label": t.theme_code, "count": t.count} for t in top_themes],
                "source": "database"
            }
            
            # Filter out nodes with invalid coordinates
            if node_data["lat"] != 0 and node_data["lon"] != 0:
                nodes.append(node_data)
        
        return {"nodes": nodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
