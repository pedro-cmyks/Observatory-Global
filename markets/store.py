"""L4 markets — the accumulation store (sqlite, stdlib only).

The two ACCUMULATING panels that make the #226 October re-run physically possible
(design §6). Append-only, idempotent, forward. This is the markets-side STUDY
substrate — it lives OUTSIDE Atlas's DB (separate-consumer rule); only a thin
descriptive price table would ever land in Atlas for the product overlay (#151),
and that is a later, separate step.

Durability: the store defaults to a STABLE path outside the iCloud/worktree tree
(the crons execute from ~/AtlasLocalWorker; a worktree can be pruned). Override with
ATLAS_MARKETS_DB.

Tables:
  market_price_daily     — Yahoo daily closes + stepwise log-return (self-contained
                           return series). First run BACKFILLS Yahoo's ~4mo window
                           (the genuinely-lost-otherwise capture), then appends daily.
  news_daily_intensity   — one forward EOD snapshot per (day, axis, id). computed_pit=1
                           because a forward snapshot sees only <= today's data — it is
                           point-in-time BY CONSTRUCTION. Backfill is FORBIDDEN (a value
                           reconstructed from retrospective clustering leaks future
                           structure; the reverse study must never trust a backfilled row).
"""
from __future__ import annotations

import math
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def default_db_path() -> Path:
    env = os.environ.get("ATLAS_MARKETS_DB")
    if env:
        return Path(env).expanduser()
    stable = Path("~/AtlasLocalWorker/markets/markets.db").expanduser()
    return stable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS market_price_daily (
    symbol     TEXT NOT NULL,
    date       TEXT NOT NULL,            -- ISO date (trading day)
    close      REAL NOT NULL,
    log_return REAL,                     -- vs previous stored close for this symbol
    source     TEXT NOT NULL DEFAULT 'yahoo',
    fetched_at TEXT NOT NULL,            -- UTC ISO of the run that wrote/updated the row
    PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS ix_price_symbol_date ON market_price_daily(symbol, date);

CREATE TABLE IF NOT EXISTS news_daily_intensity (
    day            TEXT NOT NULL,        -- UTC calendar day the snapshot covers
    axis_kind      TEXT NOT NULL,        -- 'category' | 'country'
    axis_id        TEXT NOT NULL,        -- category label/slug or ISO country code
    intensity      REAL NOT NULL,        -- summed signal_count (the intensity proxy)
    n_threads      INTEGER,              -- supporting thread count
    computed_pit   INTEGER NOT NULL DEFAULT 1,
    method_version TEXT NOT NULL,
    fetched_at     TEXT NOT NULL,
    PRIMARY KEY (day, axis_kind, axis_id, method_version)
);
CREATE INDEX IF NOT EXISTS ix_news_day ON news_daily_intensity(day, axis_kind);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    p = db_path or default_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.executescript(_SCHEMA)
    return conn


def upsert_prices(conn: sqlite3.Connection, symbol: str,
                  closes: dict[str, float], source: str = "yahoo") -> int:
    """Idempotently write a symbol's date->close map; recompute log_return over the
    full stored series for that symbol (cheap; series is small). Returns rows touched."""
    now = _utc_now_iso()
    for d, c in closes.items():
        conn.execute(
            "INSERT INTO market_price_daily(symbol,date,close,source,fetched_at) "
            "VALUES(?,?,?,?,?) "
            "ON CONFLICT(symbol,date) DO UPDATE SET close=excluded.close, "
            "source=excluded.source, fetched_at=excluded.fetched_at",
            (symbol, d, float(c), source, now),
        )
    # recompute stepwise log-returns over the stored series
    rows = conn.execute(
        "SELECT date, close FROM market_price_daily WHERE symbol=? ORDER BY date",
        (symbol,),
    ).fetchall()
    prev = None
    for d, c in rows:
        lr = None if prev is None or prev <= 0 or c <= 0 else math.log(c / prev)
        conn.execute(
            "UPDATE market_price_daily SET log_return=? WHERE symbol=? AND date=?",
            (lr, symbol, d),
        )
        prev = c
    conn.commit()
    return len(closes)


def upsert_news_intensity(conn: sqlite3.Connection, day: str, axis_kind: str,
                          axis_id: str, intensity: float, n_threads: int,
                          method_version: str) -> None:
    """Write ONE forward EOD snapshot row. computed_pit is hard-coded 1: this is only
    ever called with the CURRENT day's live aggregate (point-in-time by construction).
    There is deliberately no backfill entry point."""
    conn.execute(
        "INSERT INTO news_daily_intensity"
        "(day,axis_kind,axis_id,intensity,n_threads,computed_pit,method_version,fetched_at) "
        "VALUES(?,?,?,?,?,1,?,?) "
        "ON CONFLICT(day,axis_kind,axis_id,method_version) DO UPDATE SET "
        "intensity=excluded.intensity, n_threads=excluded.n_threads, "
        "fetched_at=excluded.fetched_at",
        (day, axis_kind, axis_id, float(intensity), int(n_threads),
         method_version, _utc_now_iso()),
    )
    conn.commit()


def coverage(conn: sqlite3.Connection) -> dict:
    """Quick health readout for the runner log."""
    p = conn.execute(
        "SELECT COUNT(DISTINCT symbol), COUNT(*), MIN(date), MAX(date) "
        "FROM market_price_daily"
    ).fetchone()
    n = conn.execute(
        "SELECT COUNT(DISTINCT day), COUNT(*), MIN(day), MAX(day) "
        "FROM news_daily_intensity"
    ).fetchone()
    return {
        "price_symbols": p[0], "price_rows": p[1],
        "price_span": (p[2], p[3]),
        "news_days": n[0], "news_rows": n[1], "news_span": (n[2], n[3]),
    }
