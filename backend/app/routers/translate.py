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

CASUALTY GUARD (2026-08-13, veracity scorecard claim 2). Every translation
served by any of the three lanes — fresh OR from cache — is checked against
its original for casualty figures that changed category. The witness: a
Romanian headline saying "224 de morţi şi peste 600 de răniţi" (INJURED)
reached readers as "224 dead and over 600 dead". When the guard fires the
translation is not served, not persisted and not cached; the lane returns the
original text with `error: "translation_unverified"` plus a `guard` block
naming the number and the two categories. Cache hits are checked too, on
purpose: the poisoned row is already in prod's signal_translations, so a
guard that only watched fresh provider calls would keep serving it forever.
See app/services/casualty_guard.py.

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
from app.services import casualty_guard

router = APIRouter()
logger = logging.getLogger(__name__)

UNVERIFIED = "translation_unverified"


def _verify(original: Optional[str], translated: Optional[str], **context) -> Optional[dict]:
    """None when the translation may be served; a `guard` block when it may not.

    Fails CLOSED. If our own verifier raises we do not know whether the
    number survived translation, and "we could not verify" is the honest
    answer — the frontend already renders per-receipt unavailable states. The
    lane still never 500s.
    """
    if not original or not translated:
        return None
    try:
        verdict = casualty_guard.check_translation(original, translated)
    except Exception:
        logger.exception("casualty guard raised; refusing the translation")
        return {"reason": "guard_error", "message": "translation could not be verified", "findings": []}
    if not verdict.fired:
        return None
    casualty_guard.record_fire(
        verdict, {**context, "original": original, "translated": translated}
    )
    return casualty_guard.guard_payload(verdict)

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_TARGET_LANG = "en"


# Context-aware translations carry their own model stamp so a cached
# context-free row is never mistaken for one (campaign review 2026-09-14: El
# País "40 tiendas de migrantes incendiadas" was cached as "40 migrant SHOPS
# burned" — the tents of a migrant camp; the story label "Ceuta Migrant
# Crisis" is what disambiguates `tiendas`). A caller that supplies context
# gets a context translation even when a plain one is cached, and the new
# row overwrites the old one.
CTX_MODEL = f"{DEEPSEEK_MODEL}+ctx1"
CONTEXT_MAX_CHARS = 160


def _build_prompt(headline: str, target_lang: str, context: Optional[str] = None) -> str:
    ctx = (context or "").strip()
    ctx_block = (
        "Context — the news story this headline belongs to; use it ONLY to "
        "resolve ambiguous words (e.g. in a migrant-camp story, Spanish "
        "'tiendas' means tents, not shops). Never add facts from it.\n"
        f"Story: {ctx}\n\n"
        if ctx else ""
    )
    return (
        f"Translate this news headline to {target_lang} (ISO 639-1). "
        "Preserve named entities, dates, and numbers verbatim. Do not "
        "add commentary or quotation marks. If the headline is already "
        f"in {target_lang}, return it unchanged.\n\n"
        f"{ctx_block}"
        'Return JSON only: {"translated": "..."}\n\n'
        f"Headline:\n{headline}"
    )


async def _deepseek_translate(
    client: httpx.AsyncClient,
    headline: str,
    target_lang: str,
    api_key: str,
    context: Optional[str] = None,
) -> Optional[str]:
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": _build_prompt(headline, target_lang, context)}],
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
    # The join carries the ORIGINAL headline back with the cached translation
    # so a cache hit can be guarded without a second query.
    row = await conn.fetchrow(
        "SELECT t.translated, t.model, t.source_lang, s.headline "
        "FROM signal_translations t "
        "LEFT JOIN signals_v2 s ON s.id = t.signal_id "
        "WHERE t.signal_id=$1 AND t.target_lang=$2",
        signal_id, target_lang,
    )
    return dict(row) if row else None


_PERSIST_SQL = """
    INSERT INTO signal_translations
        (signal_id, target_lang, translated, model, source_lang)
    VALUES ($1, $2, $3, $4, $5)
    ON CONFLICT (signal_id, target_lang) DO UPDATE
    SET translated  = EXCLUDED.translated,
        model       = EXCLUDED.model,
        source_lang = EXCLUDED.source_lang,
        created_at  = NOW()
"""


async def _persist(
    conn,
    signal_id: int,
    target_lang: str,
    translated: str,
    model: str,
    source_lang: Optional[str],
) -> None:
    await conn.execute(
        _PERSIST_SQL,
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
        original = html.unescape(cached.get("headline") or "")
        guard = (
            None
            if cached.get("model") == "identity"
            else _verify(
                original, cached["translated"],
                lane="signal", signal_id=signal_id, target_lang=target_lang, cached=True,
            )
        )
        if guard:
            return {
                "signal_id": signal_id,
                "target_lang": target_lang,
                "translated": None,
                "original": original,
                "source_lang": cached.get("source_lang"),
                "cached": True,
                "error": UNVERIFIED,
                "guard": guard,
            }
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
    guard = _verify(
        cleaned, translated,
        lane="signal", signal_id=signal_id, target_lang=target_lang, cached=False,
    )
    if guard:
        # Not served AND not persisted: a refused translation must not become
        # tomorrow's cache hit.
        return {
            "signal_id": signal_id,
            "target_lang": target_lang,
            "translated": None,
            "original": cleaned,
            "source_lang": source_lang,
            "cached": False,
            "error": UNVERIFIED,
            "guard": guard,
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
    # Optional story context (the story's own label) — see CTX_MODEL.
    context: Optional[str] = Field(default=None, max_length=CONTEXT_MAX_CHARS)


@router.get("/api/v2/translate")
async def get_translate(
    signal_id: int = Query(..., ge=1),
    to: str = Query(DEFAULT_TARGET_LANG, min_length=2, max_length=8),
) -> dict:
    target_lang = to.lower()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    async with db.pool.acquire() as conn, httpx.AsyncClient() as client:
        return await _translate_one(conn, client, signal_id, target_lang, api_key)


async def _cached_many(conn, signal_ids: list[int], target_lang: str) -> dict[int, dict]:
    # TWO primary-key lookups, deliberately NOT one join. The joined form
    # ("LEFT JOIN signals_v2 s ON s.id = t.signal_id") was measured in prod on
    # 2026-09-11 at 60.9s for ONE cached id: signal_translations holds ~12 rows
    # (the 7-day prune cascades into it), so the planner estimates 1 row,
    # picks a Merge Left Join and walks signals_v2's id index from the start
    # (515k buffers) to reach the key. Every /translate/batch call paid it —
    # the kit's receipt translations and "Translate all" looked dead. Both
    # lookups here are index conditions on their own PKs (0.06ms measured).
    rows = await conn.fetch(
        "SELECT signal_id, translated, model, source_lang "
        "FROM signal_translations "
        "WHERE signal_id = ANY($1::bigint[]) AND target_lang = $2",
        signal_ids, target_lang,
    )
    out = {int(r["signal_id"]): dict(r) for r in rows}
    if out:
        heads = await conn.fetch(
            "SELECT id, headline FROM signals_v2 WHERE id = ANY($1::bigint[])",
            list(out.keys()),
        )
        by_id = {int(h["id"]): h["headline"] for h in heads}
        for sid, row in out.items():
            row["headline"] = by_id.get(sid)
    return out


async def _signal_meta_many(conn, signal_ids: list[int]) -> dict[int, dict]:
    rows = await conn.fetch(
        "SELECT id, headline, source_lang FROM signals_v2 WHERE id = ANY($1::bigint[])",
        signal_ids,
    )
    return {int(r["id"]): dict(r) for r in rows}


@router.post("/api/v2/translate/batch")
async def post_translate_batch(req: TranslateBatchRequest) -> dict:
    """Translate many headlines in ONE request.

    Set-based on purpose. The first version of this endpoint acquired a single
    asyncpg connection and then handed it to five concurrent `gather` tasks;
    asyncpg forbids concurrent use of a connection, so ANY request with more
    than one id raised "another operation is in progress" and 500'd. It was
    broken from birth, nothing ever called it, and the frontend compensated by
    firing one HTTP request per receipt — ~26 per Brief load against a
    20-per-5-minutes rate-limit bucket, which is how "⇄ Translate all" became a
    silent no-op (2026-08-13 re-judge, W3).

    Now the DB is touched sequentially and in sets — one cache SELECT, one
    metadata SELECT, one write pass — while only the provider calls run
    concurrently. A 32-id batch costs 2 queries instead of 64 and cannot
    collide with itself.

    The pool connection is RELEASED before the provider fan-out and re-acquired
    to write. The old shape held one connection for the whole request, so a
    32-headline batch pinned a connection for ~15s of DeepSeek latency; on a
    10-connection pool a couple of concurrent readers were enough to starve
    every other endpoint (reproduced locally while verifying this fix).
    """
    target_lang = req.to.lower()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    context = (req.context or "").strip() or None
    provider_model = CTX_MODEL if context else DEEPSEEK_MODEL
    # Preserve request order, drop repeats: every id gets exactly one verdict.
    ids = list(dict.fromkeys(req.signal_ids))
    results: dict[int, dict] = {}
    writes: list[tuple] = []
    to_translate: list[tuple[int, str, Optional[str]]] = []

    # --- Phase 1: reads (connection held only for two set-based queries) ---
    async with db.pool.acquire() as conn:
        cached = await _cached_many(conn, ids, target_lang)
        for sid, row in cached.items():
            # A context request does not accept a context-FREE machine
            # translation from cache (identity rows are fine): re-translate
            # with the story in view and overwrite.
            if context and row.get("model") not in ("identity", CTX_MODEL):
                continue
            original = html.unescape(row.get("headline") or "")
            guard = (
                None
                if row.get("model") == "identity"
                else _verify(
                    original, row["translated"],
                    lane="signal", signal_id=sid, target_lang=target_lang, cached=True,
                )
            )
            if guard:
                results[sid] = {
                    "signal_id": sid,
                    "target_lang": target_lang,
                    "translated": None,
                    "original": original,
                    "source_lang": row.get("source_lang"),
                    "cached": True,
                    "error": UNVERIFIED,
                    "guard": guard,
                }
                continue
            results[sid] = {
                "signal_id": sid,
                "target_lang": target_lang,
                "translated": row["translated"],
                "source_lang": row.get("source_lang"),
                "cached": True,
                "model": row.get("model"),
            }
        misses = [sid for sid in ids if sid not in results]
        meta = await _signal_meta_many(conn, misses) if misses else {}

    # Identity rows (already in the target language) and the honest negatives
    # never reach the provider.
    for sid in misses:
        sig = meta.get(sid)
        if not sig:
            results[sid] = {"signal_id": sid, "target_lang": target_lang,
                            "translated": None, "error": "not_found"}
            continue
        raw = sig["headline"]
        if not raw:
            results[sid] = {"signal_id": sid, "target_lang": target_lang,
                            "translated": None, "error": "no_headline"}
            continue
        source_lang = sig["source_lang"]
        cleaned = html.unescape(raw)
        if source_lang and source_lang.lower() == target_lang:
            results[sid] = {
                "signal_id": sid, "target_lang": target_lang, "translated": cleaned,
                "source_lang": source_lang, "cached": False, "model": "identity",
            }
            writes.append((sid, target_lang, cleaned, "identity", source_lang))
            continue
        if not api_key:
            results[sid] = {"signal_id": sid, "target_lang": target_lang,
                            "translated": None, "error": "no_api_key"}
            continue
        to_translate.append((sid, cleaned, source_lang))

    # --- Phase 2: provider fan-out, holding NO connection ---
    if to_translate:
        sem = asyncio.Semaphore(5)
        async with httpx.AsyncClient() as client:
            async def _task(headline: str) -> Optional[str]:
                async with sem:
                    if context:
                        return await _deepseek_translate(
                            client, headline, target_lang, api_key, context=context)
                    return await _deepseek_translate(client, headline, target_lang, api_key)

            translated_list = await asyncio.gather(
                *(_task(headline) for _, headline, _ in to_translate)
            )
        for (sid, _cleaned, source_lang), translated in zip(to_translate, translated_list):
            if not translated:
                results[sid] = {"signal_id": sid, "target_lang": target_lang,
                                "translated": None, "error": "translate_failed"}
                continue
            guard = _verify(
                _cleaned, translated,
                lane="signal", signal_id=sid, target_lang=target_lang, cached=False,
            )
            if guard:
                # Refused rows are dropped from `writes` too — never cached.
                results[sid] = {
                    "signal_id": sid, "target_lang": target_lang, "translated": None,
                    "original": _cleaned, "source_lang": source_lang, "cached": False,
                    "error": UNVERIFIED, "guard": guard,
                }
                continue
            results[sid] = {
                "signal_id": sid, "target_lang": target_lang, "translated": translated,
                "source_lang": source_lang, "cached": False, "model": provider_model,
            }
            writes.append((sid, target_lang, translated, provider_model, source_lang))

    # --- Phase 3: one write pass ---
    if writes:
        async with db.pool.acquire() as conn:
            await conn.executemany(_PERSIST_SQL, writes)

    return {"target_lang": target_lang, "translations": [results[sid] for sid in ids]}


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


def _text_cache_key(text: str, target_lang: str, context: Optional[str] = None) -> str:
    ctx = (context or "").strip()
    digest = hashlib.sha1(
        f"{html.unescape(text).strip()}|{target_lang.lower()}|{ctx}".encode("utf-8")
    ).hexdigest()
    # v2 namespace when context rides along — a context-free cache row must
    # never answer a context request (see CTX_MODEL).
    return f"ttext:{'v2ctx' if ctx else 'v1'}:{digest}"


class TranslateTextRequest(BaseModel):
    # 600, not 300: the FROM THE SOURCE excerpts are capped at
    # EXCERPT_MAX_CHARS=420 (article_fetch.py) and the 300 bound silently
    # 422'd every excerpt over it — the client renders the original on any
    # non-200, so long Russian/Arabic quotes never translated (Pedro's
    # 2026-08-11 prod walk). 600 covers the excerpt cap with margin while
    # still refusing article-length payloads.
    text: str = Field(..., min_length=1, max_length=600)
    target_lang: str = Field(..., min_length=2, max_length=2)
    # Optional story context — see CTX_MODEL / _build_prompt.
    context: Optional[str] = Field(default=None, max_length=CONTEXT_MAX_CHARS)


def _text_unverified(original: str, guard: dict) -> dict:
    """Refusal for the free-text lane: the source text, plainly labelled.

    `degraded` is what the client already reads as "we could not measure"
    (classifyTextResponse), so an unverified translation lands in the same
    honest state as a provider outage instead of masquerading as a no-op.
    """
    return {
        "translated": original,
        "same": True,
        "cached": False,
        "degraded": True,
        "error": UNVERIFIED,
        "guard": guard,
    }


@router.post("/api/v2/translate/text")
async def post_translate_text(req: TranslateTextRequest) -> dict:
    target_lang = req.target_lang.lower()
    cleaned = html.unescape(req.text).strip()
    context = (req.context or "").strip() or None
    key = _text_cache_key(req.text, target_lang, context)

    redis = _redis()
    if redis:
        try:
            cached = await redis.get(key)
            if cached:
                data = _json.loads(cached)
                guard = _verify(
                    cleaned, data["translated"],
                    lane="text", target_lang=target_lang, cached=True,
                )
                if guard:
                    return _text_unverified(cleaned, guard)
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
                translated = (
                    await _deepseek_translate(client, cleaned, target_lang, api_key, context=context)
                    if context else
                    await _deepseek_translate(client, cleaned, target_lang, api_key)
                )
        except Exception as exc:  # never 500 — degrade to the original text
            logger.warning("translate/text provider error: %s", exc)
            translated = None

    if not translated:
        # Degraded truth: no key, provider down, or empty text. Never cached
        # (a transient failure must not pin the untranslated text for 7 days).
        return {"translated": cleaned, "same": True, "cached": False, "degraded": True}

    translated = html.unescape(translated).strip()
    guard = _verify(cleaned, translated, lane="text", target_lang=target_lang, cached=False)
    if guard:
        return _text_unverified(cleaned, guard)

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
