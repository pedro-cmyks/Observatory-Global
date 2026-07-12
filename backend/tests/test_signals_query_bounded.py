"""Regression guard for the 2026-07-11 /api/v2/signals 500 outage.

Sorting the full time window by the richness expression forced Postgres to
read every row in the window (~100K at 24h) before returning anything —
measured 18.5s against the 8s asyncpg timeout, so every unfiltered stream
request 500'd (TimeoutError at the main fetch). The fix bounds the richness
sort to a recent pool fetched via the timestamp index.

These tests freeze that query shape at the source level (same style as
test_signals_lane_contract.py).
"""
import re
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "app" / "routers" /
       "signals.py").read_text(encoding="utf-8")


def _main_query() -> str:
    """The main stream fetch — the block that binds `rows =`."""
    m = re.search(r"rows = await conn\.fetch\(f\"\"\"(.*?)\"\"\"", SRC, re.S)
    assert m, "main signals fetch not found"
    return m.group(1)


def test_richness_sort_runs_over_bounded_recent_pool():
    q = _main_query()
    # Inner subquery: timestamp-ordered, pool-limited (index-friendly).
    assert "ORDER BY timestamp DESC" in q
    assert "LIMIT {pool_limit}" in q
    assert ") recent_pool" in q
    # Outer: richness sort applies to the pool, not the full window.
    inner_end = q.index(") recent_pool")
    outer = q[inner_end:]
    assert "snippet IS NOT NULL" in outer, "richness sort must be OUTSIDE the pool subquery"


def test_richness_expression_never_orders_the_raw_window():
    """The unbounded shape (richness ORDER BY directly on signals_v2 with the
    window WHERE clause) is what timed out. Ensure the richness expression only
    appears after the pool subquery closes."""
    q = _main_query()
    pool_pos = q.index(") recent_pool")
    richness_pos = q.index("snippet IS NOT NULL")
    assert richness_pos > pool_pos


def test_pool_limit_defined_and_bounded():
    assert "pool_limit = max(fetch_limit * 4, 2000)" in SRC


def test_main_fetch_keeps_client_timeout():
    m = re.search(r"LIMIT \{fetch_limit\}\s*\"\"\", \*params, timeout=8\.0\)", SRC)
    assert m, "main fetch must keep an explicit asyncpg timeout"
