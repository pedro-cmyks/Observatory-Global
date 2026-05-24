from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query

from app.main_v2 import app
from app.services.thread_intelligence import fetch_thread_detail, fetch_threads

router = APIRouter(prefix="/api/v2", tags=["threads"])
logger = logging.getLogger(__name__)

THREADS_CACHE_TTL = 300  # 5 min — matches living-thread surge cadence
DETAIL_CACHE_TTL = 180


async def _cache_get(key: str) -> dict | None:
    if not hasattr(app.state, "redis") or not app.state.redis:
        return None
    try:
        raw = await app.state.redis.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug("threads cache read failed: %s", exc)
        return None


async def _cache_set(key: str, payload: dict, ttl: int) -> None:
    if not hasattr(app.state, "redis") or not app.state.redis:
        return
    try:
        await app.state.redis.setex(key, ttl, json.dumps(payload, default=str))
    except Exception as exc:
        logger.debug("threads cache write failed: %s", exc)


@router.get("/threads")
async def get_threads(
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    cache_key = f"threads:list:{hours}:{limit}"
    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached

    payload = {
        "beta": True,
        "hours": hours,
        "contract": "living-narrative-threads-v0",
        "threads": await fetch_threads(hours=hours, limit=limit),
    }
    await _cache_set(cache_key, payload, THREADS_CACHE_TTL)
    return payload


@router.get("/threads/{thread_id}")
async def get_thread_detail(
    thread_id: str,
    hours: int = Query(24, ge=1, le=720),
) -> dict:
    cache_key = f"threads:detail:{thread_id}:{hours}"
    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached

    thread = await fetch_thread_detail(thread_id=thread_id, hours=hours)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    payload = {
        "beta": True,
        "hours": hours,
        "contract": "living-narrative-threads-v0",
        "thread": thread,
    }
    await _cache_set(cache_key, payload, DETAIL_CACHE_TTL)
    return payload
