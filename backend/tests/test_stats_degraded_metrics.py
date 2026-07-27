"""
/api/v2/stats must not publish query FAILURES as facts.

The silent-failure incident this freezes: two timed-out queries made the
endpoint serve ``unique_sources: 0`` and ``ingestion.status: 'stalled'`` while
/api/v2/briefing independently counted 49,466 sources — the health endpoint
itself manufactured a phantom outage, and the status flapped
stalled->healthy->stalled in ~36s as the timeouts came and went.

Contract: a failed query is ``null`` + a ``degraded_metrics`` entry. A MEASURED
zero stays ``0`` and is never listed as degraded.
"""
from __future__ import annotations

import pytest

from app.routers.stats import build_ingestion_status, fetch_metric


class FakeConn:
    """Minimal asyncpg-shaped stub: replays a scripted fetchval outcome."""

    def __init__(self, value=None, raises: Exception | None = None):
        self._value = value
        self._raises = raises
        self.calls = 0

    async def fetchval(self, query: str):
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return self._value


@pytest.mark.asyncio
async def test_failed_query_is_null_and_named_degraded():
    degraded: list[str] = []
    conn = FakeConn(raises=Exception("canceling statement due to statement timeout"))

    value = await fetch_metric(conn, degraded, "unique_sources", "SELECT 1", 0)

    # The failure must NOT become the factual zero that reads as "no sources".
    assert value is None
    assert degraded == ["unique_sources"]


@pytest.mark.asyncio
async def test_measured_zero_stays_zero_and_is_not_degraded():
    degraded: list[str] = []
    conn = FakeConn(value=0)

    value = await fetch_metric(conn, degraded, "unique_sources", "SELECT 1", 0)

    assert value == 0
    assert value is not None  # a real 0 is a fact, not an unknown
    assert degraded == []


@pytest.mark.asyncio
async def test_measured_value_passes_through():
    degraded: list[str] = []
    conn = FakeConn(value=49466)

    assert await fetch_metric(conn, degraded, "unique_sources", "SELECT 1", 0) == 49466
    assert degraded == []


@pytest.mark.asyncio
async def test_sql_null_falls_back_to_default_without_degrading():
    """No rows at all (e.g. empty table) is a measured emptiness, not a failure."""
    degraded: list[str] = []
    conn = FakeConn(value=None)

    assert await fetch_metric(conn, degraded, "oldest_signal", "SELECT 1", None) is None
    assert await fetch_metric(conn, degraded, "signals_1h", "SELECT 1", 0) == 0
    assert degraded == []


@pytest.mark.asyncio
async def test_degraded_metrics_accumulate_per_metric():
    degraded: list[str] = []
    boom = FakeConn(raises=Exception("timeout"))
    ok = FakeConn(value=12)

    await fetch_metric(boom, degraded, "unique_sources", "SELECT 1", 0)
    await fetch_metric(ok, degraded, "signals_1h", "SELECT 1", 0)
    await fetch_metric(boom, degraded, "signals_last_2h", "SELECT 1", 0)

    assert degraded == ["unique_sources", "signals_last_2h"]


def test_ingestion_status_unknown_when_count_failed():
    # The load-bearing assertion: a failed count must never read as 'stalled'.
    assert build_ingestion_status(None) == "unknown"


def test_ingestion_status_from_measured_counts():
    assert build_ingestion_status(0) == "stalled"      # measured zero = real stall
    assert build_ingestion_status(1) == "low"
    assert build_ingestion_status(100) == "low"        # boundary: not > 100
    assert build_ingestion_status(101) == "healthy"
