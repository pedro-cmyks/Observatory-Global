from __future__ import annotations

from scripts import gate_coverage_report as report


def test_enrich_counts_reports_scored_kept_and_abstention_rates():
    enriched = report.enrich_counts(
        {
            "assignments": 100,
            "scored": 80,
            "kept": 50,
            "abstained": 30,
            "unscored": 20,
        }
    )

    assert enriched["scored_rate"] == 0.8
    assert enriched["kept_rate_of_scored"] == 0.625
    assert enriched["abstain_rate_of_scored"] == 0.375
    assert enriched["kept_rate_of_assignments"] == 0.5
    assert enriched["unscored_rate"] == 0.2


def test_build_report_keeps_precision_and_coverage_separate():
    db_row = {
        "overall": {
            "assignments": 10,
            "distinct_signals": 9,
            "scored": 8,
            "kept": 6,
            "abstained": 2,
            "unscored": 2,
            "avg_gate_score": 0.82,
        },
        "by_topic": [
            {
                "slug": "disease-outbreak",
                "label": "Disease outbreak",
                "assignments": 4,
                "distinct_signals": 4,
                "scored": 4,
                "kept": 3,
                "abstained": 1,
                "unscored": 0,
                "avg_gate_score": 0.91,
            }
        ],
    }

    payload = report.build_report(hours=24, db_row=db_row)

    assert payload["schema_version"] == "atlas-gate-coverage-v1"
    assert payload["precision_target"] == 0.9
    assert payload["overall"]["kept_rate_of_scored"] == 0.75
    assert payload["by_topic"][0]["abstain_rate_of_scored"] == 0.25
    assert "coverage and abstention" in payload["interpretation"]["precision_source"]


def test_build_report_accepts_asyncpg_json_strings():
    db_row = {
        "overall": '{"assignments": 2, "scored": 2, "kept": 1, "abstained": 1, "unscored": 0}',
        "by_topic": '[{"slug": "x", "label": "X", "assignments": 2, "scored": 2, "kept": 1, "abstained": 1, "unscored": 0}]',
    }

    payload = report.build_report(hours=24, db_row=db_row)

    assert payload["overall"]["kept_rate_of_scored"] == 0.5
    assert payload["by_topic"][0]["slug"] == "x"


def test_gate_coverage_sql_uses_gated_assignment_fields():
    sql = report.GATE_COVERAGE_SQL

    assert "signal_topic_assignments a" in sql
    assert "gate_score" in sql
    assert "gate_kept IS TRUE" in sql
    assert "gate_kept IS FALSE" in sql
    assert "a.model_version = $1" in sql
