from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query

from app.main_v2 import app
from app.services.deepseek_narrative import (
    build_deepseek_thread_narrative_note,
    deepseek_thread_notes_enabled,
)
from app.services.thread_intelligence import (
    V1_COMPAT_ENGINE_VERSION,
    fetch_thread_detail,
    fetch_threads,
    fetch_topic_relationship,
)

router = APIRouter(prefix="/api/v2", tags=["threads"])
logger = logging.getLogger(__name__)

THREADS_CACHE_TTL = 300  # 5 min — matches living-thread surge cadence
DETAIL_CACHE_TTL = 180
DETAIL_CACHE_VERSION = "v2"


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
    person: str | None = Query(None, min_length=2, max_length=80),
) -> dict:
    country = country_code.upper() if country_code else None
    person_q = person.strip() if person else None
    cache_key = f"threads:list:{hours}:{limit}:{country or 'global'}:{(person_q or '').lower()}"
    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached

    payload = {
        "beta": True,
        "hours": hours,
        "contract": "living-narrative-threads-v0",
        "country_code": country,
        "person": person_q,
        # #234: when filtering by person, search a wider ranked pool so the
        # person's threads aren't lost below the display limit.
        "threads": await fetch_threads(
            hours=hours,
            limit=40 if person_q else limit,
            country_codes=[country] if country else None,
            person=person_q,
        ),
    }
    await _cache_set(cache_key, payload, THREADS_CACHE_TTL)
    return payload


@router.get("/topic/{topic_id}/relationship")
async def get_topic_relationship(
    topic_id: str,
    hours: int = Query(168, ge=1, le=720),
) -> dict:
    """Unified Engine F0.4 (spec §9.2): the #168 relationship type for a topic,
    computed from typed `topic_members` role counts — media-led / public-led /
    social-led / silent-risk / uncoupled-attention. Closes the serving half of
    #168 and re-homes #172's silent-risk on the discussion/evidence ratio.

    Accepts either a raw topic_id (`<atlas-slug>` or `dynamic-topic-<n>`) or a
    served thread_id (`<slug>--<cc>`); the `--<cc>` country suffix is stripped to
    the underlying topic."""
    base = topic_id.strip().split("--", 1)[0]
    cache_key = f"topic:relationship:{base}:{hours}"
    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached

    rel = await fetch_topic_relationship(topic_id=base, hours=hours)
    payload = {
        "contract": "topic-relationship-v0",
        "topic_id": base,
        "hours": hours,
        "engine_version": V1_COMPAT_ENGINE_VERSION,
        **rel,
    }
    await _cache_set(cache_key, payload, DETAIL_CACHE_TTL)
    return payload


@router.get("/topic/{topic_id}/discussion")
async def get_topic_discussion(
    topic_id: str,
    hours: int = Query(168, ge=1, le=720),
) -> dict:
    """#237 Phase 1 — the POSTS behind the relationship ratio: forum/social
    signal attached to this topic as role='discussion'. PUBLIC DISCUSSION,
    never evidence (verified=false, claim-origin layer only). Degrades to an
    empty section, never a 500."""
    from app import db
    from app.services.community_discussion import fetch_community_discussion
    base = topic_id.strip().split("--", 1)[0]
    if db.pool is None:
        return {"contract": "community-discussion-v0", "topic_id": base,
                "count": 0, "items": []}
    async with db.pool.acquire() as conn:
        return await fetch_community_discussion(
            conn, base, V1_COMPAT_ENGINE_VERSION)


@router.get("/threads/{thread_id}")
async def get_thread_detail(
    thread_id: str,
    hours: int = Query(24, ge=1, le=720),
    llm: bool = Query(False),
) -> dict:
    use_llm = llm or deepseek_thread_notes_enabled()
    cache_key = f"threads:detail:{DETAIL_CACHE_VERSION}:{thread_id}:{hours}:llm-{int(use_llm)}"
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
