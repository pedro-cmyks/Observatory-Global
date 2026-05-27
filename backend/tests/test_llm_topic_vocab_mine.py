"""Tests for llm_topic_vocab_mine (no API calls)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import llm_topic_vocab_mine as vm


def test_parse_response_clean_payload():
    text = (
        '{"positive": ['
        '{"term": "Crop Failure", "lang": "EN", "confidence": 0.92, "why": "x"},'
        '{"term": "  ", "lang": "es", "confidence": 0.5, "why": ""}'
        '], "negative": ['
        '{"term": "harvest party", "lang": "en", "confidence": 0.7, "why": "festival"}'
        ']}'
    )
    parsed = vm._parse_response(text)
    assert len(parsed["positive"]) == 1
    p = parsed["positive"][0]
    assert p["term"] == "crop failure"
    assert p["lang"] == "en"
    assert p["confidence"] == 0.92
    assert p["role"] == "positive"
    assert len(parsed["negative"]) == 1
    assert parsed["negative"][0]["role"] == "negative"


def test_parse_response_extracts_from_codeblock():
    text = (
        "```json\n"
        '{"positive": [{"term": "war", "lang": "en", "confidence": 0.9, "why": ""}],'
        ' "negative": []}\n'
        "```"
    )
    parsed = vm._parse_response(text)
    assert parsed["positive"][0]["term"] == "war"


def test_parse_response_rejects_empty():
    try:
        vm._parse_response("")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_parse_response_skips_malformed_entries():
    text = (
        '{"positive": ['
        '{"term": "valid", "lang": "en", "confidence": 0.9, "why": ""},'
        '"not_a_dict",'
        '{"lang": "en"}'  # missing term
        '], "negative": []}'
    )
    parsed = vm._parse_response(text)
    assert len(parsed["positive"]) == 1
    assert parsed["positive"][0]["term"] == "valid"


def test_build_user_prompt_includes_topic_metadata():
    prompt = vm._build_user_prompt(
        {"slug": "disease-outbreak", "label": "Disease outbreak"},
        langs=["en", "es"],
        positive_n=10,
        negative_n=4,
    )
    assert "disease-outbreak" in prompt
    assert "Disease outbreak" in prompt
    assert "en, es" in prompt
    assert "10 POSITIVE" in prompt
    assert "4 NEGATIVE" in prompt


def test_load_topics_validates_payload(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"topics": []}')
    try:
        vm._load_topics(bad)
    except ValueError:
        return
    raise AssertionError("expected ValueError for empty topics")
