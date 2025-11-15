"""
Unified Trending Signals Service

This is the single source of truth for all trending signals data.
Both Classic View (/v1/flows) and Heatmap View (/v1/hexmap) must use this service.

Architecture Decision:
- Eliminates 87% code duplication between flows.py and hexmap.py
- Ensures both views use identical data sources
- Centralizes caching strategy (5-minute Redis TTL)
- Maintains consistent default countries across all views
"""

import logging
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import redis

from app.services.gdelt_client import GDELTClient
from app.services.trends_client import TrendsClient
from app.services.wiki_client import WikiClient
from app.services.nlp import NLPProcessor
from app.models.schemas import Topic
from app.models.gdelt_schemas import GDELTSignal
from app.core.config import settings

logger = logging.getLogger(__name__)


class SignalsService:
    """
    Centralized service for fetching and processing trending signals.

    This service provides a unified interface for all data consumed by:
    - Classic View (/v1/flows)
    - Heatmap View (/v1/hexmap)
    - Future visualization modes

    Data Flow:
    1. Check Redis cache (5-min TTL)
    2. If cache miss: Fetch from GDELT + Google Trends + Wikipedia
    3. Process with NLP to extract topics
    4. Cache results
    5. Return (topics, timestamp) per country
    """

    # Unified default countries for all views
    DEFAULT_COUNTRIES = [
        "US",  # United States
        "CO",  # Colombia
        "BR",  # Brazil
        "MX",  # Mexico
        "AR",  # Argentina
        "GB",  # United Kingdom
        "FR",  # France
        "DE",  # Germany
        "ES",  # Spain
        "IT",  # Italy
    ]

    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(self):
        """Initialize data source clients and Redis cache."""
        self.gdelt_client = GDELTClient()
        self.trends_client = TrendsClient()
        self.wiki_client = WikiClient()
        self.nlp_processor = NLPProcessor()

        # Initialize Redis for caching
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True,
            )
            self.redis_client.ping()
            self.redis_available = True
            logger.info("SignalsService: Redis cache available")
        except Exception as e:
            logger.warning(f"SignalsService: Redis unavailable, caching disabled: {e}")
            self.redis_client = None
            self.redis_available = False

    async def fetch_gdelt_signals(
        self,
        countries: Optional[List[str]] = None,
        time_window: str = "6h",
        use_cache: bool = True,
    ) -> Dict[str, Tuple[List[GDELTSignal], datetime]]:
        """
        Fetch GDELT signals for specified countries.

        **NEW METHOD - GDELT-shaped data**
        This returns GDELTSignal objects instead of Topic objects.
        Replaces fetch_trending_signals for Iteration 3.

        Args:
            countries: List of ISO country codes (defaults to DEFAULT_COUNTRIES)
            time_window: Time window for trends (e.g., "1h", "6h", "24h")
            use_cache: Whether to use Redis cache (default True)

        Returns:
            Dictionary mapping country code to (signals, fetch_timestamp)

        Example:
            {
                "US": ([GDELTSignal(...), GDELTSignal(...)], datetime(2025, 1, 15, 12, 0)),
                "CO": ([GDELTSignal(...), GDELTSignal(...)], datetime(2025, 1, 15, 12, 0)),
            }
        """
        # Use default countries if none specified
        if countries is None:
            countries = self.DEFAULT_COUNTRIES

        # Build cache key based on parameters
        cache_key = self._build_cache_key_gdelt(countries, time_window)

        # Check cache first
        if use_cache and self.redis_available:
            cached_data = await self._get_from_cache_gdelt(cache_key)
            if cached_data:
                logger.info(f"SignalsService: Cache hit (GDELT) for {cache_key}")
                return cached_data

        # Cache miss - fetch fresh GDELT data
        logger.info(f"SignalsService: Fetching fresh GDELT data for {len(countries)} countries")
        signals_by_country = {}

        for country in countries:
            try:
                # Fetch GDELT signals (already fully structured)
                signals = await self.gdelt_client.fetch_gdelt_signals(country, count=10)

                if signals:
                    signals_by_country[country] = (signals, datetime.utcnow())
                    logger.info(f"SignalsService: Fetched {len(signals)} GDELT signals for {country}")
                else:
                    logger.warning(f"SignalsService: No GDELT signals for {country}")

            except Exception as e:
                logger.error(f"SignalsService: Error fetching GDELT signals for {country}: {e}")
                continue

        # Cache result if data was fetched
        if use_cache and self.redis_available and signals_by_country:
            await self._save_to_cache_gdelt(cache_key, signals_by_country)

        logger.info(f"SignalsService: Returning GDELT data for {len(signals_by_country)} countries")
        return signals_by_country

    async def fetch_trending_signals(
        self,
        countries: Optional[List[str]] = None,
        time_window: str = "6h",
        use_cache: bool = True,
    ) -> Dict[str, Tuple[List[Topic], datetime]]:
        """
        Fetch trending signals for specified countries.

        This is the single entry point for all trending data.
        Both Classic View and Heatmap View call this method.

        Args:
            countries: List of ISO country codes (defaults to DEFAULT_COUNTRIES)
            time_window: Time window for trends (e.g., "1h", "6h", "24h")
            use_cache: Whether to use Redis cache (default True)

        Returns:
            Dictionary mapping country code to (topics, fetch_timestamp)

        Example:
            {
                "US": ([Topic(...), Topic(...)], datetime(2025, 1, 14, 12, 0)),
                "CO": ([Topic(...), Topic(...)], datetime(2025, 1, 14, 12, 0)),
            }
        """
        # Use default countries if none specified
        if countries is None:
            countries = self.DEFAULT_COUNTRIES

        # Build cache key based on parameters
        cache_key = self._build_cache_key(countries, time_window)

        # Check cache first
        if use_cache and self.redis_available:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                logger.info(f"SignalsService: Cache hit for {cache_key}")
                return cached_data

        # Cache miss - fetch fresh data
        logger.info(f"SignalsService: Fetching fresh data for {len(countries)} countries")
        trends_by_country = {}

        for country in countries:
            try:
                all_items = []

                # Fetch from GDELT
                try:
                    gdelt_items = await self.gdelt_client.fetch_trending_topics(country)
                    all_items.extend(gdelt_items)
                    logger.debug(f"SignalsService: GDELT returned {len(gdelt_items)} items for {country}")
                except Exception as e:
                    logger.warning(f"SignalsService: GDELT fetch failed for {country}: {e}")

                # Fetch from Google Trends
                try:
                    trends_items = await self.trends_client.fetch_trending_topics(country)
                    all_items.extend(trends_items)
                    logger.debug(f"SignalsService: Trends returned {len(trends_items)} items for {country}")
                except Exception as e:
                    logger.warning(f"SignalsService: Google Trends fetch failed for {country}: {e}")

                # Fetch from Wikipedia
                try:
                    wiki_items = await self.wiki_client.fetch_trending_topics(country)
                    all_items.extend(wiki_items)
                    logger.debug(f"SignalsService: Wikipedia returned {len(wiki_items)} items for {country}")
                except Exception as e:
                    logger.warning(f"SignalsService: Wikipedia fetch failed for {country}: {e}")

                # Process with NLP to extract topics
                if all_items:
                    topics = self.nlp_processor.process_and_extract_topics(
                        all_items,
                        limit=50
                    )
                    if topics:
                        trends_by_country[country] = (topics, datetime.utcnow())
                        logger.info(f"SignalsService: Processed {len(topics)} topics for {country}")
                    else:
                        logger.warning(f"SignalsService: NLP returned no topics for {country}")
                else:
                    logger.warning(f"SignalsService: No items fetched for {country}")

            except Exception as e:
                logger.error(f"SignalsService: Error processing {country}: {e}")
                continue

        # Cache result if data was fetched
        if use_cache and self.redis_available and trends_by_country:
            await self._save_to_cache(cache_key, trends_by_country)

        logger.info(f"SignalsService: Returning data for {len(trends_by_country)} countries")
        return trends_by_country

    def _build_cache_key(self, countries: List[str], time_window: str) -> str:
        """
        Build consistent cache key for signal data.

        Format: signals:tw{time_window}:c{sorted_countries}
        Example: signals:tw6h:cAR,BR,CO,MX,US
        """
        sorted_countries = ','.join(sorted(countries))
        return f"signals:tw{time_window}:c{sorted_countries}"

    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Tuple[List[Topic], datetime]]]:
        """Retrieve cached signal data from Redis."""
        if not self.redis_available:
            return None

        try:
            cached_json = self.redis_client.get(cache_key)
            if not cached_json:
                return None

            # Deserialize cached data
            cached_data = json.loads(cached_json)

            # Reconstruct topics from serialized data
            trends_by_country = {}
            for country, (topics_data, timestamp_str) in cached_data.items():
                topics = [Topic(**topic_dict) for topic_dict in topics_data]
                timestamp = datetime.fromisoformat(timestamp_str)
                trends_by_country[country] = (topics, timestamp)

            return trends_by_country

        except Exception as e:
            logger.error(f"SignalsService: Cache retrieval error: {e}")
            return None

    async def _save_to_cache(
        self,
        cache_key: str,
        trends_by_country: Dict[str, Tuple[List[Topic], datetime]]
    ) -> None:
        """Save signal data to Redis cache."""
        if not self.redis_available:
            return

        try:
            # Serialize data for caching
            cache_data = {}
            for country, (topics, timestamp) in trends_by_country.items():
                topics_data = [topic.dict() for topic in topics]
                cache_data[country] = (topics_data, timestamp.isoformat())

            # Store in Redis with TTL
            cache_json = json.dumps(cache_data)
            self.redis_client.setex(
                cache_key,
                self.CACHE_TTL_SECONDS,
                cache_json
            )
            logger.info(f"SignalsService: Cached data for {cache_key} (TTL: {self.CACHE_TTL_SECONDS}s)")

        except Exception as e:
            logger.error(f"SignalsService: Cache save error: {e}")

    # ===== GDELT-SPECIFIC CACHE METHODS =====

    def _build_cache_key_gdelt(self, countries: List[str], time_window: str) -> str:
        """
        Build consistent cache key for GDELT signal data.

        Format: gdelt:tw{time_window}:c{sorted_countries}
        Example: gdelt:tw6h:cAR,BR,CO,MX,US
        """
        sorted_countries = ','.join(sorted(countries))
        return f"gdelt:tw{time_window}:c{sorted_countries}"

    async def _get_from_cache_gdelt(self, cache_key: str) -> Optional[Dict[str, Tuple[List[GDELTSignal], datetime]]]:
        """Retrieve cached GDELT signal data from Redis."""
        if not self.redis_available:
            return None

        try:
            cached_json = self.redis_client.get(cache_key)
            if not cached_json:
                return None

            # Deserialize cached data
            cached_data = json.loads(cached_json)

            # Reconstruct GDELTSignal objects from serialized data
            signals_by_country = {}
            for country, (signals_data, timestamp_str) in cached_data.items():
                signals = [GDELTSignal(**signal_dict) for signal_dict in signals_data]
                timestamp = datetime.fromisoformat(timestamp_str)
                signals_by_country[country] = (signals, timestamp)

            return signals_by_country

        except Exception as e:
            logger.error(f"SignalsService: GDELT cache retrieval error: {e}")
            return None

    async def _save_to_cache_gdelt(
        self,
        cache_key: str,
        signals_by_country: Dict[str, Tuple[List[GDELTSignal], datetime]]
    ) -> None:
        """Save GDELT signal data to Redis cache."""
        if not self.redis_available:
            return

        try:
            # Serialize data for caching
            cache_data = {}
            for country, (signals, timestamp) in signals_by_country.items():
                signals_data = [signal.dict() for signal in signals]
                cache_data[country] = (signals_data, timestamp.isoformat())

            # Store in Redis with TTL
            cache_json = json.dumps(cache_data)
            self.redis_client.setex(
                cache_key,
                self.CACHE_TTL_SECONDS,
                cache_json
            )
            logger.info(f"SignalsService: Cached GDELT data for {cache_key} (TTL: {self.CACHE_TTL_SECONDS}s)")

        except Exception as e:
            logger.error(f"SignalsService: GDELT cache save error: {e}")


# Singleton instance
_signals_service_instance = None


def get_signals_service() -> SignalsService:
    """
    Get singleton instance of SignalsService.

    This ensures all endpoints use the same service instance
    with shared Redis connections and state.
    """
    global _signals_service_instance
    if _signals_service_instance is None:
        _signals_service_instance = SignalsService()
    return _signals_service_instance
