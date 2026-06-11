"""Research workflow endpoints (Phase 1a — read-only anchors, #215).

POST /api/v2/research/plan: deterministic intent parse + multi-lane anchor
discovery over existing thread / country / public-attention surfaces. No
ranking ledger (Phase 1b), no persistence (Phase 2), no LLM.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import db
from app.core.search_normalization import normalize_search_text
from app.main_v2 import app
from app.services.research_anchor_discovery import discover_anchors
from app.services.research_plan import parse_research_intent
from app.services.research_ranking import rank_plan
from app.services.research_semantic import (
    embed_atlas_anchors,
    embed_query,
    fetch_atlas_topic_anchors,
    fetch_topic_centroids,
)
from app.services.thread_intelligence import fetch_threads

router = APIRouter(prefix="/api/v2/research", tags=["research"])
logger = logging.getLogger(__name__)

PLAN_CACHE_TTL = 120  # seconds — matches the search/thread cache cadence


class ResearchPlanRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    hours: int = Field(72, ge=1, le=720)
    country_code: str | None = Field(None, min_length=2, max_length=2)


async def _fetch_attention(*, country_code: str, hours: int) -> list[dict]:
    """Trending searches for a country from trends_v2 (public-attention lane)."""
    if db.pool is None:
        return []
    capped = min(int(hours), 168)  # trends are short-lived; mirror /trends/search cap
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT keyword, MIN(rank) AS rank
            FROM trends_v2
            WHERE country_code = $1
              AND timestamp > NOW() - INTERVAL '{capped} hours'
            GROUP BY keyword
            ORDER BY rank ASC
            LIMIT 30
            """,
            country_code.upper(),
        )
    return [{"keyword": r["keyword"], "rank": r["rank"]} for r in rows]


@router.post("/plan")
async def research_plan(body: ResearchPlanRequest) -> dict:
    geo_hint = [body.country_code.upper()] if body.country_code else None
    intent = parse_research_intent(body.query, geo_scope=geo_hint)

    normalized = normalize_search_text(body.query)
    cache_key = (
        f"rplan:v2:{normalized}:{'-'.join(intent['geo_scope']) or 'all'}:{body.hours}"
    )
    if app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    async def _fetch_centroids() -> list[dict]:
        if db.pool is None:
            return []
        async with db.pool.acquire() as conn:
            return await fetch_topic_centroids(conn)

    async def _fetch_atlas_anchors() -> list[dict] | None:
        if db.pool is None:
            return []
        async with db.pool.acquire() as conn:
            topics = await fetch_atlas_topic_anchors(conn)
        # embedding is CPU-blocking; cached per process after first call
        return await asyncio.to_thread(embed_atlas_anchors, topics)

    plan = await discover_anchors(
        intent,
        hours=body.hours,
        fetch_threads_fn=fetch_threads,
        fetch_attention_fn=_fetch_attention,
        # embedding is CPU-blocking (model load + encode); keep it off the loop
        embed_query_fn=lambda text: asyncio.to_thread(embed_query, text),
        fetch_centroids_fn=_fetch_centroids,
        fetch_atlas_anchors_fn=_fetch_atlas_anchors,
    )
    plan = rank_plan(plan)
    plan["query"] = body.query
    # plan_id joins pin events (#218) back to this ranked anchor list. Hashed
    # from cache key + hour bucket: cache hits within the TTL share an id.
    plan["plan_id"] = "rp-" + hashlib.sha1(
        f"{cache_key}:{int(time.time() // 3600)}".encode()
    ).hexdigest()[:16]

    if app.state.redis:
        try:
            await app.state.redis.setex(cache_key, PLAN_CACHE_TTL, json.dumps(plan, default=str))
        except Exception:
            pass

    return plan


class PinEvent(BaseModel):
    anchor_id: str = Field(..., min_length=1, max_length=300)
    event_type: Literal["impression", "open", "pin", "unpin", "dismiss"]
    anchor_type: str | None = Field(None, max_length=40)
    rank_shown: int | None = Field(None, ge=0, le=500)
    visibility: str | None = Field(None, max_length=20)
    investigative_score: float | None = Field(None, ge=0, le=1)
    dwell_ms: int | None = Field(None, ge=0)


class PinEventBatch(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=64)
    investigation_id: str | None = Field(None, max_length=64)
    query_text: str | None = Field(None, max_length=500)
    events: list[PinEvent] = Field(..., min_length=1, max_length=200)


@router.post("/events", status_code=202)
async def record_pin_events(batch: PinEventBatch) -> dict:
    """Relevance-judgment telemetry (#218): impressions/opens/pins per anchor.

    Best-effort by design — a telemetry failure must never break the
    investigation UI, so DB unavailability returns accepted=0, not a 500.
    """
    if db.pool is None:
        return {"accepted": 0, "degraded": True}
    rows = [
        (
            batch.plan_id, batch.investigation_id, e.anchor_id, e.anchor_type,
            e.event_type, e.rank_shown, e.visibility, e.investigative_score,
            batch.query_text, e.dwell_ms,
        )
        for e in batch.events
    ]
    try:
        async with db.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO research_pin_events
                    (plan_id, investigation_id, anchor_id, anchor_type,
                     event_type, rank_shown, visibility, investigative_score,
                     query_text, dwell_ms)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                """,
                rows,
            )
    except Exception as exc:
        logger.warning("pin-event write failed: %s", exc)
        return {"accepted": 0, "degraded": True}
    return {"accepted": len(rows), "degraded": False}
