"""GDELT API client for fetching global events and news data."""

import asyncio
import httpx
import logging
import json
import time
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import settings
from app.models.gdelt_schemas import GDELTSignal
from app.services.gdelt_downloader import GDELTDownloader
from app.services.gdelt_parser import GDELTParser
from app.adapters.gdelt_adapter import convert_gkg_to_signals
from app.services.gdelt_placeholder_generator import get_placeholder_generator

logger = logging.getLogger(__name__)


class GDELTClient:
    """
    Client for fetching data from GDELT 2.0 API.

    **CURRENT STATUS: Real GDELT Integration**
    - Downloads real GKG files from GDELT 2.0
    - Parses with full GKG v2.1 schema support
    - Converts GKGRecord → GDELTSignal
    - Falls back to placeholders if real data unavailable

    **Features:**
    - 15-minute caching (matches GDELT update cadence)
    - Country filtering
    - Automatic fallback to placeholder data
    """

    def __init__(self):
        self.base_url = settings.GDELT_BASE
        self.timeout = 10.0
        self.downloader = GDELTDownloader()
        self.parser = GDELTParser()
        self.placeholder_generator = get_placeholder_generator()

        # Simple in-memory cache (timestamp → signals dict)
        self._cache: Dict[str, tuple[datetime, Dict[str, List[GDELTSignal]]]] = {}
        self._cache_ttl_minutes = 15  # Match GDELT update cadence

    async def fetch_gdelt_signals(self, country: str, count: int = 100) -> List[GDELTSignal]:
        """
        Fetch GDELT signals for a specific country.

        **Real GDELT Pipeline:**
        1. Check cache (15-minute TTL)
        2. Download latest GKG file from GDELT
        3. Parse tab-delimited CSV (27 columns)
        4. Convert GKGRecord → GDELTSignal (one signal per theme)
        5. Filter by country code
        6. Cache results

        Args:
            country: ISO 3166-1 alpha-2 country code (e.g., 'US', 'BR')
            count: Maximum number of signals to return (default: 100)

        Returns:
            List of GDELTSignal objects (real data or placeholder fallback)
        """
        start_time = time.time()

        try:
            # Step 1: Check cache
            cached_signals = self._get_from_cache(country)
            if cached_signals is not None:
                logger.info(json.dumps({
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": "INFO",
                    "source": "gdelt_cache",
                    "country": country,
                    "signals_returned": len(cached_signals[:count]),
                    "cache_hit": True
                }))
                return cached_signals[:count]

            # Step 2: Download latest GKG file
            csv_path = await self.downloader.download_latest()

            if csv_path is None:
                # Download failed, use placeholder fallback
                logger.warning("GDELT download failed, using placeholder data")
                return self._get_placeholder_signals(country, count)

            # Step 3 & 4: Parse and convert
            signals = await self._parse_and_convert(csv_path)

            # Step 5: Filter by country and cache
            country_signals = [s for s in signals if s.primary_location.country_code == country]
            self._cache_signals(country_signals)

            response_time_ms = int((time.time() - start_time) * 1000)

            # Log success
            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "INFO",
                "source": "gdelt_real",
                "country": country,
                "response_time_ms": response_time_ms,
                "total_signals_parsed": len(signals),
                "country_signals": len(country_signals),
                "signals_returned": len(country_signals[:count]),
                "data_quality": "real",
                "csv_file": csv_path.name if csv_path else None,
                "status": "success"
            }
            logger.info(json.dumps(log_data))

            return country_signals[:count]

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)

            # Log error and fall back to placeholders
            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "ERROR",
                "source": "gdelt_real",
                "country": country,
                "response_time_ms": response_time_ms,
                "error": str(e),
                "error_type": type(e).__name__,
                "fallback": "placeholder",
                "status": "error"
            }
            logger.error(json.dumps(log_data))

            # Graceful fallback to placeholder data
            return self._get_placeholder_signals(country, count)

    async def _parse_and_convert(self, csv_path: Path) -> List[GDELTSignal]:
        """
        Parse GKG CSV file and convert records to signals.

        Args:
            csv_path: Path to GKG CSV file

        Returns:
            List of GDELTSignal objects (one per theme in each record)
        """
        signals = []

        # Parse file (yields GKGRecord objects)
        for record in self.parser.parse_gkg_file(csv_path):
            # Convert GKGRecord → List[GDELTSignal] (one per theme)
            try:
                record_signals = convert_gkg_to_signals(record)
                signals.extend(record_signals)
            except Exception as e:
                logger.warning(f"Failed to convert record {record.record_id}: {e}")
                continue

        return signals

    def _get_from_cache(self, country: str) -> Optional[List[GDELTSignal]]:
        """Check cache for country signals."""
        for timestamp, (cached_at, signals_by_country) in list(self._cache.items()):
            # Check if cache is still valid (15 minutes)
            age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
            if age_minutes < self._cache_ttl_minutes:
                if country in signals_by_country:
                    return signals_by_country[country]
            else:
                # Cache expired, remove it
                del self._cache[timestamp]

        return None

    def _cache_signals(self, signals: List[GDELTSignal]):
        """
        Cache signals by country.

        Args:
            signals: List of signals to cache
        """
        # Group signals by country
        signals_by_country: Dict[str, List[GDELTSignal]] = {}
        for signal in signals:
            country = signal.primary_location.country_code
            if country not in signals_by_country:
                signals_by_country[country] = []
            signals_by_country[country].append(signal)

        # Store in cache with current timestamp as key
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        self._cache[timestamp] = (datetime.utcnow(), signals_by_country)

        # Clean up old cache entries (keep only 2 most recent)
        if len(self._cache) > 2:
            oldest_key = min(self._cache.keys())
            del self._cache[oldest_key]

    def _get_placeholder_signals(self, country: str, count: int) -> List[GDELTSignal]:
        """Generate placeholder signals as fallback."""
        now = datetime.utcnow()
        signals = [
            self.placeholder_generator.generate_signal(country, now)
            for _ in range(count)
        ]
        # DEBUG: Check Phase 3.5 fields
        if signals:
            logger.debug(f"DEBUG placeholder: country={country}, persons={signals[0].persons}, orgs={signals[0].organizations}, outlet={signals[0].source_outlet}")
        return signals
