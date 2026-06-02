#!/usr/bin/env python3
"""Run a small local Ollama benchmark against Atlas review rows.

This pilot is intentionally read-only with respect to review templates. It writes
separate `ollama_*` annotations plus resolved `gold_*` labels for comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.topic_benchmark_harness import (
    VALID_DECISIONS,
    VALID_ERROR_TYPES,
    VALID_EVIDENCE_ROLES,
    VALID_SCOPES,
    VALID_SUPPORTED_QUESTIONS,
)


DEFAULT_MODEL = "llama3.2:1b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
REVIEW_FIELDS = (
    "decision",
    "error_type",
    "scope",
    "evidence_role",
    "parent_thread",
    "child_thread",
    "supported_questions",
)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    cleaned = value.strip().lower().replace("-", "_").replace(" ", "_")
    if cleaned in {"", "null", "none", "n/a"}:
        return None
    return cleaned or None


def _first_meaningful_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key not in payload or not _has_value(payload[key]):
            payload[key] = value
    return payload


def _normalize_optional_label(
    *,
    raw: dict[str, Any],
    field: str,
    valid_values: set[str],
    warnings: list[str],
    output_name: str,
) -> str | None:
    value = _normalize_text(raw.get(field))
    if value is None:
        return None
    if value not in valid_values:
        warnings.append(f"Invalid {output_name}: {raw.get(field)!r}")
        return None
    return value


def _normalize_supported_questions(raw: dict[str, Any], warnings: list[str]) -> list[str]:
    questions = raw.get("supported_questions")
    if questions is None:
        return []
    if not isinstance(questions, list):
        warnings.append("supported_questions must be a list")
        return []

    normalized: list[str] = []
    for question in questions:
        value = _normalize_text(question)
        if value in VALID_SUPPORTED_QUESTIONS:
            normalized.append(value)
        else:
            warnings.append(f"Invalid supported_question: {question!r}")
    return normalized


def normalize_ollama_annotation(raw: dict[str, Any] | str) -> dict[str, Any]:
    warnings: list[str] = []
    if isinstance(raw, str):
        try:
            payload = json.loads(raw, object_pairs_hook=_first_meaningful_pairs)
        except json.JSONDecodeError as exc:
            payload = {}
            warnings.append(f"Invalid JSON response: {exc.msg}")
    else:
        payload = raw

    if not isinstance(payload, dict):
        payload = {}
        warnings.append("Ollama response must be a JSON object")

    decision = _normalize_optional_label(
        raw=payload,
        field="decision",
        valid_values=VALID_DECISIONS,
        warnings=warnings,
        output_name="decision",
    )
    error_type = _normalize_optional_label(
        raw=payload,
        field="error_type",
        valid_values=VALID_ERROR_TYPES,
        warnings=warnings,
        output_name="error_type",
    )
    scope = _normalize_optional_label(
        raw=payload,
        field="scope",
        valid_values=VALID_SCOPES,
        warnings=warnings,
        output_name="scope",
    )
    evidence_role = _normalize_optional_label(
        raw=payload,
        field="evidence_role",
        valid_values=VALID_EVIDENCE_ROLES,
        warnings=warnings,
        output_name="evidence_role",
    )

    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, str):
        notes = str(notes)

    return {
        "ollama_decision": decision,
        "ollama_error_type": error_type,
        "ollama_scope": scope,
        "ollama_evidence_role": evidence_role,
        "ollama_parent_thread": payload.get("parent_thread") or None,
        "ollama_child_thread": payload.get("child_thread") or None,
        "ollama_supported_questions": _normalize_supported_questions(payload, warnings),
        "ollama_notes": notes,
        "validation_warnings": warnings,
    }


def _review_value(row: dict[str, Any], name: str) -> Any:
    reviewer_value = row.get(f"reviewer_{name}")
    if _has_value(reviewer_value):
        return reviewer_value
    if row.get("accept_assistant_label") is True:
        return row.get(f"assistant_{name}")
    return None


def resolve_gold_from_review_row(row: dict[str, Any]) -> dict[str, Any] | None:
    decision = _review_value(row, "decision")
    if not _has_value(decision):
        return None

    review_source = (
        "reviewer_adjudicated"
        if _has_value(row.get("reviewer_decision"))
        else "assistant_accepted"
    )
    gold: dict[str, Any] = {"review_source": review_source}
    for field in REVIEW_FIELDS:
        value = _review_value(row, field)
        if field == "supported_questions" and value is None:
            value = []
        gold[f"gold_{field}"] = value
    return gold


def build_ollama_prompt(row: dict[str, Any]) -> str:
    evidence = row.get("evidence") or {}
    evidence_text = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    return f"""You are labeling one Atlas topic assignment for benchmark validation.

Return only one JSON object with these keys:
- "decision": correct | incorrect | unclear
- "error_type": substring_noise | scope_mismatch | parent_thread_candidate | primary_context_mismatch | insufficient_context | off_topic | null
- "scope": domain | parent_thread | child_thread | entity_thread | geo_context | source_context | evidence | context_signal | noise | null
- "evidence_role": primary_event | followup | background | reaction | analysis | public_attention | source_amplification | not_evidence | null
- "parent_thread": short natural-language parent thread or null
- "child_thread": short natural-language child thread or null
- "supported_questions": array using only why_moving, what_changed, where_concentrated, subthreads_forming, sources_driving, evidence_support, related_thread
- "notes": one short sentence

Decide whether the headline is real evidence for the assigned Atlas topic.

Assigned topic slug: {row.get("assigned_topic_slug")}
Assigned topic label: {row.get("assigned_topic_label")}
Headline: {row.get("headline")}
Source: {row.get("source_name")} ({row.get("source_family")})
Language: {row.get("source_lang")}
Country: {row.get("country_code")}
Evidence JSON: {evidence_text}
"""


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def call_ollama(
    *,
    prompt: str,
    model: str,
    ollama_url: str,
    timeout: float,
    num_predict: int,
    num_ctx: int,
) -> dict[str, Any]:
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        },
    }
    request = urllib.request.Request(
        f"{ollama_url.rstrip('/')}/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    payload["elapsed_seconds"] = round(time.monotonic() - started, 4)
    return payload


def _field_accuracy(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    compared = 0
    matched = 0
    for row in rows:
        gold = row.get(f"gold_{field}")
        prediction = row.get(f"ollama_{field}")
        if not _has_value(gold) or not _has_value(prediction):
            continue
        compared += 1
        if gold == prediction:
            matched += 1
    return {
        "matched": matched,
        "compared": compared,
        "accuracy": round(matched / compared, 4) if compared else None,
    }


def score_ollama_predictions(rows: list[dict[str, Any]], *, model: str) -> dict[str, Any]:
    return {
        "schema_version": "atlas-ollama-pilot-v1",
        "model": model,
        "rows": len(rows),
        "scoreable_rows": sum(1 for row in rows if _has_value(row.get("gold_decision"))),
        "invalid_prediction_rows": sum(1 for row in rows if row.get("validation_warnings")),
        "error_rows": sum(1 for row in rows if row.get("ollama_error")),
        "decision": _field_accuracy(rows, "decision"),
        "error_type": _field_accuracy(rows, "error_type"),
        "scope": _field_accuracy(rows, "scope"),
        "evidence_role": _field_accuracy(rows, "evidence_role"),
    }


def run_pilot(
    *,
    input_path: Path,
    output_path: Path,
    report_path: Path,
    model: str,
    ollama_url: str,
    limit: int,
    timeout: float,
    num_predict: int,
    num_ctx: int,
) -> dict[str, Any]:
    source_rows = _read_jsonl(input_path)
    scored_rows: list[dict[str, Any]] = []

    for row in source_rows:
        gold = resolve_gold_from_review_row(row)
        if gold is None:
            continue

        prompt = build_ollama_prompt(row)
        output_row = {
            "signal_id": row.get("signal_id"),
            "assigned_topic_slug": row.get("assigned_topic_slug"),
            "assigned_topic_label": row.get("assigned_topic_label"),
            "headline": row.get("headline"),
            "source_name": row.get("source_name"),
            "source_family": row.get("source_family"),
            "source_lang": row.get("source_lang"),
            "country_code": row.get("country_code"),
            **gold,
        }
        try:
            response = call_ollama(
                prompt=prompt,
                model=model,
                ollama_url=ollama_url,
                timeout=timeout,
                num_predict=num_predict,
                num_ctx=num_ctx,
            )
            annotation = normalize_ollama_annotation(response.get("response", ""))
            output_row.update(annotation)
            output_row["ollama_model"] = response.get("model") or model
            output_row["ollama_elapsed_seconds"] = response.get("elapsed_seconds")
            output_row["ollama_total_duration_ns"] = response.get("total_duration")
            output_row["ollama_raw_response"] = response.get("response")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            output_row.update(normalize_ollama_annotation({}))
            output_row["ollama_error"] = str(exc)

        scored_rows.append(output_row)
        if len(scored_rows) >= limit:
            break

    _write_jsonl(output_path, scored_rows)
    report = score_ollama_predictions(scored_rows, model=model)
    report.update(
        {
            "input": str(input_path),
            "output": str(output_path),
            "scoreable_source_rows": sum(
                1 for row in source_rows if resolve_gold_from_review_row(row) is not None
            ),
            "limit": limit,
        }
    )
    _write_json(report_path, report)
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local Ollama pilot on Atlas review rows")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--num-predict", type=int, default=180)
    parser.add_argument("--num-ctx", type=int, default=1024)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = run_pilot(
        input_path=args.input,
        output_path=args.output,
        report_path=args.report,
        model=args.model,
        ollama_url=args.ollama_url,
        limit=args.limit,
        timeout=args.timeout,
        num_predict=args.num_predict,
        num_ctx=args.num_ctx,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
