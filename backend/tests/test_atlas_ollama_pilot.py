from __future__ import annotations

import json

from scripts.atlas_ollama_pilot import (
    build_ollama_prompt,
    normalize_ollama_annotation,
    resolve_gold_from_review_row,
    score_ollama_predictions,
)


def test_resolve_gold_prefers_reviewer_fields_over_accepted_assistant():
    row = {
        "signal_id": 42,
        "assigned_topic_slug": "transport-corridor-disruption",
        "assistant_decision": "correct",
        "assistant_scope": "parent_thread",
        "assistant_evidence_role": "background",
        "assistant_supported_questions": ["related_thread"],
        "accept_assistant_label": True,
        "reviewer_decision": "incorrect",
        "reviewer_error_type": "scope_mismatch",
        "reviewer_scope": "context_signal",
        "reviewer_evidence_role": "not_evidence",
        "reviewer_supported_questions": ["evidence_support"],
    }

    assert resolve_gold_from_review_row(row) == {
        "gold_decision": "incorrect",
        "gold_error_type": "scope_mismatch",
        "gold_scope": "context_signal",
        "gold_evidence_role": "not_evidence",
        "gold_parent_thread": None,
        "gold_child_thread": None,
        "gold_supported_questions": ["evidence_support"],
        "review_source": "reviewer_adjudicated",
    }


def test_resolve_gold_uses_assistant_only_when_explicitly_accepted():
    row = {
        "assistant_decision": "correct",
        "assistant_scope": "child_thread",
        "assistant_evidence_role": "primary_event",
        "assistant_supported_questions": ["why_moving"],
        "accept_assistant_label": True,
        "reviewer_decision": "",
    }

    assert resolve_gold_from_review_row(row) == {
        "gold_decision": "correct",
        "gold_error_type": None,
        "gold_scope": "child_thread",
        "gold_evidence_role": "primary_event",
        "gold_parent_thread": None,
        "gold_child_thread": None,
        "gold_supported_questions": ["why_moving"],
        "review_source": "assistant_accepted",
    }


def test_resolve_gold_returns_none_for_unreviewed_rows():
    row = {
        "assistant_decision": "correct",
        "accept_assistant_label": False,
        "reviewer_decision": "",
    }

    assert resolve_gold_from_review_row(row) is None


def test_normalize_ollama_annotation_accepts_json_string_and_validates_labels():
    raw = json.dumps(
        {
            "decision": " Correct ",
            "error_type": "scope_mismatch",
            "scope": "Child_Thread",
            "evidence_role": "PRIMARY_EVENT",
            "supported_questions": ["why_moving", "bad_question"],
            "notes": "Short reason",
        }
    )

    normalized = normalize_ollama_annotation(raw)

    assert normalized["ollama_decision"] == "correct"
    assert normalized["ollama_error_type"] == "scope_mismatch"
    assert normalized["ollama_scope"] == "child_thread"
    assert normalized["ollama_evidence_role"] == "primary_event"
    assert normalized["ollama_supported_questions"] == ["why_moving"]
    assert normalized["ollama_notes"] == "Short reason"
    assert normalized["validation_warnings"] == ["Invalid supported_question: 'bad_question'"]


def test_normalize_ollama_annotation_treats_string_null_and_duplicate_keys():
    raw = '{"decision":"incorrect","error_type":"null","scope":"noise","decision":null}'

    normalized = normalize_ollama_annotation(raw)

    assert normalized["ollama_decision"] == "incorrect"
    assert normalized["ollama_error_type"] is None
    assert normalized["ollama_scope"] == "noise"
    assert normalized["validation_warnings"] == []


def test_normalize_ollama_annotation_records_invalid_values_as_warnings():
    normalized = normalize_ollama_annotation(
        {
            "decision": "yes",
            "error_type": "not close",
            "scope": "topic",
            "evidence_role": "headline",
            "supported_questions": "why_moving",
        }
    )

    assert normalized["ollama_decision"] is None
    assert normalized["ollama_error_type"] is None
    assert normalized["ollama_scope"] is None
    assert normalized["ollama_evidence_role"] is None
    assert normalized["ollama_supported_questions"] == []
    assert normalized["validation_warnings"] == [
        "Invalid decision: 'yes'",
        "Invalid error_type: 'not close'",
        "Invalid scope: 'topic'",
        "Invalid evidence_role: 'headline'",
        "supported_questions must be a list",
    ]


def test_build_ollama_prompt_contains_label_schema_and_row_context():
    prompt = build_ollama_prompt(
        {
            "assigned_topic_slug": "disease-outbreak",
            "assigned_topic_label": "Disease outbreak",
            "headline": "Officials report new dengue outbreak near border",
            "source_name": "Example News",
            "country_code": "BR",
            "evidence": {"matched_terms": ["outbreak", "dengue"]},
        }
    )

    assert "Return only one JSON object" in prompt
    assert "disease-outbreak" in prompt
    assert "Officials report new dengue outbreak near border" in prompt
    assert '"decision"' in prompt
    assert "correct | incorrect | unclear" in prompt


def test_score_ollama_predictions_compares_against_resolved_gold():
    rows = [
        {
            "signal_id": 1,
            "assigned_topic_slug": "disease-outbreak",
            "gold_decision": "correct",
            "gold_scope": "child_thread",
            "gold_evidence_role": "primary_event",
            "ollama_decision": "correct",
            "ollama_scope": "child_thread",
            "ollama_evidence_role": "background",
        },
        {
            "signal_id": 2,
            "assigned_topic_slug": "disease-outbreak",
            "gold_decision": "incorrect",
            "gold_scope": "noise",
            "gold_evidence_role": "not_evidence",
            "ollama_decision": "correct",
            "ollama_scope": "noise",
            "ollama_evidence_role": "not_evidence",
        },
        {
            "signal_id": 3,
            "assigned_topic_slug": "food-price-stress",
            "gold_decision": "unclear",
            "ollama_decision": None,
            "validation_warnings": ["Invalid decision: 'maybe'"],
        },
    ]

    report = score_ollama_predictions(rows, model="llama3.2:1b")

    assert report["model"] == "llama3.2:1b"
    assert report["rows"] == 3
    assert report["scoreable_rows"] == 3
    assert report["invalid_prediction_rows"] == 1
    assert report["decision"] == {"matched": 1, "compared": 2, "accuracy": 0.5}
    assert report["scope"] == {"matched": 2, "compared": 2, "accuracy": 1.0}
    assert report["evidence_role"] == {"matched": 1, "compared": 2, "accuracy": 0.5}
