#!/usr/bin/env python3
"""Manage Atlas benchmark labeling batches.

This helper is intentionally file-based and read-only against production data.
It keeps the paper/validation workflow reproducible:

- `split` turns a JSONL sample into numbered batch files.
- `progress` reports how many rows have labels.
- `merge` combines batch files back into one JSONL file for scoring.
- `review-packet` renders a human adjudication packet from raw rows and pilot labels.
- `review-template` writes machine-editable reviewer rows for adjudication.
- `review-progress` reports adjudication readiness for review templates.
- `finalize-review` converts completed review templates into scoreable labels.
- `apply-review-packet` copies Markdown reviewer answers into a JSONL template.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

VALID_LABEL_QUALITIES = {"reviewed", "gold"}
VALID_DECISIONS = {"correct", "incorrect", "unclear"}
VALID_ERROR_TYPES = {
    "substring_noise",
    "scope_mismatch",
    "parent_thread_candidate",
    "primary_context_mismatch",
    "insufficient_context",
    "off_topic",
}
VALID_SCOPES = {
    "domain",
    "parent_thread",
    "child_thread",
    "entity_thread",
    "geo_context",
    "source_context",
    "evidence",
    "context_signal",
    "noise",
}
VALID_EVIDENCE_ROLES = {
    "primary_event",
    "followup",
    "background",
    "reaction",
    "analysis",
    "public_attention",
    "source_amplification",
    "not_evidence",
}
VALID_SUPPORTED_QUESTIONS = {
    "why_moving",
    "what_changed",
    "where_concentrated",
    "subthreads_forming",
    "sources_driving",
    "evidence_support",
    "related_thread",
}
LABEL_ALIASES = {
    "parent thread": "parent_thread",
    "child thread": "child_thread",
    "context signal": "context_signal",
    "entity thread": "entity_thread",
    "geo context": "geo_context",
    "source context": "source_context",
    "primary event": "primary_event",
    "not evidence": "not_evidence",
}
FINAL_LABEL_FIELDS = {
    "decision": "gold_decision",
    "scope": "gold_scope",
    "evidence_role": "gold_evidence_role",
    "error_type": "gold_error_type",
    "parent_thread": "gold_parent_thread",
    "child_thread": "gold_child_thread",
    "supported_questions": "gold_supported_questions",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


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
    labels_path: Path | None,
    output_path: Path,
    title: str,
) -> Path:
    raw_rows = read_jsonl(raw_path)
    pilot_labels = rows_by_signal_id(labels_path) if labels_path else {}
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
    labels_path: Path | None,
    output_path: Path,
) -> Path:
    raw_rows = read_jsonl(raw_path)
    pilot_labels = rows_by_signal_id(labels_path) if labels_path else {}
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


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True


def _accepted_assistant(row: dict[str, Any]) -> bool:
    return row.get("accept_assistant_label") is True


def _reviewer_field(row: dict[str, Any], name: str) -> Any:
    return row.get(f"reviewer_{name}")


def _assistant_field(row: dict[str, Any], name: str) -> Any:
    return row.get(f"assistant_{name}")


def _resolved_review_value(row: dict[str, Any], name: str) -> Any:
    reviewer_value = _reviewer_field(row, name)
    if _has_value(reviewer_value):
        return reviewer_value
    if _accepted_assistant(row):
        return _assistant_field(row, name)
    return None


def review_template_progress(paths: Iterable[Path]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    total_rows = 0
    ready_rows = 0
    accepted_assistant_rows = 0
    reviewer_corrected_rows = 0

    for path in sorted(paths):
        rows = read_jsonl(path)
        file_ready = 0
        file_accepted = 0
        file_corrected = 0
        for row in rows:
            decision = _resolved_review_value(row, "decision")
            if _has_value(decision):
                file_ready += 1
            if _accepted_assistant(row):
                file_accepted += 1
            if _has_value(row.get("reviewer_decision")):
                file_corrected += 1

        row_count = len(rows)
        total_rows += row_count
        ready_rows += file_ready
        accepted_assistant_rows += file_accepted
        reviewer_corrected_rows += file_corrected
        files.append(
            {
                "path": str(path),
                "rows": row_count,
                "ready": file_ready,
                "remaining": row_count - file_ready,
                "accepted_assistant": file_accepted,
                "reviewer_corrected": file_corrected,
            }
        )

    return {
        "files": files,
        "total_rows": total_rows,
        "ready_rows": ready_rows,
        "remaining_rows": total_rows - ready_rows,
        "accepted_assistant_rows": accepted_assistant_rows,
        "reviewer_corrected_rows": reviewer_corrected_rows,
        "progress_pct": round(ready_rows / total_rows, 4) if total_rows else None,
    }


def _finalized_review_row(row: dict[str, Any], *, label_quality: str) -> dict[str, Any] | None:
    decision = _resolved_review_value(row, "decision")
    if not _has_value(decision):
        return None

    finalized = {
        key: value
        for key, value in row.items()
        if not key.startswith("assistant_")
        and not key.startswith("reviewer_")
        and key not in {"accept_assistant_label", "label_quality"}
    }
    finalized["label_quality"] = label_quality
    finalized["review_source"] = (
        "assistant_accepted" if _accepted_assistant(row) else "reviewer_adjudicated"
    )

    for review_name, gold_name in FINAL_LABEL_FIELDS.items():
        value = _resolved_review_value(row, review_name)
        if review_name == "supported_questions" and value is None:
            value = []
        finalized[gold_name] = value

    return finalized


def finalize_review_template(
    *,
    input_path: Path,
    output_path: Path,
    label_quality: str,
    require_complete: bool,
) -> dict[str, Any]:
    if label_quality not in VALID_LABEL_QUALITIES:
        raise ValueError(f"label_quality must be one of {sorted(VALID_LABEL_QUALITIES)}")

    rows = read_jsonl(input_path)
    finalized_rows: list[dict[str, Any]] = []
    for row in rows:
        finalized = _finalized_review_row(row, label_quality=label_quality)
        if finalized:
            finalized_rows.append(finalized)

    if require_complete and len(finalized_rows) != len(rows):
        missing = len(rows) - len(finalized_rows)
        raise ValueError(f"review template is incomplete: {missing} rows missing decisions")

    write_jsonl(output_path, finalized_rows)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "input_rows": len(rows),
        "written_rows": len(finalized_rows),
        "remaining_rows": len(rows) - len(finalized_rows),
        "label_quality": label_quality,
    }


def _blankish(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return value.strip() in {"", "-"}


def _split_values(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip() and part.strip() != "-"]


def _normalize_label(
    *,
    value: str | None,
    valid_values: set[str],
    field: str,
    signal_id: int,
    warnings: list[dict[str, Any]],
) -> str | None:
    if value is None or _blankish(value):
        return None

    normalized_parts = []
    for part in _split_values(value):
        label = LABEL_ALIASES.get(part.lower(), part.lower().replace(" ", "_"))
        normalized_parts.append(label)

    valid_parts = [part for part in normalized_parts if part in valid_values]
    if not valid_parts:
        warnings.append(
            {
                "signal_id": signal_id,
                "field": field,
                "value": value,
                "warning": "No valid label found; value ignored.",
            }
        )
        return None

    if len(valid_parts) > 1:
        warnings.append(
            {
                "signal_id": signal_id,
                "field": field,
                "value": value,
                "chosen": valid_parts[0],
                "warning": "Multiple valid labels supplied; first valid value chosen.",
            }
        )
    return valid_parts[0]


def _normalize_questions(
    *,
    value: str | None,
    signal_id: int,
    warnings: list[dict[str, Any]],
) -> list[str]:
    if value is None or _blankish(value):
        return []

    questions: list[str] = []
    for part in _split_values(value):
        normalized = LABEL_ALIASES.get(part.lower(), part.lower().replace(" ", "_"))
        if normalized in VALID_SUPPORTED_QUESTIONS:
            questions.append(normalized)
        else:
            warnings.append(
                {
                    "signal_id": signal_id,
                    "field": "reviewer_supported_questions",
                    "value": part,
                    "warning": "Unsupported question ignored.",
                }
            )
    return questions


def _normalize_bool(value: str | None) -> bool | None:
    if value is None or _blankish(value):
        return None
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def _normalize_free_text(value: str | None) -> str | None:
    if value is None or _blankish(value):
        return None
    return value.strip()


def parse_review_packet(path: Path) -> dict[int, dict[str, str]]:
    text = path.read_text()
    parts = re.split(r"(?m)^## (\d+)\. Signal (\d+)\s*$", text)
    parsed: dict[int, dict[str, str]] = {}
    for index in range(1, len(parts), 3):
        signal_id = int(parts[index + 1])
        body = parts[index + 2]
        fields: dict[str, str] = {}
        for match in re.finditer(r"(?m)^- `([^`]+)`: ?(.*)$", body):
            fields[match.group(1)] = match.group(2).strip()
        parsed[signal_id] = fields
    return parsed


def apply_review_packet(
    *,
    packet_path: Path,
    template_path: Path,
    output_path: Path,
    report_path: Path | None = None,
) -> dict[str, Any]:
    packet_rows = parse_review_packet(packet_path)
    template_rows = read_jsonl(template_path)
    warnings: list[dict[str, Any]] = []
    updated_rows: list[dict[str, Any]] = []

    for row in template_rows:
        signal_id = row.get("signal_id")
        if not isinstance(signal_id, int):
            raise ValueError(f"row in {template_path} is missing integer signal_id")
        fields = packet_rows.get(signal_id)
        if not fields:
            warnings.append(
                {
                    "signal_id": signal_id,
                    "warning": "No matching Markdown review section found.",
                }
            )
            updated_rows.append(row)
            continue

        accept = _normalize_bool(fields.get("accept_assistant_label"))
        reviewer_decision_raw = fields.get("reviewer_decision")
        if accept is None and reviewer_decision_raw and reviewer_decision_raw.lower() == "true":
            accept = True
            reviewer_decision_raw = None
            warnings.append(
                {
                    "signal_id": signal_id,
                    "field": "reviewer_decision",
                    "value": "true",
                    "warning": "Interpreted reviewer_decision=true as accept_assistant_label=true.",
                }
            )

        row["accept_assistant_label"] = accept
        row["reviewer_decision"] = _normalize_label(
            value=reviewer_decision_raw,
            valid_values=VALID_DECISIONS,
            field="reviewer_decision",
            signal_id=signal_id,
            warnings=warnings,
        )
        row["reviewer_scope"] = _normalize_label(
            value=fields.get("reviewer_scope"),
            valid_values=VALID_SCOPES,
            field="reviewer_scope",
            signal_id=signal_id,
            warnings=warnings,
        )
        row["reviewer_evidence_role"] = _normalize_label(
            value=fields.get("reviewer_evidence_role"),
            valid_values=VALID_EVIDENCE_ROLES,
            field="reviewer_evidence_role",
            signal_id=signal_id,
            warnings=warnings,
        )
        row["reviewer_error_type"] = _normalize_label(
            value=fields.get("reviewer_error_type"),
            valid_values=VALID_ERROR_TYPES,
            field="reviewer_error_type",
            signal_id=signal_id,
            warnings=warnings,
        )
        row["reviewer_parent_thread"] = _normalize_free_text(
            fields.get("reviewer_parent_thread")
        )
        row["reviewer_child_thread"] = _normalize_free_text(fields.get("reviewer_child_thread"))
        row["reviewer_supported_questions"] = _normalize_questions(
            value=fields.get("reviewer_supported_questions"),
            signal_id=signal_id,
            warnings=warnings,
        )
        row["reviewer_notes"] = _normalize_free_text(fields.get("reviewer_notes"))
        updated_rows.append(row)

    write_jsonl(output_path, updated_rows)
    progress = review_template_progress([output_path])
    report = {
        "packet": str(packet_path),
        "template": str(template_path),
        "output": str(output_path),
        "rows": len(updated_rows),
        "parsed_markdown_rows": len(packet_rows),
        "warning_count": len(warnings),
        "warnings": warnings,
        "progress": progress,
    }
    if report_path:
        write_json(report_path, report)
    return report


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
    review.add_argument("--labels", type=Path)
    review.add_argument("--output", type=Path, required=True)
    review.add_argument("--title", required=True)

    review_template = subparsers.add_parser(
        "review-template",
        help="Write a machine-editable JSONL adjudication template",
    )
    review_template.add_argument("--raw", type=Path, required=True)
    review_template.add_argument("--labels", type=Path)
    review_template.add_argument("--output", type=Path, required=True)

    review_progress = subparsers.add_parser(
        "review-progress",
        help="Report adjudication readiness for review template JSONL files",
    )
    review_progress.add_argument("paths", type=Path, nargs="+")

    finalize = subparsers.add_parser(
        "finalize-review",
        help="Convert completed review template rows into scoreable labels",
    )
    finalize.add_argument("--input", type=Path, required=True)
    finalize.add_argument("--output", type=Path, required=True)
    finalize.add_argument("--label-quality", choices=sorted(VALID_LABEL_QUALITIES), required=True)
    finalize.add_argument("--require-complete", action="store_true")

    apply_packet = subparsers.add_parser(
        "apply-review-packet",
        help="Copy Markdown reviewer answers into a JSONL review template",
    )
    apply_packet.add_argument("--packet", type=Path, required=True)
    apply_packet.add_argument("--template", type=Path, required=True)
    apply_packet.add_argument("--output", type=Path, required=True)
    apply_packet.add_argument("--report", type=Path)

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

    if args.command == "review-progress":
        print(json.dumps(review_template_progress(args.paths), indent=2, sort_keys=True))
        return

    if args.command == "finalize-review":
        result = finalize_review_template(
            input_path=args.input,
            output_path=args.output,
            label_quality=args.label_quality,
            require_complete=args.require_complete,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    if args.command == "apply-review-packet":
        report = apply_review_packet(
            packet_path=args.packet,
            template_path=args.template,
            output_path=args.output,
            report_path=args.report,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return

    row_count = merge_batches(
        input_dir=args.input_dir,
        output_path=args.output,
        pattern=args.pattern,
    )
    print(json.dumps({"output": str(args.output), "rows": row_count}, indent=2))


if __name__ == "__main__":
    main()
