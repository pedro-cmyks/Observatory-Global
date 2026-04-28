"""Hexmap API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
from datetime import datetime

# DEPRECATED: HexmapGenerator removed in favor of client-side Gaussian Heatmap
# from app.services.hexmap_generator import HexmapGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

# Response models
class HexCell(BaseModel):
    """Single hexagon cell with intensity."""
    h3_index: str = Field(..., description="H3 hexagon index")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Normalized intensity [0, 1]")


class HexmapMetadata(BaseModel):
    """Metadata about the hexmap generation."""
    resolution: int = Field(..., description="H3 resolution level (0-15)")
    k_ring: int = Field(..., description="K-ring smoothing radius")
    hex_count: int = Field(..., description="Number of hexagons returned")
    countries_analyzed: List[str] = Field(..., description="List of countries included")
    cache_hit: bool = Field(..., description="Whether this response came from cache")
    time_window: str = Field(..., description="Time window used for data")


class HexmapResponse(BaseModel):
    """Hexagonal heatmap response."""
    hexes: List[HexCell] = Field(..., description="List of hexagon cells with intensities")
    metadata: HexmapMetadata = Field(..., description="Metadata about the hexmap")
    generated_at: datetime = Field(..., description="Timestamp when hexmap was generated")


@router.get("", response_model=HexmapResponse)
async def get_hexmap(
    time_window: str = Query("24h"),
    resolution: Optional[int] = Query(None),
    zoom: Optional[float] = Query(None),
    k_ring: int = Query(2),
    countries: Optional[str] = Query(None),
    cache: bool = Query(True),
) -> HexmapResponse:
    """
    [DEPRECATED] Generate hexagonal heatmap.
    
    This endpoint is deprecated. The frontend now uses client-side Gaussian Heatmaps
    driven by the /v1/flows endpoint data.
    
    Returns empty list to maintain API contract temporarily.
    """
    logger.warning("Call to deprecated /v1/hexmap endpoint")
    
    return HexmapResponse(
        hexes=[],
        metadata=HexmapMetadata(
            resolution=0,
            k_ring=0,
            hex_count=0,
            countries_analyzed=[],
            cache_hit=False,
            time_window=time_window
        ),
        generated_at=datetime.utcnow()
    )
