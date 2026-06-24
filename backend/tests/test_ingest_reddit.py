"""Reddit social-signal ingestion — credential-free combined-RSS parse path.

Reddit's JSON Data API now requires OAuth + (since Nov-2025) pre-approval, but
the per-subreddit Atom feed `/r/<sub>/.rss` is a built-in, credential-free
surface that still returns 200 to a browser User-Agent. To dodge per-IP rate
limiting we fetch a COMBINED feed `/r/a+b+c/.rss` (one request) and recover each
entry's origin subreddit from its <category term>. These tests prove that
mapping + signal shaping without any network or credentials; the verified INSERT
(idx_signals_v2_source_url_unique backs the ON CONFLICT) is exercised live.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta

from app.services import ingest_reddit
from app.services.ingest_reddit import (
    SUBREDDITS,
    _fetch_chunk,
    reddit_enabled,
)


def _atom(entries: list[dict]) -> bytes:
    """Build a minimal Reddit-style combined Atom feed. Each entry dict needs
    title/link/published/sub (sub → the <category term>)."""
    items = []
    for e in entries:
        ts = e["published"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        items.append(
            f"<entry><author><name>/u/x</name></author>"
            f"<category term='{e['sub']}' label='r/{e['sub']}'/>"
            f"<content type='html'>submitted by /u/x</content>"
            f"<id>t3_{e.get('id','abc')}</id>"
            f"<link href='{e['link']}' />"
            f"<updated>{ts}</updated><published>{ts}</published>"
            f"<title>{e['title']}</title></entry>"
        )
    body = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<feed xmlns='http://www.w3.org/2005/Atom'>"
        "<title>combined</title>" + "".join(items) + "</feed>"
    )
    return body.encode("utf-8")


class _FakeResp:
    def __init__(self, body: bytes, status=200):
        self._body = body
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def read(self):
        return self._body


class _FakeSession:
    def __init__(self, body: bytes, status=200):
        self._body = body
        self._status = status

    def get(self, *a, **k):
        return _FakeResp(self._body, self._status)


def _run(body, subs, since, status=200):
    session = _FakeSession(body, status)
    return asyncio.run(_fetch_chunk(session, subs, since))


def test_reddit_enabled_by_default_no_creds(monkeypatch):
    # Credential-free RSS: enabled unless the explicit kill-switch is set.
    monkeypatch.setattr(ingest_reddit, "REDDIT_INGEST_ENABLED", True)
    assert reddit_enabled() is True
    monkeypatch.setattr(ingest_reddit, "REDDIT_INGEST_ENABLED", False)
    assert reddit_enabled() is False


def test_subreddits_config_is_sane():
    assert SUBREDDITS, "subreddit watchlist is empty"
    for name, country, family in SUBREDDITS:
        assert isinstance(name, str) and name
        assert country is None or (isinstance(country, str) and len(country) == 2)
        assert family == "social"


def test_atom_entry_parses_into_social_signal():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=2)
    body = _atom([{
        "title": "Ukraine reports new strikes near Kharkiv", "sub": "worldnews",
        "link": "https://www.reddit.com/r/worldnews/comments/a/strikes/",
        "published": now - timedelta(minutes=10),
    }])

    signals = _run(body, ["worldnews"], since)

    assert len(signals) == 1
    s = signals[0]
    assert s["source_name"] == "reddit/r/worldnews"
    assert s["source_family"] == "social"
    # Reddit is commentary, not corroboration — provenance must say so.
    assert s["signal_class"] == "social_commentary"
    assert s["attribution_method"] == "reddit_rss"
    assert s["headline"] == "Ukraine reports new strikes near Kharkiv"
    assert s["source_url"] == "https://www.reddit.com/r/worldnews/comments/a/strikes/"
    # extract_country found UA from "Ukraine"/"Kharkiv"; never XX when matched.
    assert s["country_code"] == "UA"


def test_combined_feed_maps_each_entry_to_its_subreddit():
    # One request, two subs mixed — each entry routed by its <category term>.
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=2)
    body = _atom([
        {"title": "debate over zoning rules", "sub": "colombia",  # no geo token
         "link": "https://www.reddit.com/r/colombia/comments/z/zoning/",
         "published": now - timedelta(minutes=5)},
        {"title": "parliament vote on budget", "sub": "Venezuela",  # no geo token
         "link": "https://www.reddit.com/r/Venezuela/comments/v/budget/",
         "published": now - timedelta(minutes=5)},
    ])

    signals = _run(body, ["colombia", "Venezuela"], since)
    by_url = {s["source_url"]: s for s in signals}
    co = by_url["https://www.reddit.com/r/colombia/comments/z/zoning/"]
    ve = by_url["https://www.reddit.com/r/Venezuela/comments/v/budget/"]
    # default_country recovered from the per-entry subreddit tag.
    assert co["country_code"] == "CO"
    assert co["source_name"] == "reddit/r/colombia"
    assert ve["country_code"] == "VE"
    assert ve["source_name"] == "reddit/r/Venezuela"


def test_old_posts_are_skipped():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=2)
    body = _atom([
        {"title": "stale headline", "sub": "worldnews",
         "link": "https://www.reddit.com/r/worldnews/comments/o/old/",
         "published": now - timedelta(hours=5)},          # < since → dropped
        {"title": "kept headline", "sub": "worldnews",
         "link": "https://www.reddit.com/r/worldnews/comments/k/kept/",
         "published": now - timedelta(minutes=5)},
    ])

    signals = _run(body, ["worldnews"], since)
    assert [s["headline"] for s in signals] == ["kept headline"]


def test_429_skips_without_retry_and_returns_empty():
    # 429 must be a clean skip (no retry — retrying escalates the IP penalty).
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=2)
    signals = _run(b"", ["worldnews"], since, status=429)
    assert signals == []


def test_non_200_returns_no_signals():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=2)
    assert _run(b"", ["worldnews"], since, status=403) == []
