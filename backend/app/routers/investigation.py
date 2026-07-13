"""Stateless typed Investigation Graph node normalization."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app import db
from app.services.investigation_nodes import (
    CONTRACT,
    ResolveNodeInput,
    resolve_investigation_node,
)
from app.services.thread_intelligence import fetch_thread_detail

router = APIRouter(prefix="/api/v2/investigation", tags=["investigation"])


async def _fetch_signal(signal_id: int) -> dict[str, Any] | None:
    if db.pool is None:
        return None
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, headline, snippet, source_name, source_url, source_lang,
                   country_code, timestamp, sentiment, persons, themes
            FROM signals_v2
            WHERE id = $1
            """,
            signal_id,
            timeout=5,
        )
    return dict(row) if row else None


@router.post("/resolve-node")
async def resolve_node(body: ResolveNodeInput) -> dict[str, Any]:
    node = await resolve_investigation_node(
        body,
        thread_fetcher=fetch_thread_detail,
        signal_fetcher=_fetch_signal,
    )
    statuses = {name: 0 for name in (
        "resolved", "partial", "metadata_only", "unavailable"
    )}
    statuses[node.resolution_status] = 1
    return {
        "contract": CONTRACT,
        "node": node,
        "completion": {"requested": 1, **statuses},
    }
