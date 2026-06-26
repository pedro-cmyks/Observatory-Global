"""Public-attention endpoint (L2 review C1).

GET /api/v2/public-attention[?country=CC&hours=&limit=]

Today this serves the forum (Reddit) discussion lane; the combined
search + wiki + forum panel (C2) layers on top of this contract.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.public_attention import fetch_forum_attention

router = APIRouter()


@router.get("/api/v2/public-attention")
async def get_public_attention(
    country: str | None = Query(None, min_length=2, max_length=2),
    hours: int = Query(168, ge=1, le=720),
    limit: int = Query(30, ge=1, le=100),
) -> dict:
    c = country.upper() if country else None
    forum = await fetch_forum_attention(country=c, hours=hours, limit=limit)
    return {
        "contract": "public-attention-v0",
        "country": c,
        "hours": hours,
        "forum": forum,
    }
