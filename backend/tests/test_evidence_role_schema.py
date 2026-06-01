from __future__ import annotations

import json

import pytest

from scripts.evidence_role_schema import (
    EVIDENCE_ROLE_SCHEMA_VERSION,
    REASON_CODES,
    ROLES,
    normalize_reason_codes,
    validate_teacher_label,
)


def test_validate_teacher_label_accepts_role_rationale_and_reason_codes():
    row = {
        "schema_version": EVIDENCE_ROLE_SCHEMA_VERSION,
        "signal_id": 101,
        "cluster_id": "2026-06-01T12:00:00Z/48",
        "headline": "Iran threatens retaliation after US sanctions",
        "cluster_label": "Iran Threats to US",
        "cluster_description": "Coverage of Iran-US threats and sanctions.",
        "candidate_topic_slug": "sanctions-diplomatic-pressure",
        "role": "reaction",
        "role_confidence": 0.86,
        "belongs_to_cluster": True,
        "supports_cluster_claim": True,
        "reason_codes": ["public_reaction", "same_actor", "same_time_window"],
        "rationale": "The headline describes a reaction by Iran inside the same Iran-US sanctions cluster.",
        "alternate_role": "context",
        "teacher_model": "deepseek-chat",
        "teacher_vendor": "deepseek",
    }

    validated = validate_teacher_label(row)

    assert validated["role"] == "reaction"
    assert validated["reason_codes"] == ["public_reaction", "same_actor", "same_time_window"]
    assert validated["role_confidence"] == 0.86


def test_validate_teacher_label_rejects_unknown_role_and_reason_code():
    bad_role = {
        "signal_id": 101,
        "cluster_id": "snap/1",
        "headline": "Headline",
        "cluster_label": "Cluster",
        "role": "rumor",
        "role_confidence": 0.5,
        "belongs_to_cluster": True,
        "supports_cluster_claim": False,
        "reason_codes": ["same_actor"],
        "rationale": "Reason",
        "teacher_model": "model",
        "teacher_vendor": "vendor",
    }
    with pytest.raises(ValueError, match="invalid evidence role"):
        validate_teacher_label(bad_role)

    bad_reason = dict(bad_role, role="context", reason_codes=["vibes"])
    with pytest.raises(ValueError, match="invalid reason code"):
        validate_teacher_label(bad_reason)


def test_normalize_reason_codes_dedupes_and_sorts_known_codes():
    assert normalize_reason_codes(["same_actor", "off_topic", "same_actor"]) == [
        "off_topic",
        "same_actor",
    ]


def test_role_and_reason_sets_are_stable_for_teacher_prompts():
    assert "primary_evidence" in ROLES
    assert "context" in ROLES
    assert "noise" in ROLES
    assert "direct_event_match" in REASON_CODES
    assert "generic_roundup" in REASON_CODES
