"""Phase 0.5 — list/detail reconciliation for atlas-topic threads.

Bug: `/api/v2/threads?country_code=IR` lists `flood-landslide-disaster--ir`
with N signals (counted from `signal_topic_assignments`), but
`/api/v2/theme/flood-landslide-disaster?hours=168&country_code=IR` returned
`total=0` because long windows force the `historical_topic_country_daily`
branch, which has no row for that atlas slug. A thread that lists with N
signals must never open to 0 without an explicit gap explanation.

Fix: when the historical branch is empty for an atlas slug, fall back to the
atlas-topic assignment resolver (`_atlas_topic_detail`) — the same source the
thread list counts — before declaring zero.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import pytest

import app.main_v2  # noqa: F401 — initialize app + routers before importing themes
from app import db
from app.routers import themes


class _FakeConn:
    def __init__(self, atlas_row):
        self._atlas_row = atlas_row

    async def execute(self, *args, **kwargs):
        return None

    async def fetchrow(self, query, *args, **kwargs):
        if "FROM atlas_topics" in query:
            return self._atlas_row
        return None

    async def fetchval(self, *args, **kwargs):
        return None

    async def fetch(self, *args, **kwargs):
        return []


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self._conn


def _install(monkeypatch, *, atlas_row, atlas_detail_result):
    monkeypatch.setattr(db, "pool", _FakePool(_FakeConn(atlas_row)), raising=False)
    # Long window -> historical branch fires; force it empty.
    monkeypatch.setattr(themes, "use_processed_history", lambda hours: True)

    async def _empty_historical(*args, **kwargs):
        return None

    monkeypatch.setattr(themes, "query_historical_topic_detail", _empty_historical)

    captured = {}

    async def _fake_atlas_detail(conn, *, topic_id, slug, label, hours, country_code=None):
        captured.update(
            topic_id=topic_id, slug=slug, label=label,
            hours=hours, country_code=country_code,
        )
        return atlas_detail_result

    monkeypatch.setattr(themes, "_atlas_topic_detail", _fake_atlas_detail)

    class _Coverage:
        def to_dict(self):
            return {"from": None, "to": None, "row_count": 0}

    async def _fake_coverage(conn, *, hours):
        return _Coverage()

    monkeypatch.setattr(themes, "build_historical_coverage", _fake_coverage)
    return captured


def test_atlas_slug_thread_detail_reconciles_through_assignments(monkeypatch):
    """Empty historical + a known atlas slug -> resolve via assignments, not 0."""
    sentinel = {"theme": "flood-landslide-disaster", "total": 176,
                "source": "atlas_topic_gated"}
    captured = _install(
        monkeypatch,
        atlas_row={"id": 7, "slug": "flood-landslide-disaster",
                   "label": "Flood and landslide disaster"},
        atlas_detail_result=sentinel,
    )

    result = asyncio.run(
        themes.get_theme_details(
            "flood-landslide-disaster", country_code="IR", hours=168,
        )
    )

    assert result is sentinel
    assert result["total"] == 176
    assert captured["topic_id"] == 7
    assert captured["slug"] == "flood-landslide-disaster"
    assert captured["country_code"] == "IR"
    assert captured["hours"] == 168


def test_atlas_slug_unknown_returns_explained_empty(monkeypatch):
    """Empty historical + no matching atlas slug -> honest empty with explanation."""
    _install(
        monkeypatch,
        atlas_row=None,
        atlas_detail_result={"should": "not be used"},
    )

    result = asyncio.run(
        themes.get_theme_details(
            "not-a-real-topic", country_code="IR", hours=168,
        )
    )

    assert result["total"] == 0
    assert result["source"] == "historical_topic_country_daily"
    assert "no_processed_topic_history" in result["warnings"]


def test_thread_id_with_country_suffix_resolves_atlas_branch(monkeypatch):
    """'slug--cc' thread ids must parse to (slug, country) before the atlas
    lookup — Pedro's 2026-06-12 PE review: 'election-legitimacy-dispute--pe'
    listed 48 signals, opened to 0 because the suffixed id missed
    atlas_topics.slug and fell through to the GDELT path."""
    sentinel = {"theme": "election-legitimacy-dispute", "total": 48,
                "source": "atlas_topic_gated"}
    captured = _install(
        monkeypatch,
        atlas_row={"id": 9, "slug": "election-legitimacy-dispute",
                   "label": "Election legitimacy dispute"},
        atlas_detail_result=sentinel,
    )

    result = asyncio.run(
        themes.get_theme_details(
            "election-legitimacy-dispute--pe", country_code=None, hours=168,
        )
    )

    assert result is sentinel
    assert captured["slug"] == "election-legitimacy-dispute"
    # Single-country suffix scopes the detail to that country.
    assert captured["country_code"] == "PE"


def test_thread_id_multi_country_suffix_stays_global(monkeypatch):
    """Multi-country ids ('slug--us-ir-sa') strip the suffix but do not force
    a single-country filter — the thread is global."""
    sentinel = {"theme": "currency-debt-stress", "total": 409,
                "source": "atlas_topic_gated"}
    captured = _install(
        monkeypatch,
        atlas_row={"id": 4, "slug": "currency-debt-stress",
                   "label": "Currency and debt stress"},
        atlas_detail_result=sentinel,
    )

    result = asyncio.run(
        themes.get_theme_details(
            "currency-debt-stress--us-ir-sa", country_code=None, hours=168,
        )
    )

    assert result is sentinel
    assert captured["slug"] == "currency-debt-stress"
    assert captured["country_code"] is None


def test_thread_id_explicit_country_param_wins(monkeypatch):
    """An explicit country_code query param overrides the id suffix."""
    sentinel = {"theme": "election-legitimacy-dispute", "total": 5,
                "source": "atlas_topic_gated"}
    captured = _install(
        monkeypatch,
        atlas_row={"id": 9, "slug": "election-legitimacy-dispute",
                   "label": "Election legitimacy dispute"},
        atlas_detail_result=sentinel,
    )

    asyncio.run(
        themes.get_theme_details(
            "election-legitimacy-dispute--pe", country_code="co", hours=168,
        )
    )

    assert captured["country_code"] == "CO"
