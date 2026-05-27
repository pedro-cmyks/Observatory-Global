"""Tests for llm_reasoning_mine (no API calls)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import llm_reasoning_mine as mine


def test_tokens_strips_stopwords_and_short():
    out = mine._tokens("The Ebola outbreak in eastern Congo confirmed by WHO")
    assert "ebola" in out
    assert "outbreak" in out
    assert "eastern" in out
    assert "congo" in out
    assert "confirmed" in out
    assert "the" not in out
    assert "by" not in out  # short stopword
    assert "in" not in out


def test_tokens_handles_accented_characters():
    out = mine._tokens("Crisis económica y devaluación del peso argentino")
    assert "crisis" in out
    assert "económica" in out
    assert "devaluación" in out
    assert "peso" in out
    assert "argentino" in out


def test_tokens_returns_empty_for_empty_input():
    assert mine._tokens("") == []
    assert mine._tokens(None) == []


def test_bigrams_pairs_consecutive_tokens():
    out = mine._bigrams(["alpha", "beta", "gamma"])
    assert out == ["alpha beta", "beta gamma"]


def test_mine_agree_vs_disagree_counts():
    predictions = [
        {
            "llm_mode": "zero_shot",
            "atlas_assigned_slug": "disease-outbreak",
            "llm_predicted_slug": "disease-outbreak",
            "llm_reasoning": "Ebola cluster confirmed in eastern Congo",
        },
        {
            "llm_mode": "zero_shot",
            "atlas_assigned_slug": "disease-outbreak",
            "llm_predicted_slug": "none",
            "llm_reasoning": "Football match coverage with no health relevance",
        },
        {
            "llm_mode": "zero_shot",
            "atlas_assigned_slug": "armed-conflict-escalation",
            "llm_predicted_slug": "armed-conflict-escalation",
            "llm_reasoning": "Missile strikes on civilian targets",
        },
    ]
    report = mine.mine(predictions, mode_filter="zero_shot")
    do = report["by_topic"]["disease-outbreak"]
    assert do["agree_rows"] == 1
    assert do["disagree_rows"] == 1
    assert do["rows"] == 2
    assert do["llm_atlas_agreement"] == 0.5
    agree_terms = dict(do["top_agree_terms"])
    assert "ebola" in agree_terms
    disagree_terms = dict(do["top_disagree_terms"])
    assert "football" in disagree_terms
    targets = dict(do["disagree_targets"])
    assert targets["none"] == 1


def test_mine_skips_errored_rows():
    predictions = [
        {
            "llm_mode": "zero_shot",
            "atlas_assigned_slug": "disease-outbreak",
            "llm_predicted_slug": "disease-outbreak",
            "llm_reasoning": "skipped because errored",
            "api_error": "rate_limited",
        },
        {
            "llm_mode": "zero_shot",
            "atlas_assigned_slug": "disease-outbreak",
            "llm_predicted_slug": "disease-outbreak",
            "llm_reasoning": "Ebola cluster confirmed",
        },
    ]
    report = mine.mine(predictions, mode_filter="zero_shot")
    assert report["by_topic"]["disease-outbreak"]["rows"] == 1


def test_mine_filters_by_mode():
    predictions = [
        {
            "llm_mode": "zero_shot",
            "atlas_assigned_slug": "x",
            "llm_predicted_slug": "x",
            "llm_reasoning": "alpha beta",
        },
        {
            "llm_mode": "few_shot",
            "atlas_assigned_slug": "x",
            "llm_predicted_slug": "x",
            "llm_reasoning": "gamma delta",
        },
    ]
    report = mine.mine(predictions, mode_filter="zero_shot")
    terms = dict(report["by_topic"]["x"]["top_agree_terms"])
    assert "alpha" in terms
    assert "gamma" not in terms
