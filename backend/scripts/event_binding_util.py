"""Shared helpers for the event→topic movement binders (#256).

Both binders (compute_event_movement, bind_disaster_movement) run inside the
scoped-snapshot cron IMMEDIATELY after the snapshot mass-rewrites the tables
they read (dynamic_topic_members / emergent_clusters / topic_members), so they
hit stale planner stats + cold cache + autovacuum and a 120s budget with zero
retries — the 2026-07-12 silent-staleness incident. This module gives them:

- fetch_with_retry: per-statement SET LOCAL statement_timeout + bounded retries
- apply_session_budget: session statement_timeout above the pooler 2min default
- build_receipt: machine-readable freshness receipt (lag is a number, not a vibe)

Timeout discipline (2026-08-13): the pooler's effective statement_timeout is
2min (server config file — verified with SHOW), and the old client budget
(240s) sat BELOW what the bind query needs under post-snapshot contention.
The 2026-08-12 receipt logged `all_windows_timed_out` because the query's
dominant cost — the dyn_sig membership materialization + ~129k signals_v2
probes, measured 21s uncontended on 08-13 — is WINDOW-INDEPENDENT, so the
half/quarter fallback windows died exactly like the full one. Every heavy
fetch now runs inside its own transaction with a SET LOCAL statement_timeout
(the sanctioned pooler pattern, cf. etl_topic_members/_execute_guarded), and
the client backstop sits ABOVE the server budget so the server cancels first
with a clean QueryCanceledError instead of asyncpg killing a statement the
server would have finished.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Sequence

try:  # asyncpg present in prod venvs; tests only need the fallback tuple
    from asyncpg.exceptions import QueryCanceledError
    _RETRYABLE: tuple[type[BaseException], ...] = (TimeoutError, QueryCanceledError)
except Exception:  # pragma: no cover
    _RETRYABLE = (TimeoutError,)

# Per-statement server budget (SET LOCAL) — the authoritative guard.
STMT_TIMEOUT = os.environ.get("ATLAS_EVENT_BIND_STMT_TIMEOUT", "540s")
DEFAULT_QUERY_TIMEOUT = 560.0  # seconds — client backstop ABOVE the SET LOCAL budget
DEFAULT_ATTEMPTS = 2
DEFAULT_BACKOFF = 20.0


async def apply_session_budget(conn: Any, seconds: int = 540) -> None:
    """Session statement_timeout above the pooler's 2min default.

    Belt for the direct fetches outside fetch_with_retry (e.g. the receipt's
    MAX(timestamp)); the per-statement SET LOCAL inside fetch_with_retry is
    the authoritative guard for the heavy binds."""
    await conn.execute(f"SET statement_timeout = '{int(seconds)}s'")


async def fetch_with_retry(
    conn: Any,
    sql: str,
    *args: Any,
    timeout: float = DEFAULT_QUERY_TIMEOUT,
    attempts: int = DEFAULT_ATTEMPTS,
    backoff: float = DEFAULT_BACKOFF,
) -> Sequence[Any]:
    """conn.fetch with a per-statement SET LOCAL statement_timeout + retries.

    Each attempt runs in its own transaction so the SET LOCAL cannot leak past
    the statement and is guaranteed to reach the backend executing THIS
    statement under any pooling mode. Re-raises after the retry budget."""
    last_exc: BaseException | None = None
    for attempt in range(attempts):
        try:
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('statement_timeout', $1, true)", STMT_TIMEOUT
                )
                return await conn.fetch(sql, *args, timeout=timeout)
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt + 1 < attempts and backoff > 0:
                await asyncio.sleep(backoff)
    assert last_exc is not None
    raise last_exc


def build_receipt(
    *,
    engine: str,
    ingested_max: datetime | None,
    bound_max: datetime | None,
    scanned: int,
    matched: int,
    written: int,
    window_hours: int,
    now: datetime,
    window_hours_used: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Freshness receipt: how far behind ingestion the bindings are, in hours."""
    lag_hours: float | None = None
    if ingested_max is not None and bound_max is not None:
        lag_hours = round((ingested_max - bound_max).total_seconds() / 3600.0, 1)
    receipt: dict[str, Any] = {
        "engine": engine,
        "run_at": now.isoformat(),
        "window_hours": window_hours,
        "ingested_max_event_time": ingested_max.isoformat() if ingested_max else None,
        "bound_max_event_time": bound_max.isoformat() if bound_max else None,
        "lag_hours": lag_hours,
        "scanned": scanned,
        "matched": matched,
        "written": written,
    }
    if window_hours_used is not None and window_hours_used != window_hours:
        receipt["window_hours_used"] = window_hours_used
    if notes:
        receipt["notes"] = notes
    return receipt


def print_receipt(receipt: dict[str, Any]) -> None:
    print(f"RECEIPT {json.dumps(receipt, sort_keys=True)}")
