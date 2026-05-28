"""Tests for multi_annotator_agreement (no API calls)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import multi_annotator_agreement as maa


def test_cohen_kappa_perfect():
    pairs = [("correct", "correct"), ("incorrect", "incorrect")]
    r = maa.cohen_kappa(pairs, ["correct", "incorrect"])
    assert math.isclose(r["kappa"], 1.0, abs_tol=1e-9)


def test_cohen_kappa_textbook():
    pairs = (
        [("yes", "yes")] * 20 + [("no", "no")] * 15
        + [("yes", "no")] * 10 + [("no", "yes")] * 5
    )
    r = maa.cohen_kappa(pairs, ["yes", "no"])
    assert math.isclose(r["kappa"], 0.4, abs_tol=1e-6)


def test_fleiss_kappa_perfect_agreement():
    # 3 annotators, 4 items, all agree.
    items = [
        {"a": "correct", "b": "correct", "c": "correct"},
        {"a": "incorrect", "b": "incorrect", "c": "incorrect"},
        {"a": "correct", "b": "correct", "c": "correct"},
        {"a": "partial", "b": "partial", "c": "partial"},
    ]
    r = maa.fleiss_kappa(items, ["a", "b", "c"], ["correct", "incorrect", "partial"])
    assert math.isclose(r["kappa"], 1.0, abs_tol=1e-9)
    assert r["n_items"] == 4
    assert r["n_annotators"] == 3


def test_fleiss_kappa_restricts_to_common_items():
    # Item 2 missing annotator c -> excluded.
    items = [
        {"a": "correct", "b": "correct", "c": "correct"},
        {"a": "incorrect", "b": "incorrect"},
    ]
    r = maa.fleiss_kappa(items, ["a", "b", "c"], ["correct", "incorrect", "partial"])
    assert r["n_items"] == 1


def test_landis_koch_bands():
    assert maa.landis_koch_band(0.1) == "slight"
    assert maa.landis_koch_band(0.5) == "moderate"
    assert maa.landis_koch_band(0.7) == "substantial"
    assert maa.landis_koch_band(0.9) == "almost_perfect"


def test_build_report_pairwise_and_distribution(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text(
        '{"signal_id": 1, "annotator_decision": "correct"}\n'
        '{"signal_id": 2, "annotator_decision": "incorrect"}\n'
        '{"signal_id": 3, "annotator_decision": "correct"}\n',
        encoding="utf-8",
    )
    b.write_text(
        '{"signal_id": 1, "annotator_decision": "correct"}\n'
        '{"signal_id": 2, "annotator_decision": "incorrect"}\n'
        '{"signal_id": 3, "annotator_decision": "incorrect"}\n',
        encoding="utf-8",
    )
    report = maa.build_report(
        [f"alpha:annotator_decision:{a}", f"beta:annotator_decision:{b}"],
        ["correct", "incorrect", "partial"],
    )
    assert report["annotators"] == ["alpha", "beta"]
    assert report["distributions"]["alpha"]["correct"] == 2
    assert report["distributions"]["beta"]["incorrect"] == 2
    pair = report["pairwise_cohen_kappa"][0]
    assert pair["overlap"] == 3


def test_build_report_handles_different_decision_fields(tmp_path):
    human = tmp_path / "human.jsonl"
    llm = tmp_path / "llm.jsonl"
    human.write_text('{"signal_id": 1, "gold_decision": "correct"}\n', encoding="utf-8")
    llm.write_text('{"signal_id": 1, "annotator_decision": "correct"}\n', encoding="utf-8")
    report = maa.build_report(
        [f"pedro:gold_decision:{human}", f"sonnet:annotator_decision:{llm}"],
        ["correct", "incorrect", "partial"],
    )
    # LLM-only fleiss should exclude pedro -> only 1 llm annotator -> None.
    assert report["fleiss_kappa_llm_only"] is None
    assert report["distributions"]["pedro"]["correct"] == 1
