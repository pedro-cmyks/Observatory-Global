"""POST /api/v2/corroborate — query-time claim corroboration (corroboration-v1).

Council Phase 3a, the publish-blocker Marcos named. Given a claim (a dossier
receipt's headline + optional focal figure/country/date), returns corroborating
and contradicting matches drawn from THREE corpora unified by relation math:

  basis=doc20         GDELT DOC 2.0 (free, no key, query-time, throttles hard)
  basis=atlas_hot     signal_embeddings semantic match (last ~8 days)
  basis=atlas_archive historical_evidence_samples text match (May-3 → present)

so corroboration spans months, not the 8-day hot window. Every corpus is
best-effort; `source_status` states exactly which lanes were reached — a
throttled DOC 2.0 never silently drops the Atlas matches (honest degraded
mode). The compact `verdict` is what the dossier renders next to a receipt.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import db
from app.services.corroboration import corroborate_claim
from app.services.research_semantic import embed_query

router = APIRouter(prefix="/api/v2", tags=["corroboration"])
logger = logging.getLogger(__name__)


class CorroborateRequest(BaseModel):
    headline: str = Field(..., min_length=3, max_length=500)
    figure: float | None = None
    country: str | None = Field(default=None, max_length=3)
    published_date: str | None = None
    # corroborate-v2 F1: the CLAIM's source language, so "1.700" from an
    # Indonesian receipt parses as 1700 and not 1.7 (council C-N17).
    lang: str | None = Field(default=None, max_length=8)


@router.post("/corroborate")
async def corroborate(body: CorroborateRequest) -> dict:
    """Corroborate a single claim across DOC 2.0 ∪ atlas_hot ∪ atlas_archive."""
    conn_holder: dict = {}

    # The cold + hot lanes need a pooled connection; acquire one only if the
    # pool exists (Fly always has it; a torch-less box still runs the DOC 2.0
    # + archive lanes). embed_query returns None where the embedder is absent,
    # and corroborate_claim then reports atlas_hot 'unavailable' honestly.
    if db.pool is not None:
        async with db.pool.acquire() as conn:
            return await corroborate_claim(
                headline=body.headline,
                figure=body.figure,
                country=(body.country or None),
                published_date=body.published_date,
                lang=(body.lang or None),
                conn=conn,
                embed_fn=lambda text: asyncio.to_thread(embed_query, text),
            )
    # No DB pool (unit/dev) — DOC 2.0 lane still runs.
    return await corroborate_claim(
        headline=body.headline,
        figure=body.figure,
        country=(body.country or None),
        published_date=body.published_date,
        lang=(body.lang or None),
    )
