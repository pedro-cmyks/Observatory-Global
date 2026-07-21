"""L4 markets — accumulator unit tests (pure helpers + store idempotency).

Run:  python3 -m pytest markets/tests/test_accumulate.py -q
"""
from __future__ import annotations

import math
from pathlib import Path

from markets import store
from markets.accumulate_news_intensity import aggregate
from markets.instruments import all_symbols, symbol_labels


def _db(tmp_path: Path):
    return store.connect(tmp_path / "t.db")


def test_instruments_dedup_and_labels():
    syms = all_symbols()
    assert len(syms) == len(set(syms)), "symbols must be deduped"
    # ^GSPC appears in both world basket and US universe -> exactly once
    assert syms.count("^GSPC") == 1
    labels = symbol_labels()
    assert labels["COP=X"][0].startswith("Colombian peso")
    assert "EC" in labels and "KC=F" in labels  # champion + export commodity present


def test_price_upsert_idempotent_and_logreturn(tmp_path):
    conn = _db(tmp_path)
    store.upsert_prices(conn, "CL=F", {"2026-07-01": 100.0, "2026-07-02": 110.0})
    rows = conn.execute(
        "SELECT date, close, log_return FROM market_price_daily "
        "WHERE symbol='CL=F' ORDER BY date").fetchall()
    assert [r[1] for r in rows] == [100.0, 110.0]
    assert rows[0][2] is None                                  # first day: no return
    assert math.isclose(rows[1][2], math.log(110.0 / 100.0), rel_tol=1e-9)

    # re-run same day with a revised close -> updates in place, no dup row
    store.upsert_prices(conn, "CL=F", {"2026-07-02": 121.0})
    rows2 = conn.execute(
        "SELECT date, close FROM market_price_daily WHERE symbol='CL=F' "
        "ORDER BY date").fetchall()
    assert len(rows2) == 2 and rows2[1][1] == 121.0            # updated, not appended


def test_price_appends_new_day_recomputes_return(tmp_path):
    conn = _db(tmp_path)
    store.upsert_prices(conn, "GC=F", {"2026-07-01": 2000.0})
    store.upsert_prices(conn, "GC=F", {"2026-07-02": 2020.0})  # separate daily run
    r = conn.execute("SELECT log_return FROM market_price_daily "
                     "WHERE symbol='GC=F' AND date='2026-07-02'").fetchone()
    assert math.isclose(r[0], math.log(2020.0 / 2000.0), rel_tol=1e-9)


def test_news_aggregate_category_and_country_cooccurrence():
    threads = [
        {"category": "Armed conflict escalation", "signal_count": 100,
         "subject_countries": ["RU", "UA"]},
        {"category": "Armed conflict escalation", "signal_count": 50,
         "subject_countries": ["UA"]},
        {"parent_domain": "Oil and gas supply risk", "signal_count": 30,
         "subject_countries": ["SA"]},
    ]
    by_cat, by_cc = aggregate(threads)
    assert by_cat["Armed conflict escalation"] == (150.0, 2)
    assert by_cat["Oil and gas supply risk"] == (30.0, 1)     # parent_domain fallback
    assert by_cc["UA"] == (150.0, 2)                          # 100 + 50, two threads
    assert by_cc["RU"] == (100.0, 1)                          # co-occurrence intensity
    assert by_cc["SA"] == (30.0, 1)


def test_news_upsert_pit_and_idempotent(tmp_path):
    conn = _db(tmp_path)
    store.upsert_news_intensity(conn, "2026-07-21", "category",
                                "Armed conflict escalation", 150.0, 2, "v0")
    store.upsert_news_intensity(conn, "2026-07-21", "category",
                                "Armed conflict escalation", 175.0, 3, "v0")  # rerun
    rows = conn.execute(
        "SELECT intensity, n_threads, computed_pit FROM news_daily_intensity "
        "WHERE day='2026-07-21'").fetchall()
    assert len(rows) == 1                                     # idempotent on the key
    assert rows[0] == (175.0, 3, 1)                           # updated + PIT flag set
