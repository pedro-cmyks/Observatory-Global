"""#256 — event-binding freshness: timeout/retry, bounded queries, honest receipts.

The 2026-07-12 incident: bind_disaster_movement + compute_event_movement timed out
inside the scoped-snapshot cron (statement timeout / client 120s) and the runner
swallowed the failure as non-fatal → bindings silently stale since 07-10.
These tests freeze the fix contract: retries with a real budget, bounded
_topic_country, machine-readable freshness receipts, and the semantic guardrails
(movement-role only, never evidence, idempotent writes).
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.event_binding_util import build_receipt, fetch_with_retry
from scripts import bind_disaster_movement as bdm
from scripts import compute_event_movement as cem


class _FakeTxn:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        self.conn.txn_depth += 1

    async def __aexit__(self, *exc):
        self.conn.txn_depth -= 1


class FakeConn:
    def __init__(self, results=None, fail_times=0, exc=TimeoutError):
        self.calls: list[tuple] = []
        self.exec_calls: list[tuple] = []  # (sql, args, txn_depth)
        self.results = results if results is not None else []
        self.fail_times = fail_times
        self.exc = exc
        self.txn_depth = 0

    def transaction(self):
        return _FakeTxn(self)

    async def execute(self, sql, *args):
        self.exec_calls.append((sql, args, self.txn_depth))
        return "SELECT 1"

    async def fetch(self, sql, *args, timeout=None):
        self.calls.append((sql, args, timeout, self.txn_depth))
        if self.fail_times > 0:
            self.fail_times -= 1
            raise self.exc()
        return self.results


def _run(coro):
    return asyncio.run(coro)


# --- retry budget -----------------------------------------------------------

def test_fetch_with_retry_recovers_after_timeout():
    conn = FakeConn(results=[{"x": 1}], fail_times=1)
    rows = _run(fetch_with_retry(conn, "SELECT 1", timeout=5, attempts=2, backoff=0))
    assert rows == [{"x": 1}]
    assert len(conn.calls) == 2


def test_fetch_with_retry_exhausts_and_raises():
    conn = FakeConn(fail_times=99)
    with pytest.raises(TimeoutError):
        _run(fetch_with_retry(conn, "SELECT 1", timeout=5, attempts=3, backoff=0))
    assert len(conn.calls) == 3


def test_fetch_with_retry_passes_timeout_to_driver():
    conn = FakeConn(results=[])
    _run(fetch_with_retry(conn, "SELECT 1", "arg", timeout=42, attempts=1, backoff=0))
    sql, args, timeout, _depth = conn.calls[0]
    assert timeout == 42 and args == ("arg",)


# --- per-statement SET LOCAL guard (2026-08-13) ------------------------------
# The pooler's effective statement_timeout is 2min; the 08-12 receipt logged
# all_windows_timed_out because the client budget sat below the query's real
# cost. Every attempt must now carry its own SET LOCAL inside a transaction.

def test_fetch_with_retry_sets_local_timeout_inside_txn(monkeypatch):
    import scripts.event_binding_util as ebu
    monkeypatch.setattr(ebu, "STMT_TIMEOUT", "540s")
    conn = FakeConn(results=[{"x": 1}])
    _run(fetch_with_retry(conn, "SELECT 1", timeout=5, attempts=1, backoff=0))
    (set_sql, set_args, set_depth), = conn.exec_calls
    assert "set_config('statement_timeout', $1, true)" in set_sql
    assert set_args == ("540s",) and set_depth == 1     # inside the txn
    assert conn.calls[0][3] == 1                        # fetch in the SAME txn


def test_fetch_with_retry_reissues_set_local_each_attempt():
    conn = FakeConn(results=[{"x": 1}], fail_times=1)
    _run(fetch_with_retry(conn, "SELECT 1", timeout=5, attempts=2, backoff=0))
    set_calls = [c for c in conn.exec_calls if "set_config" in c[0]]
    assert len(set_calls) == 2                          # one per attempt
    assert conn.txn_depth == 0                          # txns all closed


def test_client_backstop_sits_above_server_budget():
    # server must cancel first (clean QueryCanceledError), never the client
    import scripts.event_binding_util as ebu
    server_s = float(ebu.STMT_TIMEOUT.rstrip("s"))
    assert ebu.DEFAULT_QUERY_TIMEOUT > server_s


# --- bounded _topic_country --------------------------------------------------

def test_topic_country_is_bounded_to_given_topics():
    conn = FakeConn(results=[])
    _run(bdm._topic_country(conn, ["dynamic-topic-1", "dynamic-topic-2"]))
    sql, args, _timeout, _depth = conn.calls[0]
    assert "= ANY($1" in sql, "must restrict to the disaster-topic ids, not all topics"
    assert args[0] == ["dynamic-topic-1", "dynamic-topic-2"]


def test_topic_country_empty_topics_short_circuits():
    conn = FakeConn(results=[])
    out = _run(bdm._topic_country(conn, []))
    assert out == {}
    assert conn.calls == [], "no query when there are no disaster topics"


# --- freshness receipt -------------------------------------------------------

def test_receipt_lag_hours_computed():
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    receipt = build_receipt(
        engine="disaster-v1",
        ingested_max=now,
        bound_max=now - timedelta(hours=36),
        scanned=100, matched=8, written=8,
        window_hours=336, now=now,
    )
    assert receipt["lag_hours"] == 36.0
    assert receipt["engine"] == "disaster-v1"
    json.dumps(receipt)  # machine-readable


def test_receipt_honest_when_nothing_bound():
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    receipt = build_receipt(
        engine="movement-v1",
        ingested_max=now, bound_max=None,
        scanned=50, matched=0, written=0,
        window_hours=168, now=now,
    )
    assert receipt["lag_hours"] is None
    assert receipt["bound_max_event_time"] is None
    json.dumps(receipt)


def test_receipt_honest_when_no_ingested_events():
    receipt = build_receipt(
        engine="disaster-v1",
        ingested_max=None, bound_max=None,
        scanned=0, matched=0, written=0,
        window_hours=336,
        now=datetime(2026, 7, 12, tzinfo=timezone.utc),
    )
    assert receipt["lag_hours"] is None
    assert receipt["ingested_max_event_time"] is None


# --- semantic guardrails (movement never evidence, idempotent writes) --------

def test_disaster_insert_stays_movement_and_unverified():
    assert "'movement'" in bdm._INSERT_SQL
    assert "ON CONFLICT DO NOTHING" in bdm._INSERT_SQL
    assert "false" in bdm._INSERT_SQL  # gate_kept=false — never evidence


def test_cameo_insert_stays_movement_and_unverified():
    assert "'movement'" in cem._INSERT_SQL
    assert "ON CONFLICT DO NOTHING" in cem._INSERT_SQL
    assert "false" in cem._INSERT_SQL


def test_bounded_window_fallback_sequence():
    # timeout at full window must fall back to smaller bounded windows, never 0
    assert cem.fallback_windows(168) == [168, 84, 42]
    assert cem.fallback_windows(48) == [48, 24, 12]
    assert all(h > 0 for h in cem.fallback_windows(6))
