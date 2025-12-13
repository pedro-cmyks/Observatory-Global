"""
Title and Snippet Fetcher

Fetches HTML titles and meta descriptions from source URLs
with caching and rate limiting.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import logging
from collections import deque

logger = logging.getLogger(__name__)

# In-memory cache (would use Redis in production)
_title_cache: Dict[str, Tuple[Tuple[Optional[str], Optional[str]], datetime]] = {}
_CACHE_TTL = timedelta(hours=24)

# Rate limiting
_RATE_LIMIT_PER_MINUTE = 30
_request_times: deque = deque(maxlen=_RATE_LIMIT_PER_MINUTE)


def _is_rate_limited() -> bool:
    """Check if we've exceeded the rate limit."""
    now = datetime.utcnow()
    # Remove requests older than 1 minute
    while _request_times and (now - _request_times[0]) > timedelta(minutes=1):
        _request_times.popleft()
    return len(_request_times) >= _RATE_LIMIT_PER_MINUTE


def _record_request():
    """Record a request for rate limiting."""
    _request_times.append(datetime.utcnow())


def get_cached(url: str) -> Optional[Tuple[Optional[str], Optional[str]]]:
    """
    Get cached title/snippet for a URL if available and not expired.
    
    Returns:
        (title, snippet) tuple if cached, None if not cached or expired
    """
    if url not in _title_cache:
        return None
    
    cached_value, cached_at = _title_cache[url]
    if datetime.utcnow() - cached_at > _CACHE_TTL:
        # Expired
        del _title_cache[url]
        return None
    
    return cached_value


def set_cached(url: str, title: Optional[str], snippet: Optional[str]):
    """Cache a title/snippet result."""
    _title_cache[url] = ((title, snippet), datetime.utcnow())


async def fetch_title_and_snippet(
    url: str,
    timeout_seconds: int = 10
) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch HTML title and meta description from a URL.
    
    Features:
    - In-memory caching (24h TTL)
    - Rate limiting (30 requests/minute)
    - Timeout handling
    - Error resilience
    
    Args:
        url: The URL to fetch
        timeout_seconds: Request timeout
    
    Returns:
        (title, snippet) tuple, or (None, None) on failure
    """
    # Check cache first
    cached = get_cached(url)
    if cached is not None:
        logger.debug(f"Cache hit for {url}")
        return cached
    
    # Check rate limit
    if _is_rate_limited():
        logger.warning(f"Rate limit reached, skipping fetch for {url}")
        return None, None
    
    _record_request()
    
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        headers = {
            'User-Agent': 'Observatory-Global/1.0 (https://observatory.example.com)',
            'Accept': 'text/html,application/xhtml+xml',
        }
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                if resp.status != 200:
                    logger.debug(f"Non-200 status ({resp.status}) for {url}")
                    set_cached(url, None, None)
                    return None, None
                
                # Check content type
                content_type = resp.headers.get('Content-Type', '')
                if 'text/html' not in content_type.lower():
                    logger.debug(f"Non-HTML content type for {url}")
                    set_cached(url, None, None)
                    return None, None
                
                # Read and parse HTML
                html = await resp.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = None
        if soup.title and soup.title.string:
            title = soup.title.string.strip()[:500]
        elif soup.find('meta', property='og:title'):
            og_title = soup.find('meta', property='og:title')
            title = og_title.get('content', '')[:500] if og_title else None
        
        # Extract snippet (meta description)
        snippet = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            snippet = meta_desc['content'].strip()[:500]
        elif soup.find('meta', property='og:description'):
            og_desc = soup.find('meta', property='og:description')
            snippet = og_desc.get('content', '')[:500] if og_desc else None
        
        # Cache and return
        set_cached(url, title, snippet)
        logger.debug(f"Fetched title for {url}: {title[:50] if title else 'None'}...")
        
        return title, snippet
        
    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching {url}")
        return None, None
    except aiohttp.ClientError as e:
        logger.warning(f"Client error fetching {url}: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Error fetching title for {url}: {e}")
        return None, None


async def fetch_titles_batch(
    urls: list,
    max_concurrent: int = 5
) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    """
    Fetch titles for multiple URLs with concurrency limit.
    
    Args:
        urls: List of URLs to fetch
        max_concurrent: Maximum concurrent requests
    
    Returns:
        Dict mapping URL to (title, snippet) tuple
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results = {}
    
    async def fetch_with_semaphore(url: str):
        async with semaphore:
            result = await fetch_title_and_snippet(url)
            results[url] = result
    
    await asyncio.gather(*[fetch_with_semaphore(url) for url in urls])
    return results


def get_cache_stats() -> dict:
    """Get statistics about the cache."""
    now = datetime.utcnow()
    valid_count = sum(
        1 for url, (_, cached_at) in _title_cache.items()
        if now - cached_at <= _CACHE_TTL
    )
    
    return {
        "total_cached": len(_title_cache),
        "valid_cached": valid_count,
        "rate_limit_used": len(_request_times),
        "rate_limit_max": _RATE_LIMIT_PER_MINUTE
    }


def clear_cache():
    """Clear the title cache."""
    _title_cache.clear()
    logger.info("Title cache cleared")
