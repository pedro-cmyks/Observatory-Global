"""Served market receipts for the prose guards (X3-A, 2026-08-13).

The markets endpoint (`routers/markets.py`, markets-descriptive-v0) already
serves the world bellwether basket and a country's own instruments. This module
hands the SAME rows to the synthesis path, where they exist for exactly one
purpose: to check a generated sentence that claims a market moved.

It is still descriptive. A receipt says what a price did; it never says news
moved it, and no consumer of this module may present it as a relation (that
tier stays gated on #226).

The measured direction is the LAST SESSION's net change (last close vs the
prior close in the 30-day sparkline) — not the trailing 30-day change, which
would call a market "rising" on a day it fell. When the series is too short the
change is None: an absent measurement is never read as "no move".
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, Sequence

from app import db

logger = logging.getLogger(__name__)

STATEMENT_TIMEOUT_MS = 2500
# Kept in sync with routers/markets.WORLD_BASKET (one basket, two readers).
WORLD_BASKET = ["CL=F", "GC=F", "HG=F", "^GSPC", "DX-Y.NYB", "^VIX"]


def session_change_pct(spark: Sequence[Any] | None) -> float | None:
    """Net % change of the last session (last close vs the prior close)."""
    if not spark or len(spark) < 2:
        return None
    try:
        prev, last = float(spark[-2]), float(spark[-1])
    except (TypeError, ValueError):
        return None
    if prev == 0:
        return None
    return round((last - prev) / abs(prev) * 100.0, 2)


def market_receipt_from_row(row: Any) -> dict[str, Any]:
    """Pure row → receipt dict (the SynthMarketReceipt shape)."""
    get = row.get if isinstance(row, dict) else (lambda k, d=None: row[k] if k in row.keys() else d)
    spark = get("spark_30d")
    last_close = get("last_close")
    last_close_at = get("last_close_at")
    return {
        "symbol": get("symbol"),
        "label": get("label"),
        "asset_class": get("asset_class"),
        "role": get("role"),
        "country_code": get("country_code"),
        "last_close": float(last_close) if last_close is not None else None,
        "last_close_at": last_close_at.isoformat() if hasattr(last_close_at, "isoformat")
        else (str(last_close_at) if last_close_at else None),
        "change_pct": session_change_pct(list(spark) if spark is not None else None),
    }


async def fetch_market_receipts(
    country_codes: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """World basket + the given countries' own instruments. Best-effort by
    contract: any failure returns [] and the caller's prose guard simply falls
    back to 'uncorroborated' — a missing receipt never blocks a seal."""
    codes = [str(c).upper()[:2] for c in (country_codes or []) if c]
    if db.pool is None:
        return []
    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
            rows = await conn.fetch(
                "SELECT symbol, label, asset_class, NULL::text AS role, "
                "       NULL::text AS country_code, last_close, last_close_at, spark_30d "
                "FROM market_series WHERE symbol = ANY($1::text[])",
                WORLD_BASKET,
            )
            out = [market_receipt_from_row(r) for r in rows]
            if codes:
                crows = await conn.fetch(
                    "SELECT ms.symbol, ms.label, ms.asset_class, ciu.role, "
                    "       ciu.country_code, ms.last_close, ms.last_close_at, ms.spark_30d "
                    "FROM country_instrument_universe ciu "
                    "JOIN market_series ms USING (symbol) "
                    "WHERE ciu.country_code = ANY($1::text[])",
                    codes,
                )
                seen = {r["symbol"] for r in out}
                out += [market_receipt_from_row(r) for r in crows
                        if r["symbol"] not in seen]
            return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("market receipts unavailable: %s: %s",
                       type(exc).__name__, str(exc)[:200])
        return []
