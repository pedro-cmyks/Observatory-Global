"""Workbench article enrichment endpoints (contract research-articles-v0).

Spec: docs/specs/2026-07-20-workbench-article-enrichment.md — F1.

The Workbench (not the dossier) owns enrichment: pinning fires a fire-and-
forget fetch of the pin's frozen evidence URLs; the dossier only inherits.
Full extracted text NEVER crosses this API (legal posture: excerpts + citation
only); synthesize/AI-read consume it server-side via
article_fetch.full_texts_for.

Spec deviation (documented): the spec sketched `GET /articles?urls=` — URLs
contain commas/ampersands, so the lookup is a POST body instead.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.article_fetch import article_states, enqueue_fetches

router = APIRouter(prefix="/api/v2/research/articles", tags=["research"])
logger = logging.getLogger(__name__)

CONTRACT = "research-articles-v0"
MAX_URLS = 64


class UrlsRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=MAX_URLS)


@router.post("/fetch")
async def fetch_articles(req: UrlsRequest):
    """Gate + enqueue background fetches; immediate per-URL status."""
    items = await enqueue_fetches(req.urls[:MAX_URLS])
    return {"contract": CONTRACT, "items": items}


@router.post("/state")
async def articles_state(req: UrlsRequest):
    """Cached display states (status/excerpt/outlet/...) — no full text."""
    items = await article_states(req.urls[:MAX_URLS])
    found = {i["url"] for i in items}
    missing = [u for u in req.urls[:MAX_URLS] if (u or "").strip() and u not in found]
    return {"contract": CONTRACT, "items": items, "unknown": missing}
