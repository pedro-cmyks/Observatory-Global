"""Lazy translation cache for signals_v2 headlines.

The brief / threads / theme-detail surfaces preserve the
original-language headline and render a translation underneath in a
secondary color. Translation is fetched on demand the first time a
consumer asks for a given (signal_id, target_lang) pair, then cached
in signal_translations (mig 047) until the signal is pruned.

Endpoints:
  GET  /api/v2/translate?signal_id=N&to=en
  POST /api/v2/translate/batch   {"signal_ids": [...], "to": "en"}
  POST /api/v2/translate/text    {"text": "...", "target_lang": "en"}

/translate/text (#204b) serves free TEXT with no signal id — dynamic-topic
LABELS ("Peluncuran Program B50") reaching the Brief/console untranslated
because TranslatableHeadline is signal_id-bound. Cache = Redis (app.state,
same client the research router uses) keyed sha1(text|target_lang), 7-day
TTL. NEVER 500s: provider failure degrades to the original text with
`degraded: true`.

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
import hashlib
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
        "add commentary or quotation marks. If the headline is already "
        f"in {target_lang}, return it unchanged.\n\n"
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
        payload = r.json()
        content = payload["choices"][0]["message"]["content"]
        # Cost ledger — real (non-cached, non-identity) DeepSeek call.
        try:
            from app.services.ai_cost import log_ai_cost
            u = payload.get("usage") or {}
            log_ai_cost("translate", "deepseek", DEEPSEEK_MODEL,
                        u.get("prompt_tokens", 0) or 0,
                        u.get("completion_tokens", 0) or 0)
        except Exception:
            pass
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


# --------------------------------------------------------------------------
# Free-TEXT translation (#204b): thread/topic labels have no signal_id, so
# the signal_translations cache can't serve them. Redis-cached instead.
# --------------------------------------------------------------------------

TEXT_CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _redis():
    """The shared app Redis client (same one the research router uses).

    Lazy import to avoid a circular import at module load (main_v2 imports
    this router); returns None when Redis is unavailable so callers degrade.
    """
    try:
        from app.main_v2 import app as _app
        return getattr(_app.state, "redis", None)
    except Exception:  # pragma: no cover - import-order edge
        return None


def _text_cache_key(text: str, target_lang: str) -> str:
    digest = hashlib.sha1(
        f"{html.unescape(text).strip()}|{target_lang.lower()}".encode("utf-8")
    ).hexdigest()
    return f"ttext:v1:{digest}"


class TranslateTextRequest(BaseModel):
    # 600, not 300: the FROM THE SOURCE excerpts are capped at
    # EXCERPT_MAX_CHARS=420 (article_fetch.py) and the 300 bound silently
    # 422'd every excerpt over it — the client renders the original on any
    # non-200, so long Russian/Arabic quotes never translated (Pedro's
    # 2026-08-11 prod walk). 600 covers the excerpt cap with margin while
    # still refusing article-length payloads.
    text: str = Field(..., min_length=1, max_length=600)
    target_lang: str = Field(..., min_length=2, max_length=2)


@router.post("/api/v2/translate/text")
async def post_translate_text(req: TranslateTextRequest) -> dict:
    target_lang = req.target_lang.lower()
    cleaned = html.unescape(req.text).strip()
    key = _text_cache_key(req.text, target_lang)

    redis = _redis()
    if redis:
        try:
            cached = await redis.get(key)
            if cached:
                data = _json.loads(cached)
                return {
                    "translated": data["translated"],
                    "same": bool(data.get("same", data["translated"] == cleaned)),
                    "cached": True,
                }
        except Exception:
            pass  # cache is best-effort; fall through to the provider

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    translated: Optional[str] = None
    if api_key and cleaned:
        try:
            async with httpx.AsyncClient() as client:
                translated = await _deepseek_translate(client, cleaned, target_lang, api_key)
        except Exception as exc:  # never 500 — degrade to the original text
            logger.warning("translate/text provider error: %s", exc)
            translated = None

    if not translated:
        # Degraded truth: no key, provider down, or empty text. Never cached
        # (a transient failure must not pin the untranslated text for 7 days).
        return {"translated": cleaned, "same": True, "cached": False, "degraded": True}

    translated = html.unescape(translated).strip()
    same = translated == cleaned
    if redis:
        try:
            await redis.setex(
                key, TEXT_CACHE_TTL_SECONDS,
                _json.dumps({"translated": translated, "same": same}),
            )
        except Exception:
            pass  # cache write is best-effort

    return {"translated": translated, "same": same, "cached": False}
