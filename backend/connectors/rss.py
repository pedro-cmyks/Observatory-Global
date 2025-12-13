"""
RSS Feed Connector

Connects to RSS/Atom feeds to fetch news articles.
Free fallback option that doesn't require an API key.

Requires RSS_FEEDS environment variable (comma-separated URLs).
"""

import os
import aiohttp
from datetime import datetime, timezone
from typing import Dict, AsyncIterator, Any, List
from urllib.parse import urlparse
import logging

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

from .base import BaseConnector, NormalizedSignal

logger = logging.getLogger(__name__)

# Load feed URLs from environment
_raw_feeds = os.getenv("RSS_FEEDS", "")
RSS_FEEDS: List[str] = [f.strip() for f in _raw_feeds.split(",") if f.strip()]


# Default feeds if none configured (major international news)
DEFAULT_RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.theguardian.com/world/rss",
    "https://feeds.reuters.com/reuters/worldNews",
]


class RSSConnector(BaseConnector):
    """
    Connector for RSS/Atom feeds.
    
    Features:
    - No API key required
    - Configurable feed list
    - Falls back to default major news feeds
    - Uses feedparser library
    
    Configuration:
        Set RSS_FEEDS environment variable with comma-separated feed URLs
        Or use default feeds if not set
    """
    
    def __init__(self, feed_urls: List[str] = None):
        if not FEEDPARSER_AVAILABLE:
            raise ImportError("feedparser package required for RSS connector")
        
        self.feed_urls = feed_urls or RSS_FEEDS or DEFAULT_RSS_FEEDS
    
    @property
    def name(self) -> str:
        return "rss"
    
    @property
    def description(self) -> str:
        return f"RSS Feed connector - {len(self.feed_urls)} feed(s) configured"
    
    def is_configured(self) -> bool:
        return bool(self.feed_urls) and FEEDPARSER_AVAILABLE
    
    async def fetch(self, since: datetime) -> AsyncIterator[Dict[str, Any]]:
        """
        Fetch entries from all configured RSS feeds.
        
        Yields entries published after 'since' timestamp.
        """
        async with aiohttp.ClientSession() as session:
            for feed_url in self.feed_urls:
                try:
                    async with session.get(
                        feed_url,
                        timeout=aiohttp.ClientTimeout(total=30),
                        headers={'User-Agent': 'Observatory-Global/1.0'}
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(f"RSS feed returned {resp.status}: {feed_url}")
                            continue
                        
                        content = await resp.text()
                        feed = feedparser.parse(content)
                        
                        if feed.bozo:
                            logger.warning(f"RSS parse error for {feed_url}: {feed.bozo_exception}")
                            continue
                        
                        for entry in feed.entries:
                            # Check if entry is newer than 'since'
                            entry_time = self._parse_entry_time(entry)
                            if entry_time and entry_time > since:
                                yield {
                                    "feed_url": feed_url,
                                    "feed_title": feed.feed.get("title", ""),
                                    "entry": entry
                                }
                                
                except aiohttp.ClientError as e:
                    logger.warning(f"Error fetching RSS feed {feed_url}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error for feed {feed_url}: {e}")
                    continue
    
    def _parse_entry_time(self, entry) -> datetime:
        """Parse publication time from RSS entry."""
        # Try various date fields
        for attr in ['published_parsed', 'updated_parsed', 'created_parsed']:
            if hasattr(entry, attr) and getattr(entry, attr):
                try:
                    time_struct = getattr(entry, attr)
                    return datetime(*time_struct[:6], tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
        
        return datetime.now(timezone.utc)
    
    def normalize(self, raw: Dict[str, Any]) -> NormalizedSignal:
        """
        Normalize an RSS entry to NormalizedSignal format.
        """
        entry = raw.get("entry", {})
        
        # Get URL
        url = entry.get("link", "")
        if not url:
            raise ValueError("RSS entry missing link")
        
        # Extract domain
        try:
            domain = urlparse(url).netloc
        except Exception:
            domain = raw.get("feed_title", "unknown")
        
        # Get publication time
        published_at = self._parse_entry_time(entry)
        
        # Get title
        title = entry.get("title", "")[:500] if entry.get("title") else ""
        
        # Get snippet from summary or description
        snippet = ""
        if entry.get("summary"):
            snippet = entry.get("summary", "")[:500]
        elif entry.get("description"):
            snippet = entry.get("description", "")[:500]
        
        # Strip HTML tags from snippet (basic)
        import re
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()
        
        return NormalizedSignal(
            source_url=url,
            source_domain=domain,
            title=title,
            snippet=snippet,
            published_at=published_at,
            country_codes=[],  # Would need NLP to extract
            themes=[],  # Would need NLP to extract
            persons=[],
            sentiment=0.0,
            raw_data=raw
        )
    
    def get_config(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "configured": self.is_configured(),
            "feedparser_available": FEEDPARSER_AVAILABLE,
            "feed_count": len(self.feed_urls),
            "feeds": self.feed_urls[:5] if len(self.feed_urls) <= 5 else self.feed_urls[:5] + ["..."]
        }
