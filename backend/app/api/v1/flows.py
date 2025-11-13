"""Flows API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import logging
from datetime import datetime

from app.models.flows import FlowsResponse, FlowsMetadata
from app.models.schemas import Topic
from app.services.flow_detector import FlowDetector, parse_time_window
from app.services.gdelt_client import GDELTClient
from app.services.trends_client import TrendsClient
from app.services.wiki_client import WikiClient
from app.services.nlp import NLPProcessor
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize clients
gdelt_client = GDELTClient()
trends_client = TrendsClient()
wiki_client = WikiClient()
nlp_processor = NLPProcessor()


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
            # Default countries
            country_list = ["US", "CO", "BR", "MX", "AR"]

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

        # Fetch trends for all countries
        trends_by_country = {}

        for country in country_list:
            try:
                # Fetch data from all sources
                all_items = []

                # GDELT
                try:
                    gdelt_items = await gdelt_client.fetch_trending_topics(country)
                    all_items.extend(gdelt_items)
                except Exception as e:
                    logger.warning(f"GDELT fetch failed for {country}: {e}")

                # Google Trends
                try:
                    trends_items = await trends_client.fetch_trending_topics(country)
                    all_items.extend(trends_items)
                except Exception as e:
                    logger.warning(f"Google Trends fetch failed for {country}: {e}")

                # Wikipedia
                try:
                    wiki_items = await wiki_client.fetch_trending_topics(country)
                    all_items.extend(wiki_items)
                except Exception as e:
                    logger.warning(f"Wikipedia fetch failed for {country}: {e}")

                # Fallback data if no sources available
                if not all_items:
                    logger.warning(f"No data for {country}, using fallback")
                    all_items = _generate_fallback_data(country)

                # Process topics with NLP
                topics = nlp_processor.process_and_extract_topics(all_items, limit=50)

                if topics:
                    trends_by_country[country] = (topics, datetime.utcnow())
                    logger.info(f"Fetched {len(topics)} topics for {country}")

            except Exception as e:
                logger.error(f"Error fetching trends for {country}: {e}", exc_info=True)
                # Continue with other countries (graceful degradation)
                continue

        if len(trends_by_country) < 2:
            raise HTTPException(
                status_code=503,
                detail=f"Insufficient data: only {len(trends_by_country)} countries had valid data. Need at least 2.",
            )

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
