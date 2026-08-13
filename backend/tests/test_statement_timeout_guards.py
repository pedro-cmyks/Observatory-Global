"""Per-statement SET LOCAL statement_timeout guards (2026-08-13 sweep).

The pooler's effective statement_timeout is 2min (server config file), while
several nightly statements scale with table growth: the movement aggregate
measured 28.6s uncontended at 169k topic_members, and the umbrella rebuild
(Step 3) ran with no budget at all right after the snapshot rewrites its
tables. These tests freeze the sanctioned pattern from etl_topic_members:
every heavy statement runs in its own transaction with a SET LOCAL
statement_timeout, so no statement inherits the 2min default and nothing
leaks past its transaction.
"""
from __future__ import annotations

import asyncio

import scripts.build_umbrella_topics as umbrella
import scripts.compute_topic_movement as movement


class _Txn:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        self.conn.txn_depth += 1

    async def __aexit__(self, *exc):
        self.conn.txn_depth -= 1


class FakeConn:
    def __init__(self, rows=None):
        self.txn_depth = 0
        self.exec_calls = []   # (sql, args, txn_depth)
        self.fetch_calls = []  # (sql, args, txn_depth)
        self.rows = rows if rows is not None else []

    def transaction(self):
        return _Txn(self)

    async def execute(self, sql, *args):
        self.exec_calls.append((sql, args, self.txn_depth))
        return "SELECT 1"

    async def fetch(self, sql, *args, **kw):
        self.fetch_calls.append((sql, args, self.txn_depth))
        return self.rows


def test_movement_series_fetch_is_guarded(monkeypatch):
    monkeypatch.setattr(movement, "STMT_TIMEOUT", "540s")
    conn = FakeConn(rows=[])
    out = asyncio.run(movement._series_by_topic(conn))
    assert out == {}
    (set_sql, set_args, set_depth), = conn.exec_calls
    assert "set_config('statement_timeout', $1, true)" in set_sql
    assert set_args == ("540s",) and set_depth == 1     # SET LOCAL inside txn
    assert conn.fetch_calls[0][2] == 1                  # fetch in the SAME txn
    assert conn.txn_depth == 0                          # txn closed


def test_movement_series_preserves_query_shape():
    conn = FakeConn(rows=[])
    asyncio.run(movement._series_by_topic(conn))
    sql = conn.fetch_calls[0][0]
    # lifecycle semantics untouched: same rows read as before the guard
    assert "FROM topic_members tm JOIN signals_v2 s" in sql
    assert "tm.role = 'evidence'" in sql
    assert f"INTERVAL '{movement.WINDOW_DAYS} days'" in sql


def test_umbrella_fetch_guarded_wraps_in_txn(monkeypatch):
    monkeypatch.setattr(umbrella, "STMT_TIMEOUT", "540s")
    conn = FakeConn(rows=[{"id": 1}])
    rows = asyncio.run(umbrella._fetch_guarded(conn, "SELECT 1", 7))
    assert rows == [{"id": 1}]
    (set_sql, set_args, set_depth), = conn.exec_calls
    assert "set_config('statement_timeout', $1, true)" in set_sql
    assert set_args == ("540s",) and set_depth == 1
    assert conn.fetch_calls == [("SELECT 1", (7,), 1)]  # args pass through, in txn
    assert conn.txn_depth == 0


def test_umbrella_load_query_unchanged():
    # the guard bounds the statement, never the row set
    assert "WHERE state = 'active' AND is_umbrella = false" in umbrella._LOAD
    assert "centroid_vec IS NOT NULL" in umbrella._LOAD
    assert "ORDER BY id" in umbrella._LOAD
