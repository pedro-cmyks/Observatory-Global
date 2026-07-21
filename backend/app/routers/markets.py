"""L4 markets — the descriptive product surface (contract markets-descriptive-v0).

Serves the DESCRIPTIVE tier only (design
docs/research/markets-l4/2026-07-21-markets-relational-axis-design.md §7/§8): the
world bellwether basket + a country's OWN instruments (currency / index / champion /
export-commodity), level + trend. It NEVER serves a claim that news moved a price, a
lead-lag, a direction, or a trade signal. The discovered-relation tier stays a
reserved-but-dark slot (`relation_status: pending-validation-226`) until the #226
event study clears at ~150 trading days.

Reads the thin descriptive tables (migration 088). Prices are populated by the M1
accumulator push (markets/push_atlas_db.py); until then instruments serve with
last_close=null (honest "pending" skeleton state), never a fabricated tick.

Degradation contract mirrors voice_mix: bounded statement timeout, honest 200
`{degraded:true, reason}` shape, never a 500.
"""
import logging

import asyncpg
from fastapi import APIRouter, Query

from app import db

router = APIRouter()
logger = logging.getLogger(__name__)

CONTRACT = "markets-descriptive-v0"
STATEMENT_TIMEOUT_MS = 2500

# The fixed world bellwether basket (design §5). Order is display order.
WORLD_BASKET = ["CL=F", "GC=F", "HG=F", "^GSPC", "DX-Y.NYB", "^VIX"]

_HONESTY = ("measured market data — descriptive only; NOT a claim that news moved "
            "these, and never a trade signal. Relation analysis is gated on #226.")

_DB_BUSY_ERRORS = (
    asyncpg.exceptions.QueryCanceledError,
    asyncpg.exceptions.TooManyConnectionsError,
    asyncpg.exceptions.ConnectionDoesNotExistError,
    TimeoutError,
)


def _change_pct(spark) -> float | None:
    """Trailing net change from the sparkline (last vs first available), if present."""
    if not spark or len(spark) < 2:
        return None
    a, b = float(spark[0]), float(spark[-1])
    if a == 0:
        return None
    return round((b - a) / abs(a) * 100.0, 2)


def _serialize(row) -> dict:
    spark = list(row["spark_30d"]) if row["spark_30d"] is not None else None
    role = row["role"] if "role" in row.keys() else None
    return {
        "symbol": row["symbol"],
        "label": row["label"],
        "asset_class": row["asset_class"],
        "role": role,
        "last_close": float(row["last_close"]) if row["last_close"] is not None else None,
        "last_close_at": row["last_close_at"].isoformat() if row["last_close_at"] else None,
        "spark_30d": spark,
        "change_pct": _change_pct(spark),
        "price_pending": row["last_close"] is None,
    }


async def _relation_status(conn, country: str | None) -> str:
    """The dark relation slot. Lit only if a tier>=1 relation exists for this scope —
    which cannot happen until #226 clears (market_relation_public is empty by design)."""
    q = ("SELECT count(*) FROM market_relation_public WHERE tier >= 1"
         + (" AND axis_kind='country' AND axis_id=$1" if country else ""))
    n = await (conn.fetchval(q, country) if country else conn.fetchval(q))
    return "measured" if (n or 0) > 0 else "pending-validation-226"


@router.get("/api/v2/markets")
async def get_markets(country: str | None = Query(None, min_length=2, max_length=2)):
    """Descriptive markets: world basket (+ a country's own instruments when ?country=CC).

    Never blends into narrative data; the frontend renders these inside the
    `.atlas-instrument` container only (design §7)."""
    cc = country.upper() if country else None
    base = {
        "contract": CONTRACT,
        "tier": "descriptive",
        "relation_status": "pending-validation-226",
        "honesty": _HONESTY,
        "world": [],
        "country": None,
        "as_of": None,
        "degraded": False,
    }
    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")

            world_rows = await conn.fetch(
                "SELECT symbol,label,asset_class,last_close,last_close_at,spark_30d "
                "FROM market_series WHERE symbol = ANY($1::text[])",
                WORLD_BASKET,
            )
            by_sym = {r["symbol"]: r for r in world_rows}
            base["world"] = [_serialize(by_sym[s]) for s in WORLD_BASKET if s in by_sym]

            if cc:
                crows = await conn.fetch(
                    "SELECT ciu.symbol, ciu.role, ms.label, ms.asset_class, "
                    "ms.last_close, ms.last_close_at, ms.spark_30d "
                    "FROM country_instrument_universe ciu "
                    "JOIN market_series ms USING (symbol) "
                    "WHERE ciu.country_code = $1 "
                    "ORDER BY CASE ciu.role WHEN 'currency' THEN 0 WHEN 'index' THEN 1 "
                    "  WHEN 'champion' THEN 2 ELSE 3 END, ciu.symbol",
                    cc,
                )
                base["country"] = {
                    "country_code": cc,
                    # role is carried so the frontend country CARD can drop
                    # export-commodity (a globally-moving price beside country news is
                    # the causal trap, design §7); the dock tab may show all.
                    "instruments": [_serialize(r) for r in crows],
                    "has_own_instruments": len(crows) > 0,
                }

            base["relation_status"] = await _relation_status(conn, cc)

            dates = [r["last_close_at"] for r in world_rows if r["last_close_at"]]
            base["as_of"] = max(dates).isoformat() if dates else None
    except _DB_BUSY_ERRORS as e:
        logger.warning("markets endpoint degraded: %s", e)
        return {**base, "degraded": True, "reason": "db_busy"}
    except Exception as e:  # noqa: BLE001
        logger.error("markets endpoint error: %s", e)
        return {**base, "degraded": True, "reason": "error"}

    return base
