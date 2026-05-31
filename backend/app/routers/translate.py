"""Lazy translation cache for signals_v2 headlines.

The brief / threads / theme-detail surfaces preserve the
original-language headline and render a translation underneath in a
secondary color. Translation is fetched on demand the first time a
consumer asks for a given (signal_id, target_lang) pair, then cached
in signal_translations (mig 047) until the signal is pruned.

Endpoints:
  GET  /api/v2/translate?signal_id=N&to=en
  POST /api/v2/translate/batch   {"signal_ids": [...], "to": "en"}

Backed by deepseek-chat (V3). Cost is trivial (~30 in / ~35 out
tokens per headline; cache makes repeat reads free). Degrades to
`translated: null` + an `error` field when DEEPSEEK_API_KEY is unset
on the API process or DeepSeek itself fails — the frontend already
falls back to the original headline in that case.

Spec: docs/superpowers/specs/2026-05-29-emergent-topic-discovery-design.md
(Translation layer).
"""
from __future__ import annotations

import asyncio
import html
import json as _json
import logging
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app import db

router = APIRouter()
logger = logging.getLogger(__name__)

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_TARGET_LANG = "en"


def _build_prompt(headline: str, target_lang: str) -> str:
    return (
        f"Translate this news headline to {target_lang} (ISO 639-1). "
        "Preserve named entities, dates, and numbers verbatim. Do not "
        "add commentary or quotation marks.\n\n"
        'Return JSON only: {"translated": "..."}\n\n'
        f"Headline:\n{headline}"
    )


async def _deepseek_translate(
    client: httpx.AsyncClient,
    headline: str,
    target_lang: str,
    api_key: str,
) -> Optional[str]:
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": _build_prompt(headline, target_lang)}],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 200,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = await client.post(DEEPSEEK_URL, json=body, headers=headers, timeout=15.0)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return _json.loads(content).get("translated")
    except Exception as exc:
        logger.warning("deepseek translate failed: %s", exc)
        return None


async def _cached(conn, signal_id: int, target_lang: str) -> Optional[dict]:
    row = await conn.fetchrow(
        "SELECT translated, model, source_lang "
        "FROM signal_translations WHERE signal_id=$1 AND target_lang=$2",
        signal_id, target_lang,
    )
    return dict(row) if row else None


async def _persist(
    conn,
    signal_id: int,
    target_lang: str,
    translated: str,
    model: str,
    source_lang: Optional[str],
) -> None:
    await conn.execute(
        """
        INSERT INTO signal_translations
            (signal_id, target_lang, translated, model, source_lang)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (signal_id, target_lang) DO UPDATE
        SET translated  = EXCLUDED.translated,
            model       = EXCLUDED.model,
            source_lang = EXCLUDED.source_lang,
            created_at  = NOW()
        """,
        signal_id, target_lang, translated, model, source_lang,
    )


async def _signal_meta(conn, signal_id: int) -> Optional[dict]:
    row = await conn.fetchrow(
        "SELECT id, headline, source_lang FROM signals_v2 WHERE id=$1",
        signal_id,
    )
    return dict(row) if row else None


async def _translate_one(
    conn,
    client: httpx.AsyncClient,
    signal_id: int,
    target_lang: str,
    api_key: Optional[str],
) -> dict:
    cached = await _cached(conn, signal_id, target_lang)
    if cached:
        return {
            "signal_id": signal_id,
            "target_lang": target_lang,
            "translated": cached["translated"],
            "source_lang": cached.get("source_lang"),
            "cached": True,
            "model": cached.get("model"),
        }

    sig = await _signal_meta(conn, signal_id)
    if not sig:
        return {
            "signal_id": signal_id,
            "target_lang": target_lang,
            "translated": None,
            "error": "not_found",
        }
    raw_headline = sig["headline"]
    source_lang = sig["source_lang"]
    if not raw_headline:
        return {
            "signal_id": signal_id,
            "target_lang": target_lang,
            "translated": None,
            "error": "no_headline",
        }

    # Identity short-circuit: no translation needed when the signal is
    # already in the target language. Cache so future reads stay free.
    if source_lang and source_lang.lower() == target_lang.lower():
        cleaned = html.unescape(raw_headline)
        await _persist(conn, signal_id, target_lang, cleaned, "identity", source_lang)
        return {
            "signal_id": signal_id,
            "target_lang": target_lang,
            "translated": cleaned,
            "source_lang": source_lang,
            "cached": False,
            "model": "identity",
        }

    if not api_key:
        return {
            "signal_id": signal_id,
            "target_lang": target_lang,
            "translated": None,
            "error": "no_api_key",
        }

    cleaned = html.unescape(raw_headline)
    translated = await _deepseek_translate(client, cleaned, target_lang, api_key)
    if not translated:
        return {
            "signal_id": signal_id,
            "target_lang": target_lang,
            "translated": None,
            "error": "translate_failed",
        }
    await _persist(conn, signal_id, target_lang, translated, DEEPSEEK_MODEL, source_lang)
    return {
        "signal_id": signal_id,
        "target_lang": target_lang,
        "translated": translated,
        "source_lang": source_lang,
        "cached": False,
        "model": DEEPSEEK_MODEL,
    }


class TranslateBatchRequest(BaseModel):
    signal_ids: list[int] = Field(..., min_length=1, max_length=64)
    to: str = DEFAULT_TARGET_LANG


@router.get("/api/v2/translate")
async def get_translate(
    signal_id: int = Query(..., ge=1),
    to: str = Query(DEFAULT_TARGET_LANG, min_length=2, max_length=8),
) -> dict:
    target_lang = to.lower()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    async with db.pool.acquire() as conn, httpx.AsyncClient() as client:
        return await _translate_one(conn, client, signal_id, target_lang, api_key)


@router.post("/api/v2/translate/batch")
async def post_translate_batch(req: TranslateBatchRequest) -> dict:
    target_lang = req.to.lower()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    async with db.pool.acquire() as conn, httpx.AsyncClient() as client:
        sem = asyncio.Semaphore(5)

        async def _task(sid: int) -> dict:
            async with sem:
                return await _translate_one(conn, client, sid, target_lang, api_key)

        results = await asyncio.gather(*(_task(sid) for sid in req.signal_ids))
    return {"target_lang": target_lang, "translations": results}
