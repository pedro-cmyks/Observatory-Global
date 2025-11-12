"""Trends API endpoints."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging
import json
import time
from datetime import datetime

from app.models.schemas import TrendsResponse
from app.services.gdelt_client import GDELTClient
from app.services.trends_client import TrendsClient
from app.services.wiki_client import WikiClient
from app.services.nlp import NLPProcessor

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize clients
gdelt_client = GDELTClient()
trends_client = TrendsClient()
wiki_client = WikiClient()
nlp_processor = NLPProcessor()


@router.get("/top", response_model=TrendsResponse)
async def get_top_trends(
    country: str = Query(..., description="ISO 3166-1 alpha-2 country code", min_length=2, max_length=2),
    limit: int = Query(10, description="Number of topics to return", ge=1, le=50),
) -> TrendsResponse:
    """
    Get top trending topics for a specific country.

    Aggregates data from GDELT, Google Trends, and Wikipedia, then performs
    NLP analysis to extract and normalize topics.

    Args:
        country: Two-letter country code (e.g., "US", "CO", "BR")
        limit: Maximum number of topics to return

    Returns:
        TrendsResponse with aggregated and analyzed topics
    """
    start_time = time.time()
    country_upper = country.upper()

    # Structured request logging
    request_log = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "INFO",
        "endpoint": "/v1/trends/top",
        "country": country_upper,
        "limit": limit,
        "phase": "request_started"
    }
    logger.info(json.dumps(request_log))

    try:
        # Fetch data from all sources concurrently
        all_items = []
        source_counts = {}

        # GDELT data
        try:
            gdelt_items = await gdelt_client.fetch_trending_topics(country_upper)
            all_items.extend(gdelt_items)
            source_counts["gdelt"] = len(gdelt_items)
        except Exception as e:
            source_counts["gdelt"] = 0
            logger.warning(f"GDELT fetch failed: {e}")

        # Google Trends data
        try:
            trends_items = await trends_client.fetch_trending_topics(country_upper)
            all_items.extend(trends_items)
            source_counts["trends"] = len(trends_items)
        except Exception as e:
            source_counts["trends"] = 0
            logger.warning(f"Google Trends fetch failed: {e}")

        # Wikipedia data
        try:
            wiki_items = await wiki_client.fetch_trending_topics(country_upper)
            all_items.extend(wiki_items)
            source_counts["wikipedia"] = len(wiki_items)
        except Exception as e:
            source_counts["wikipedia"] = 0
            logger.warning(f"Wikipedia fetch failed: {e}")

        # If no data from any source, return fallback
        used_fallback = False
        if not all_items:
            logger.warning("No data from any source, using fallback")
            all_items = _generate_fallback_data(country_upper)
            source_counts["fallback"] = len(all_items)
            used_fallback = True

        # Process and analyze topics
        nlp_start = time.time()
        topics = nlp_processor.process_and_extract_topics(all_items, limit=limit)
        nlp_time_ms = int((time.time() - nlp_start) * 1000)

        response_time_ms = int((time.time() - start_time) * 1000)

        # Structured success logging
        success_log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "INFO",
            "endpoint": "/v1/trends/top",
            "country": country_upper,
            "limit": limit,
            "response_time_ms": response_time_ms,
            "nlp_processing_ms": nlp_time_ms,
            "source_counts": source_counts,
            "total_items_fetched": len(all_items),
            "topics_returned": len(topics),
            "used_fallback": used_fallback,
            "phase": "request_completed",
            "status": "success"
        }
        logger.info(json.dumps(success_log))

        return TrendsResponse(
            country=country_upper,
            generated_at=datetime.utcnow(),
            topics=topics,
        )

    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)

        # Structured error logging
        error_log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "ERROR",
            "endpoint": "/v1/trends/top",
            "country": country_upper,
            "limit": limit,
            "response_time_ms": response_time_ms,
            "error": str(e),
            "phase": "request_failed",
            "status": "error"
        }
        logger.error(json.dumps(error_log))

        raise HTTPException(status_code=500, detail=f"Error fetching trends: {str(e)}")


def _generate_fallback_data(country: str) -> list:
    """Generate fallback data when all sources fail."""
    return [
        {
            "title": f"Breaking News in {country}",
            "source": "fallback",
            "count": 100,
        },
        {
            "title": f"Economic Updates {country}",
            "source": "fallback",
            "count": 85,
        },
        {
            "title": f"Political Developments {country}",
            "source": "fallback",
            "count": 72,
        },
        {
            "title": f"Technology Trends {country}",
            "source": "fallback",
            "count": 68,
        },
        {
            "title": f"Sports Highlights {country}",
            "source": "fallback",
            "count": 55,
        },
        {
            "title": f"Cultural Events {country}",
            "source": "fallback",
            "count": 45,
        },
        {
            "title": f"Environmental News {country}",
            "source": "fallback",
            "count": 38,
        },
        {
            "title": f"Health Updates {country}",
            "source": "fallback",
            "count": 32,
        },
        {
            "title": f"Education Reforms {country}",
            "source": "fallback",
            "count": 28,
        },
        {
            "title": f"Entertainment News {country}",
            "source": "fallback",
            "count": 25,
        },
    ]
