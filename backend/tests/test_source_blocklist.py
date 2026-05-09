"""Tests for source domain blocklist."""
import pytest
from app.config.source_blocklist import is_blocked


@pytest.mark.parametrize("url,expected", [
    # iHeart subdomain variants
    ("https://k103.iheart.com/content/2026-05-08-youngboy-never-broke-again", True),
    ("https://twincitiesnewstalk.iheart.com/content/2026-05-08-unruly-teens", True),
    ("https://www.iheart.com/podcast/1234", True),
    # Other blocked entertainment domains
    ("https://tmz.com/2026/05/08/celebrity-news/", True),
    ("https://www.eonline.com/news/1234", True),
    ("https://pagesix.com/2026/05/08/story", True),
    ("https://prweb.com/releases/2026/story.html", True),
    # Press releases — blocked
    ("https://www.prnewswire.com/news-releases/2026-05-01", True),
    ("https://www.businesswire.com/news/home/2026/story", True),
    # Legitimate news — NOT blocked
    ("https://www.bbc.com/news/world-middle-east-12345", False),
    ("https://aljazeera.com/news/2026/5/8/iran-story", False),
    ("https://reuters.com/world/iran-2026-05-08", False),
    ("https://nytimes.com/2026/05/08/world/", False),
    ("https://gcaptain.com/strait-of-hormuz-tanker/", False),
    ("https://dw.com/en/canvas-cyberattack/a-12345", False),
    # Edge cases
    ("", False),
    (None, False),  # type: ignore[arg-type]
    ("not-a-url", False),
])
def test_is_blocked(url, expected):
    assert is_blocked(url) is expected


def test_blocked_does_not_catch_similar_domains():
    """Domains that contain a blocked name but are not actually blocked."""
    # "iheartlocal.org" is not iheart.com
    assert is_blocked("https://iheartlocal.org/news/story") is False
    # "newsun.com" is not thesun.co.uk
    assert is_blocked("https://newsun.com/article") is False
