from __future__ import annotations

import json

from scripts.atlas_validation_report import generate_report, render_bar_svg


def test_render_bar_svg_writes_chart(tmp_path):
    output = tmp_path / "chart.svg"

    render_bar_svg(title="Scope", values={"child_thread": 3, "noise": 1}, output_path=output)

    payload = output.read_text()
    assert "<svg" in payload
    assert "child_thread" in payload
    assert "noise" in payload


def test_generate_report_writes_markdown_and_charts(tmp_path):
    score = {
        "schema_version": "atlas-topic-benchmark-v2",
        "gate": {"minimum": 0.85, "target": 0.9},
        "overall": {
            "labeled": 3,
            "correct": 2,
            "incorrect": 1,
            "unclear": 0,
            "precision": 0.6667,
            "gate": "fail",
        },
        "by_topic": {
            "armed-conflict-escalation": {
                "labeled": 3,
                "correct": 2,
                "incorrect": 1,
                "unclear": 0,
                "precision": 0.6667,
                "gate": "fail",
            }
        },
        "by_scope": {"child_thread": 2, "noise": 1},
        "by_evidence_role": {"primary_event": 2, "not_evidence": 1},
        "by_supported_question": {"evidence_support": 2},
    }
    score_path = tmp_path / "score.json"
    score_path.write_text(json.dumps(score))

    report_path = generate_report(
        score_path=score_path,
        output_dir=tmp_path / "reports",
        title="Pilot Report",
        label_quality="assistant-pilot",
        report_name="pilot",
    )

    markdown = report_path.read_text()
    assert "Pilot Report" in markdown
    assert "66.67%" in markdown
    assert "assistant-pilot" in markdown
    assert (tmp_path / "reports" / "pilot-scope.svg").exists()
