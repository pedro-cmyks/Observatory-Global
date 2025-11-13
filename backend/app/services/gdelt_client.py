"""GDELT API client for fetching global events and news data."""

import httpx
import logging
import json
import time
import io
import zipfile
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter

from app.core.config import settings

logger = logging.getLogger(__name__)


class GDELTClient:
    """Client for fetching real data from GDELT 2.0 GKG files."""

    # GDELT GKG column indices (tab-delimited)
    # Full spec: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
    COL_DATE = 0
    COL_LOCATIONS = 9  # All location mentions
    COL_THEMES = 7     # All themes mentioned
    COL_GCAM = 15      # Global Content Analysis Measures (sentiment)

    # Country code mapping for GDELT filtering
    COUNTRY_CODES = {
        'US': 'United States',
        'GB': 'United Kingdom',
        'IN': 'India',
        'BR': 'Brazil',
        'CO': 'Colombia',
        'MX': 'Mexico',
        'AR': 'Argentina',
        'CL': 'Chile',
        'PE': 'Peru',
        'ES': 'Spain',
        'FR': 'France',
        'DE': 'Germany',
        'IT': 'Italy',
        'JP': 'Japan',
        'KR': 'South Korea',
        'AU': 'Australia',
        'CA': 'Canada',
    }

    def __init__(self):
        self.base_url = settings.GDELT_BASE
        self.timeout = 30.0  # Increased for CSV download

    async def fetch_trending_topics(self, country: str) -> List[Dict[str, Any]]:
        """
        Fetch real trending topics from GDELT GKG CSV files.

        Args:
            country: ISO 3166-1 alpha-2 country code

        Returns:
            List of dictionaries with title, source, and count
        """
        start_time = time.time()

        try:
            # Get the most recent GDELT file timestamp
            # GDELT updates every 15 minutes
            gkg_url = self._get_latest_gkg_url()

            # Download and parse CSV
            topics = await self._download_and_parse_gkg(gkg_url, country)

            response_time_ms = int((time.time() - start_time) * 1000)

            # Structured logging
            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "INFO",
                "source": "gdelt",
                "country": country,
                "url": gkg_url,
                "response_time_ms": response_time_ms,
                "records_fetched": len(topics),
                "cache_hit": False,
                "status": "success",
                "data_source": "real_csv"
            }
            logger.info(json.dumps(log_data))

            return topics

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)

            # Structured error logging
            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "WARNING",
                "source": "gdelt",
                "country": country,
                "response_time_ms": response_time_ms,
                "error": str(e),
                "error_type": type(e).__name__,
                "status": "fallback",
                "data_source": "fallback"
            }
            logger.warning(json.dumps(log_data))

            # Fallback to backup strategy
            return self._generate_gdelt_fallback(country)

    def _get_latest_gkg_url(self) -> str:
        """
        Generate URL for the most recent GDELT GKG file.

        GDELT publishes files every 15 minutes at:
        http://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip

        Returns:
            URL string for latest GKG file
        """
        now = datetime.utcnow()

        # Round down to nearest 15-minute interval
        # GDELT files are typically 15-30 minutes delayed
        rounded_minutes = (now.minute // 15) * 15
        rounded_time = now.replace(minute=rounded_minutes, second=0, microsecond=0)

        # Try most recent file, with 30-minute delay buffer
        file_time = rounded_time - timedelta(minutes=30)
        timestamp = file_time.strftime("%Y%m%d%H%M%S")

        return f"{self.base_url}/{timestamp}.gkg.csv.zip"

    async def _download_and_parse_gkg(
        self,
        url: str,
        country: str,
        max_themes: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Download GDELT GKG CSV.zip file and extract trending topics.

        Args:
            url: GDELT GKG file URL
            country: ISO alpha-2 country code to filter by
            max_themes: Maximum number of themes to process

        Returns:
            List of topic dictionaries
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Download the ZIP file
            response = await client.get(url)
            response.raise_for_status()

            # Unzip and read CSV
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # GKG files contain a single CSV with same name
                csv_filename = zip_file.namelist()[0]
                csv_data = zip_file.read(csv_filename).decode('utf-8', errors='ignore')

            # Parse CSV and extract themes
            themes_counter = Counter()
            location_match_count = 0
            total_rows = 0

            csv_reader = csv.reader(io.StringIO(csv_data), delimiter='\t')

            for row in csv_reader:
                total_rows += 1

                # Skip malformed rows
                if len(row) < 16:
                    continue

                # Check if this record mentions the target country
                locations = row[self.COL_LOCATIONS] if len(row) > self.COL_LOCATIONS else ""

                if self._is_country_relevant(locations, country):
                    location_match_count += 1

                    # Extract themes (semicolon-separated)
                    themes_str = row[self.COL_THEMES] if len(row) > self.COL_THEMES else ""
                    themes = self._parse_themes(themes_str)

                    # Count theme frequencies
                    for theme in themes[:max_themes]:  # Limit themes per record
                        themes_counter[theme] += 1

            # Convert to topic format (top 10 themes)
            topics = []
            for theme, count in themes_counter.most_common(10):
                topics.append({
                    "title": self._clean_theme_name(theme),
                    "source": "gdelt",
                    "count": count,
                })

            logger.info(
                f"GDELT processed {total_rows} rows, {location_match_count} matched {country}, "
                f"extracted {len(topics)} topics"
            )

            # If no matches found, try fallback
            if len(topics) == 0:
                raise ValueError(f"No GDELT data found for {country}")

            return topics

    def _is_country_relevant(self, locations: str, country: str) -> bool:
        """
        Check if location string mentions the target country.

        GDELT locations format: "1#CountryName#CC#Lat#Lon;2#OtherCountry#CC#..."

        Args:
            locations: GDELT locations field
            country: ISO alpha-2 country code

        Returns:
            True if country is mentioned
        """
        if not locations:
            return False

        country_name = self.COUNTRY_CODES.get(country, country)

        # Simple contains check (locations field includes country names)
        return country in locations or country_name in locations

    def _parse_themes(self, themes_str: str) -> List[str]:
        """
        Parse GDELT themes string into list.

        Format: "THEME1;THEME2;THEME3"

        Args:
            themes_str: Semicolon-separated themes

        Returns:
            List of theme strings
        """
        if not themes_str:
            return []

        themes = themes_str.split(';')

        # Filter out empty and very long themes
        return [t.strip() for t in themes if t.strip() and len(t) < 100]

    def _clean_theme_name(self, theme: str) -> str:
        """
        Clean GDELT theme names for display.

        GDELT themes often look like: "WB_632_ECONOMIC_POLICY"
        Convert to: "Economic Policy"

        Args:
            theme: Raw GDELT theme string

        Returns:
            Cleaned theme name
        """
        # Remove common prefixes
        theme = theme.replace('WB_', '').replace('TAX_', '').replace('UNGP_', '')

        # Remove leading numbers and underscores
        parts = theme.split('_')
        cleaned_parts = [p for p in parts if not p.isdigit()]

        # Title case
        cleaned = ' '.join(cleaned_parts).title()

        # Limit length
        if len(cleaned) > 50:
            cleaned = cleaned[:47] + "..."

        return cleaned if cleaned else theme

    def _generate_gdelt_fallback(self, country: str) -> List[Dict[str, Any]]:
        """
        Generate fallback GDELT-style data when real API fails.

        Args:
            country: Country code for contextualized fallback

        Returns:
            List of fallback topics
        """
        return [
            {
                "title": f"Political Developments in {country}",
                "source": "gdelt_fallback",
                "count": 45,
            },
            {
                "title": f"Economic Indicators {country}",
                "source": "gdelt_fallback",
                "count": 38,
            },
            {
                "title": f"International Relations {country}",
                "source": "gdelt_fallback",
                "count": 32,
            },
            {
                "title": f"Public Safety {country}",
                "source": "gdelt_fallback",
                "count": 28,
            },
            {
                "title": f"Government Policy {country}",
                "source": "gdelt_fallback",
                "count": 25,
            },
        ]
