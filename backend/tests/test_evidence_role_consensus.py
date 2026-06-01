from __future__ import annotations

from scripts.evidence_role_consensus import consensus_for_group


def test_consensus_accepts_two_of_three_role_majority():
    group = [
        {
            "signal_id": 1,
            "cluster_id": "snap/1",
            "role": "context",
            "role_confidence": 0.8,
            "reason_codes": ["background_only"],
            "teacher_vendor": "a",
            "rationale": "A",
        },
        {
            "signal_id": 1,
            "cluster_id": "snap/1",
            "role": "context",
            "role_confidence": 0.7,
            "reason_codes": ["same_actor"],
            "teacher_vendor": "b",
            "rationale": "B",
        },
        {
            "signal_id": 1,
            "cluster_id": "snap/1",
            "role": "reaction",
            "role_confidence": 0.9,
            "reason_codes": ["public_reaction"],
            "teacher_vendor": "c",
            "rationale": "C",
        },
    ]

    row = consensus_for_group(group)

    assert row["consensus_role"] == "context"
    assert row["agreement"] == "2_of_3"
    assert row["teacher_count"] == 3
    assert row["reason_codes"] == ["background_only", "same_actor"]


def test_consensus_marks_no_majority_as_disagreement():
    group = [
        {
            "signal_id": 1,
            "cluster_id": "snap/1",
            "role": "context",
            "role_confidence": 0.8,
            "reason_codes": [],
            "teacher_vendor": "a",
            "rationale": "A",
        },
        {
            "signal_id": 1,
            "cluster_id": "snap/1",
            "role": "reaction",
            "role_confidence": 0.7,
            "reason_codes": [],
            "teacher_vendor": "b",
            "rationale": "B",
        },
        {
            "signal_id": 1,
            "cluster_id": "snap/1",
            "role": "analysis",
            "role_confidence": 0.9,
            "reason_codes": [],
            "teacher_vendor": "c",
            "rationale": "C",
        },
    ]

    row = consensus_for_group(group)

    assert row["consensus_role"] is None
    assert row["agreement"] == "no_majority"


def test_consensus_does_not_make_single_teacher_gold():
    group = [
        {
            "signal_id": 1,
            "cluster_id": "snap/1",
            "role": "context",
            "role_confidence": 0.8,
            "reason_codes": ["background_only"],
            "teacher_vendor": "a",
            "rationale": "A",
        }
    ]

    row = consensus_for_group(group)

    assert row["consensus_role"] is None
    assert row["agreement"] == "insufficient_teachers"
    assert row["is_training_gold"] is False
