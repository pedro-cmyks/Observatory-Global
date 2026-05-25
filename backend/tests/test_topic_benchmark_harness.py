from __future__ import annotations

import json

from scripts.topic_benchmark_harness import (
    BENCHMARK_SCHEMA_VERSION,
    PrecisionGate,
    build_benchmark_item,
    score_labeled_items,
)


def test_build_benchmark_item_outputs_label_ready_record():
    item = build_benchmark_item(
        signal_id=42,
        topic_slug="disease-outbreak",
        topic_label="Disease outbreak",
        headline="Ebola outbreak spreads as health officials issue travel advisory",
        source_name="example.org",
        country_code="UG",
        confidence=0.83,
        evidence={"lex_count": 2, "matched_terms": ["outbreak", "ebola"]},
        sample_bucket="lex_supported",
    )

    assert item == {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "signal_id": 42,
        "assigned_topic_slug": "disease-outbreak",
        "assigned_topic_label": "Disease outbreak",
        "headline": "Ebola outbreak spreads as health officials issue travel advisory",
        "source_name": "example.org",
        "country_code": "UG",
        "confidence": 0.83,
        "sample_bucket": "lex_supported",
        "evidence": {"lex_count": 2, "matched_terms": ["outbreak", "ebola"]},
        "gold_decision": None,
        "gold_topic_slug": None,
        "notes": None,
    }


def test_score_labeled_items_computes_per_topic_precision_and_gates():
    rows = [
        {"assigned_topic_slug": "disease-outbreak", "gold_decision": "correct"},
        {"assigned_topic_slug": "disease-outbreak", "gold_decision": "correct"},
        {"assigned_topic_slug": "disease-outbreak", "gold_decision": "incorrect"},
        {"assigned_topic_slug": "food-price-stress", "gold_decision": "correct"},
        {"assigned_topic_slug": "food-price-stress", "gold_decision": "correct"},
        {"assigned_topic_slug": "food-price-stress", "gold_decision": "unclear"},
    ]

    report = score_labeled_items(rows)

    assert report["overall"] == {
        "labeled": 5,
        "correct": 4,
        "incorrect": 1,
        "unclear": 1,
        "precision": 0.8,
        "gate": "fail",
    }
    assert report["by_topic"]["disease-outbreak"] == {
        "labeled": 3,
        "correct": 2,
        "incorrect": 1,
        "unclear": 0,
        "precision": 0.6667,
        "gate": "fail",
    }
    assert report["by_topic"]["food-price-stress"] == {
        "labeled": 2,
        "correct": 2,
        "incorrect": 0,
        "unclear": 1,
        "precision": 1.0,
        "gate": "pass_target",
    }


def test_precision_gate_has_minimum_and_target_thresholds():
    gate = PrecisionGate(minimum=0.85, target=0.90)

    assert gate.classify(0.8499) == "fail"
    assert gate.classify(0.85) == "pass_minimum"
    assert gate.classify(0.8999) == "pass_minimum"
    assert gate.classify(0.90) == "pass_target"


def test_score_labeled_items_accepts_jsonl_lines():
    payload = "\n".join(
        [
            json.dumps({"assigned_topic_slug": "x", "gold_decision": "correct"}),
            json.dumps({"assigned_topic_slug": "x", "gold_decision": "incorrect"}),
        ]
    )

    report = score_labeled_items(payload.splitlines())

    assert report["overall"]["precision"] == 0.5
    assert report["by_topic"]["x"]["labeled"] == 2
