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

    # Consumer tech / product news — classified as geopolitical noise (audit 2026-05-11)
    "macrumors.com",
    "9to5mac.com",
    "appleinsider.com",
    "iphoneincanada.ca",
    "phonearena.com",
    "gsmarena.com",
    "androidpolice.com",
    "androidauthority.com",
    "theverge.com",       # mix of tech/culture with minimal geopolitical signal
    "engadget.com",
    "gizmodo.com",
    "techradar.com",
    "tomsguide.com",
    "tomshardware.com",
    "pcmag.com",
    "cnet.com",           # consumer reviews, rarely geopolitical
    "zdnet.com",

    # Legal / personal injury / class action news (kratom, supplements, lawsuits)
    "drugwatch.com",
    "classaction.org",
    "legalnewsline.com",
    "topclassactions.com",
    "aboutlawsuits.com",
    "lawyersandsettlements.com",

    # Health supplements / alternative medicine noise
    "naturalnews.com",
    "greenmedinfo.com",
    "mercola.com",

    # Local US traffic / crime / weather aggregators
    "patch.com",
    "local10.com",
    "local12.com",
    "fox5atlanta.com",
    "fox5ny.com",
    "fox4news.com",
    "wkrn.com",
    "wsmv.com",
    "wvlt.tv",
    "wbir.com",

    # Sports leagues / fantasy
    "nfl.com",
    "nba.com",
    "mlb.com",
    "nhl.com",
    "espn.com",
    "cbssports.com",
    "si.com",
    "theathletic.com",

    # Entertainment streaming / gaming
    "ign.com",
    "gamespot.com",
    "kotaku.com",
    "polygon.com",
    "pcgamer.com",
    "screenrant.com",
    "collider.com",
    "rottentomatoes.com",
    "imdb.com",
    "deadline.com",
    "hollywoodreporter.com",
    "variety.com",
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
