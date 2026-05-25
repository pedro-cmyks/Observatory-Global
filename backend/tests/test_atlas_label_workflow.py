from __future__ import annotations

import json

from scripts.atlas_label_workflow import (
    build_review_template_row,
    label_progress,
    merge_batches,
    render_review_packet,
    split_batches,
    write_review_template,
)


def test_split_batches_writes_numbered_jsonl_files(tmp_path):
    input_path = tmp_path / "sample.jsonl"
    input_path.write_text(
        "\n".join(json.dumps({"signal_id": index}) for index in range(5)) + "\n"
    )

    written = split_batches(
        input_path=input_path,
        output_dir=tmp_path / "batches",
        batch_size=2,
        prefix="atlas-v2",
    )

    assert [path.name for path in written] == [
        "atlas-v2-batch-01.jsonl",
        "atlas-v2-batch-02.jsonl",
        "atlas-v2-batch-03.jsonl",
    ]
    assert len(written[0].read_text().splitlines()) == 2
    assert len(written[2].read_text().splitlines()) == 1


def test_label_progress_counts_labeled_rows(tmp_path):
    batch = tmp_path / "batch.jsonl"
    batch.write_text(
        "\n".join(
            [
                json.dumps({"signal_id": 1, "gold_decision": "correct"}),
                json.dumps({"signal_id": 2, "gold_decision": None}),
                json.dumps({"signal_id": 3}),
            ]
        )
        + "\n"
    )

    report = label_progress([batch])

    assert report["total_rows"] == 3
    assert report["labeled_rows"] == 1
    assert report["remaining_rows"] == 2
    assert report["progress_pct"] == 0.3333
    assert report["files"][0]["labeled"] == 1


def test_merge_batches_concatenates_sorted_files(tmp_path):
    batch_dir = tmp_path / "batches"
    batch_dir.mkdir()
    (batch_dir / "batch-02.jsonl").write_text(json.dumps({"signal_id": 2}) + "\n")
    (batch_dir / "batch-01.jsonl").write_text(json.dumps({"signal_id": 1}) + "\n")
    output = tmp_path / "merged.jsonl"

    row_count = merge_batches(input_dir=batch_dir, output_path=output, pattern="*.jsonl")

    assert row_count == 2
    assert [json.loads(line)["signal_id"] for line in output.read_text().splitlines()] == [1, 2]


def test_render_review_packet_joins_raw_rows_and_pilot_labels(tmp_path):
    raw_path = tmp_path / "raw.jsonl"
    labels_path = tmp_path / "labels.jsonl"
    output_path = tmp_path / "review.md"
    raw_path.write_text(
        json.dumps(
            {
                "signal_id": 101,
                "headline": "Canal strike disrupts cargo movement",
                "assigned_topic_label": "Transport corridor disruption",
                "assigned_topic_slug": "transport-corridor-disruption",
                "country_code": "PA",
                "source_name": "example.test",
                "source_family": "gdelt",
                "source_lang": "en",
                "sample_bucket": "lex_high_conf",
                "confidence": 0.8,
                "evidence": {
                    "formula": "theme-hint-lex-v2",
                    "matched_terms": ["canal", "cargo"],
                    "lex_count": 2,
                    "theme_hits": 1,
                    "hint_count": 2,
                },
            }
        )
        + "\n"
    )
    labels_path.write_text(
        json.dumps(
            {
                "signal_id": 101,
                "gold_decision": "correct",
                "gold_scope": "child_thread",
                "gold_evidence_role": "primary_event",
                "gold_error_type": None,
                "gold_parent_thread": "maritime-logistics",
                "gold_child_thread": "panama-canal-disruption",
                "gold_supported_questions": ["why_moving_now", "where_concentrated"],
                "notes": "Assistant pilot label.",
            }
        )
        + "\n"
    )

    rendered = render_review_packet(
        raw_path=raw_path,
        labels_path=labels_path,
        output_path=output_path,
        title="Review Packet",
    )

    text = rendered.read_text()
    assert "# Review Packet" in text
    assert "Canal strike disrupts cargo movement" in text
    assert "`scope`: child_thread" in text
    assert "`reviewer_decision`:" in text
    assert "panama-canal-disruption" in text


def test_render_review_packet_handles_missing_pilot_label(tmp_path):
    raw_path = tmp_path / "raw.jsonl"
    labels_path = tmp_path / "labels.jsonl"
    output_path = tmp_path / "review.md"
    raw_path.write_text(json.dumps({"signal_id": 101, "headline": "Unlabeled row"}) + "\n")
    labels_path.write_text(json.dumps({"signal_id": 202, "gold_decision": "correct"}) + "\n")

    render_review_packet(
        raw_path=raw_path,
        labels_path=labels_path,
        output_path=output_path,
        title="Review Packet",
    )

    assert "No assistant-pilot label found" in output_path.read_text()


def test_build_review_template_row_keeps_assistant_and_reviewer_fields_separate():
    row = build_review_template_row(
        raw_row={
            "signal_id": 101,
            "schema_version": "atlas-topic-benchmark-v2",
            "headline": "Canal strike disrupts cargo movement",
            "assigned_topic_slug": "transport-corridor-disruption",
            "evidence": {"matched_terms": ["canal"]},
        },
        pilot_label={
            "gold_decision": "correct",
            "gold_scope": "child_thread",
            "gold_evidence_role": "primary_event",
            "gold_error_type": None,
            "gold_parent_thread": "maritime-logistics",
            "gold_child_thread": "panama-canal-disruption",
            "gold_supported_questions": ["why_moving_now"],
            "notes": "Assistant pilot label.",
        },
    )

    assert row["assistant_decision"] == "correct"
    assert row["assistant_scope"] == "child_thread"
    assert row["reviewer_decision"] is None
    assert row["reviewer_supported_questions"] == []
    assert row["label_quality"] == "review-template"


def test_write_review_template_outputs_jsonl(tmp_path):
    raw_path = tmp_path / "raw.jsonl"
    labels_path = tmp_path / "labels.jsonl"
    output_path = tmp_path / "review-template.jsonl"
    raw_path.write_text(
        json.dumps(
            {
                "signal_id": 101,
                "headline": "Canal strike disrupts cargo movement",
                "assigned_topic_slug": "transport-corridor-disruption",
            }
        )
        + "\n"
    )
    labels_path.write_text(json.dumps({"signal_id": 101, "gold_decision": "correct"}) + "\n")

    write_review_template(raw_path=raw_path, labels_path=labels_path, output_path=output_path)

    [row] = [json.loads(line) for line in output_path.read_text().splitlines()]
    assert row["signal_id"] == 101
    assert row["assistant_decision"] == "correct"
    assert row["reviewer_decision"] is None
