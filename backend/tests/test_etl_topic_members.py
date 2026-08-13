"""Timeout discipline for the v1-compat members ETL (2026-08-13).

The single 168h INSERT..SELECT outran the pooler's 2min statement_timeout two
nights running (Step 3.5, 08-12 + 08-13). These tests freeze the bounded
rewrite: anchored slabs with NO drift gaps, an open-ended newest slab, and a
SET LOCAL timeout around every statement.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import scripts.etl_topic_members as etl

ANCHOR = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)


def test_slab_bounds_cover_window_without_gaps():
    bounds = etl.slab_bounds(ANCHOR, 168, slab_hours=24)
    assert len(bounds) == 7
    assert bounds[0][0] == ANCHOR - timedelta(hours=168)   # oldest first
    assert bounds[-1][1] is None                           # newest slab open-ended
    for (_, hi), (lo2, _) in zip(bounds, bounds[1:]):
        assert hi == lo2                                   # half-open, zero gap


def test_slab_bounds_single_slab_when_window_fits():
    assert etl.slab_bounds(ANCHOR, 24, slab_hours=24) == [(ANCHOR - timedelta(hours=24), None)]
    assert etl.slab_bounds(ANCHOR, 12, slab_hours=24) == [(ANCHOR - timedelta(hours=12), None)]


def test_slab_bounds_legacy_opt_out():
    assert etl.slab_bounds(ANCHOR, 168, slab_hours=0) == [(ANCHOR - timedelta(hours=168), None)]


def test_slab_bounds_ragged_tail():
    bounds = etl.slab_bounds(ANCHOR, 50, slab_hours=24)
    assert bounds[0] == (ANCHOR - timedelta(hours=50), ANCHOR - timedelta(hours=26))
    assert bounds[1] == (ANCHOR - timedelta(hours=26), ANCHOR - timedelta(hours=2))
    assert bounds[2] == (ANCHOR - timedelta(hours=2), None)


def test_rowcount_parses_insert_status():
    assert etl._rowcount("INSERT 0 123") == 123
    assert etl._rowcount("INSERT 0 0") == 0
    assert etl._rowcount("garbage") == 0


def test_execute_guarded_wraps_in_txn_with_set_local(monkeypatch):
    class _Txn:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            self.conn.txn_depth += 1

        async def __aexit__(self, *exc):
            self.conn.txn_depth -= 1

    class _FakeConn:
        def __init__(self):
            self.txn_depth = 0
            self.calls = []

        def transaction(self):
            return _Txn(self)

        async def execute(self, sql, *args):
            self.calls.append((sql, args, self.txn_depth))
            if "set_config" in sql:
                return "SELECT 1"
            return "INSERT 0 7"

    monkeypatch.setattr(etl, "STMT_TIMEOUT", "540s")
    conn = _FakeConn()
    n = asyncio.run(etl._execute_guarded(conn, "INSERT ...", 1, 2))
    assert n == 7
    set_call, insert_call = conn.calls
    assert "set_config('statement_timeout', $1, true)" in set_call[0]
    assert set_call[1] == ("540s",) and set_call[2] == 1   # inside the txn
    assert insert_call[2] == 1                             # same txn (SET LOCAL applies)
