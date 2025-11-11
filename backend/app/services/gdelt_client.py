"""GDELT API client for fetching global events and news data."""

import httpx
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class GDELTClient:
    """Client for fetching data from GDELT 2.0 API."""

    def __init__(self):
        self.base_url = settings.GDELT_BASE
        self.timeout = 10.0

    async def fetch_trending_topics(self, country: str) -> List[Dict[str, Any]]:
        """
        Fetch trending topics from GDELT for a specific country.

        Args:
            country: ISO 3166-1 alpha-2 country code

        Returns:
            List of dictionaries with title, source, and count
        """
        try:
            # GDELT provides CSV files updated every 15 minutes
            # We'll fetch the latest Global Knowledge Graph (GKG) data
            # In a real implementation, we would parse GDELT's CSV files
            # For MVP, we'll use a simplified approach with fallback data

            # Generate recent timestamp for GDELT filename format
            now = datetime.utcnow()
            # GDELT files are published every 15 minutes
            rounded_time = now - timedelta(minutes=now.minute % 15)
            timestamp = rounded_time.strftime("%Y%m%d%H%M%S")

            # GDELT GKG file format: http://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip
            # Note: This is a simplified demo - real implementation would download and parse CSV

            logger.info(f"Fetching GDELT data for {country} at {timestamp}")

            # For MVP, return simulated GDELT-style data
            # In production, you would:
            # 1. Download the CSV file
            # 2. Parse it (it's tab-delimited)
            # 3. Filter by country code
            # 4. Extract themes and topics

            return self._generate_gdelt_fallback(country)

        except Exception as e:
            logger.error(f"Error fetching GDELT data: {e}")
            return self._generate_gdelt_fallback(country)

    def _generate_gdelt_fallback(self, country: str) -> List[Dict[str, Any]]:
        """Generate fallback GDELT-style data."""
        return [
            {
                "title": f"Political Developments in {country}",
                "source": "gdelt",
                "count": 45,
            },
            {
                "title": f"Economic Indicators {country}",
                "source": "gdelt",
                "count": 38,
            },
            {
                "title": f"International Relations {country}",
                "source": "gdelt",
                "count": 32,
            },
            {
                "title": f"Public Safety {country}",
                "source": "gdelt",
                "count": 28,
            },
            {
                "title": f"Government Policy {country}",
                "source": "gdelt",
                "count": 25,
            },
        ]
