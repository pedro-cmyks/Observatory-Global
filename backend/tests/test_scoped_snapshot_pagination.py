"""Lane B (2026-07-18) — keyset-paginated per-country fetch in run_scoped_snapshot.

The single-statement US pull (~74k vectors, ~650MB of vec::text) exceeded the
600s statement_timeout under daytime contention and dropped the most-covered
country from every contended snapshot (2026-07-17 log: 3/3 attempts
"canceling statement due to statement timeout"). The fix keyset-paginates on
(timestamp DESC, id DESC) — never OFFSET — with bounded pages accumulated
client-side, plus se.vec::real[] binary decode.

These tests freeze the loop's pure behaviour against a fake conn:

- pages accumulate until a short/empty page; the keyset cursor advances to the
  last row of each FULL page (never an extra probe after a short page);
- the result equals the old single statement (ORDER BY timestamp DESC LIMIT
  cap): same corpus, newest-first — load-bearing because `_clean_and_dedupe`
  keeps the FIRST occurrence of a duplicate headline (must stay the newest);
- cap>0 reproduces LIMIT NULLIF(cap,0) semantics; cap<=0 traverses everything.

NOTE: run_scoped_snapshot imports emergent_poc which imports hdbscan at module
level — these tests run in the M1 mlvenv (which has hdbscan) and skip cleanly
in the API .venv.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytest.importorskip("hdbscan")
pytest.importorskip("asyncpg")

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import backend.scripts.run_scoped_snapshot as rss  # noqa: E402
from backend.scripts.emergent_poc import _clean_and_dedupe  # noqa: E402

T0 = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)


def _row(i: int, minutes_ago: int, headline: str | None = None) -> dict:
    return {
        "id": i,
        "headline": headline or f"Headline number {i} with enough length here",
        "country_code": "US",
        "source_name": "src",
        "timestamp": T0 - timedelta(minutes=minutes_ago),
        "emb": [0.1, 0.2],
    }


class _FakeConn:
    """Serves (timestamp DESC, id DESC) keyset pages from an in-memory corpus,
    mirroring _FETCH_PAGE's WHERE (s.timestamp, s.id) < ($4, $5) contract."""

    def __init__(self, rows: list[dict]):
        self.rows = sorted(rows, key=lambda r: (r["timestamp"], r["id"]),
                           reverse=True)
        self.calls: list[tuple] = []  # (limit, last_ts, last_id) per statement

    async def fetch(self, sql, cc, hours, limit, last_ts, last_id):
        assert "OFFSET" not in sql.upper()
        self.calls.append((limit, last_ts, last_id))
        hits = [r for r in self.rows
                if (r["timestamp"], r["id"]) < (last_ts, last_id)]
        return hits[:limit]


def _fetch(conn, cap, page_rows):
    return asyncio.run(
        rss._fetch_country_embeddings(conn, "US", 168, cap, page_rows))


def test_accumulates_all_pages_and_terminates_on_short_page():
    rows = [_row(i, minutes_ago=i) for i in range(1, 24)]  # 23 rows, id1 newest
    conn = _FakeConn(rows)
    out = _fetch(conn, cap=0, page_rows=10)
    assert len(out) == 23
    # 10 + 10 + 3(short → stop): exactly 3 statements
    assert len(conn.calls) == 3
    # cursor = last row of each FULL page
    assert conn.calls[0][1:] == (datetime(9999, 12, 31, 23, 59, 59,
                                          tzinfo=timezone.utc), rss._MAX_BIGINT)
    assert conn.calls[1][1:] == (rows[9]["timestamp"], 10)
    assert conn.calls[2][1:] == (rows[19]["timestamp"], 20)
    # same corpus as the old single statement, newest-first
    assert [r["id"] for r in out] == list(range(1, 24))


def test_exact_page_multiple_terminates_via_empty_page():
    rows = [_row(i, minutes_ago=i) for i in range(1, 21)]  # 20 rows, pages of 10
    conn = _FakeConn(rows)
    out = _fetch(conn, cap=0, page_rows=10)
    assert len(out) == 20
    assert len(conn.calls) == 3  # 10 + 10 + empty(stop)


def test_matches_old_order_by_timestamp_desc_limit_cap():
    # timestamps NOT monotone with id; duplicates timestamps included
    rows = [_row(i, minutes_ago=(i * 7) % 40) for i in range(1, 16)]
    conn = _FakeConn(rows)
    out = _fetch(conn, cap=5, page_rows=4)
    oracle = sorted(rows, key=lambda r: (r["timestamp"], r["id"]),
                    reverse=True)[:5]  # old ORDER BY ts DESC LIMIT 5, det. ties
    assert [r["id"] for r in out] == [r["id"] for r in oracle]


def test_cap_never_overfetches():
    rows = [_row(i, minutes_ago=i) for i in range(1, 30)]
    conn = _FakeConn(rows)
    out = _fetch(conn, cap=7, page_rows=5)
    assert [r["id"] for r in out] == [1, 2, 3, 4, 5, 6, 7]
    # last statement asks only for the remaining 2, not a full page
    assert conn.calls[-1][0] == 2


def test_timestamp_tie_cursor_does_not_skip_or_duplicate_rows():
    # 7 rows sharing ONE timestamp, page smaller than the tie group — the id
    # tiebreak in the keyset must walk through the tie without loss/dup
    rows = [_row(i, minutes_ago=15) for i in range(1, 8)]
    conn = _FakeConn(rows)
    out = _fetch(conn, cap=0, page_rows=3)
    assert sorted(r["id"] for r in out) == list(range(1, 8))
    assert len(out) == 7  # no duplicates


def test_dedupe_newest_wins_contract_preserved():
    # _clean_and_dedupe keeps the FIRST occurrence — the paginated pull must
    # still deliver the NEWEST duplicate first (old timestamp-DESC behaviour)
    dup = "Same breaking story headline repeated verbatim"
    rows = [_row(1, 60, headline=dup), _row(2, 5, headline=dup)]
    conn = _FakeConn(rows)
    out = _fetch(conn, cap=0, page_rows=10)
    kept = _clean_and_dedupe([dict(r) for r in out])
    assert len(kept) == 1
    assert kept[0]["id"] == 2  # newest survived, exactly as pre-pagination
