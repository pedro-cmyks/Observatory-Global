"""Coverage-gap service — the canonical 'what is a coverage gap' definition."""
import sys
import types

import pytest

from app.services.coverage_gaps import (
    COUNTRY_GAPS_SQL,
    EXTENDED_RECEIPTS_SQL,
    GLOBAL_GAP_FLOOR,
    GLOBAL_GAPS_SQL,
    country_gap_floor,
    fetch_coverage_gaps,
    gap_status,
)


class FakeConn:
    """Minimal asyncpg-conn stub: records the calls, returns canned rows.

    SQL-aware: `rows` answers the primary gaps query (GLOBAL_GAPS_SQL /
    COUNTRY_GAPS_SQL); `receipts_by_slug` (optional) answers
    EXTENDED_RECEIPTS_SQL, keyed by the slug bound as its first argument. A
    value that is an Exception instance is raised instead of returned, so
    tests can exercise the per-slug failure guard. This makes the default
    with_receipts=True (production) path exercisable without a real DB.
    """

    def __init__(self, rows, receipts_by_slug=None):
        self._rows = rows
        self._receipts_by_slug = receipts_by_slug or {}
        self.calls = []
        self.timeouts = []

    async def fetch(self, sql, *args, **kwargs):
        self.calls.append((sql, args))
        self.timeouts.append(kwargs.get("timeout"))
        if sql == EXTENDED_RECEIPTS_SQL:
            slug = args[0]
            result = self._receipts_by_slug.get(slug, [])
            if isinstance(result, Exception):
                raise result
            return result
        return self._rows


def _themes_stub(per_topic_ext, global_ext=1.0):
    """A fake `app.routers.themes` module exposing only what
    `fetch_extended_receipts_by_slug`'s lazy import needs — lets tests
    exercise that path without pulling in the real router (and its heavier
    import chain that this suite must not trigger)."""
    stub = types.ModuleType("app.routers.themes")
    stub._extended_gate_thresholds = lambda: (per_topic_ext, global_ext)
    return stub


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


def test_country_gap_floor_falls_back_on_garbage_value(monkeypatch, caplog):
    monkeypatch.setenv("ATLAS_COUNTRY_GAP_MIN", "not-a-number")
    with caplog.at_level("WARNING"):
        assert country_gap_floor() == 8
    assert "ATLAS_COUNTRY_GAP_MIN" in caplog.text


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


# --- Blocker 2: country normalization -------------------------------------

@pytest.mark.asyncio
async def test_country_lowercase_and_whitespace_normalized_to_uppercase(monkeypatch):
    monkeypatch.setenv("ATLAS_COUNTRY_GAP_MIN", "8")
    conn = FakeConn([])
    await fetch_coverage_gaps(conn, hours=24, country=" co ", with_receipts=False)

    sql, args = conn.calls[0]
    assert sql == COUNTRY_GAPS_SQL
    assert args == (24, "CO", 8)


@pytest.mark.asyncio
async def test_country_empty_string_takes_global_path():
    conn = FakeConn([])
    await fetch_coverage_gaps(conn, hours=24, country="", with_receipts=False)

    sql, args = conn.calls[0]
    assert sql == GLOBAL_GAPS_SQL
    assert args == (24, GLOBAL_GAP_FLOOR)


# --- Blocker 1: timeout propagation ----------------------------------------

@pytest.mark.asyncio
async def test_timeout_defaults_to_none():
    conn = FakeConn([])
    await fetch_coverage_gaps(conn, hours=24, with_receipts=False)
    assert conn.timeouts == [None]


@pytest.mark.asyncio
async def test_timeout_forwarded_to_primary_and_receipts_queries(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "app.routers.themes", _themes_stub({"telecom-shutdown": 0.75})
    )
    gap_rows = [{"slug": "telecom-shutdown", "label": "Telecom or internet shutdown",
                 "raw_signals": 280, "verified": 0, "scored": 280}]
    conn = FakeConn(gap_rows, receipts_by_slug={"telecom-shutdown": []})

    await fetch_coverage_gaps(conn, hours=24, timeout=5.0)

    # one call for the primary gaps query, one for the receipts query
    assert conn.timeouts == [5.0, 5.0]


# --- Blocker 3: the default with_receipts=True path -------------------------

@pytest.mark.asyncio
async def test_receipts_attach_to_matching_gap_slug(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "app.routers.themes", _themes_stub({"telecom-shutdown": 0.75})
    )
    gap_rows = [{"slug": "telecom-shutdown", "label": "Telecom or internet shutdown",
                 "raw_signals": 280, "verified": 0, "scored": 280}]
    receipts = {"telecom-shutdown": [
        {"headline": "Regulator confirms nationwide telecom outage",
         "source": "Reuters", "url": "http://x", "gate_score": 0.81},
    ]}
    conn = FakeConn(gap_rows, receipts_by_slug=receipts)

    gaps = await fetch_coverage_gaps(conn, hours=24)  # with_receipts defaults True

    assert gaps[0]["slug"] == "telecom-shutdown"
    assert gaps[0]["extended_receipts"] == [{
        "headline": "Regulator confirms nationwide telecom outage",
        "source": "Reuters",
        "url": "http://x",
        "gate_score": 0.81,
        "tier": "extended",
    }]


@pytest.mark.asyncio
async def test_receipts_skipped_when_no_threshold_configured(monkeypatch):
    # no threshold configured for this slug at all
    monkeypatch.setitem(sys.modules, "app.routers.themes", _themes_stub({}))
    gap_rows = [{"slug": "mining-safety", "label": "Mining and resource safety crisis",
                 "raw_signals": 12, "verified": 0, "scored": 0}]
    conn = FakeConn(gap_rows, receipts_by_slug={
        "mining-safety": [{"headline": "Collapse reported at regional mine site",
                            "source": "AP", "url": "http://y", "gate_score": 0.9}],
    })

    gaps = await fetch_coverage_gaps(conn, hours=24)

    assert gaps[0]["extended_receipts"] == []
    # no threshold -> the receipts query for this slug is never even issued
    assert not any(sql == EXTENDED_RECEIPTS_SQL for sql, _args in conn.calls)


@pytest.mark.asyncio
async def test_receipts_guard_isolates_failure_per_gap(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "app.routers.themes",
        _themes_stub({"telecom-shutdown": 0.75, "mining-safety": 0.70}),
    )
    gap_rows = [
        {"slug": "telecom-shutdown", "label": "Telecom or internet shutdown",
         "raw_signals": 280, "verified": 0, "scored": 280},
        {"slug": "mining-safety", "label": "Mining and resource safety crisis",
         "raw_signals": 12, "verified": 0, "scored": 12},
    ]
    conn = FakeConn(gap_rows, receipts_by_slug={
        "telecom-shutdown": RuntimeError("db exploded"),
        "mining-safety": [{"headline": "Collapse reported at regional mine site",
                            "source": "AP", "url": "http://y", "gate_score": 0.9}],
    })

    gaps = await fetch_coverage_gaps(conn, hours=24)

    by_slug = {g["slug"]: g for g in gaps}
    assert by_slug["telecom-shutdown"]["extended_receipts"] == []
    assert by_slug["mining-safety"]["extended_receipts"][0]["headline"] == (
        "Collapse reported at regional mine site"
    )
