"""Coverage-gap service — the canonical 'what is a coverage gap' definition."""
import asyncio as real_asyncio
import sys
import types
from types import SimpleNamespace

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


class _FakeAcquire:
    async def __aenter__(self):
        class _C:
            async def execute(self, *a, **k):
                return None
        return _C()

    async def __aexit__(self, *a):
        return False


class _FakePool:
    def acquire(self):
        return _FakeAcquire()


class _FakeAcquireRaisesOnExit:
    """Simulates the real reachable failure mode behind the 1a fix: the query
    inside the `async with` block succeeds, but releasing the connection
    raises inside `__aexit__` (asyncpg terminates + re-raises on a failed
    reset — a genuine Supabase-pooler-drop mode)."""

    async def __aenter__(self):
        class _C:
            async def execute(self, *a, **k):
                return None
        return _C()

    async def __aexit__(self, *a):
        raise RuntimeError("connection reset failed")


class _FakePoolRaisesOnRelease:
    def acquire(self):
        return _FakeAcquireRaisesOnExit()


def _themes_stub(per_topic_ext, global_ext=1.0):
    """A fake `app.routers.themes` module exposing only what
    `fetch_extended_receipts_by_slug`'s lazy import needs — lets tests
    exercise that path without pulling in the real router (and its heavier
    import chain that this suite must not trigger)."""
    stub = types.ModuleType("app.routers.themes")
    stub._extended_gate_thresholds = lambda: (per_topic_ext, global_ext)
    return stub


def test_global_gap_floor_is_20():
    # The whole briefing-refactor equivalence hinges on this constant matching
    # the value the inline SQL used to hardcode. `args == (24, GLOBAL_GAP_FLOOR)`
    # assertions elsewhere are tautological on their own — they'd stay green
    # even if this constant silently changed the served payload. Pin the value.
    assert GLOBAL_GAP_FLOOR == 20


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


# --- Endpoint: GET /api/v2/attention/coverage-gaps -------------------------

@pytest.mark.asyncio
async def test_endpoint_returns_contract_and_global_scope(monkeypatch):
    from app.routers import attention_threads as at

    async def fake_fetch(conn, *, hours, country=None, **kw):
        return [{"slug": "cyber", "label": "Cyberattack on infrastructure",
                 "raw_signals": 189, "verified": 0, "scored": 189,
                 "status": "none_verified", "extended_receipts": []}]

    monkeypatch.setattr(at, "fetch_coverage_gaps", fake_fetch)
    # raising=False: `app.db` is shadowed by the sibling `app/db/` package on
    # this branch (both tracked since ancient commits bf037cf7/d2ae56cb; the
    # package wins CPython's package-vs-module resolution), so `db.pool` has no
    # attribute to overwrite until real app startup sets it dynamically.
    # test_thread_intelligence.py hits the same shadow via plain attribute
    # assignment; raising=False is the monkeypatch equivalent, with
    # auto-teardown. Unrelated to this endpoint or Task 1/2 — see all
    # `raising=False` call sites below.
    monkeypatch.setattr(at.db, "pool", _FakePool(), raising=False)

    out = await at.get_coverage_gaps(country=None, hours=24)
    assert out["contract"] == "coverage-gaps-v0"
    assert out["scope"] == "global"
    assert out["country"] is None
    assert out["status"] == "ok"
    assert out["gaps"][0]["slug"] == "cyber"


@pytest.mark.asyncio
async def test_endpoint_country_scope_uppercases_cc(monkeypatch):
    from app.routers import attention_threads as at
    seen = {}

    async def fake_fetch(conn, *, hours, country=None, **kw):
        seen["country"] = country
        seen["hours"] = hours
        return []

    monkeypatch.setattr(at, "fetch_coverage_gaps", fake_fetch)
    monkeypatch.setattr(at.db, "pool", _FakePool(), raising=False)  # see raising=False note above

    out = await at.get_coverage_gaps(country="co", hours=48)
    assert seen["country"] == "CO"
    assert seen["hours"] == 48  # hours must reach the service, not just the response echo
    assert out["hours"] == 48
    assert out["scope"] == "country"
    assert out["country"] == "CO"


@pytest.mark.asyncio
async def test_endpoint_degrades_when_db_unavailable(monkeypatch):
    from app.routers import attention_threads as at
    monkeypatch.setattr(at.db, "pool", None, raising=False)  # see raising=False note above

    out = await at.get_coverage_gaps(country=None, hours=24)
    assert out["gaps"] == []
    assert out["status"] == "degraded"
    assert "database unavailable" in out["notes"]


@pytest.mark.asyncio
async def test_endpoint_degrades_on_query_failure(monkeypatch):
    from app.routers import attention_threads as at

    async def boom(conn, *, hours, country=None, **kw):
        raise RuntimeError("statement timeout")

    monkeypatch.setattr(at, "fetch_coverage_gaps", boom)
    monkeypatch.setattr(at.db, "pool", _FakePool(), raising=False)  # see raising=False note above

    out = await at.get_coverage_gaps(country=None, hours=24)
    assert out["gaps"] == []
    assert out["status"] == "degraded"
    # Exact text, not a substring match on "unavailable" — the db-unavailable
    # branch's note also contains that word, so a mutant that routes this
    # scenario through the wrong branch must still be caught.
    assert "coverage gaps temporarily unavailable" in out["notes"]


@pytest.mark.asyncio
async def test_endpoint_gaps_reset_when_release_raises_after_success(monkeypatch):
    """Pins the docstring's promise: a degraded response ALWAYS carries
    `gaps: []`. The real reachable failure mode is the query succeeding
    (fetch_coverage_gaps returns real rows, assigning `gaps`) and THEN the
    connection release raising inside __aexit__ (asyncpg terminates +
    re-raises on a failed reset — a genuine Supabase-pooler-drop mode).
    Without the except-block reset, `gaps` would keep its populated value
    while `status` reports "degraded" — real gaps rendered under error
    chrome, which a frontend trusting `status` absolutely would miss."""
    from app.routers import attention_threads as at

    async def fake_fetch(conn, *, hours, country=None, **kw):
        return [{"slug": "cyber", "label": "Cyberattack on infrastructure",
                 "raw_signals": 189, "verified": 0, "scored": 189,
                 "status": "none_verified", "extended_receipts": []}]

    monkeypatch.setattr(at, "fetch_coverage_gaps", fake_fetch)
    monkeypatch.setattr(at.db, "pool", _FakePoolRaisesOnRelease(), raising=False)

    out = await at.get_coverage_gaps(country=None, hours=24)
    assert out["status"] == "degraded"
    assert out["gaps"] == []


@pytest.mark.asyncio
async def test_endpoint_degrades_when_query_exceeds_wall_clock_budget(monkeypatch):
    """Pins the `async with asyncio.timeout(10):` wall-clock bound — the fix
    for the most severe earlier finding. No committed test previously proved
    this line exists; removing it would leave every other test green. Uses
    the REAL timeout machinery with a tiny budget (monkeypatch the module's
    `asyncio` so `asyncio.timeout(10)` resolves to a real 0.05s timeout
    instead of the hardcoded 10s) against a fetch that sleeps well past it.

    Verified load-bearing by hand: with `async with asyncio.timeout(10):`
    temporarily removed from attention_threads.py (de-indenting the block
    beneath it), this test FAILS (status == "ok", gaps populated, no bound
    on the slow fetch); restoring the line makes it pass again."""
    from app.routers import attention_threads as at

    async def slow_fetch(conn, *, hours, country=None, **kw):
        await real_asyncio.sleep(1.0)  # far past the 0.05s budget below
        return [{"slug": "cyber", "label": "Cyberattack on infrastructure",
                 "raw_signals": 189, "verified": 0, "scored": 189,
                 "status": "none_verified", "extended_receipts": []}]

    monkeypatch.setattr(at, "fetch_coverage_gaps", slow_fetch)
    monkeypatch.setattr(at.db, "pool", _FakePool(), raising=False)
    monkeypatch.setattr(
        at, "asyncio",
        SimpleNamespace(timeout=lambda _seconds: real_asyncio.timeout(0.05)),
    )

    out = await at.get_coverage_gaps(country=None, hours=24)
    assert out["status"] == "degraded"
    assert out["gaps"] == []


@pytest.mark.asyncio
async def test_endpoint_honest_empty_global_scope_names_floor(monkeypatch):
    from app.routers import attention_threads as at

    async def fake_fetch(conn, *, hours, country=None, **kw):
        return []

    monkeypatch.setattr(at, "fetch_coverage_gaps", fake_fetch)
    monkeypatch.setattr(at.db, "pool", _FakePool(), raising=False)  # see raising=False note above

    out = await at.get_coverage_gaps(country=None, hours=24)
    assert out["status"] == "empty"
    assert out["floor"] == GLOBAL_GAP_FLOOR
    assert any(
        f"no category reached the {GLOBAL_GAP_FLOOR}-signal floor" in n
        for n in out["notes"]
    )
    # must NOT overclaim verified coverage for categories that never reached
    # the floor at all (those are unmeasured here, not "cleared the gate")
    assert not any("cleared the gate" in n for n in out["notes"])


@pytest.mark.asyncio
async def test_endpoint_honest_empty_country_scope_names_floor(monkeypatch):
    from app.routers import attention_threads as at
    monkeypatch.delenv("ATLAS_COUNTRY_GAP_MIN", raising=False)  # pin the default floor (8)

    async def fake_fetch(conn, *, hours, country=None, **kw):
        return []

    monkeypatch.setattr(at, "fetch_coverage_gaps", fake_fetch)
    monkeypatch.setattr(at.db, "pool", _FakePool(), raising=False)  # see raising=False note above

    out = await at.get_coverage_gaps(country="co", hours=24)
    assert out["status"] == "empty"
    assert out["floor"] == country_gap_floor() == 8
    assert any(
        "no category reached the 8-signal floor" in n for n in out["notes"]
    )
