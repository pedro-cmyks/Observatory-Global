"""Tests for benchmark_bootstrap statistical helpers."""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Allow importing scripts/ as a module path.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_bootstrap as bb


def test_wilson_zero_n_returns_zero_band():
    assert bb.wilson_interval(0, 0) == (0.0, 0.0)


def test_wilson_known_value_for_5_of_10():
    low, high = bb.wilson_interval(5, 10, confidence=0.95)
    # Wilson 95% CI for 5/10 is approximately [0.2366, 0.7634].
    assert math.isclose(low, 0.2366, abs_tol=0.005)
    assert math.isclose(high, 0.7634, abs_tol=0.005)


def test_wilson_extremes_are_clamped():
    low, high = bb.wilson_interval(0, 5)
    assert low == 0.0
    assert high > 0.0
    low, high = bb.wilson_interval(5, 5)
    assert low < 1.0
    assert high == 1.0


def test_decision_of_prefers_gold_over_reviewer():
    row = {"gold_decision": "correct", "reviewer_decision": "incorrect"}
    assert bb._decision_of(row) == "correct"


def test_decision_of_returns_none_for_unknown_values():
    assert bb._decision_of({"gold_decision": "maybe"}) is None
    assert bb._decision_of({}) is None


def test_stratified_bootstrap_recovers_known_precision():
    # All-correct stratum and all-incorrect stratum of equal size.
    strata = {"a": [1] * 10, "b": [0] * 10}
    result = bb.stratified_bootstrap_precision(
        strata, n_resamples=2000, confidence=0.95, seed=42
    )
    # Expected precision is 0.5; bootstrap CI should bracket 0.5 tightly here.
    assert 0.30 <= result["low"] <= 0.50
    assert 0.50 <= result["high"] <= 0.70


def test_compute_report_counts_outcomes_and_handles_unclear():
    rows = [
        {"assigned_topic_slug": "alpha", "gold_decision": "correct"},
        {"assigned_topic_slug": "alpha", "gold_decision": "correct"},
        {"assigned_topic_slug": "alpha", "gold_decision": "incorrect"},
        {"assigned_topic_slug": "beta", "gold_decision": "correct"},
        {"assigned_topic_slug": "beta", "gold_decision": "unclear"},
    ]
    report = bb.compute_report(
        rows,
        n_resamples=500,
        confidence=0.95,
        minimum=0.85,
        target=0.90,
        seed=1,
        inputs=["test"],
    )
    overall = report["overall"]
    assert overall["labeled"] == 4
    assert overall["correct"] == 3
    assert overall["incorrect"] == 1
    assert overall["unclear"] == 1
    assert math.isclose(overall["precision"], 0.75, abs_tol=1e-9)
    assert report["by_topic"]["alpha"]["labeled"] == 3
    assert report["by_topic"]["alpha"]["correct"] == 2
    assert report["by_topic"]["beta"]["unclear"] == 1


def test_gate_label_thresholds():
    assert bb.gate_label(0.95, 0.85, 0.90) == "pass_target"
    assert bb.gate_label(0.87, 0.85, 0.90) == "pass_minimum"
    assert bb.gate_label(0.50, 0.85, 0.90) == "fail"
