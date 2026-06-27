"""Public-attention endpoint (L2 review C1).

GET /api/v2/public-attention[?country=CC&hours=&limit=]

Today this serves the forum (Reddit) discussion lane; the combined
search + wiki + forum panel (C2) layers on top of this contract.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.public_attention import (
    fetch_forum_attention,
    fetch_forum_thread_attention,
    parse_dynamic_topic_id,
)

router = APIRouter()


@router.get("/api/v2/public-attention")
async def get_public_attention(
    country: str | None = Query(None, min_length=2, max_length=2),
    thread: str | None = Query(None, description="dynamic-topic-<id> or bare id"),
    hours: int = Query(168, ge=1, le=720),
    limit: int = Query(30, ge=1, le=100),
) -> dict:
    # Per-thread mode (C3): semantic-neighbor forum discussion for one thread.
    # Only dynamic topics carry a centroid; other threads degrade to empty.
    topic_id = parse_dynamic_topic_id(thread)
    if thread is not None:
        forum = (
            await fetch_forum_thread_attention(
                topic_id=topic_id, hours=hours, limit=min(limit, 12)
            )
            if topic_id is not None
            else {
                "source": "reddit",
                "lane": "discussion",
                "verified": False,
                "thread_id": None,
                "count": 0,
                "items": [],
            }
        )
        return {
            "contract": "public-attention-v0",
            "thread": thread,
            "hours": hours,
            "forum": forum,
        }

    c = country.upper() if country else None
    forum = await fetch_forum_attention(country=c, hours=hours, limit=limit)
    return {
        "contract": "public-attention-v0",
        "country": c,
        "hours": hours,
        "forum": forum,
    }
