"""Hexmap API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
import json
import redis
from datetime import datetime

from app.services.hexmap_generator import HexmapGenerator
from app.services.flow_detector import FlowDetector, parse_time_window
from app.services.signals_service import get_signals_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
hexmap_generator = HexmapGenerator()

# Initialize Redis client
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
    )
    redis_available = True
    logger.info("Redis client initialized for hexmap caching")
except Exception as e:
    logger.warning(f"Redis unavailable: {e}")
    redis_client = None
    redis_available = False


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
    time_window: str = Query(
        "24h",
        description="Time window for data aggregation (e.g., '1h', '6h', '12h', '24h')",
    ),
    resolution: Optional[int] = Query(
        None,
        description="H3 resolution (0-15). If not specified, uses zoom-based resolution. "
                    "Lower = larger hexes (0=global, 3=country, 6=city)",
        ge=0,
        le=15,
    ),
    zoom: Optional[float] = Query(
        None,
        description="Map zoom level (0-12+). Used to auto-select resolution if resolution not specified.",
        ge=0,
        le=20,
    ),
    k_ring: int = Query(
        2,
        description="K-ring smoothing radius for blob effect. 0=no smoothing, 1=immediate neighbors, 2=extended smoothing",
        ge=0,
        le=5,
    ),
    countries: Optional[str] = Query(
        None,
        description="Comma-separated list of ISO country codes (e.g., 'US,CO,BR'). If not specified, uses default countries.",
    ),
    cache: bool = Query(
        True,
        description="Whether to use cached data (5-minute TTL)",
    ),
) -> HexmapResponse:
    """
    Generate hexagonal heatmap from country-level trending data.

    Converts country hotspots into a smooth hexagonal heatmap suitable for deck.gl rendering.
    Uses H3 spatial indexing with k-ring smoothing to create organic "blob" visualizations.

    **Resolution Mapping** (zoom → resolution):
    - Zoom 0-2: Resolution 1 (global, ~1,100km hexes)
    - Zoom 3-4: Resolution 2 (continental, ~400km hexes)
    - Zoom 5-6: Resolution 3 (country, ~160km hexes) ← Default
    - Zoom 7-8: Resolution 4 (state, ~60km hexes)
    - Zoom 9-10: Resolution 5 (city, ~20km hexes)
    - Zoom 11-12: Resolution 6 (urban, ~8km hexes)

    **K-Ring Smoothing**:
    - k=0: No smoothing (discrete hexagons)
    - k=1: Immediate neighbors (7 total hexes)
    - k=2: Extended neighbors (~19 hexes) ← Recommended for blobs
    - k=3: Wide smoothing (~37 hexes)

    Args:
        time_window: Time window for trending data
        resolution: H3 resolution (overrides zoom if specified)
        zoom: Map zoom level (auto-selects resolution)
        k_ring: K-ring smoothing radius
        countries: Optional comma-separated country codes
        cache: Whether to use cached results (5-minute TTL)

    Returns:
        HexmapResponse with hex cells and metadata
    """
    try:
        # Determine resolution
        if resolution is not None:
            # User-specified resolution
            selected_resolution = resolution
        elif zoom is not None:
            # Auto-select from zoom level
            selected_resolution = hexmap_generator.get_resolution_for_zoom(zoom)
        else:
            # Default resolution (country-level)
            selected_resolution = hexmap_generator.default_resolution

        # Parse countries
        if countries:
            country_list = [c.strip().upper() for c in countries.split(",") if c.strip()]
        else:
            # Use SignalsService default countries (aligned with flows view)
            signals_service = get_signals_service()
            country_list = signals_service.DEFAULT_COUNTRIES

        if not country_list:
            raise HTTPException(status_code=400, detail="At least one country must be specified")

        # Build cache key
        cache_key = f"hexmap:r{selected_resolution}:k{k_ring}:tw{time_window}:c{','.join(sorted(country_list))}"

        # Check cache
        cached_response = None
        if cache and redis_available:
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    cached_response = json.loads(cached_data)
                    logger.info(f"Hexmap cache hit: {cache_key}")
            except Exception as e:
                logger.warning(f"Cache read error: {e}")

        if cached_response:
            # Return cached response with updated timestamp
            return HexmapResponse(**cached_response)

        # Cache miss - generate fresh hexmap
        logger.info(
            f"Generating hexmap: resolution={selected_resolution}, "
            f"k_ring={k_ring}, countries={country_list}, time_window={time_window}"
        )

        # Parse time window
        try:
            time_window_hours = parse_time_window(time_window)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Fetch trending signals using unified service
        # Note: SignalsService has its own cache (5-min TTL) for raw signals
        # This endpoint also caches the final hexmap (after H3 conversion & k-ring smoothing)
        signals_service = get_signals_service()
        trends_by_country = await signals_service.fetch_trending_signals(
            countries=country_list,
            time_window=time_window,
            use_cache=True,
        )

        if not trends_by_country:
            raise HTTPException(
                status_code=503,
                detail="No data available for any country"
            )

        # Calculate hotspots (country-level intensities)
        flow_detector = FlowDetector()
        hotspots, _, _ = flow_detector.detect_flows(
            trends_by_country,
            time_window_hours=time_window_hours
        )

        # Convert hotspots to hexmap format
        hotspot_data = [
            {"country_code": h.country_code, "intensity": h.intensity}
            for h in hotspots
        ]

        # Generate hexmap with k-ring smoothing
        hexes = hexmap_generator.generate_hexmap(
            hotspots=hotspot_data,
            resolution=selected_resolution,
            k_ring=k_ring,
            normalize=True
        )

        # Build response
        metadata = HexmapMetadata(
            resolution=selected_resolution,
            k_ring=k_ring,
            hex_count=len(hexes),
            countries_analyzed=list(trends_by_country.keys()),
            cache_hit=False,
            time_window=time_window
        )

        response = HexmapResponse(
            hexes=[HexCell(**h) for h in hexes],
            metadata=metadata,
            generated_at=datetime.utcnow()
        )

        # Cache response (5-minute TTL)
        if cache and redis_available:
            try:
                cache_data = response.model_dump_json()
                redis_client.setex(cache_key, 300, cache_data)  # 5 minutes
                logger.info(f"Hexmap cached: {cache_key}")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")

        logger.info(
            f"Hexmap generated: {len(hexes)} hexes, "
            f"resolution={selected_resolution}, k_ring={k_ring}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating hexmap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating hexmap: {str(e)}")
