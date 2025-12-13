"""
NewsAPI Connector

Connects to NewsAPI.org to fetch news articles.
Provides title and snippet directly (unlike GDELT which requires fetching).

Requires NEWSAPI_KEY environment variable.
"""

import os
import aiohttp
from datetime import datetime, timezone
from typing import Dict, AsyncIterator, Any
from urllib.parse import urlparse

from .base import BaseConnector, NormalizedSignal


# Check if API key is available
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_ENABLED = bool(NEWSAPI_KEY)


class NewsAPIConnector(BaseConnector):
    """
    Connector for NewsAPI.org
    
    Features:
    - Provides titles and snippets directly
    - Wide source coverage
    - Rate limited on free tier
    
    Requires: NEWSAPI_KEY environment variable
    """
    
    def __init__(self):
        if not NEWSAPI_KEY:
            raise ValueError("NEWSAPI_KEY environment variable is required")
        self.api_key = NEWSAPI_KEY
        self.base_url = "https://newsapi.org/v2"
    
    @property
    def name(self) -> str:
        return "newsapi"
    
    @property
    def description(self) -> str:
        return "NewsAPI.org - Global news aggregator with 150,000+ sources"
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def fetch(self, since: datetime) -> AsyncIterator[Dict[str, Any]]:
        """
        Fetch articles from NewsAPI.
        
        Uses the 'everything' endpoint for broad coverage.
        """
        params = {
            "apiKey": self.api_key,
            "from": since.isoformat(),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 100
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/everything",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 401:
                        raise ValueError("Invalid NewsAPI key")
                    if resp.status == 429:
                        raise ValueError("NewsAPI rate limit exceeded")
                    if resp.status != 200:
                        return
                    
                    data = await resp.json()
                    
                    if data.get("status") != "ok":
                        return
                    
                    for article in data.get("articles", []):
                        yield article
                        
        except aiohttp.ClientError:
            return
    
    def normalize(self, raw: Dict[str, Any]) -> NormalizedSignal:
        """
        Normalize a NewsAPI article to NormalizedSignal format.
        """
        url = raw.get("url", "")
        if not url:
            raise ValueError("Article missing URL")
        
        # Extract domain
        try:
            domain = urlparse(url).netloc
        except Exception:
            domain = raw.get("source", {}).get("name", "unknown")
        
        # Parse publication date
        published_str = raw.get("publishedAt", "")
        try:
            if published_str:
                # Handle ISO format with Z suffix
                published_at = datetime.fromisoformat(
                    published_str.replace("Z", "+00:00")
                )
            else:
                published_at = datetime.now(timezone.utc)
        except ValueError:
            published_at = datetime.now(timezone.utc)
        
        # Get title and description
        title = raw.get("title", "")[:500] if raw.get("title") else ""
        description = raw.get("description", "")[:500] if raw.get("description") else ""
        
        # NewsAPI doesn't provide country codes directly
        # Would need NLP or geo-lookup to extract
        country_codes = []
        
        # No themes from NewsAPI - would need NLP extraction
        themes = []
        
        return NormalizedSignal(
            source_url=url,
            source_domain=domain,
            title=title,
            snippet=description,
            published_at=published_at,
            country_codes=country_codes,
            themes=themes,
            persons=[],
            sentiment=0.0,  # Would need sentiment analysis
            raw_data=raw
        )
    
    def get_config(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "configured": self.is_configured(),
            "api_key_set": bool(self.api_key),
            "api_key_preview": f"{self.api_key[:4]}..." if self.api_key else "not set"
        }
