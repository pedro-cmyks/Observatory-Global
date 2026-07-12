"""Universe view endpoint (contract universe-v0).

The heavy build (numpy SVD + full-space neighbors + 5 topic_members joins,
~11s) lives in `app.services.universe_build` — fastapi-free so the M1 cron
builder can import it. This router only serves the precomputed
universe_snapshot (a cheap JSONB read) and triggers self-healing rebuilds.

Spec: docs/specs/2026-07-02-universe-view.md.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Query

from app import db
from app.services.universe_build import (
    TIMELINE_DAYS,
    _SNAPSHOT_FRESH_S,
    _last_good,
    _rebuild_snapshot_bg,
    store_universe_snapshot,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/v2/universe")
async def get_universe(days: int = Query(TIMELINE_DAYS, ge=7, le=90)):
    """The living story universe: bodies + full-space relations + time.

    Serves the precomputed universe_snapshot (a cheap JSONB read). A live
    rebuild is ~11s — too slow for the frontend's abort — so it happens on the
    cron / in a background task, never on the serving path when a snapshot
    already exists. Freshness is best-effort; reliability is the priority.
    """
    empty = {"contract": "universe-v0", "nodes": [], "edges": [], "meta": None}
    try:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT payload, "
                "EXTRACT(EPOCH FROM (NOW() - built_at)) AS age_s "
                "FROM universe_snapshot WHERE days = $1",
                days,
            )
    except Exception as exc:
        logger.error("universe snapshot read failed: %s", exc)
        row = None

    if row is not None:
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        _last_good[days] = payload
        # Stale → kick a non-blocking rebuild, but serve the stale snapshot NOW.
        if (row["age_s"] or 0) > _SNAPSHOT_FRESH_S:
            asyncio.create_task(_rebuild_snapshot_bg(days))
        return payload

    # No snapshot yet (first-ever load). Compute synchronously once, persist,
    # and serve; every subsequent request is the cheap read above.
    try:
        return await store_universe_snapshot(days)
    except Exception as exc:
        logger.error("universe first-build failed: %s", exc)
        if days in _last_good:
            return _last_good[days]
        return {**empty, "reason": "error"}
