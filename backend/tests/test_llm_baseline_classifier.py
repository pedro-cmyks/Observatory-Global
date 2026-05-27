"""Tests for llm_baseline_classifier parsing and scoring (no API calls)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import llm_baseline_classifier as llm  # noqa: E402


def test_parse_response_extracts_json_block():
    payload = (
        "Some preamble text.\n"
        '{"predicted_slug": "disease-outbreak", "confidence": 0.9, "reasoning": "Ebola cluster."}'
    )
    parsed = llm._parse_llm_response(payload)
    assert parsed["predicted_slug"] == "disease-outbreak"
    assert parsed["confidence"] == 0.9
    assert "Ebola" in parsed["reasoning"]


def test_parse_response_handles_strict_json():
    payload = '{"predicted_slug":"none","confidence":0.0,"reasoning":""}'
    parsed = llm._parse_llm_response(payload)
    assert parsed["predicted_slug"] == "none"
    assert parsed["confidence"] == 0.0


def test_parse_response_rejects_missing_slug():
    try:
        llm._parse_llm_response('{"confidence": 0.5}')
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError when predicted_slug is missing")


def test_gold_correct_slug_matches_assigned_when_correct():
    row = {
        "assigned_topic_slug": "disease-outbreak",
        "gold_decision": "correct",
    }
    assert llm._gold_correct_slug(row) == "disease-outbreak"


def test_gold_correct_slug_returns_none_for_incorrect():
    row = {
        "assigned_topic_slug": "disease-outbreak",
        "gold_decision": "incorrect",
    }
    assert llm._gold_correct_slug(row) is None


def _pred(**kwargs):
    base = dict(
        signal_id=1,
        headline="",
        country_code=None,
        source_lang=None,
        atlas_assigned_slug=None,
        gold_decision=None,
        gold_correct_slug=None,
        llm_mode="zero_shot",
        llm_model="claude-sonnet-4-6",
        llm_predicted_slug="",
        llm_confidence=None,
        llm_reasoning="",
        llm_raw_response="",
        api_attempts=1,
        api_error=None,
    )
    base.update(kwargs)
    return llm.Prediction(**base)


def test_score_predictions_true_positive():
    preds = [
        _pred(
            atlas_assigned_slug="disease-outbreak",
            gold_decision="correct",
            gold_correct_slug="disease-outbreak",
            llm_predicted_slug="disease-outbreak",
        )
    ]
    summary = llm.score_predictions(preds)
    mode = summary["modes"]["zero_shot"]
    assert mode["labeled"] == 1
    assert mode["llm_matches_gold_correct"] == 1
    assert mode["llm_matches_atlas_assigned"] == 1
    assert mode["confusion"]["tp"] == 1


def test_score_predictions_handles_incorrect_negative():
    preds = [
        _pred(
            atlas_assigned_slug="disease-outbreak",
            gold_decision="incorrect",
            gold_correct_slug=None,
            llm_predicted_slug="none",
        )
    ]
    summary = llm.score_predictions(preds)["modes"]["zero_shot"]
    assert summary["labeled"] == 1
    # LLM also rejected the (wrong) atlas assignment.
    assert summary["llm_matches_gold_correct"] == 1
    assert summary["confusion"]["tn_none"] == 1


def test_score_predictions_skips_unclear():
    preds = [
        _pred(gold_decision="unclear"),
        _pred(
            atlas_assigned_slug="disease-outbreak",
            gold_decision="correct",
            gold_correct_slug="disease-outbreak",
            llm_predicted_slug="disease-outbreak",
        ),
    ]
    summary = llm.score_predictions(preds)["modes"]["zero_shot"]
    assert summary["labeled"] == 1
    assert summary["gold_unlabeled_skipped"] == 1


def test_score_predictions_counts_errors():
    preds = [
        _pred(gold_decision="correct", api_error="rate_limited"),
        _pred(
            atlas_assigned_slug="disease-outbreak",
            gold_decision="correct",
            gold_correct_slug="disease-outbreak",
            llm_predicted_slug="disease-outbreak",
        ),
    ]
    summary = llm.score_predictions(preds)["modes"]["zero_shot"]
    assert summary["errors"] == 1
    assert summary["labeled"] == 1


def test_build_user_prompt_excludes_atlas_label():
    row = {
        "headline": "Ebola cluster reported",
        "themes": ["TAX_DISEASE_EBOLA"],
        "source_lang": "en",
        "country_code": "CD",
        "source_name": "WHO",
        "assigned_topic_slug": "disease-outbreak",
        "assigned_topic_label": "Disease outbreak",
    }
    topics = [{"slug": "disease-outbreak", "label": "Disease outbreak"}]
    prompt = llm._build_user_prompt(row, topics, "zero_shot")
    assert "Ebola cluster reported" in prompt
    assert "TAX_DISEASE_EBOLA" in prompt
    # Atlas's pre-existing assignment must not be passed to the LLM.
    assert "assigned_topic_slug" not in prompt
    assert "assigned_topic_label" not in prompt


def test_few_shot_prompt_contains_examples():
    row = {"headline": "h", "themes": [], "source_lang": "en", "country_code": "US", "source_name": ""}
    topics = [{"slug": "x", "label": "X"}]
    prompt = llm._build_user_prompt(row, topics, "few_shot")
    assert "Example input:" in prompt
    assert "Example output:" in prompt
    assert "Ebola" in prompt  # one of the seeded examples


def test_load_topics_snapshot(tmp_path):
    snapshot = tmp_path / "snap.json"
    snapshot.write_text(json.dumps({
        "topics": [
            {"slug": "a", "label": "Alpha"},
            {"slug": "b", "label": "Beta"},
        ],
    }))
    topics = llm._load_topics_snapshot(snapshot)
    assert [t["slug"] for t in topics] == ["a", "b"]
