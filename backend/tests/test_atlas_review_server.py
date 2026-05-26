from __future__ import annotations

import json

from scripts.atlas_review_server import load_review_state, normalize_update, update_review_row


def test_normalize_update_accepts_known_review_fields():
    update = normalize_update(
        {
            "accept_assistant_label": False,
            "reviewer_decision": "incorrect",
            "reviewer_scope": "noise",
            "reviewer_evidence_role": "not_evidence",
            "reviewer_error_type": "off_topic",
            "reviewer_supported_questions": ["related_thread"],
            "reviewer_parent_thread": "  parent  ",
            "unknown": "ignored",
        }
    )

    assert update == {
        "accept_assistant_label": False,
        "reviewer_decision": "incorrect",
        "reviewer_scope": "noise",
        "reviewer_evidence_role": "not_evidence",
        "reviewer_error_type": "off_topic",
        "reviewer_supported_questions": ["related_thread"],
        "reviewer_parent_thread": "parent",
    }


def test_update_review_row_persists_to_template(tmp_path):
    template = tmp_path / "review-template.jsonl"
    template.write_text(
        json.dumps(
            {
                "signal_id": 101,
                "headline": "Test headline",
                "assistant_decision": "correct",
                "reviewer_decision": None,
            }
        )
        + "\n"
    )

    state = update_review_row(
        template,
        101,
        {
            "accept_assistant_label": True,
            "reviewer_supported_questions": ["evidence_support"],
        },
    )

    [row] = [json.loads(line) for line in template.read_text().splitlines()]
    assert row["accept_assistant_label"] is True
    assert row["reviewer_supported_questions"] == ["evidence_support"]
    assert state["progress"]["ready_rows"] == 1


def test_load_review_state_returns_options_and_rows(tmp_path):
    template = tmp_path / "review-template.jsonl"
    template.write_text(json.dumps({"signal_id": 101, "headline": "Test"}) + "\n")

    state = load_review_state(template)

    assert state["rows"][0]["signal_id"] == 101
    assert "child_thread" in state["options"]["scopes"]
    assert state["progress"]["total_rows"] == 1
