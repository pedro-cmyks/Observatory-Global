"""AI cost ledger (2026-07-07) — measure per-interaction LLM cost, don't guess.

Every paid model call (DeepSeek chat, Anthropic Haiku, OpenAI embeddings) can
drop one row in `ai_cost_events` tagged by SURFACE + real token counts + an
estimated dollar amount at a price table. `backend/scripts/ai_cost_report.py`
rolls it up.

Two entry points:
  * ``log_ai_cost(...)``   — fire-and-forget from the API process (uses db.pool,
    schedules the write on the running loop; NEVER blocks or raises).
  * ``write_ai_cost_row``  — awaitable, for offline scripts that hold their own
    asyncpg connection (e.g. the M1 typing cron).

Both compute the dollar estimate via ``price_usd`` (pure, unit-tested).

Prices are USD per 1M tokens, env-overridable with a JSON blob in
``ATLAS_AI_PRICES`` (partial — only the keys you override), e.g.::

    ATLAS_AI_PRICES='{"deepseek-chat": {"in": 0.27, "out": 1.10}}'

Model keys are matched by longest-prefix so dated ids
(``claude-haiku-4-5-20251001``) resolve to their family price.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

# USD per 1,000,000 tokens. Confirmed 2026-07-07 against public price sheets;
# override any entry via the ATLAS_AI_PRICES env JSON.
#   - deepseek-chat (V3): $0.27 in (cache-miss) / $1.10 out.
#   - Claude Haiku 4.5:   $1.00 in / $5.00 out.
#   - OpenAI text-embedding-3-small: $0.02 in (embeddings have no output tokens).
_DEFAULT_PRICES: dict[str, dict[str, float]] = {
    "deepseek-chat": {"in": 0.27, "out": 1.10},
    "deepseek-v4-flash": {"in": 0.27, "out": 1.10},
    "claude-haiku-4-5": {"in": 1.00, "out": 5.00},
    "text-embedding-3-small": {"in": 0.02, "out": 0.00},
}


def _load_prices() -> dict[str, dict[str, float]]:
    prices = {k: dict(v) for k, v in _DEFAULT_PRICES.items()}
    raw = os.getenv("ATLAS_AI_PRICES")
    if raw:
        try:
            for model, pair in json.loads(raw).items():
                prices.setdefault(model, {"in": 0.0, "out": 0.0})
                if "in" in pair:
                    prices[model]["in"] = float(pair["in"])
                if "out" in pair:
                    prices[model]["out"] = float(pair["out"])
        except Exception as exc:  # bad env should not crash the app
            logger.warning("ATLAS_AI_PRICES parse failed, using defaults: %s", exc)
    return prices


PRICES = _load_prices()


def resolve_price(model: str) -> dict[str, float]:
    """Longest-prefix match so `claude-haiku-4-5-20251001` finds `claude-haiku-4-5`."""
    if model in PRICES:
        return PRICES[model]
    best: str | None = None
    for key in PRICES:
        if model.startswith(key) and (best is None or len(key) > len(best)):
            best = key
    if best is not None:
        return PRICES[best]
    logger.warning("no price for model %r — logging cost as $0", model)
    return {"in": 0.0, "out": 0.0}


def price_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    p = resolve_price(model)
    return (input_tokens * p["in"] + output_tokens * p["out"]) / 1_000_000.0


def build_event(
    surface: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    session_id: str | None = None,
) -> dict:
    return {
        "surface": surface,
        "provider": provider,
        "model": model,
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "usd": price_usd(model, int(input_tokens or 0), int(output_tokens or 0)),
        "session_id": session_id,
    }


_INSERT_SQL = (
    "INSERT INTO ai_cost_events "
    "(surface, provider, model, input_tokens, output_tokens, usd, session_id) "
    "VALUES ($1, $2, $3, $4, $5, $6, $7)"
)


async def write_ai_cost_row(conn, event: dict) -> None:
    """Awaitable insert for callers holding their own asyncpg connection."""
    await conn.execute(
        _INSERT_SQL,
        event["surface"], event["provider"], event["model"],
        event["input_tokens"], event["output_tokens"],
        event["usd"], event.get("session_id"),
    )


async def _write_via_pool(event: dict) -> None:
    from app import db
    if db.pool is None:
        return
    try:
        async with db.pool.acquire() as conn:
            await write_ai_cost_row(conn, event)
    except Exception as exc:  # never surface into the user path
        logger.warning("ai_cost write failed: %s", exc)


def log_ai_cost(
    surface: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    session_id: str | None = None,
) -> dict:
    """Fire-and-forget cost log. Schedules the DB write on the running loop and
    returns the event dict immediately. Safe to call from sync or async code in
    the API process; a missing loop / pool just drops the row (best-effort)."""
    event = build_event(surface, provider, model, input_tokens, output_tokens, session_id)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_write_via_pool(event))
    except RuntimeError:
        # No running loop (e.g. a plain script) — caller should use
        # write_ai_cost_row with its own connection instead.
        logger.debug("log_ai_cost: no running loop, row not persisted (%s)", surface)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("log_ai_cost scheduling failed: %s", exc)
    return event
