"""Tests for propose_migration_042 (no API calls, no DB)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import propose_migration_042 as pm


def test_normalize_term_lowercases_and_strips():
    assert pm._normalize_term("  Crop Failure  ") == "crop failure"


def test_normalize_term_rejects_short():
    assert pm._normalize_term("ab") is None
    assert pm._normalize_term("") is None
    assert pm._normalize_term(None) is None


def test_normalize_term_rejects_mostly_punctuation():
    assert pm._normalize_term("---,") is None


def test_normalize_term_keeps_internal_hyphen():
    assert pm._normalize_term("anti-corruption") == "anti-corruption"


def test_sql_literal_escapes_quotes():
    assert pm._sql_literal("a'b") == "'a''b'"
    assert pm._sql_literal("plain") == "'plain'"


def test_cross_topic_distractors_detects_overlap():
    rows = [
        {"topic_slug": "a", "positive": [{"term": "ENERGY CRISIS"}, {"term": "Power Cut"}]},
        {"topic_slug": "b", "positive": [{"term": "energy crisis"}, {"term": "outage"}]},
    ]
    result = pm._cross_topic_distractors(rows)
    assert "energy crisis" in result["a"]
    assert "energy crisis" in result["b"]
    assert "power cut" not in result["a"]


def test_build_proposal_filters_low_confidence():
    vocab_rows = [
        {
            "topic_slug": "x",
            "positive": [
                {"term": "highconf", "lang": "en", "confidence": 0.9, "why": ""},
                {"term": "lowconf", "lang": "en", "confidence": 0.5, "why": ""},
            ],
            "negative": [],
        }
    ]
    reasoning = {"by_topic": {}}
    topics_meta = {"x": {"label": "X", "existing_lexicon": []}}
    proposal = pm._build_proposal(
        vocab_rows=vocab_rows,
        reasoning_report=reasoning,
        topics_meta=topics_meta,
        min_vocab_confidence=0.75,
    )
    out = proposal["by_topic"]["x"]
    terms = [t["term"] for t in out["terms_to_add"]]
    assert "highconf" in terms
    assert "lowconf" not in terms
    assert any(r["term"] == "lowconf" for r in out["rejected_low_confidence"])


def test_build_proposal_filters_existing_terms():
    vocab_rows = [
        {
            "topic_slug": "x",
            "positive": [
                {"term": "already-have", "lang": "en", "confidence": 0.9, "why": ""},
                {"term": "new term", "lang": "en", "confidence": 0.9, "why": ""},
            ],
            "negative": [],
        }
    ]
    reasoning = {"by_topic": {}}
    topics_meta = {"x": {"label": "X", "existing_lexicon": ["already-have"]}}
    proposal = pm._build_proposal(
        vocab_rows=vocab_rows,
        reasoning_report=reasoning,
        topics_meta=topics_meta,
        min_vocab_confidence=0.75,
    )
    terms = [t["term"] for t in proposal["by_topic"]["x"]["terms_to_add"]]
    assert "already-have" not in terms
    assert "new term" in terms


def test_build_proposal_flags_removal_from_reasoning_mining():
    vocab_rows = [
        {"topic_slug": "x", "positive": [], "negative": []},
    ]
    reasoning = {
        "by_topic": {
            "x": {
                "top_agree_terms": [],
                "top_disagree_terms": [["distractor", 5], ["one-off", 1]],
                "llm_atlas_agreement": 0.3,
            }
        }
    }
    topics_meta = {"x": {"label": "X", "existing_lexicon": ["distractor", "good-term"]}}
    proposal = pm._build_proposal(
        vocab_rows=vocab_rows,
        reasoning_report=reasoning,
        topics_meta=topics_meta,
        min_vocab_confidence=0.75,
    )
    flagged = proposal["by_topic"]["x"]["terms_to_flag_for_removal"]
    assert any(f["term"] == "distractor" for f in flagged)
    # one-off (count 1 < threshold 2) should not be flagged
    assert not any(f["term"] == "one-off" for f in flagged)


def test_render_sql_draft_skips_topics_with_no_adds():
    proposal = {
        "schema_version": pm.SCHEMA_VERSION,
        "min_vocab_confidence": 0.75,
        "by_topic": {
            "empty": {
                "label": "Empty",
                "existing_lexicon_count": 0,
                "terms_to_add": [],
                "terms_to_flag_for_removal": [],
            },
            "withadds": {
                "label": "With adds",
                "existing_lexicon_count": 2,
                "terms_to_add": [
                    {"term": "alpha", "lang": "en", "confidence": 0.9, "why": ""},
                    {"term": "beta", "lang": "en", "confidence": 0.9, "why": ""},
                ],
                "terms_to_flag_for_removal": [],
            },
        },
    }
    sql = pm.render_sql_draft(proposal)
    assert "withadds" in sql
    assert "alpha" in sql
    assert "UPDATE atlas_topics" in sql
    # Empty topic should not generate UPDATE.
    update_count = sql.count("UPDATE atlas_topics")
    assert update_count == 1
