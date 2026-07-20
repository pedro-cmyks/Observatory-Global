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
from app.services.article_read import PROMPT_VERSION, cross_read, read_articles
from app.services.research_leads import find_leads

router = APIRouter(prefix="/api/v2/research/articles", tags=["research"])
leads_router = APIRouter(prefix="/api/v2/research", tags=["research"])
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


@router.post("/read")
async def articles_read(req: UrlsRequest):
    """F2 AI-read: quote-gated grounded reading per fetched article. Cache-first
    (ai_readings); absent text or dead LLM chain = absent entry, never invented."""
    readings = await read_articles(req.urls[:MAX_URLS])
    return {
        "contract": "workbench-ai-read-v0",
        "prompt_version": PROMPT_VERSION,
        "readings": readings,
        "note": "AI READ — claims carry verbatim quotes from the fetched text; quoteless claims were dropped at parse",
    }


@router.post("/crossread")
async def articles_crossread(req: UrlsRequest):
    """F2 cross-read: corroboration/tension map over quote-backed claims."""
    return await cross_read(req.urls[:MAX_URLS])


class LeadsRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=MAX_URLS)
    pinned_ids: list[str] = Field(default_factory=list, max_length=128)


@leads_router.post("/leads")
async def research_leads(req: LeadsRequest):
    """F2.5 LEADS: body entities interrogate the measured Atlas substrate —
    pinnable threads the analyst was not looking at. The body never writes
    the engine; it queries it."""
    return await find_leads(req.urls[:MAX_URLS], req.pinned_ids)
