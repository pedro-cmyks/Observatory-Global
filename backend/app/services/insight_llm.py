"""B0 (L1 deep review 2026-07-05) — insight LLM provider chain.

The Brief's "Editor's Analysis" and the theme insight were Anthropic-only and
went SILENTLY dark when the key ran out of credits (~06-29, discovered 07-05).
This module gives every insight caller one chain (order via ATLAS_INSIGHT_CHAIN):

    Anthropic (if ANTHROPIC_API_KEY) → DeepSeek (if DEEPSEEK_API_KEY)
      → claude CLI (M1 only, ATLAS_CLAUDE_CLI=on) → None

The response always names the provider (or the failure), so the weekly usage
read can alert on a dead AI lane instead of the honest fallback hiding it.

claude_cli leg (2026-07-28): rides the local `claude` CLI subscription
($0 marginal) as a FAILOVER — the 07-28 measurement put DeepSeek at p50 1.5s
per court-style call while the CLI pays multi-second subprocess startup per
call, so the CLI is a de-risk leg for the single-balance failure class (the
07-24..27 L1 blackout), not a primary. Guards, in order:
  - ATLAS_CLAUDE_CLI=on required (default off — Pedro flips it);
  - never on Fly (FLY_APP_NAME / FLY_MACHINE_ID env → leg skipped: the
    containers have no authenticated CLI);
  - the binary must exist on PATH.
Exhaustion honesty: a cap-hit / dead-auth CLI response is classified as
exhaustion-of-that-leg (falls through, logged with a NON-canonical phrase so a
recovered chain never trips the runner's PROVIDER_EXHAUSTED grep). Only when
the WHOLE chain fails with the CLI leg exhausted does the final log line carry
the canonical "quota exceeded" vocabulary that the atlas_step guard
(_ATLAS_EXHAUSTED_RE, e658dddf) recognizes — the ledger fires exactly when the
step truly produced nothing.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil

import httpx

logger = logging.getLogger(__name__)

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = os.getenv("INSIGHT_DEEPSEEK_MODEL", "deepseek-chat")
ANTHROPIC_MODEL = os.getenv("INSIGHT_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# claude CLI leg — model alias resolved by the CLI itself; haiku is the right
# tier for court/insight-sized calls and the fastest headless option.
CLAUDE_CLI_BIN = os.getenv("ATLAS_CLAUDE_CLI_BIN", "claude")
CLAUDE_CLI_MODEL = os.getenv("INSIGHT_CLAUDE_CLI_MODEL", "haiku")
CLAUDE_CLI_TIMEOUT = float(os.getenv("ATLAS_CLAUDE_CLI_TIMEOUT", "120"))

DEFAULT_CHAIN = "anthropic,deepseek,claude_cli"

# Cap-hit / dead-auth dialects of the headless CLI, all = exhaustion of THIS
# leg (fall through, never fatal). The 401 shape was measured live 2026-07-28
# ("OAuth access token has expired"); the usage-limit shapes are the Max/Pro
# window cap. Substring match over the envelope's result text, lowercased.
CLI_EXHAUSTED_MARKERS = (
    "usage limit reached",
    "reached your usage limit",
    "out of extra usage",
    "limit will reset",
    "oauth access token has expired",
    "oauth token has expired",
    "not logged in",
    "please run /login",
    "credit balance",
    "insufficient_quota",
    "quota exceeded",
)
# HTTP statuses in the envelope's api_error_status that mean the account (not
# the request) is refused — same exhaustion class.
_CLI_EXHAUSTED_STATUSES = {401, 402, 403, 429}


async def _anthropic_insight(
    system: str, user: str, max_tokens: int, api_key: str,
) -> tuple[str | None, dict]:
    """Returns (text, usage) where usage = {model, input_tokens, output_tokens}."""
    import anthropic as _anthropic
    # Cap the request: the SDK default timeout is minutes, so a stalled
    # Anthropic call would otherwise hang the insight lane (and, historically,
    # the whole Brief render). The chain falls through to DeepSeek on failure.
    client = _anthropic.AsyncAnthropic(api_key=api_key, timeout=20.0)
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


class ClaudeCliError(Exception):
    """CLI leg failure. `exhausted` = cap/auth refusal (leg dead, not transient)."""

    def __init__(self, reason: str, *, exhausted: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.exhausted = exhausted


def claude_cli_available() -> bool:
    """CLI leg eligibility. Server-side (Fly) must NEVER spawn the CLI: the
    containers carry no authenticated binary, and FLY_APP_NAME/FLY_MACHINE_ID
    are set by the Fly runtime — their absence + an on-PATH binary is the M1
    marker (the mlvenv/runner env)."""
    if os.getenv("ATLAS_CLAUDE_CLI", "off").strip().lower() not in ("on", "1", "true"):
        return False
    if os.getenv("FLY_APP_NAME") or os.getenv("FLY_MACHINE_ID"):
        return False
    return shutil.which(CLAUDE_CLI_BIN) is not None


def parse_cli_envelope(stdout: str) -> dict | None:
    """`--output-format json` envelope → dict, tolerant of stray output around
    it (same truncation-repair discipline as the DeepSeek JSON consumers:
    strict parse first, then the outermost {...} span). None = unparseable."""
    raw = (stdout or "").strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, ValueError):
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(raw[start:end + 1])
            return obj if isinstance(obj, dict) else None
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def classify_cli_failure(envelope: dict | None, stderr: str = "") -> ClaudeCliError:
    """Failed CLI response → typed error. Cap-hit / dead-auth = exhausted
    (the leg is dry for the session window — falling through is the honest
    move); anything else = ordinary transient failure."""
    text = ""
    status = None
    if envelope:
        text = str(envelope.get("result") or "")
        status = envelope.get("api_error_status")
    blob = f"{text} {stderr or ''}".lower()
    if status in _CLI_EXHAUSTED_STATUSES or any(m in blob for m in CLI_EXHAUSTED_MARKERS):
        detail = text or stderr or f"api_error_status={status}"
        return ClaudeCliError(detail[:200], exhausted=True)
    return ClaudeCliError((text or stderr or "claude CLI error")[:200])


async def _run_claude_cli(cmd: list[str], timeout: float) -> tuple[int, str, str]:
    """Isolated subprocess boundary (tests monkeypatch this). Kills on timeout."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise ClaudeCliError(f"claude CLI timeout after {timeout:.0f}s") from None
    return proc.returncode or 0, out.decode(errors="replace"), err.decode(errors="replace")


async def _claude_cli_insight(
    system: str, user: str, max_tokens: int,
) -> tuple[str | None, dict]:
    """One headless CLI call. --safe-mode keeps subscription OAuth working while
    skipping hooks/plugins/MCP startup (--bare would DISABLE keychain auth —
    measured 2026-07-28: bare always answers "Not logged in"). --tools ""
    disables tool use: insight calls are pure text generation. The CLI has no
    max-tokens flag; the prompts bound their own length (max_tokens unused)."""
    cmd = [
        CLAUDE_CLI_BIN, "-p", user,
        "--system-prompt", system,
        "--output-format", "json",
        "--model", CLAUDE_CLI_MODEL,
        "--safe-mode",
        "--no-session-persistence",
        "--tools", "",
    ]
    rc, stdout, stderr = await _run_claude_cli(cmd, CLAUDE_CLI_TIMEOUT)
    envelope = parse_cli_envelope(stdout)
    if envelope is None:
        raise ClaudeCliError(f"unparseable CLI output (rc={rc}): {stdout[:160] or stderr[:160]}")
    if rc != 0 or envelope.get("is_error"):
        raise classify_cli_failure(envelope, stderr)
    text = str(envelope.get("result") or "").strip()
    if not text:
        raise ClaudeCliError("empty CLI result")
    u = envelope.get("usage") or {}
    usage = {
        "model": f"claude-cli/{CLAUDE_CLI_MODEL}",
        "input_tokens": u.get("input_tokens", 0) or 0,
        "output_tokens": u.get("output_tokens", 0) or 0,
    }
    return text, usage


def _chain_order() -> list[str]:
    order = os.getenv("ATLAS_INSIGHT_CHAIN", DEFAULT_CHAIN)
    return [p.strip().lower() for p in order.split(",") if p.strip()]


async def generate_insight(
    system: str, user: str, *, max_tokens: int = 256,
    surface: str | None = None, session_id: str | None = None,
) -> tuple[str | None, str | None, str | None, dict | None]:
    """Returns (text, provider, error_code, usage). Exactly one of text/error is set.

    usage = {model, input_tokens, output_tokens} for the provider that answered
    (None on failure). When `surface` is given, the cost is also logged to the
    ai_cost_events ledger (fire-and-forget — never blocks or raises).

    Chain order comes from ATLAS_INSIGHT_CHAIN (default anthropic,deepseek,
    claude_cli); a leg missing its key/binary/flag is skipped silently, a leg
    that errors falls through loudly (logged, never silent).

    error codes: 'insight_no_credits' (Anthropic broke AND nothing after it
    answered), 'insight_cli_exhausted' (the CLI leg hit its cap/auth wall and
    nothing answered), 'insight_unavailable' (no provider configured or all
    failed).
    """
    from app.services.ai_cost import log_ai_cost

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    anthropic_error: str | None = None
    cli_exhausted = False

    for leg in _chain_order():
        if leg == "anthropic":
            if not anthropic_key:
                continue
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
        elif leg == "deepseek":
            if not deepseek_key:
                continue
            try:
                text, usage = await _deepseek_insight(system, user, max_tokens, deepseek_key)
                if text:
                    if surface:
                        log_ai_cost(surface, "deepseek", usage["model"],
                                    usage["input_tokens"], usage["output_tokens"], session_id)
                    return text, "deepseek", None, usage
            except Exception as e:
                logger.warning("deepseek insight failed: %s", str(e)[:200])
        elif leg == "claude_cli":
            if not claude_cli_available():
                continue
            try:
                text, usage = await _claude_cli_insight(system, user, max_tokens)
                if text:
                    if surface:
                        log_ai_cost(surface, "claude_cli", usage["model"],
                                    usage["input_tokens"], usage["output_tokens"], session_id)
                    return text, "claude_cli", None, usage
            except ClaudeCliError as e:
                if e.exhausted:
                    cli_exhausted = True
                    # NON-canonical phrasing on purpose: if a later leg (or a
                    # retry) recovers, this line must NOT match the runner's
                    # _ATLAS_EXHAUSTED_RE grep.
                    logger.warning("claude_cli insight leg dry (usage cap / auth): %s — falling through", e.reason)
                else:
                    logger.warning("claude_cli insight failed: %s", e.reason)
            except Exception as e:  # unexpected — never let the leg break the chain
                logger.warning("claude_cli insight failed unexpectedly: %s", str(e)[:200])
        else:
            logger.warning("unknown insight chain leg %r skipped", leg)

    if cli_exhausted:
        # Canonical vocabulary ("quota exceeded") ONLY here, on total chain
        # failure: the atlas_step guard greps failed-step output against
        # _ATLAS_EXHAUSTED_RE and must see the CLI cap as provider exhaustion.
        logger.error("insight chain produced nothing; claude_cli leg quota exceeded (usage cap)")
    error = anthropic_error or ("insight_cli_exhausted" if cli_exhausted else None) or "insight_unavailable"
    return None, None, error, None
