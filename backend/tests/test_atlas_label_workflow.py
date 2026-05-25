from __future__ import annotations

import json

from scripts.atlas_label_workflow import label_progress, merge_batches, split_batches


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
