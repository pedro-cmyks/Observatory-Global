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


async def _anthropic_insight(system: str, user: str, max_tokens: int, api_key: str) -> str | None:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return next((b.text for b in response.content if b.type == "text"), None)


async def _deepseek_insight(system: str, user: str, max_tokens: int, api_key: str) -> str | None:
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
        content = r.json()["choices"][0]["message"]["content"]
    return content.strip() if content else None


async def generate_insight(
    system: str, user: str, *, max_tokens: int = 256,
) -> tuple[str | None, str | None, str | None]:
    """Returns (text, provider, error_code). Exactly one of text/error is set.

    error codes: 'insight_no_credits' (Anthropic broke AND DeepSeek absent),
    'insight_unavailable' (no provider configured or all failed).
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    anthropic_error: str | None = None

    if anthropic_key:
        try:
            text = await _anthropic_insight(system, user, max_tokens, anthropic_key)
            if text:
                return text, "anthropic", None
        except Exception as e:
            err = str(e)
            anthropic_error = "insight_no_credits" if "credit balance" in err.lower() else "insight_unavailable"
            logger.warning("anthropic insight failed (%s): %s", anthropic_error, err[:200])

    if deepseek_key:
        try:
            text = await _deepseek_insight(system, user, max_tokens, deepseek_key)
            if text:
                return text, "deepseek", None
        except Exception as e:
            logger.warning("deepseek insight failed: %s", str(e)[:200])

    return None, None, anthropic_error or "insight_unavailable"
