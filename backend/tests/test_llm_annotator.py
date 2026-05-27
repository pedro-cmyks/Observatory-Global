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


def test_parse_response_rejects_invalid_scope():
    text = '{"decision": "correct", "scope": "weird_scope", "evidence_role": "background"}'
    try:
        ann._parse_response(text)
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid scope")


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
