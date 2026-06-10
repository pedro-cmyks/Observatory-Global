"""Research workflow endpoints (Phase 1a — read-only anchors, #215).

POST /api/v2/research/plan: deterministic intent parse + multi-lane anchor
discovery over existing thread / country / public-attention surfaces. No
ranking ledger (Phase 1b), no persistence (Phase 2), no LLM.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import db
from app.core.search_normalization import normalize_search_text
from app.main_v2 import app
from app.services.research_anchor_discovery import discover_anchors
from app.services.research_plan import parse_research_intent
from app.services.research_ranking import rank_plan
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

    plan = await discover_anchors(
        intent,
        hours=body.hours,
        fetch_threads_fn=fetch_threads,
        fetch_attention_fn=_fetch_attention,
    )
    plan = rank_plan(plan)
    plan["query"] = body.query

    if app.state.redis:
        try:
            await app.state.redis.setex(cache_key, PLAN_CACHE_TTL, json.dumps(plan, default=str))
        except Exception:
            pass

    return plan
