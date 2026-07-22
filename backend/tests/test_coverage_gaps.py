"""Coverage-gap service — the canonical 'what is a coverage gap' definition."""
import pytest

from app.services.coverage_gaps import (
    COUNTRY_GAPS_SQL,
    GLOBAL_GAP_FLOOR,
    GLOBAL_GAPS_SQL,
    country_gap_floor,
    fetch_coverage_gaps,
    gap_status,
)


class FakeConn:
    """Minimal asyncpg-conn stub: records the calls, returns canned rows."""

    def __init__(self, rows):
        self._rows = rows
        self.calls = []

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return self._rows


def test_gap_status_gate_pending_when_nothing_scored():
    assert gap_status(0) == "gate_pending"


def test_gap_status_none_verified_when_scored():
    assert gap_status(280) == "none_verified"


def test_country_gap_floor_defaults_to_8(monkeypatch):
    monkeypatch.delenv("ATLAS_COUNTRY_GAP_MIN", raising=False)
    assert country_gap_floor() == 8


def test_country_gap_floor_reads_env(monkeypatch):
    monkeypatch.setenv("ATLAS_COUNTRY_GAP_MIN", "15")
    assert country_gap_floor() == 15


@pytest.mark.asyncio
async def test_global_scope_uses_global_sql_and_floor():
    conn = FakeConn([
        {"slug": "telecom-shutdown", "label": "Telecom or internet shutdown",
         "raw_signals": 280, "verified": 0, "scored": 280},
    ])
    gaps = await fetch_coverage_gaps(conn, hours=24, with_receipts=False)

    sql, args = conn.calls[0]
    assert sql == GLOBAL_GAPS_SQL
    assert args == (24, GLOBAL_GAP_FLOOR)
    assert gaps == [{
        "slug": "telecom-shutdown",
        "label": "Telecom or internet shutdown",
        "raw_signals": 280,
        "verified": 0,
        "scored": 280,
        "status": "none_verified",
        "extended_receipts": [],
    }]


@pytest.mark.asyncio
async def test_country_scope_uses_country_sql_with_cc_and_floor(monkeypatch):
    monkeypatch.setenv("ATLAS_COUNTRY_GAP_MIN", "8")
    conn = FakeConn([
        {"slug": "mining-safety", "label": "Mining and resource safety crisis",
         "raw_signals": 12, "verified": 0, "scored": 0},
    ])
    gaps = await fetch_coverage_gaps(conn, hours=24, country="CO", with_receipts=False)

    sql, args = conn.calls[0]
    assert sql == COUNTRY_GAPS_SQL
    assert args == (24, "CO", 8)
    assert gaps[0]["status"] == "gate_pending"


@pytest.mark.asyncio
async def test_empty_window_returns_empty_list():
    conn = FakeConn([])
    assert await fetch_coverage_gaps(conn, hours=24, with_receipts=False) == []
