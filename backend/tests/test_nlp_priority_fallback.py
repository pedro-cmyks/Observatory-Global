"""Fleet selector resilience (#184 ops, 2026-07-16).

The mixed-priority selector runs as ONE statement; when the backlog_pool
15-day scan crawls under DB IO pressure the whole query hits the statement
timeout and every phase gets ZERO rows — the fleet starved for ~9h (2,266
QueryCanceledError) while the hot lane alone answered in 1.3s. Contract: on
QueryCanceledError the selector falls back to a HOT-ONLY select (24h pool,
same priority expression); a second timeout degrades to an empty batch (the
worker lives to try next cycle); non-timeout errors still propagate.
"""

import asyncio

import pytest
from asyncpg.exceptions import QueryCanceledError

from enrichment.nlp_pipeline import (
    _fetch_priority_rows,
    _hot_only_select_sql,
    _priority_select_sql,
)


class FakeConn:
    def __init__(self, behaviors):
        # behaviors: list of Exception-to-raise or rows-to-return, consumed in order
        self.behaviors = list(behaviors)
        self.calls: list[str] = []

    async def fetch(self, sql, *args, **kwargs):
        self.calls.append(sql)
        b = self.behaviors.pop(0)
        if isinstance(b, Exception):
            raise b
        return b


def test_hot_only_sql_has_no_backlog_or_sample_lane():
    sql = _hot_only_select_sql("nlp_processed_at")
    assert "hot_pool" in sql
    assert "backlog_pool" not in sql and "sample_lane" not in sql


def test_hot_only_sql_validates_target_column():
    with pytest.raises(ValueError):
        _hot_only_select_sql("evil; DROP TABLE")


def test_timeout_falls_back_to_hot_only():
    rows = [{"id": 1}]
    conn = FakeConn([QueryCanceledError("canceling statement"), rows])
    out = asyncio.run(_fetch_priority_rows(conn, "nlp_processed_at", 100))
    assert out == rows
    assert conn.calls[0] == _priority_select_sql("nlp_processed_at")
    assert conn.calls[1] == _hot_only_select_sql("nlp_processed_at")


def test_double_timeout_degrades_to_empty_batch():
    conn = FakeConn([QueryCanceledError("t1"), QueryCanceledError("t2")])
    out = asyncio.run(_fetch_priority_rows(conn, "nlp_processed_at", 100))
    assert out == []


def test_non_timeout_errors_propagate():
    conn = FakeConn([RuntimeError("connection reset")])
    with pytest.raises(RuntimeError):
        asyncio.run(_fetch_priority_rows(conn, "nlp_processed_at", 100))
