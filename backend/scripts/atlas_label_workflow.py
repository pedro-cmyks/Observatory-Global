#!/usr/bin/env python3
"""Manage Atlas benchmark labeling batches.

This helper is intentionally file-based and read-only against production data.
It keeps the paper/validation workflow reproducible:

- `split` turns a JSONL sample into numbered batch files.
- `progress` reports how many rows have labels.
- `merge` combines batch files back into one JSONL file for scoring.
- `review-packet` renders a human adjudication packet from raw rows and pilot labels.
- `review-template` writes machine-editable reviewer rows for adjudication.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    )


def split_batches(
    *,
    input_path: Path,
    output_dir: Path,
    batch_size: int,
    prefix: str,
) -> list[Path]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    rows = read_jsonl(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for index, start in enumerate(range(0, len(rows), batch_size), start=1):
        batch_rows = rows[start : start + batch_size]
        path = output_dir / f"{prefix}-batch-{index:02d}.jsonl"
        write_jsonl(path, batch_rows)
        written.append(path)

    return written


def label_progress(paths: Iterable[Path]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    total_rows = 0
    labeled_rows = 0

    for path in sorted(paths):
        rows = read_jsonl(path)
        row_count = len(rows)
        labeled_count = sum(1 for row in rows if row.get("gold_decision") is not None)
        total_rows += row_count
        labeled_rows += labeled_count
        files.append(
            {
                "path": str(path),
                "rows": row_count,
                "labeled": labeled_count,
                "remaining": row_count - labeled_count,
            }
        )

    return {
        "files": files,
        "total_rows": total_rows,
        "labeled_rows": labeled_rows,
        "remaining_rows": total_rows - labeled_rows,
        "progress_pct": round(labeled_rows / total_rows, 4) if total_rows else None,
    }


def merge_batches(*, input_dir: Path, output_path: Path, pattern: str) -> int:
    rows: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob(pattern)):
        rows.extend(read_jsonl(path))
    write_jsonl(output_path, rows)
    return len(rows)


def rows_by_signal_id(path: Path) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for row in read_jsonl(path):
        signal_id = row.get("signal_id")
        if not isinstance(signal_id, int):
            raise ValueError(f"row in {path} is missing integer signal_id")
        if signal_id in rows:
            raise ValueError(f"duplicate signal_id {signal_id} in {path}")
        rows[signal_id] = row
    return rows


def _csv(values: Any) -> str:
    if values is None:
        return ""
    if isinstance(values, list):
        return ", ".join(str(value) for value in values)
    return str(values)


def _md_value(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (dict, list)):
        return "`" + json.dumps(value, ensure_ascii=False, sort_keys=True) + "`"
    return str(value).replace("\n", " ").strip()


def _pilot_summary(label: dict[str, Any] | None) -> str:
    if not label:
        return "_No assistant-pilot label found for this signal._"

    fields = [
        ("decision", label.get("gold_decision")),
        ("scope", label.get("gold_scope")),
        ("evidence_role", label.get("gold_evidence_role")),
        ("error_type", label.get("gold_error_type")),
        ("parent_thread", label.get("gold_parent_thread")),
        ("child_thread", label.get("gold_child_thread")),
        ("supported_questions", _csv(label.get("gold_supported_questions"))),
        ("notes", label.get("notes")),
    ]
    return "\n".join(f"- `{name}`: {_md_value(value)}" for name, value in fields)


def _assistant_label_fields(label: dict[str, Any] | None) -> dict[str, Any]:
    if not label:
        return {
            "assistant_decision": None,
            "assistant_scope": None,
            "assistant_evidence_role": None,
            "assistant_error_type": None,
            "assistant_parent_thread": None,
            "assistant_child_thread": None,
            "assistant_supported_questions": [],
            "assistant_notes": None,
        }

    return {
        "assistant_decision": label.get("gold_decision"),
        "assistant_scope": label.get("gold_scope"),
        "assistant_evidence_role": label.get("gold_evidence_role"),
        "assistant_error_type": label.get("gold_error_type"),
        "assistant_parent_thread": label.get("gold_parent_thread"),
        "assistant_child_thread": label.get("gold_child_thread"),
        "assistant_supported_questions": label.get("gold_supported_questions") or [],
        "assistant_notes": label.get("notes"),
    }


def build_review_template_row(
    *,
    raw_row: dict[str, Any],
    pilot_label: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build one machine-editable adjudication row.

    The assistant fields are suggestions only. Reviewer fields stay blank so the
    file cannot be mistaken for gold labels before human adjudication.
    """

    return {
        "signal_id": raw_row["signal_id"],
        "schema_version": raw_row.get("schema_version"),
        "headline": raw_row.get("headline"),
        "assigned_topic_label": raw_row.get("assigned_topic_label"),
        "assigned_topic_slug": raw_row.get("assigned_topic_slug"),
        "confidence": raw_row.get("confidence"),
        "country_code": raw_row.get("country_code"),
        "source_name": raw_row.get("source_name"),
        "source_family": raw_row.get("source_family"),
        "source_lang": raw_row.get("source_lang"),
        "sample_bucket": raw_row.get("sample_bucket"),
        "evidence": raw_row.get("evidence"),
        **_assistant_label_fields(pilot_label),
        "accept_assistant_label": None,
        "reviewer_decision": None,
        "reviewer_scope": None,
        "reviewer_evidence_role": None,
        "reviewer_error_type": None,
        "reviewer_parent_thread": None,
        "reviewer_child_thread": None,
        "reviewer_supported_questions": [],
        "reviewer_notes": None,
        "label_quality": "review-template",
    }


def _row_review_section(
    *,
    index: int,
    raw_row: dict[str, Any],
    pilot_label: dict[str, Any] | None,
) -> str:
    evidence = raw_row.get("evidence") or {}
    matched_terms = evidence.get("matched_terms", [])
    signal_id = raw_row["signal_id"]
    headline = raw_row.get("headline") or "(no headline)"

    return f"""## {index}. Signal {signal_id}

**Headline:** {headline}

| Field | Value |
|---|---|
| Assigned topic | {_md_value(raw_row.get("assigned_topic_label"))} |
| Topic slug | `{_md_value(raw_row.get("assigned_topic_slug"))}` |
| Country | `{_md_value(raw_row.get("country_code"))}` |
| Source | {_md_value(raw_row.get("source_name"))} |
| Source family | `{_md_value(raw_row.get("source_family"))}` |
| Source language | `{_md_value(raw_row.get("source_lang"))}` |
| Sample bucket | `{_md_value(raw_row.get("sample_bucket"))}` |
| Confidence | `{_md_value(raw_row.get("confidence"))}` |
| Matched terms | {_md_value(matched_terms)} |
| Evidence formula | `{_md_value(evidence.get("formula"))}` |
| Lex/theme/hint counts | `lex={_md_value(evidence.get("lex_count"))}; theme={_md_value(evidence.get("theme_hits"))}; hint={_md_value(evidence.get("hint_count"))}` |

### Assistant-Pilot Suggestion

{_pilot_summary(pilot_label)}

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:

"""


def render_review_packet(
    *,
    raw_path: Path,
    labels_path: Path,
    output_path: Path,
    title: str,
) -> Path:
    raw_rows = read_jsonl(raw_path)
    pilot_labels = rows_by_signal_id(labels_path)
    sections = [
        f"# {title}",
        "",
        "This packet is for human review/adjudication. Assistant-pilot labels are",
        "suggestions only; they are not paper-grade gold labels until reviewed.",
        "",
        "## Review Rules",
        "",
        "- Judge whether the assigned Atlas topic is supported by the headline evidence.",
        "- Prefer precise child-thread labels when the row is specific.",
        "- Mark broad but relevant context as `parent_thread` or `context_signal`.",
        "- Mark unsupported or misleading rows as `noise` or `incorrect`.",
        "- Keep reviewer notes short and evidence-based.",
        "",
        "## Rows",
        "",
    ]

    for index, raw_row in enumerate(raw_rows, start=1):
        signal_id = raw_row.get("signal_id")
        if not isinstance(signal_id, int):
            raise ValueError(f"row in {raw_path} is missing integer signal_id")
        sections.append(
            _row_review_section(
                index=index,
                raw_row=raw_row,
                pilot_label=pilot_labels.get(signal_id),
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(sections))
    return output_path


def write_review_template(
    *,
    raw_path: Path,
    labels_path: Path,
    output_path: Path,
) -> Path:
    raw_rows = read_jsonl(raw_path)
    pilot_labels = rows_by_signal_id(labels_path)
    template_rows: list[dict[str, Any]] = []

    for raw_row in raw_rows:
        signal_id = raw_row.get("signal_id")
        if not isinstance(signal_id, int):
            raise ValueError(f"row in {raw_path} is missing integer signal_id")
        template_rows.append(
            build_review_template_row(
                raw_row=raw_row,
                pilot_label=pilot_labels.get(signal_id),
            )
        )

    write_jsonl(output_path, template_rows)
    return output_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas labeling workflow helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    split = subparsers.add_parser("split", help="Split a sample JSONL into batches")
    split.add_argument("--input", type=Path, required=True)
    split.add_argument("--output-dir", type=Path, required=True)
    split.add_argument("--batch-size", type=int, default=32)
    split.add_argument("--prefix", required=True)

    progress = subparsers.add_parser("progress", help="Report label progress")
    progress.add_argument("paths", type=Path, nargs="+")

    merge = subparsers.add_parser("merge", help="Merge labeled batches")
    merge.add_argument("--input-dir", type=Path, required=True)
    merge.add_argument("--output", type=Path, required=True)
    merge.add_argument("--pattern", default="*.jsonl")

    review = subparsers.add_parser(
        "review-packet",
        help="Render a Markdown adjudication packet from raw rows and pilot labels",
    )
    review.add_argument("--raw", type=Path, required=True)
    review.add_argument("--labels", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)
    review.add_argument("--title", required=True)

    review_template = subparsers.add_parser(
        "review-template",
        help="Write a machine-editable JSONL adjudication template",
    )
    review_template.add_argument("--raw", type=Path, required=True)
    review_template.add_argument("--labels", type=Path, required=True)
    review_template.add_argument("--output", type=Path, required=True)

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.command == "split":
        paths = split_batches(
            input_path=args.input,
            output_dir=args.output_dir,
            batch_size=args.batch_size,
            prefix=args.prefix,
        )
        print(json.dumps({"written": [str(path) for path in paths]}, indent=2))
        return

    if args.command == "progress":
        print(json.dumps(label_progress(args.paths), indent=2, sort_keys=True))
        return

    if args.command == "review-packet":
        output_path = render_review_packet(
            raw_path=args.raw,
            labels_path=args.labels,
            output_path=args.output,
            title=args.title,
        )
        print(json.dumps({"output": str(output_path)}, indent=2))
        return

    if args.command == "review-template":
        output_path = write_review_template(
            raw_path=args.raw,
            labels_path=args.labels,
            output_path=args.output,
        )
        print(json.dumps({"output": str(output_path)}, indent=2))
        return

    row_count = merge_batches(
        input_dir=args.input_dir,
        output_path=args.output,
        pattern=args.pattern,
    )
    print(json.dumps({"output": str(args.output), "rows": row_count}, indent=2))


if __name__ == "__main__":
    main()
