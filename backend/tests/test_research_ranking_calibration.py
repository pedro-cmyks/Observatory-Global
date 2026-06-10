"""Calibration harness for ranking weights — deterministic, no DB."""
from __future__ import annotations

from app.services.research_ranking import RANKING_WEIGHTS
from app.services.research_ranking_calibration import (
    POSITIVE_COMPONENTS,
    build_gold_constraints,
    evaluate_constraints,
    sample_weight_vector,
    search_weights,
)
import random


def test_gold_constraints_well_formed():
    constraints = build_gold_constraints()
    assert len(constraints) >= 8
    ids = [c["id"] for c in constraints]
    assert len(ids) == len(set(ids))
    for c in constraints:
        assert c["winner"] is not c["loser"]
        assert c["intent"]["geo_scope"]


def test_evaluate_reports_violations_not_just_counts():
    constraints = build_gold_constraints()
    result = evaluate_constraints(RANKING_WEIGHTS, constraints)
    assert result["total"] == len(constraints)
    assert result["satisfied"] + len(result["violations"]) == result["total"]


def test_sampled_vectors_normalized():
    rng = random.Random(7)
    for _ in range(50):
        weights = sample_weight_vector(rng)
        positive_sum = sum(weights[k] for k in POSITIVE_COMPONENTS)
        assert abs(positive_sum - 1.0) < 0.01
        assert all(0.05 <= weights[k] <= 0.15
                   for k in weights if "adjustment" in k)


def test_search_is_deterministic_and_never_worse_than_baseline():
    constraints = build_gold_constraints()
    a = search_weights(constraints, n_samples=200, seed=42)
    b = search_weights(constraints, n_samples=200, seed=42)
    assert a["weights"] == b["weights"]
    assert a["evaluation"]["satisfied"] >= a["baseline_evaluation"]["satisfied"]


def test_search_finds_weights_satisfying_gold_set():
    constraints = build_gold_constraints()
    result = search_weights(constraints, n_samples=2000, seed=42)
    # the gold set encodes the spec's own acceptance criteria; a full miss
    # would mean the scoring model cannot express the spec at all
    assert result["evaluation"]["satisfied"] >= result["evaluation"]["total"] - 1
