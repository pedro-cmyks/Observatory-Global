"""B0 (L1 deep review 2026-07-05) — insight LLM provider chain.

The Brief's "Editor's Analysis" and the theme insight were Anthropic-only and
went SILENTLY dark when the key ran out of credits (~06-29, discovered 07-05).
This module gives every insight caller one chain:

    Anthropic (if ANTHROPIC_API_KEY) → DeepSeek (if DEEPSEEK_API_KEY) → None

The response always names the provider (or the failure), so the weekly usage
read can alert on a dead AI lane instead of the honest fallback hiding it.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = os.getenv("INSIGHT_DEEPSEEK_MODEL", "deepseek-chat")
ANTHROPIC_MODEL = os.getenv("INSIGHT_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


async def _anthropic_insight(
    system: str, user: str, max_tokens: int, api_key: str,
) -> tuple[str | None, dict]:
    """Returns (text, usage) where usage = {model, input_tokens, output_tokens}."""
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = next((b.text for b in response.content if b.type == "text"), None)
    u = getattr(response, "usage", None)
    usage = {
        "model": ANTHROPIC_MODEL,
        "input_tokens": getattr(u, "input_tokens", 0) or 0,
        "output_tokens": getattr(u, "output_tokens", 0) or 0,
    }
    return text, usage


async def _deepseek_insight(
    system: str, user: str, max_tokens: int, api_key: str,
) -> tuple[str | None, dict]:
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        r = await client.post(DEEPSEEK_URL, json=body, headers=headers, timeout=20.0)
        r.raise_for_status()
        payload = r.json()
        content = payload["choices"][0]["message"]["content"]
    u = payload.get("usage") or {}
    usage = {
        "model": DEEPSEEK_MODEL,
        "input_tokens": u.get("prompt_tokens", 0) or 0,
        "output_tokens": u.get("completion_tokens", 0) or 0,
    }
    return (content.strip() if content else None), usage


async def generate_insight(
    system: str, user: str, *, max_tokens: int = 256,
    surface: str | None = None, session_id: str | None = None,
) -> tuple[str | None, str | None, str | None, dict | None]:
    """Returns (text, provider, error_code, usage). Exactly one of text/error is set.

    usage = {model, input_tokens, output_tokens} for the provider that answered
    (None on failure). When `surface` is given, the cost is also logged to the
    ai_cost_events ledger (fire-and-forget — never blocks or raises).

    error codes: 'insight_no_credits' (Anthropic broke AND DeepSeek absent),
    'insight_unavailable' (no provider configured or all failed).
    """
    from app.services.ai_cost import log_ai_cost

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    anthropic_error: str | None = None

    if anthropic_key:
        try:
            text, usage = await _anthropic_insight(system, user, max_tokens, anthropic_key)
            if text:
                if surface:
                    log_ai_cost(surface, "anthropic", usage["model"],
                                usage["input_tokens"], usage["output_tokens"], session_id)
                return text, "anthropic", None, usage
        except Exception as e:
            err = str(e)
            anthropic_error = "insight_no_credits" if "credit balance" in err.lower() else "insight_unavailable"
            logger.warning("anthropic insight failed (%s): %s", anthropic_error, err[:200])

    if deepseek_key:
        try:
            text, usage = await _deepseek_insight(system, user, max_tokens, deepseek_key)
            if text:
                if surface:
                    log_ai_cost(surface, "deepseek", usage["model"],
                                usage["input_tokens"], usage["output_tokens"], session_id)
                return text, "deepseek", None, usage
        except Exception as e:
            logger.warning("deepseek insight failed: %s", str(e)[:200])

    return None, None, anthropic_error or "insight_unavailable", None
