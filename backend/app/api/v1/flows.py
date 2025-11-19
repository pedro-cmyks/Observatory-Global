"""Flows API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Tuple
import logging
from datetime import datetime

from app.models.flows import FlowsResponse, FlowsMetadata
from app.models.schemas import Topic
from app.models.gdelt_schemas import GDELTSignal
from app.services.flow_detector import FlowDetector, parse_time_window
from app.services.signals_service import get_signals_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def gdelt_signal_to_topic(signal: GDELTSignal) -> Topic:
    """
    Convert GDELT signal to Topic for flow detector compatibility.

    This adapter ensures backward compatibility with the existing FlowDetector
    which expects Topic objects. Uses human-readable theme_labels (not raw GDELT codes).

    Args:
        signal: GDELTSignal object from fetch_gdelt_signals()

    Returns:
        Topic object compatible with FlowDetector
    """
    # Sum all theme counts to get total mention volume
    total_count = sum(signal.theme_counts.values()) if signal.theme_counts else 1

    # Use human-readable theme_labels (e.g., "Terrorism") not GDELT codes (e.g., "TAX_TERROR")
    primary_label = signal.theme_labels[0] if signal.theme_labels else signal.primary_theme

    return Topic(
        id=signal.signal_id,
        label=primary_label,
        count=total_count,
        sample_titles=[],  # GDELTSignal doesn't have sample_titles, leave empty
        sources=["gdelt"],
        confidence=signal.confidence
    )


def convert_gdelt_to_topics(
    signals_by_country: Dict[str, Tuple[List[GDELTSignal], datetime]]
) -> Dict[str, Tuple[List[Topic], datetime]]:
    """
    Convert GDELT signals to Topics for all countries.

    Args:
        signals_by_country: Dict mapping country code to (signals, timestamp)

    Returns:
        Dict mapping country code to (topics, timestamp) for FlowDetector
    """
    topics_by_country = {}

    for country, (signals, timestamp) in signals_by_country.items():
        topics = [gdelt_signal_to_topic(signal) for signal in signals]
        topics_by_country[country] = (topics, timestamp)
        logger.debug(f"Converted {len(signals)} GDELT signals to Topics for {country}")

    return topics_by_country


@router.get("", response_model=FlowsResponse)
async def get_flows(
    time_window: str = Query(
        "24h",
        description="Time window for flow detection (e.g., '1h', '6h', '12h', '24h')",
    ),
    countries: Optional[str] = Query(
        None,
        description="Comma-separated list of ISO country codes (e.g., 'US,CO,BR'). If not specified, uses default countries.",
    ),
    threshold: float = Query(
        0.5,
        description="Minimum heat threshold for flows [0, 1]",
        ge=0.0,
        le=1.0,
    ),
) -> FlowsResponse:
    """
    Detect information flows between countries.

    Analyzes trending topics across countries and calculates:
    - **Hotspots**: Countries with high topic intensity
    - **Flows**: Information propagation between countries based on topic similarity and timing

    The heat formula uses TF-IDF cosine similarity and exponential time decay:
    ```
    heat = similarity × exp(-Δt / 6h)
    ```

    Only flows with heat >= threshold are returned.

    Args:
        time_window: Time window for analysis (e.g., '24h')
        countries: Optional comma-separated country codes (default: US,CO,BR,MX,AR)
        threshold: Minimum heat score to include flow (default: 0.5)

    Returns:
        FlowsResponse with hotspots, flows, and metadata
    """
    try:
        # Parse time window
        try:
            time_window_hours = parse_time_window(time_window)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Parse countries
        if countries:
            country_list = [c.strip().upper() for c in countries.split(",") if c.strip()]
        else:
            # Use SignalsService default countries (aligned with heatmap view)
            signals_service = get_signals_service()
            country_list = signals_service.DEFAULT_COUNTRIES

        if not country_list:
            raise HTTPException(status_code=400, detail="At least one country must be specified")

        if len(country_list) < 2:
            raise HTTPException(
                status_code=400, detail="At least two countries required for flow detection"
            )

        logger.info(
            f"Fetching flows: countries={country_list}, "
            f"time_window={time_window_hours}h, threshold={threshold}"
        )

        # Fetch GDELT signals using unified service
        signals_service = get_signals_service()
        gdelt_signals_by_country = await signals_service.fetch_gdelt_signals(
            countries=country_list,
            time_window=time_window,
            use_cache=True,
        )

        if len(gdelt_signals_by_country) < 2:
            raise HTTPException(
                status_code=503,
                detail=f"Insufficient data: only {len(gdelt_signals_by_country)} countries had valid data. Need at least 2.",
            )

        # Convert GDELT signals to Topics for flow detector compatibility
        trends_by_country = convert_gdelt_to_topics(gdelt_signals_by_country)
        logger.debug(f"Converted GDELT signals for {len(trends_by_country)} countries")

        # Initialize flow detector with custom threshold
        # Get halflife from config (default: 6h)
        halflife = getattr(settings, "HEAT_HALFLIFE_HOURS", 6.0)
        flow_detector = FlowDetector(heat_halflife_hours=halflife, flow_threshold=threshold)

        # Detect flows
        hotspots, flows, metadata_dict = flow_detector.detect_flows(
            trends_by_country, time_window_hours=time_window_hours
        )

        # Build response
        metadata = FlowsMetadata(**metadata_dict)

        response = FlowsResponse(
            hotspots=hotspots,
            flows=flows,
            metadata=metadata,
            generated_at=datetime.utcnow(),
        )

        logger.info(
            f"Flows response generated: {len(hotspots)} hotspots, "
            f"{len(flows)} flows (threshold={threshold})"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting flows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error detecting flows: {str(e)}")


def _generate_fallback_data(country: str) -> list:
    """Generate fallback data when all sources fail."""
    return [
        {"title": f"Breaking News in {country}", "source": "fallback", "count": 100},
        {"title": f"Economic Updates {country}", "source": "fallback", "count": 85},
        {"title": f"Political Developments {country}", "source": "fallback", "count": 72},
        {"title": f"Technology Trends {country}", "source": "fallback", "count": 68},
        {"title": f"Sports Highlights {country}", "source": "fallback", "count": 55},
    ]
