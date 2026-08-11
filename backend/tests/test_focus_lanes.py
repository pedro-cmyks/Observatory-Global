"""Council R4 DESKTOP-N26 — `/api/v2/focus` must never hang, never 500, and
never report an unmeasured lane as zero.

The defect: six unbounded lanes on one connection, each carrying an
unindexable person predicate, behind a frontend skeleton with no time bound
(45-120s mute). The fix has two halves and this file freezes both —

  1. the predicate is spelled the way migration 090 indexed it, so the
     planner can use `idx_signals_v2_persons_text_trgm` (measured: nodes
     lane 576ms warm for `%trump%` vs a seq scan before);
  2. every lane runs under a statement_timeout inside a global deadline and
     degrades to a NAMED reason instead of holding the request open.

Pure machinery (`app.services.focus_lanes`) is exercised directly with fakes
— no DB — mirroring `test_focus_timeline.py`'s style. The router gets
fake-conn integration tests mirroring `test_edge_diff.py`'s
`_FakeConn`/`_FakePool` pattern.
"""
from __future__ import annotations

import asyncio

import asyncpg
import pytest

import app.main_v2  # noqa: F401 — initialize app + routers FIRST. `app.routers.
                     # themes` does `from app.main_v2 import app` (the
                     # geo.py/threads.py cache-access idiom); importing the full
                     # app module here avoids the partial-module circular-import
                     # trap.
from app import db
from app.routers import themes as themes_mod
from app.services.focus_lanes import (
    GLOBAL_DEADLINE_MS,
    LANE_BUDGETS_MS,
    LANE_DEGRADED,
    LANE_LIVE,
    LANE_ORDER,
    PERSON_MATCH_EXPR,
    LaneRunner,
    person_like_needle,
)


def _run(coro):
    # asyncio.run, not get_event_loop(): any earlier asyncio.run() in the
    # session closes the thread's loop and leaves it unset.
    return asyncio.run(coro)


# --------------------------------------------------------------- predicate

class TestPersonPredicateSpelling:
    """The trigram index only serves a predicate matching its expression
    character for character — this is the whole fix, so freeze it."""

    def test_expression_matches_migration_090_index(self):
        # mig 090 indexed f_unaccent(lower(f_arr_text(persons))). Any drift
        # here silently returns the endpoint to a seq scan (the N26 hang).
        assert PERSON_MATCH_EXPR == (
            "persons IS NOT NULL AND f_unaccent(lower(f_arr_text(persons))) LIKE"
        )

    def test_does_not_use_the_unindexable_unnest_spelling(self):
        assert "unnest" not in PERSON_MATCH_EXPR.lower()

    def test_folds_accents_so_the_index_side_matches(self):
        # The Mbappé hole: raw %mbappé% matched 0 rows, folded matched 8.
        assert person_like_needle("Mbappé") == "%mbappe%"

    def test_hyphenated_names_bridge_via_single_char_wildcard(self):
        # 1.2% of stored person values keep punctuation (mostly Arabic
        # names). A literal space would miss all of them.
        assert person_like_needle("Abdel Fattah al-Sisi") == "%abdel_fattah_al_sisi%"

    def test_non_latin_script_falls_back_instead_of_matching_everything(self):
        # An empty fold would leave '%%' and match the entire corpus.
        needle = person_like_needle("習近平")
        assert needle is not None
        assert needle != "%%"
        assert "習近平" in needle

    def test_like_metacharacters_escaped_on_the_fallback_path(self):
        needle = person_like_needle("%_")
        assert needle is None or "\\%" in needle or "\\_" in needle

    def test_empty_ref_yields_no_needle(self):
        assert person_like_needle("   ") is None


# ------------------------------------------------------------ lane budgets

class TestLaneBudgets:
    def test_every_ordered_lane_has_a_budget(self):
        for lane in LANE_ORDER:
            assert lane in LANE_BUDGETS_MS

    def test_nodes_gets_the_largest_budget(self):
        # nodes is the only unbounded lane (GROUP BY, no LIMIT) and owns the
        # measured variance (284ms -> 14.5s).
        assert LANE_BUDGETS_MS["nodes"] == max(LANE_BUDGETS_MS.values())

    def test_budgets_clear_the_measured_worst_case_for_bounded_lanes(self):
        # Worst measured non-nodes lane was trump's ner at 2,741ms.
        assert LANE_BUDGETS_MS["ner"] >= 2741
        assert LANE_BUDGETS_MS["persons"] >= 2741

    def test_global_deadline_bounds_the_handler_below_the_old_hang(self):
        # The witness was 45-120s. Whatever the budgets sum to, the deadline
        # is the real bound and must be far under that.
        assert GLOBAL_DEADLINE_MS <= 10_000

    def test_nodes_runs_first_so_the_deadline_never_costs_primary_content(self):
        assert LANE_ORDER[0] == "nodes"


# ------------------------------------------------------------- lane runner

class _StubConn:
    """Records statement_timeout settings and can be told to raise per lane."""

    def __init__(self, *, raise_on_fetch=None, rows=None, sleep_ms=0):
        self.raise_on_fetch = raise_on_fetch
        self.rows = rows if rows is not None else [{"ok": 1}]
        self.timeouts: list[int] = []
        self.fetches: list[str] = []
        self.sleep_ms = sleep_ms

    async def execute(self, sql):
        if "statement_timeout" in sql:
            self.timeouts.append(int(sql.split("=")[1].strip()))

    async def fetch(self, sql, *params):
        self.fetches.append(sql)
        if self.raise_on_fetch is not None:
            raise self.raise_on_fetch
        return self.rows


class _FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance_ms(self, ms):
        self.t += ms / 1000.0


class TestLaneRunnerBounds:
    def test_live_lane_returns_rows_and_sets_its_budget(self):
        conn = _StubConn()
        runner = LaneRunner(conn)
        rows = _run(runner.run("nodes", "SELECT 1"))
        assert rows == [{"ok": 1}]
        assert runner.status("nodes") == LANE_LIVE
        assert conn.timeouts == [LANE_BUDGETS_MS["nodes"]]

    def test_cancelled_query_degrades_with_a_named_reason_and_never_raises(self):
        conn = _StubConn(raise_on_fetch=asyncpg.exceptions.QueryCanceledError("cancelled"))
        runner = LaneRunner(conn)
        rows = _run(runner.run("nodes", "SELECT 1"))
        # Honest absence, not an exception and not a 500.
        assert rows == []
        assert runner.status("nodes") == LANE_DEGRADED
        assert runner.reasons["nodes"] == "db_busy"

    def test_one_degraded_lane_does_not_stop_the_next(self):
        conn = _StubConn(raise_on_fetch=asyncpg.exceptions.QueryCanceledError("x"))
        runner = LaneRunner(conn)
        _run(runner.run("nodes", "SELECT 1"))
        conn.raise_on_fetch = None
        rows = _run(runner.run("headlines", "SELECT 2"))
        assert rows == [{"ok": 1}]
        assert runner.status("nodes") == LANE_DEGRADED
        assert runner.status("headlines") == LANE_LIVE

    def test_spent_deadline_skips_the_query_entirely(self):
        clock = _FakeClock()
        conn = _StubConn()
        runner = LaneRunner(conn, clock=clock)
        clock.advance_ms(GLOBAL_DEADLINE_MS + 1)
        rows = _run(runner.run("related", "SELECT 1"))
        assert rows == []
        # The point of the deadline: no query is issued at all.
        assert conn.fetches == []
        assert runner.reasons["related"] == "deadline"

    def test_late_lane_timeout_is_clamped_to_remaining_deadline(self):
        clock = _FakeClock()
        conn = _StubConn()
        runner = LaneRunner(conn, clock=clock)
        # 8s spent of a 9s deadline: the nodes budget (6000) must not be
        # allowed to overrun the handler's total bound.
        clock.advance_ms(8000)
        _run(runner.run("nodes", "SELECT 1"))
        assert conn.timeouts[0] <= GLOBAL_DEADLINE_MS - 8000

    def test_degraded_lanes_are_enumerated_for_the_contract(self):
        conn = _StubConn(raise_on_fetch=asyncpg.exceptions.QueryCanceledError("x"))
        runner = LaneRunner(conn)
        _run(runner.run("ner", "SELECT 1"))
        assert runner.degraded_lanes == ["ner"]
        assert runner.any_degraded() is True


# ------------------------------------------------------- router integration

class _FocusFakeConn:
    """SQL-dispatch fake for the six `/api/v2/focus` lanes, mirroring
    `test_edge_diff.py`'s `_FakeConn`. `slow_lanes` names the lanes that
    should behave as a cancelled statement."""

    def __init__(self, *, slow_lanes=(), nodes_rows=None):
        self.slow_lanes = set(slow_lanes)
        self.nodes_rows = nodes_rows if nodes_rows is not None else [
            {"country_code": "US", "signal_count": 120,
             "avg_sentiment": -1.2, "unique_sources": 30},
        ]
        self.seen_sql: list[str] = []

    async def execute(self, sql):
        return None

    def _lane_of(self, sql: str) -> str:
        if "GROUP BY country_code" in sql:
            return "nodes"
        if "unnest(themes)" in sql:
            return "related"
        if "GROUP BY source_name" in sql:
            return "sources"
        if "DISTINCT ON" in sql:
            return "headlines"
        if "jsonb_array_elements" in sql:
            return "ner"
        if "unnest(persons)" in sql:
            return "persons"
        return "unknown"

    async def fetch(self, sql, *params):
        self.seen_sql.append(sql)
        lane = self._lane_of(sql)
        if lane in self.slow_lanes:
            raise asyncpg.exceptions.QueryCanceledError("statement timeout")
        if lane == "nodes":
            return self.nodes_rows
        return []


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return self._conn


class _AcquireCtx:
    """asyncpg's `pool.acquire()` is an async context manager; the fakes in
    this repo return the conn directly, so wrap it the way themes.py uses."""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class _CtxPool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return _AcquireCtx(self._conn)


def _call_focus(focus_type="person", value="trump", hours=24):
    return themes_mod.get_focus_data(focus_type=focus_type, value=value, hours=hours)


class TestFocusEndpointHonesty:
    def test_person_focus_uses_the_indexed_predicate(self, monkeypatch):
        conn = _FocusFakeConn()
        monkeypatch.setattr(db, "pool", _CtxPool(conn))
        _run(_call_focus())
        assert conn.seen_sql, "no lane ran"
        # Every lane must carry the mig-090 spelling, not the unnest form
        # that produced the hang.
        for sql in conn.seen_sql:
            assert "f_unaccent(lower(f_arr_text(persons)))" in sql
            assert "FROM unnest(persons) p WHERE LOWER(p)" not in sql

    def test_degraded_nodes_lane_is_named_not_reported_as_zero(self, monkeypatch):
        conn = _FocusFakeConn(slow_lanes={"nodes"})
        monkeypatch.setattr(db, "pool", _CtxPool(conn))
        out = _run(_call_focus())
        assert out["lanes"]["nodes"] == LANE_DEGRADED
        # THE zero-as-fact trap: an unmeasured lane must not serve 0.
        assert out["summary"]["total_signals"] is None
        assert out["summary"]["total_countries"] is None
        assert "nodes" in out["degraded_lanes"]

    def test_live_lanes_still_serve_while_another_degrades(self, monkeypatch):
        conn = _FocusFakeConn(slow_lanes={"ner"})
        monkeypatch.setattr(db, "pool", _CtxPool(conn))
        out = _run(_call_focus())
        assert out["lanes"]["nodes"] == LANE_LIVE
        assert out["lanes"]["ner"] == LANE_DEGRADED
        # Partial payload, not an all-or-nothing failure.
        assert out["summary"]["total_signals"] == 120

    def test_all_lanes_degraded_still_returns_a_payload_never_a_500(self, monkeypatch):
        conn = _FocusFakeConn(slow_lanes=set(LANE_ORDER))
        monkeypatch.setattr(db, "pool", _CtxPool(conn))
        out = _run(_call_focus())
        assert out["summary"]["total_signals"] is None
        assert sorted(out["degraded_lanes"]) == sorted(LANE_ORDER)
        assert out["nodes"] == []

    def test_healthy_person_focus_reports_every_lane_live(self, monkeypatch):
        conn = _FocusFakeConn()
        monkeypatch.setattr(db, "pool", _CtxPool(conn))
        out = _run(_call_focus())
        assert out["degraded_lanes"] == []
        assert all(v == LANE_LIVE for v in out["lanes"].values())

    def test_non_person_focus_keeps_its_own_filter(self, monkeypatch):
        conn = _FocusFakeConn()
        monkeypatch.setattr(db, "pool", _CtxPool(conn))
        _run(_call_focus(focus_type="country", value="co"))
        assert conn.seen_sql
        for sql in conn.seen_sql:
            assert "country_code = $1" in sql
