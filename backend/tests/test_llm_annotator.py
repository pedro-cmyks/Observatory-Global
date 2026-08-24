"""Tests for llm_annotator parsing (no API calls)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import llm_annotator as ann


def test_parse_response_full_payload():
    text = (
        '{"decision": "correct", "scope": "child_thread", '
        '"evidence_role": "primary_event", "error_type": null, '
        '"parent_thread": "ebola-outbreak-2026", "child_thread": "cd-equateur-cluster", '
        '"supported_questions": ["why_moving", "evidence_support"], '
        '"confidence": 0.85, "notes": "Ebola cluster confirmed in CD."}'
    )
    parsed = ann._parse_response(text)
    assert parsed["decision"] == "correct"
    assert parsed["scope"] == "child_thread"
    assert parsed["evidence_role"] == "primary_event"
    assert parsed["error_type"] is None
    assert parsed["parent_thread"] == "ebola-outbreak-2026"
    assert parsed["child_thread"] == "cd-equateur-cluster"
    assert parsed["supported_questions"] == ["why_moving", "evidence_support"]
    assert parsed["confidence"] == 0.85
    assert "Ebola" in parsed["notes"]


def test_parse_response_rejects_invalid_decision():
    text = '{"decision": "maybe", "scope": "domain", "evidence_role": "background"}'
    try:
        ann._parse_response(text)
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid decision")


def test_parse_response_coerces_invalid_scope_to_none():
    text = '{"decision": "correct", "scope": "weird_scope", "evidence_role": "background"}'

    parsed = ann._parse_response(text)

    assert parsed["decision"] == "correct"
    assert parsed["scope"] is None


def test_parse_response_accepts_null_optionals():
    text = (
        '{"decision": "incorrect", "scope": null, "evidence_role": null, '
        '"error_type": "off_topic", "parent_thread": null, "child_thread": null, '
        '"supported_questions": [], "confidence": 0.1, "notes": ""}'
    )
    parsed = ann._parse_response(text)
    assert parsed["scope"] is None
    assert parsed["evidence_role"] is None
    assert parsed["parent_thread"] is None
    assert parsed["child_thread"] is None
    assert parsed["supported_questions"] == []


def test_parse_response_filters_unknown_questions():
    text = (
        '{"decision": "correct", "scope": "domain", "evidence_role": "background", '
        '"error_type": null, "supported_questions": ["why_moving", "totally_invalid"], '
        '"confidence": 0.5}'
    )
    parsed = ann._parse_response(text)
    assert parsed["supported_questions"] == ["why_moving"]


def test_parse_response_handles_empty_error_type_string():
    text = (
        '{"decision": "correct", "scope": "domain", "evidence_role": "primary_event", '
        '"error_type": "", "supported_questions": [], "confidence": 0.5}'
    )
    parsed = ann._parse_response(text)
    assert parsed["error_type"] is None


def test_parse_response_normalizes_empty_threads():
    text = (
        '{"decision": "correct", "scope": "domain", "evidence_role": "primary_event", '
        '"parent_thread": "  ", "child_thread": "", "supported_questions": [], '
        '"confidence": 0.5}'
    )
    parsed = ann._parse_response(text)
    assert parsed["parent_thread"] is None
    assert parsed["child_thread"] is None


def test_build_user_prompt_includes_atlas_label():
    row = {
        "headline": "Outbreak confirmed",
        "themes": ["MEDICAL", "TAX_DISEASE_EBOLA"],
        "source_lang": "en",
        "country_code": "CD",
        "source_name": "WHO",
        "assigned_topic_slug": "disease-outbreak",
        "assigned_topic_label": "Disease outbreak",
    }
    prompt = ann._build_user_prompt(row)
    # Annotator (unlike classifier) SHOULD see the atlas assignment.
    assert "disease-outbreak" in prompt
    assert "Disease outbreak" in prompt
    assert "MEDICAL" in prompt


# --- claude-CLI anthropic leg (2026-08-24: API dry, CLI IS the provider) ---


def test_claude_cli_available_gating(monkeypatch):
    monkeypatch.delenv("ATLAS_CLAUDE_CLI", raising=False)
    assert ann._claude_cli_available() is False

    monkeypatch.setenv("ATLAS_CLAUDE_CLI", "on")
    monkeypatch.setattr(ann.shutil, "which", lambda _: "/usr/local/bin/claude")
    assert ann._claude_cli_available() is True

    # Fly machines must never spawn the CLI.
    monkeypatch.setenv("FLY_APP_NAME", "atlas-api-pedro")
    assert ann._claude_cli_available() is False
    monkeypatch.delenv("FLY_APP_NAME")

    monkeypatch.setattr(ann.shutil, "which", lambda _: None)
    assert ann._claude_cli_available() is False


def _cli_client(monkeypatch) -> "ann.ClaudeCliClient":
    monkeypatch.setenv("ATLAS_CLAUDE_CLI_BIN", "claude")
    return ann.ClaudeCliClient()


def test_call_llm_cli_branch_returns_text(monkeypatch):
    client = _cli_client(monkeypatch)
    monkeypatch.setattr(client, "complete", lambda system, user: '{"decision": "correct"}')
    text, attempts, error = ann._call_llm(
        client, model="claude-cli/sonnet", user_prompt="p",
        max_tokens=100, temperature=0.0, retries=3, backoff_seconds=0.0,
    )
    assert text == '{"decision": "correct"}'
    assert attempts == 1
    assert error is None


def test_call_llm_cli_exhausted_fails_fast(monkeypatch):
    client = _cli_client(monkeypatch)
    calls = {"n": 0}

    def _boom(system, user):
        calls["n"] += 1
        raise ann.ClaudeCliError("usage limit reached", exhausted=True)

    monkeypatch.setattr(client, "complete", _boom)
    try:
        ann._call_llm(
            client, model="claude-cli/sonnet", user_prompt="p",
            max_tokens=100, temperature=0.0, retries=3, backoff_seconds=0.0,
        )
        raise AssertionError("expected AnnotatorExhausted")
    except ann.AnnotatorExhausted:
        pass
    # Account-level refusal: exactly one attempt, no per-row retries.
    assert calls["n"] == 1


def test_call_llm_cli_transient_error_retries(monkeypatch):
    client = _cli_client(monkeypatch)
    calls = {"n": 0}

    def _flaky(system, user):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ann.ClaudeCliError("claude CLI timeout after 120s")
        return '{"decision": "incorrect"}'

    monkeypatch.setattr(client, "complete", _flaky)
    text, attempts, error = ann._call_llm(
        client, model="claude-cli/sonnet", user_prompt="p",
        max_tokens=100, temperature=0.0, retries=3, backoff_seconds=0.0,
    )
    assert text == '{"decision": "incorrect"}'
    assert attempts == 3
    assert error is None


def test_existing_signal_ids_skips_only_decided(tmp_path):
    """--resume must retry rows that were written with a null decision
    (provider error): only decided rows enter the skip set."""
    import json as _json

    out = tmp_path / "annot.jsonl"
    rows = [
        {"signal_id": 1, "annotator_decision": None,
         "annotator_error": "BadRequestError: credit balance too low"},
        {"signal_id": 2, "annotator_decision": "correct"},
    ]
    out.write_text("\n".join(_json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert ann._existing_signal_ids(out) == {2}
