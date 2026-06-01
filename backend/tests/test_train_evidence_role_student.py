from __future__ import annotations

from scripts.train_evidence_role_student import (
    tier_from_roles,
    visible_coverage,
)


def test_tier_from_roles_promotes_verified_when_primary_evidence_is_strong():
    tier = tier_from_roles(
        [
            {"predicted_role": "primary_evidence", "role_score": 0.91},
            {"predicted_role": "primary_evidence", "role_score": 0.87},
            {"predicted_role": "context", "role_score": 0.75},
        ]
    )

    assert tier == "verified"


def test_tier_from_roles_marks_mixed_evidence_as_candidate():
    tier = tier_from_roles(
        [
            {"predicted_role": "primary_evidence", "role_score": 0.72},
            {"predicted_role": "reaction", "role_score": 0.84},
            {"predicted_role": "context", "role_score": 0.81},
        ]
    )

    assert tier == "candidate"


def test_visible_coverage_excludes_suppressed():
    rows = [
        {"tier": "verified"},
        {"tier": "candidate"},
        {"tier": "context_rich"},
        {"tier": "suppressed"},
    ]

    assert visible_coverage(rows) == 0.75
