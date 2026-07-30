"""ATLAS_CJK_LEN_FLOOR wiring on the R1 scoped-snapshot pull
(run_scoped_snapshot.py). See test_script_floor.py for the pure
script-aware-floor logic; this file only pins that the two SQL builders
(`_countries_sql`, `_fetch_page_sql`) actually read the env gate and stay
byte-identical to the pre-2026-07-30 flat floor when it is off.

NOTE: run_scoped_snapshot imports emergent_poc which imports hdbscan at
module level — these tests run in the M1 mlvenv (which has hdbscan) and
skip cleanly in the API .venv, same as the sibling test_scoped_*.py files.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("hdbscan")
pytest.importorskip("asyncpg")

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import backend.scripts.run_scoped_snapshot as rss  # noqa: E402
from backend.scripts.script_floor import headline_floor_sql  # noqa: E402


def test_countries_sql_default_off_is_flat_floor(monkeypatch):
    monkeypatch.delenv("ATLAS_CJK_LEN_FLOOR", raising=False)
    sql = rss._countries_sql()
    assert "length(s.headline) >= 20" in sql
    assert "CASE WHEN" not in sql


def test_fetch_page_sql_default_off_is_flat_floor(monkeypatch):
    monkeypatch.delenv("ATLAS_CJK_LEN_FLOOR", raising=False)
    sql = rss._fetch_page_sql()
    assert "length(s.headline) >= 20" in sql
    assert "CASE WHEN" not in sql


def test_countries_sql_on_uses_script_aware_case(monkeypatch):
    monkeypatch.setenv("ATLAS_CJK_LEN_FLOOR", "on")
    sql = rss._countries_sql()
    assert headline_floor_sql("s.headline") in sql
    assert "CASE WHEN" in sql


def test_fetch_page_sql_on_uses_script_aware_case(monkeypatch):
    monkeypatch.setenv("ATLAS_CJK_LEN_FLOOR", "on")
    sql = rss._fetch_page_sql()
    assert headline_floor_sql("s.headline") in sql
    assert "CASE WHEN" in sql


def test_toggling_the_env_var_changes_the_next_call_only(monkeypatch):
    # No caching/staleness — each call re-reads the gate, so a test (or a
    # long-running process whose env changes) never sees a stuck value.
    monkeypatch.delenv("ATLAS_CJK_LEN_FLOOR", raising=False)
    assert "CASE WHEN" not in rss._countries_sql()
    monkeypatch.setenv("ATLAS_CJK_LEN_FLOOR", "on")
    assert "CASE WHEN" in rss._countries_sql()
    monkeypatch.delenv("ATLAS_CJK_LEN_FLOOR", raising=False)
    assert "CASE WHEN" not in rss._countries_sql()


def test_other_predicates_unchanged_around_the_floor(monkeypatch):
    """The floor swap must not disturb the rest of either query's WHERE
    clause — country scoping, timestamp window, keyset pagination."""
    monkeypatch.delenv("ATLAS_CJK_LEN_FLOOR", raising=False)
    countries_sql = rss._countries_sql()
    assert "s.country_code IS NOT NULL AND s.country_code <> 'XX'" in countries_sql
    assert "GROUP BY s.country_code HAVING COUNT(*) >= $3" in countries_sql

    fetch_sql = rss._fetch_page_sql()
    assert "WHERE s.country_code = $1" in fetch_sql
    assert "(s.timestamp, s.id) < ($4::timestamptz, $5::bigint)" in fetch_sql
    assert "OFFSET" not in fetch_sql.upper()
