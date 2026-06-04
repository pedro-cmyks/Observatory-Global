from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_DEEPSEEK_THREAD_NOTE_MODEL = "deepseek-v4-flash"


def deepseek_thread_notes_enabled() -> bool:
    return os.getenv("ENABLE_LLM_THREAD_NOTES", "false").lower() in {"1", "true", "yes"}


def _compact_evidence(thread: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    rows = []
    for sample in (thread.get("evidence_samples") or [])[:limit]:
        if not sample:
            continue
        rows.append({
            "headline": sample.get("headline"),
            "snippet": sample.get("snippet"),
            "source": sample.get("source"),
            "country": sample.get("country_name") or sample.get("country_code"),
            "role": sample.get("evidence_role"),
        })
    return rows


def build_deepseek_thread_note_messages(thread: dict[str, Any]) -> list[dict[str, str]]:
    payload = {
        "label": thread.get("label"),
        "signal_count": thread.get("signal_count"),
        "changed_10h": thread.get("changed_10h"),
        "trend": thread.get("trend"),
        "countries": thread.get("top_country_names") or thread.get("top_countries") or [],
        "top_sources": thread.get("top_sources") or thread.get("source_mix", {}).get("top_sources") or [],
        "source_mix": thread.get("source_mix") or {},
        "quality": thread.get("quality") or {},
        "related_threads": thread.get("related_threads") or [],
        "hourly_timeline": (thread.get("hourly_timeline") or [])[-12:],
        "evidence_samples": _compact_evidence(thread),
    }
    return [
        {
            "role": "system",
            "content": (
                "You write concise Atlas narrative intelligence notes. Use only the "
                "provided JSON. Do not invent facts. If evidence is mixed, noisy, or "
                "not a coherent story, say that clearly. Return strict JSON only with "
                "keys: lede, movement, evidence, caveat, quality. quality must be one "
                "of strong, provisional, thin."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    ]


def parse_deepseek_thread_note(raw: str, *, model: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("DeepSeek narrative note returned non-JSON content")
        return None

    quality = parsed.get("quality")
    if quality not in {"strong", "provisional", "thin"}:
        quality = "provisional"

    note = {
        "lede": str(parsed.get("lede") or "").strip(),
        "movement": str(parsed.get("movement") or "").strip(),
        "evidence": str(parsed.get("evidence") or "").strip(),
        "caveat": str(parsed.get("caveat") or "").strip() or None,
        "quality": quality,
        "source": f"deepseek:{model}",
    }
    if not note["lede"] or not note["movement"] or not note["evidence"]:
        return None
    return note


async def build_deepseek_thread_narrative_note(
    thread: dict[str, Any],
    *,
    model: str | None = None,
    timeout: float = 12.0,
) -> dict[str, Any] | None:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None

    selected_model = model or os.getenv(
        "DEEPSEEK_THREAD_NOTE_MODEL",
        DEFAULT_DEEPSEEK_THREAD_NOTE_MODEL,
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": selected_model,
                    "messages": build_deepseek_thread_note_messages(thread),
                    "temperature": 0.2,
                    "max_tokens": 420,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("DeepSeek narrative note failed: %s", exc)
        return None

    content = (
        payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    return parse_deepseek_thread_note(content, model=selected_model)
