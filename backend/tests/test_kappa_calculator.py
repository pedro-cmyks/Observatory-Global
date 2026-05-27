"""Tests for kappa_calculator (no API calls)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import kappa_calculator as kc


def test_kappa_perfect_agreement_is_one():
    pairs = [("correct", "correct"), ("incorrect", "incorrect"), ("correct", "correct")]
    result = kc.cohen_kappa(pairs, ["correct", "incorrect"])
    assert math.isclose(result["kappa"], 1.0, abs_tol=1e-9)
    assert math.isclose(result["observed_agreement"], 1.0, abs_tol=1e-9)


def test_kappa_zero_when_all_chance():
    # Even split, all combinations equally likely: kappa ≈ 0 when off-diagonal balances.
    pairs = [
        ("correct", "correct"),
        ("correct", "incorrect"),
        ("incorrect", "correct"),
        ("incorrect", "incorrect"),
    ]
    result = kc.cohen_kappa(pairs, ["correct", "incorrect"])
    # Po = 0.5, Pe = 0.5 → kappa = 0
    assert math.isclose(result["kappa"], 0.0, abs_tol=1e-9)


def test_kappa_known_textbook_value():
    # Classic example: two annotators, n=50.
    # 20 both YES, 15 both NO, 10 A=YES B=NO, 5 A=NO B=YES.
    pairs = (
        [("yes", "yes")] * 20
        + [("no", "no")] * 15
        + [("yes", "no")] * 10
        + [("no", "yes")] * 5
    )
    result = kc.cohen_kappa(pairs, ["yes", "no"])
    # Po = 35/50 = 0.7
    # Pe = (30/50)*(25/50) + (20/50)*(25/50) = 0.5
    # κ = (0.7-0.5)/(1-0.5) = 0.4
    assert math.isclose(result["observed_agreement"], 0.7, abs_tol=1e-6)
    assert math.isclose(result["chance_agreement"], 0.5, abs_tol=1e-6)
    assert math.isclose(result["kappa"], 0.4, abs_tol=1e-6)


def test_landis_koch_band():
    assert kc.landis_koch_band(0.10) == "slight"
    assert kc.landis_koch_band(0.30) == "fair"
    assert kc.landis_koch_band(0.55) == "moderate"
    assert kc.landis_koch_band(0.70) == "substantial"
    assert kc.landis_koch_band(0.90) == "almost_perfect"


def test_bootstrap_ci_brackets_point_estimate():
    pairs = (
        [("yes", "yes")] * 20
        + [("no", "no")] * 15
        + [("yes", "no")] * 10
        + [("no", "yes")] * 5
    )
    result = kc.bootstrap_kappa_ci(pairs, ["yes", "no"], n_resamples=2000, seed=1)
    # Point estimate is 0.4; bootstrap CI should bracket it.
    assert result["low"] < 0.4 < result["high"]


def test_build_report_excludes_unclear(tmp_path):
    gold_path = tmp_path / "gold.jsonl"
    annot_path = tmp_path / "annot.jsonl"
    gold_path.write_text(
        '{"signal_id": 1, "gold_decision": "correct"}\n'
        '{"signal_id": 2, "gold_decision": "unclear"}\n'
        '{"signal_id": 3, "gold_decision": "incorrect"}\n',
        encoding="utf-8",
    )
    annot_path.write_text(
        '{"signal_id": 1, "annotator_decision": "correct"}\n'
        '{"signal_id": 2, "annotator_decision": "correct"}\n'
        '{"signal_id": 3, "annotator_decision": "incorrect"}\n',
        encoding="utf-8",
    )
    report = kc.build_report(
        gold_paths=[gold_path],
        annotator_path=annot_path,
        exclude_unclear=True,
        n_resamples=200,
    )
    assert report["matched_pairs"] == 2
    assert report["skipped_unclear"] == 1
    assert math.isclose(report["observed_agreement"], 1.0)
    assert math.isclose(report["kappa"], 1.0)
