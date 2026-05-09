"""
Source domain blocklist for signal ingestion.

Domains here are filtered at parse time — no signal is inserted from them.
This targets known entertainment, tabloid, and low-quality domains that
flood the signal stream with noise unrelated to geopolitical narratives.

Investigation finding (2026-05-08): iHeart.com was Atlas's #1 global source
(4,695 signals/day) producing carnival stories tagged as "Manmade Disaster."
"""
from urllib.parse import urlparse

# Exact domain matches and suffix matches (e.g. "iheart.com" blocks k103.iheart.com)
_BLOCKED: frozenset[str] = frozenset({
    # Entertainment radio — #1 source of geopolitical noise
    "iheart.com",
    "iheartradio.com",

    # Celebrity / tabloid
    "tmz.com",
    "pagesix.com",
    "eonline.com",
    "radaronline.com",
    "thesun.co.uk",
    "dailystar.co.uk",
    "ok.co.uk",
    "hellomagazine.com",
    "people.com",
    "usmagazine.com",

    # Sports-only (not geopolitical)
    "bleacherreport.com",
    "sportingnews.com",

    # Podcast platforms (article text = episode descriptions)
    "audioboom.com",
    "podbean.com",
    "buzzsprout.com",

    # SEO/content farm patterns
    "prweb.com",
    "prnewswire.com",   # press releases — low editorial signal
    "businesswire.com",
    "globenewswire.com",
    "accesswire.com",
})


def is_blocked(url: str) -> bool:
    """Return True if this URL's domain is on the blocklist."""
    if not url:
        return False
    try:
        host = urlparse(url).netloc.lower()
        # Strip www. and port
        host = host.removeprefix("www.").split(":")[0]
        # Exact match or subdomain suffix match
        return host in _BLOCKED or any(
            host.endswith("." + blocked) for blocked in _BLOCKED
        )
    except Exception:
        return False
