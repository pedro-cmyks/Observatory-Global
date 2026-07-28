"""claude_cli insight leg (2026-07-28): guards, envelope parsing, exhaustion
classification, chain fallthrough — all against a FAKE subprocess boundary
(_run_claude_cli), never the real CLI.

The exhaustion-vocabulary tests freeze the contract with the runner guard
(_ATLAS_EXHAUSTED_RE in scripts/run-*.sh, e658dddf): leg-level fallthrough
lines must NOT match it; the total-chain-failure line MUST.
"""
from __future__ import annotations

import json
import logging
import re

import pytest

pytestmark = pytest.mark.asyncio

from app.services import insight_llm
from app.services.insight_llm import (
    ClaudeCliError,
    claude_cli_available,
    classify_cli_failure,
    generate_insight,
    parse_cli_envelope,
)

# Byte-for-byte copy of the runner guard's regex (grep -E, case-insensitive).
ATLAS_EXHAUSTED_RE = re.compile(
    r"payment required|credit balance is too low|insufficient balance"
    r"|insufficient_quota|quota exceeded"
    r"|(http|status|code|error)[^0-9a-z]{0,8}402([^0-9]|$)",
    re.IGNORECASE,
)

# The 401 envelope shape measured live on the M1, 2026-07-28.
MEASURED_401_ENVELOPE = {
    "type": "result", "subtype": "success", "is_error": True,
    "api_error_status": 401, "duration_ms": 8650, "num_turns": 1,
    "result": "Failed to authenticate. API Error: 401 OAuth access token has "
              "expired. Re-authenticate to continue.",
    "total_cost_usd": 0,
    "usage": {"input_tokens": 0, "output_tokens": 0},
}

OK_ENVELOPE = {
    "type": "result", "subtype": "success", "is_error": False,
    "result": '{"verdict": "entailed", "reason": "label fits"}',
    "usage": {"input_tokens": 380, "output_tokens": 40},
}


def _enable_cli(monkeypatch, *, which="/usr/local/bin/claude"):
    monkeypatch.setenv("ATLAS_CLAUDE_CLI", "on")
    monkeypatch.delenv("FLY_APP_NAME", raising=False)
    monkeypatch.delenv("FLY_MACHINE_ID", raising=False)
    monkeypatch.setattr(insight_llm.shutil, "which", lambda _bin: which)


# ---------------------------------------------------------------- guards

def test_cli_leg_default_off(monkeypatch):
    monkeypatch.delenv("ATLAS_CLAUDE_CLI", raising=False)
    assert claude_cli_available() is False


def test_cli_leg_never_spawns_on_fly(monkeypatch):
    _enable_cli(monkeypatch)
    monkeypatch.setenv("FLY_APP_NAME", "atlas-api-pedro")
    assert claude_cli_available() is False
    monkeypatch.delenv("FLY_APP_NAME")
    monkeypatch.setenv("FLY_MACHINE_ID", "e2865932c05e18")
    assert claude_cli_available() is False


def test_cli_leg_requires_binary(monkeypatch):
    _enable_cli(monkeypatch, which=None)
    assert claude_cli_available() is False


def test_cli_leg_on_when_m1_shaped(monkeypatch):
    _enable_cli(monkeypatch)
    assert claude_cli_available() is True


# ------------------------------------------------------- envelope parsing

def test_parse_envelope_strict():
    assert parse_cli_envelope(json.dumps(OK_ENVELOPE))["is_error"] is False


def test_parse_envelope_tolerates_surrounding_noise():
    noisy = "some hook output\n" + json.dumps(OK_ENVELOPE) + "\ntrailing"
    assert parse_cli_envelope(noisy)["result"] == OK_ENVELOPE["result"]


def test_parse_envelope_truncated_or_empty_is_none():
    assert parse_cli_envelope(json.dumps(OK_ENVELOPE)[:40]) is None
    assert parse_cli_envelope("") is None
    assert parse_cli_envelope("not json at all") is None


# ------------------------------------------------- exhaustion classification

def test_measured_401_is_exhaustion():
    err = classify_cli_failure(MEASURED_401_ENVELOPE)
    assert err.exhausted is True


def test_usage_cap_text_is_exhaustion():
    env = dict(MEASURED_401_ENVELOPE, api_error_status=None,
               result="You've reached your usage limit. Your limit will reset at 3pm.")
    assert classify_cli_failure(env).exhausted is True


def test_logged_out_is_exhaustion():
    env = dict(MEASURED_401_ENVELOPE, api_error_status=None,
               result="Not logged in · Please run /login")
    assert classify_cli_failure(env).exhausted is True


def test_429_status_is_exhaustion():
    env = dict(MEASURED_401_ENVELOPE, api_error_status=429, result="overloaded")
    assert classify_cli_failure(env).exhausted is True


def test_ordinary_error_is_not_exhaustion():
    env = dict(MEASURED_401_ENVELOPE, api_error_status=None,
               result="Internal error: stream disconnected")
    err = classify_cli_failure(env)
    assert err.exhausted is False


# ------------------------------------------------------- chain fallthrough

def _fake_cli(envelope, rc=0):
    async def fake(cmd, timeout):
        return rc, json.dumps(envelope), ""
    return fake


async def test_chain_cli_success(monkeypatch):
    _enable_cli(monkeypatch)
    monkeypatch.setenv("ATLAS_INSIGHT_CHAIN", "claude_cli")
    monkeypatch.setattr(insight_llm, "_run_claude_cli", _fake_cli(OK_ENVELOPE))
    text, provider, error, usage = await generate_insight("sys", "user")
    assert provider == "claude_cli"
    assert error is None
    assert "entailed" in text
    assert usage["input_tokens"] == 380 and usage["output_tokens"] == 40
    assert usage["model"].startswith("claude-cli/")


async def test_chain_cli_exhausted_falls_through_to_deepseek(monkeypatch, caplog):
    _enable_cli(monkeypatch)
    monkeypatch.setenv("ATLAS_INSIGHT_CHAIN", "claude_cli,deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(insight_llm, "_run_claude_cli",
                        _fake_cli(MEASURED_401_ENVELOPE, rc=1))

    async def fake_deepseek(system, user, max_tokens, key):
        return "deepseek answer", {"model": "deepseek-chat",
                                   "input_tokens": 10, "output_tokens": 5}
    monkeypatch.setattr(insight_llm, "_deepseek_insight", fake_deepseek)

    with caplog.at_level(logging.WARNING):
        text, provider, error, _ = await generate_insight("sys", "user")
    assert provider == "deepseek" and text == "deepseek answer" and error is None
    # The RECOVERED chain must not emit runner-recognizable exhaustion text.
    for record in caplog.records:
        assert not ATLAS_EXHAUSTED_RE.search(record.getMessage())


async def test_chain_total_failure_cli_exhausted_is_canonical(monkeypatch, caplog):
    _enable_cli(monkeypatch)
    monkeypatch.setenv("ATLAS_INSIGHT_CHAIN", "claude_cli")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(insight_llm, "_run_claude_cli",
                        _fake_cli(MEASURED_401_ENVELOPE, rc=1))
    with caplog.at_level(logging.WARNING):
        text, provider, error, usage = await generate_insight("sys", "user")
    assert (text, provider, usage) == (None, None, None)
    assert error == "insight_cli_exhausted"
    # Total failure MUST speak the runner guard's vocabulary exactly once.
    canonical = [r for r in caplog.records
                 if ATLAS_EXHAUSTED_RE.search(r.getMessage())]
    assert len(canonical) == 1
    assert canonical[0].levelno == logging.ERROR


async def test_chain_ordinary_cli_error_not_exhaustion_code(monkeypatch, caplog):
    _enable_cli(monkeypatch)
    monkeypatch.setenv("ATLAS_INSIGHT_CHAIN", "claude_cli")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    env = dict(MEASURED_401_ENVELOPE, api_error_status=None,
               result="Internal error: stream disconnected")
    monkeypatch.setattr(insight_llm, "_run_claude_cli", _fake_cli(env, rc=1))
    with caplog.at_level(logging.WARNING):
        _, _, error, _ = await generate_insight("sys", "user")
    assert error == "insight_unavailable"
    for record in caplog.records:
        assert not ATLAS_EXHAUSTED_RE.search(record.getMessage())


async def test_chain_skips_cli_when_gated_off(monkeypatch):
    monkeypatch.delenv("ATLAS_CLAUDE_CLI", raising=False)
    monkeypatch.setenv("ATLAS_INSIGHT_CHAIN", "claude_cli")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    async def boom(cmd, timeout):  # must never run
        raise AssertionError("CLI spawned while gated off")
    monkeypatch.setattr(insight_llm, "_run_claude_cli", boom)
    text, provider, error, _ = await generate_insight("sys", "user")
    assert (text, provider) == (None, None)
    assert error == "insight_unavailable"


async def test_chain_order_env_respected(monkeypatch):
    """claude_cli first when the env says so — order is measurement-driven."""
    _enable_cli(monkeypatch)
    monkeypatch.setenv("ATLAS_INSIGHT_CHAIN", "claude_cli,deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(insight_llm, "_run_claude_cli", _fake_cli(OK_ENVELOPE))

    async def fail_deepseek(system, user, max_tokens, key):  # must not be reached
        raise AssertionError("deepseek called before claude_cli")
    monkeypatch.setattr(insight_llm, "_deepseek_insight", fail_deepseek)
    _, provider, _, _ = await generate_insight("sys", "user")
    assert provider == "claude_cli"


async def test_cli_timeout_is_ordinary_failure(monkeypatch):
    _enable_cli(monkeypatch)
    monkeypatch.setenv("ATLAS_INSIGHT_CHAIN", "claude_cli")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    async def timeout_cli(cmd, timeout):
        raise ClaudeCliError(f"claude CLI timeout after {timeout:.0f}s")
    monkeypatch.setattr(insight_llm, "_run_claude_cli", timeout_cli)
    _, _, error, _ = await generate_insight("sys", "user")
    assert error == "insight_unavailable"
