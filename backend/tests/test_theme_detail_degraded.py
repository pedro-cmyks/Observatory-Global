"""Timeout-as-absence in the theme detail handler.

Bug: `get_theme_details` wraps its queries in a broad ``except`` that turns a
query timeout into ``total: 0`` with no degraded flag — a timeout renders as
the measured claim "0 signals". Reproduced repeatedly under DB load
(concurrent build saturating Supabase, responses 27-113s). Same class already
fixed in search (cc0bf804) and the focus timeline (A4 reason codes).

Contract (mirrors /api/v2/stats): on timeout/error serve ``total: null`` +
``degraded: true`` + a reason code — never a fabricated number, never the raw
exception string (db_error never reaches the screen).
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import asyncpg
import pytest

import app.main_v2  # noqa: F401 — initialize app + routers before importing themes
from app import db
from app.routers import themes


class _ExplodingConn:
    """Every query raises — models a saturated database."""

    def __init__(self, exc: Exception):
        self._exc = exc

    async def execute(self, *args, **kwargs):
        raise self._exc

    async def fetchrow(self, *args, **kwargs):
        raise self._exc

    async def fetchval(self, *args, **kwargs):
        raise self._exc

    async def fetch(self, *args, **kwargs):
        raise self._exc


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self._conn


def _run(theme_code: str = "dynamic-topic-99", hours: int = 24):
    return asyncio.run(
        themes.get_theme_details(theme_code, country_code=None, hours=hours)
    )


def _install(monkeypatch, exc: Exception):
    monkeypatch.setattr(db, "pool", _FakePool(_ExplodingConn(exc)))


@pytest.mark.parametrize(
    "exc",
    [
        asyncio.TimeoutError(),
        TimeoutError(),
        asyncpg.exceptions.QueryCanceledError(
            "canceling statement due to statement timeout"
        ),
    ],
    ids=["asyncio-timeout", "builtin-timeout", "statement-timeout"],
)
def test_timeout_serves_null_total_with_degraded_reason(monkeypatch, exc):
    """A timed-out count is NOT MEASURED — never the measured claim 0."""
    _install(monkeypatch, exc)

    result = _run()

    assert result["total"] is None
    assert result["avgSentiment"] is None
    assert result["degraded"] is True
    assert result["degraded_reason"] == "db_timeout"
    assert result["signals"] == []


def test_generic_db_error_serves_null_total_with_db_error_reason(monkeypatch):
    _install(monkeypatch, RuntimeError("connection is closed"))

    result = _run()

    assert result["total"] is None
    assert result["avgSentiment"] is None
    assert result["degraded"] is True
    assert result["degraded_reason"] == "db_error"


def test_degraded_payload_never_leaks_raw_exception_text(monkeypatch):
    """Raw driver internals must not reach the client (lensErrorCopy rule)."""
    secret = "SELECT * FROM signals_v2 WHERE secret_predicate"
    _install(monkeypatch, RuntimeError(secret))

    result = _run()

    assert secret not in str(result)


def test_degraded_payload_keeps_contract_shape(monkeypatch):
    """Existing consumers iterate these arrays — shape survives degradation."""
    _install(monkeypatch, TimeoutError())

    result = _run(theme_code="armed-conflict-escalation", hours=48)

    for key in (
        "theme", "country", "hours", "signals", "countryBreakdown",
        "relatedThemes", "topSources", "topPersons", "timeline",
        "countryFraming",
    ):
        assert key in result, f"missing {key}"
    assert result["theme"] == "armed-conflict-escalation"
    assert result["hours"] == 48
