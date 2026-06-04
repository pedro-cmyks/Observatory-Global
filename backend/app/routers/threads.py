from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query

from app.main_v2 import app
from app.services.deepseek_narrative import (
    build_deepseek_thread_narrative_note,
    deepseek_thread_notes_enabled,
)
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
    country_code: str | None = Query(None, min_length=2, max_length=2),
) -> dict:
    country = country_code.upper() if country_code else None
    cache_key = f"threads:list:{hours}:{limit}:{country or 'global'}"
    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached

    payload = {
        "beta": True,
        "hours": hours,
        "contract": "living-narrative-threads-v0",
        "country_code": country,
        "threads": await fetch_threads(
            hours=hours,
            limit=limit,
            country_codes=[country] if country else None,
        ),
    }
    await _cache_set(cache_key, payload, THREADS_CACHE_TTL)
    return payload


@router.get("/threads/{thread_id}")
async def get_thread_detail(
    thread_id: str,
    hours: int = Query(24, ge=1, le=720),
    llm: bool = Query(False),
) -> dict:
    use_llm = llm or deepseek_thread_notes_enabled()
    cache_key = f"threads:detail:{thread_id}:{hours}:llm-{int(use_llm)}"
    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached

    thread = await fetch_thread_detail(thread_id=thread_id, hours=hours)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    if use_llm:
        llm_note = await build_deepseek_thread_narrative_note(thread)
        if llm_note is not None:
            thread["narrative_note"] = llm_note
    payload = {
        "beta": True,
        "hours": hours,
        "contract": "living-narrative-threads-v0",
        "thread": thread,
    }
    await _cache_set(cache_key, payload, DETAIL_CACHE_TTL)
    return payload
