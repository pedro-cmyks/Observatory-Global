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

        # File-level cache: filename → (fetch_time, {country: [signals]})
        # Parse ONCE per GDELT file, cache ALL countries
        self._file_cache: Optional[tuple[str, datetime, Dict[str, List[GDELTSignal]]]] = None
        self._cache_ttl_minutes = 15  # Match GDELT update cadence

    async def fetch_gdelt_signals(self, country: str, count: int = 100) -> List[GDELTSignal]:
        """
        Fetch GDELT signals for a specific country.

        **Optimized Pipeline (parse once, filter many times):**
        1. Check if file is already parsed and cached
        2. If not cached: Download + parse ENTIRE file ONCE
        3. Group all signals by country code
        4. Cache grouped signals (15-minute TTL)
        5. Return filtered signals for requested country

        **Performance:**
        - First request: ~2s (download + parse 1273 rows)
        - Subsequent requests: <10ms (filter from cache)
        - Works for 31 countries without timeout!

        Args:
            country: ISO 3166-1 alpha-2 country code (e.g., 'US', 'BR')
            count: Maximum number of signals to return (default: 100)

        Returns:
            List of GDELTSignal objects (real data or placeholder fallback)
        """
        start_time = time.time()

        try:
            # Step 1: Download latest file metadata (cheap operation)
            csv_path = await self.downloader.download_latest()

            if csv_path is None:
                # Download failed, use placeholder fallback
                logger.warning("GDELT download failed, using placeholder data")
                return self._get_placeholder_signals(country, count)

            filename = csv_path.name

            # Step 2: Check file-level cache
            if self._file_cache is not None:
                cached_filename, cached_at, signals_by_country = self._file_cache

                # Same file and within TTL?
                age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                if cached_filename == filename and age_minutes < self._cache_ttl_minutes:
                    # Cache hit!
                    country_signals = signals_by_country.get(country, [])
                    response_time_ms = int((time.time() - start_time) * 1000)

                    logger.info(json.dumps({
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "level": "INFO",
                        "source": "gdelt_cache",
                        "country": country,
                        "cached_file": filename,
                        "cache_age_minutes": round(age_minutes, 2),
                        "signals_returned": len(country_signals[:count]),
                        "response_time_ms": response_time_ms,
                        "cache_hit": True
                    }))
                    return country_signals[:count]

            # Step 3: Cache miss - parse file ONCE
            logger.info(f"Parsing GDELT file {filename} (will cache for all countries)")
            all_signals = await self._parse_and_convert(csv_path)

            # Step 4: Group by country code
            signals_by_country: Dict[str, List[GDELTSignal]] = {}
            for signal in all_signals:
                country_code = signal.primary_location.country_code
                if country_code not in signals_by_country:
                    signals_by_country[country_code] = []
                signals_by_country[country_code].append(signal)

            # Step 5: Cache at file level (all countries)
            self._file_cache = (filename, datetime.utcnow(), signals_by_country)

            # Step 6: Return requested country's signals
            country_signals = signals_by_country.get(country, [])

            response_time_ms = int((time.time() - start_time) * 1000)

            # Log success (first parse of this file)
            countries_in_cache = len(signals_by_country)
            total_signals = sum(len(sigs) for sigs in signals_by_country.values())

            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "INFO",
                "source": "gdelt_real",
                "country": country,
                "response_time_ms": response_time_ms,
                "total_signals_parsed": total_signals,
                "countries_found": countries_in_cache,
                "country_signals": len(country_signals),
                "signals_returned": len(country_signals[:count]),
                "data_quality": "real",
                "csv_file": filename,
                "cache_status": "populated",
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
        for record in self.parser.parse_file(str(csv_path)):
            # Convert GKGRecord → List[GDELTSignal] (one per theme)
            try:
                record_signals = convert_gkg_to_signals(record)
                signals.extend(record_signals)
            except Exception as e:
                logger.warning(f"Failed to convert record {record.record_id}: {e}")
                continue

        return signals


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
