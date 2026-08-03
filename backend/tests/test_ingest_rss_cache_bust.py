"""Stuck-feed-cache bypass (#235, sana.sy): the origin page cache served a
copy of /en/feed/ frozen at 2026-07-28 while the site kept publishing, so
every item fell outside the 2h overlap window and the feed yielded zero
signals. Fix: feeds listed in _CACHE_BUST_FEEDS get a timestamped, otherwise
unrecognized query param appended per fetch — measured to bypass the cache
where known params (?feed=rss2) and Cache-Control request headers do not."""
import asyncio
import re
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from app.services.ingest_rss import (
    CURATED_FEEDS,
    _CACHE_BUST_FEEDS,
    _cache_bust,
    fetch_feed,
)


def test_cache_bust_appends_param_to_bare_url():
    busted = _cache_bust("https://sana.sy/en/feed/")
    assert re.fullmatch(r"https://sana\.sy/en/feed/\?_cb=\d+", busted)


def test_cache_bust_appends_with_ampersand_when_query_exists():
    busted = _cache_bust("https://example.com/?feed=rss2")
    assert re.fullmatch(r"https://example\.com/\?feed=rss2&_cb=\d+", busted)


def test_sana_sy_uses_canonical_feed_url_and_is_cache_busted():
    url, family, cc, lang, is_state = CURATED_FEEDS["sana_sy"]
    # canonical path — the old /en/?feed=rss2 form 301'd onto the stuck copy
    assert url == "https://sana.sy/en/feed/"
    assert (family, cc, lang, is_state) == ("state", "SY", "en", True)
    assert "sana_sy" in _CACHE_BUST_FEEDS


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body
        self.status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def read(self):
        return self._body


class _FakeSession:
    def __init__(self, body: bytes):
        self._body = body
        self.requested_urls: list[str] = []

    def get(self, url, *a, **k):
        self.requested_urls.append(url)
        return _FakeResp(self._body)


def _rss_body(pub_time: datetime) -> bytes:
    return f"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>SANA</title>
<item>
  <title>Test headline from Damascus</title>
  <link>https://sana.sy/en/syria/999001/</link>
  <pubDate>{format_datetime(pub_time)}</pubDate>
  <description>body</description>
</item>
</channel></rss>""".encode()


def test_fetch_feed_requests_cache_busted_url_and_still_parses():
    fresh = datetime.now(timezone.utc) - timedelta(minutes=10)
    session = _FakeSession(_rss_body(fresh))
    since = datetime.now(timezone.utc) - timedelta(hours=2)

    signals = asyncio.run(fetch_feed(
        session, "sana_sy", "https://sana.sy/en/feed/",
        "state", "SY", "en", True, since,
    ))

    assert len(session.requested_urls) == 1
    assert re.fullmatch(
        r"https://sana\.sy/en/feed/\?_cb=\d+", session.requested_urls[0]
    )
    # the buster must not break parsing or attribution
    assert len(signals) == 1
    s = signals[0]
    assert s["source_url"] == "https://sana.sy/en/syria/999001/"
    assert s["source_name"] == "sana.sy"
    assert s["source_origin_country"] == "SY"
    assert s["is_state_media"] is True
    assert s["source_family"] == "state"


def test_fetch_feed_leaves_unlisted_feeds_untouched():
    fresh = datetime.now(timezone.utc) - timedelta(minutes=10)
    session = _FakeSession(_rss_body(fresh))
    since = datetime.now(timezone.utc) - timedelta(hours=2)

    asyncio.run(fetch_feed(
        session, "granma_cu", "http://www.granma.cu/feed",
        "state", "CU", "es", True, since,
    ))

    assert session.requested_urls == ["http://www.granma.cu/feed"]
