"""Multi-provider LLM client for the taxonomy-revision ensemble (#204).

A provider-neutral async client over the four model families Atlas can reach:
  - anthropic  (Claude, Messages API)          → claude-opus-4-8
  - deepseek   (OpenAI-compatible)             → deepseek-chat
  - openai     (Chat Completions)              → gpt-4o
  - gemini     (CLI, no API key in env)        → `gemini -p` subprocess

Raw httpx (not the per-provider SDKs) on purpose: the whole point of the ensemble
is ONE uniform call surface across heterogeneous providers, and it matches the
repo's existing LLM pattern (`app/services/deepseek_narrative.py` uses httpx).
The Anthropic wire shape follows the documented Messages API exactly
(POST /v1/messages, x-api-key + anthropic-version, content[].text response).

Each call returns the raw assistant text; callers parse JSON (use `extract_json`).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from dataclasses import dataclass

import httpx

ANTHROPIC_MODEL = os.getenv("ATLAS_ANTHROPIC_MODEL", "claude-opus-4-8")
DEEPSEEK_MODEL = os.getenv("ATLAS_DEEPSEEK_MODEL", "deepseek-chat")
OPENAI_MODEL = os.getenv("ATLAS_OPENAI_MODEL", "gpt-4o")
# Gemini via CLI default model (forcing -m to an unavailable id 400s; the CLI's
# own default is authed + works).
GEMINI_MODEL = os.getenv("ATLAS_GEMINI_MODEL", "")

# API providers reachable over HTTP with a working key/credits. Anthropic is in
# call_llm but excluded by default (this org's API credits are dry — Claude joins
# the ensemble via the orchestrator/subagent path instead, free). Override with
# ATLAS_API_PROVIDERS="deepseek,openai,anthropic".
API_PROVIDERS = tuple(
    p.strip() for p in os.getenv("ATLAS_API_PROVIDERS", "deepseek,openai").split(",") if p.strip()
)
ALL_PROVIDERS = API_PROVIDERS + ("gemini",)


@dataclass
class LLMError(Exception):
    provider: str
    message: str

    def __str__(self) -> str:  # noqa: D105
        return f"[{self.provider}] {self.message}"


def model_for(provider: str) -> str:
    return {
        "anthropic": ANTHROPIC_MODEL,
        "deepseek": DEEPSEEK_MODEL,
        "openai": OPENAI_MODEL,
        "gemini": GEMINI_MODEL,
    }[provider]


async def call_llm(
    provider: str,
    *,
    system: str,
    user: str,
    client: httpx.AsyncClient,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    json_mode: bool = True,
    model: str | None = None,
    retries: int = 4,
) -> str:
    """One uniform call across API providers. Returns the assistant text.
    Retries 429/5xx with exponential backoff (providers rate-limit under fan-out)."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            return await _call_llm_once(
                provider, system=system, user=user, client=client,
                max_tokens=max_tokens, temperature=temperature, json_mode=json_mode, model=model)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code in (429, 500, 502, 503, 529) and attempt < retries - 1:
                # honour Retry-After when present, else exponential backoff
                ra = exc.response.headers.get("retry-after")
                delay = float(ra) if (ra and ra.replace(".", "").isdigit()) else 2.0 * (2 ** attempt)
                await asyncio.sleep(min(delay, 30.0))
                last = exc
                continue
            raise
    raise last or LLMError(provider, "exhausted retries")


async def _call_llm_once(
    provider: str, *, system: str, user: str, client: httpx.AsyncClient,
    max_tokens: int, temperature: float, json_mode: bool, model: str | None,
) -> str:
    model = model or model_for(provider)
    if provider == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("anthropic", "ANTHROPIC_API_KEY not set")
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
        )
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    # OpenAI-compatible (deepseek + openai)
    if provider in ("deepseek", "openai"):
        if provider == "deepseek":
            key, url = os.getenv("DEEPSEEK_API_KEY"), "https://api.deepseek.com/chat/completions"
        else:
            key, url = os.getenv("OPENAI_API_KEY"), "https://api.openai.com/v1/chat/completions"
        if not key:
            raise LLMError(provider, "API key not set")
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        r = await client.post(
            url,
            headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
            json=body,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    raise LLMError(provider, f"unknown API provider {provider!r}")


# ── Subscription-CLI fallbacks (no API usage) ───────────────────────────────
# Pedro's Anthropic API credits are dry; OpenAI/DeepSeek API may also run low.
# Subscription paths that bypass API billing:
#   - CLAUDE  → the orchestrator / Agent tool (this Claude Code session runs on
#               the Claude subscription). `claude -p` subprocess 401s (its stored
#               token differs from the session), so the Claude annotator is the
#               orchestrator itself or a spawned subagent — handled in the gold
#               flow, not callable from this script.
#   - CODEX   → `codex exec` (ChatGPT subscription). Best-effort below; the local
#               codex is currently broken (default gpt-5.5 needs a newer CLI;
#               gpt-5/gpt-5-codex unsupported/empty; MCP servers 401; jobs table
#               missing). Wired so it works once the CLI is upgraded + MCP cleared.
# Default model only: gpt-5-codex/gpt-5 are NOT supported on a ChatGPT account
# (codex returns the model via the default; forcing -m breaks it). Empty = default.
CODEX_MODEL = os.getenv("ATLAS_CODEX_MODEL", "")


def call_codex(prompt: str, *, model: str | None = None, timeout: float = 180.0) -> str:
    """GPT via the codex CLI (ChatGPT subscription, no API usage). Uses `--json`
    (clean JSONL on stdout; the human transcript goes to stderr) and returns the
    final `agent_message` text. ~28K input tokens/call of skills/hook overhead — so
    BATCH (one call labels many items)."""
    model = model or CODEX_MODEL
    cmd = ["codex", "exec", "--json",
           "--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check"]
    if model:
        cmd[2:2] = ["-m", model]
    cmd.append(prompt)
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        raise LLMError("codex", f"CLI not found: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise LLMError("codex", "CLI timeout") from exc
    answer = None
    turn_error = None
    for line in (out.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = ev.get("item") or {}
        if ev.get("type") == "item.completed" and item.get("type") == "agent_message":
            answer = item.get("text", "")
        elif ev.get("type") in ("turn.failed", "error"):
            turn_error = ev.get("error", {}).get("message") if isinstance(ev.get("error"), dict) else ev.get("message")
    if answer:
        return answer
    raise LLMError("codex", f"no agent_message ({turn_error or (out.stderr or '')[:160]})")


def call_gemini(prompt: str, *, model: str | None = None, timeout: float = 90.0) -> str:
    """Gemini via the authenticated CLI (no API key in env). Sync subprocess —
    fine for the low-volume proposal phase; not used in bulk annotation."""
    model = model or GEMINI_MODEL
    cmd = ["gemini"] + (["-m", model] if model else []) + ["-p", prompt]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise LLMError("gemini", f"CLI not found: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise LLMError("gemini", "CLI timeout") from exc
    if out.returncode != 0:
        raise LLMError("gemini", f"CLI rc={out.returncode}: {out.stderr[:200]}")
    return out.stdout.strip()


def _iter_balanced(text: str, open_ch: str, close_ch: str):
    """Yield balanced open..close substrings (handles nested braces + strings)."""
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == open_ch:
            if depth == 0:
                start = i
            depth += 1
        elif ch == close_ch and depth:
            depth -= 1
            if depth == 0 and start >= 0:
                yield text[start:i + 1]


def extract_json(text: str):
    """Parse JSON from a model reply, tolerating ```json fences and noisy CLI
    output (codex prints hooks/MCP logs + a token count around the answer). Strategy:
    whole-string first, else the LAST balanced {..}/[..] that parses (the model's
    final answer comes last)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    last = None
    for op, cl in (("{", "}"), ("[", "]")):
        for cand in _iter_balanced(text, op, cl):
            try:
                last = json.loads(cand)
            except json.JSONDecodeError:
                continue
    if last is not None:
        return last
    raise json.JSONDecodeError("no JSON found", text, 0)


async def ping(provider: str) -> tuple[str, bool, str]:
    """Smoke one provider: ask for a 1-word JSON. Returns (provider, ok, detail)."""
    try:
        async with httpx.AsyncClient(timeout=40.0) as c:
            txt = await call_llm(
                provider,
                system="You reply only with compact JSON.",
                user='Reply exactly {"ok": true}.',
                client=c, max_tokens=20,
            )
        return provider, bool(extract_json(txt).get("ok")), txt[:60]
    except Exception as exc:  # noqa: BLE001
        return provider, False, str(exc)[:160]


async def _ping_all() -> None:
    results = await asyncio.gather(*[ping(p) for p in API_PROVIDERS])
    for prov, ok, detail in results:
        print(f"  {prov:10s} {model_for(prov):20s} {'OK' if ok else 'FAIL'}  {detail}")
    # gemini CLI (sync)
    try:
        g = call_gemini('Reply exactly {"ok": true} and nothing else.')
        print(f"  {'gemini':10s} {GEMINI_MODEL:20s} {'OK' if extract_json(g).get('ok') else 'FAIL'}  {g[:60]}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {'gemini':10s} {GEMINI_MODEL:20s} FAIL  {str(exc)[:120]}")


if __name__ == "__main__":
    print("=== ensemble provider ping ===")
    asyncio.run(_ping_all())
