#!/usr/bin/env python3
"""LLM-as-annotator for the Atlas topic benchmark.

Unlike `llm_baseline_classifier.py`, which has the LLM predict a topic
from scratch, this script has the LLM **judge** the existing Atlas v2
assignment in the same role as the human reviewer. Output fields mirror
the reviewer template (`annotator_decision`, `annotator_scope`,
`annotator_evidence_role`, `annotator_error_type`,
`annotator_parent_thread`, `annotator_child_thread`,
`annotator_supported_questions`, `annotator_notes`,
`annotator_confidence`).

Schema version: atlas-llm-annotator-v1
Provenance label: defaults to `sonnet46_initial` (single LLM annotator,
initial pass, NOT consensus / NOT calibrated).

Required env:
  ANTHROPIC_API_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import anthropic
except ImportError as exc:  # pragma: no cover
    print(f"missing dependency: {exc}", file=sys.stderr)
    sys.exit(2)


SCHEMA_VERSION = "atlas-llm-annotator-v1"
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 600
DEFAULT_TEMPERATURE = 0.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 4.0
DEFAULT_PROVENANCE = "sonnet46_initial"

VALID_DECISIONS = {"correct", "incorrect", "partial", "unclear"}
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
VALID_ERROR_TYPES = {
    "substring_noise",
    "scope_mismatch",
    "parent_thread_candidate",
    "primary_context_mismatch",
    "insufficient_context",
    "off_topic",
}
VALID_QUESTIONS = {
    "why_moving",
    "what_changed",
    "where_concentrated",
    "subthreads_forming",
    "sources_driving",
    "evidence_support",
    "related_thread",
}


SYSTEM_PROMPT = (
    "You are a single-reviewer annotator for a narrative-intelligence "
    "benchmark. You will be shown a news headline, its theme tags, and the "
    "topic label that an automated classifier (Atlas v2) assigned. Your job "
    "is to judge whether that classifier label is supported by the headline "
    "as primary evidence. Be strict: reject the label if the headline is "
    "merely tangential or about a different scope. Reply in strict JSON "
    "with the keys: decision (one of correct, incorrect, partial, unclear), "
    "scope (one of domain, parent_thread, child_thread, entity_thread, "
    "geo_context, source_context, evidence, context_signal, noise), "
    "evidence_role (one of primary_event, followup, background, reaction, "
    "analysis, public_attention, source_amplification, not_evidence), "
    "error_type (one of substring_noise, scope_mismatch, "
    "parent_thread_candidate, primary_context_mismatch, "
    "insufficient_context, off_topic, or null if decision is correct), "
    "parent_thread (free-text slug or null), "
    "child_thread (free-text slug or null), "
    "supported_questions (list of why_moving, what_changed, "
    "where_concentrated, subthreads_forming, sources_driving, "
    "evidence_support, related_thread; empty list if none), "
    "confidence (0..1 float), and notes (one short sentence, no more than "
    "30 words). Output the JSON object only. No prose."
)


def _build_user_prompt(row: dict[str, Any]) -> str:
    themes = row.get("themes") or []
    if not isinstance(themes, list):
        themes = []
    return "\n".join(
        [
            f"headline: {str(row.get('headline', '')).strip()}",
            f"themes: {', '.join(themes) if themes else '(none)'}",
            f"source_lang: {row.get('source_lang') or 'unknown'}",
            f"country_code: {row.get('country_code') or 'unknown'}",
            f"source_name: {row.get('source_name') or 'unknown'}",
            f"atlas_assigned_topic_slug: {row.get('assigned_topic_slug')}",
            f"atlas_assigned_topic_label: {row.get('assigned_topic_label')}",
            "",
            "OUTPUT (strict JSON, no prose):",
        ]
    )


_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def _parse_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("empty response")
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        raise ValueError(f"no JSON object in response: {text[:200]!r}")
    payload = json.loads(match.group(0))

    decision = payload.get("decision")
    if decision not in VALID_DECISIONS:
        raise ValueError(f"invalid decision: {decision!r}")

    scope = payload.get("scope")
    if scope not in VALID_SCOPES and scope is not None:
        raise ValueError(f"invalid scope: {scope!r}")

    evidence_role = payload.get("evidence_role")
    if evidence_role not in VALID_EVIDENCE_ROLES and evidence_role is not None:
        raise ValueError(f"invalid evidence_role: {evidence_role!r}")

    error_type = payload.get("error_type")
    if error_type is not None and error_type not in VALID_ERROR_TYPES:
        # Accept empty string as null for forgiveness.
        if str(error_type).strip() == "":
            error_type = None
        else:
            raise ValueError(f"invalid error_type: {error_type!r}")

    parent = payload.get("parent_thread")
    parent = str(parent).strip() if parent else None
    child = payload.get("child_thread")
    child = str(child).strip() if child else None
    if parent == "":
        parent = None
    if child == "":
        child = None

    questions = payload.get("supported_questions") or []
    if not isinstance(questions, list):
        questions = []
    questions = [q for q in questions if q in VALID_QUESTIONS]

    confidence = payload.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = None

    notes = str(payload.get("notes") or "").strip()

    return {
        "decision": decision,
        "scope": scope,
        "evidence_role": evidence_role,
        "error_type": error_type,
        "parent_thread": parent,
        "child_thread": child,
        "supported_questions": questions,
        "confidence": confidence,
        "notes": notes,
    }


def _call_llm(
    client: "anthropic.Anthropic",
    *,
    model: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
    retries: int,
    backoff_seconds: float,
) -> tuple[str, int, str | None]:
    last_error: str | None = None
    for attempt in range(1, retries + 1):
        try:
            create_kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}],
            }
            # Some models (e.g. opus-4-7) reject the temperature parameter.
            if temperature is not None:
                create_kwargs["temperature"] = temperature
            response = client.messages.create(**create_kwargs)
            text = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            )
            return text, attempt, None
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(backoff_seconds * attempt)
    return "", retries, last_error


def annotate_row(
    row: dict[str, Any],
    *,
    client: "anthropic.Anthropic",
    model: str,
    provenance: str,
    max_tokens: int,
    temperature: float,
    retries: int,
    backoff_seconds: float,
) -> dict[str, Any]:
    user_prompt = _build_user_prompt(row)
    raw, attempts, error = _call_llm(
        client,
        model=model,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        retries=retries,
        backoff_seconds=backoff_seconds,
    )
    annotation = {
        "annotator_provenance": provenance,
        "annotator_model": model,
        "annotator_decision": None,
        "annotator_scope": None,
        "annotator_evidence_role": None,
        "annotator_error_type": None,
        "annotator_parent_thread": None,
        "annotator_child_thread": None,
        "annotator_supported_questions": [],
        "annotator_notes": "",
        "annotator_confidence": None,
        "annotator_raw_response": raw,
        "annotator_attempts": attempts,
        "annotator_error": error,
    }
    if raw and not error:
        try:
            parsed = _parse_response(raw)
            annotation["annotator_decision"] = parsed["decision"]
            annotation["annotator_scope"] = parsed["scope"]
            annotation["annotator_evidence_role"] = parsed["evidence_role"]
            annotation["annotator_error_type"] = parsed["error_type"]
            annotation["annotator_parent_thread"] = parsed["parent_thread"]
            annotation["annotator_child_thread"] = parsed["child_thread"]
            annotation["annotator_supported_questions"] = parsed["supported_questions"]
            annotation["annotator_notes"] = parsed["notes"]
            annotation["annotator_confidence"] = parsed["confidence"]
        except (ValueError, json.JSONDecodeError) as exc:
            annotation["annotator_error"] = f"parse_error: {exc}"

    merged = {**row, **annotation, "schema_version": SCHEMA_VERSION}
    return merged


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _existing_signal_ids(path: Path) -> set[int]:
    if not path.exists():
        return set()
    seen: set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        seen.add(int(row.get("signal_id", -1)))
    return seen


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM-as-annotator for atlas benchmark.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--provenance", default=DEFAULT_PROVENANCE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--no-temperature", action="store_true",
                        help="Omit the temperature parameter (required for opus-4-7).")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--backoff-seconds", type=float, default=DEFAULT_BACKOFF_SECONDS)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(2)

    rows = _read_jsonl(args.input)
    if args.max_rows is not None:
        rows = rows[: args.max_rows]

    skip = _existing_signal_ids(args.output) if args.resume else set()
    client = anthropic.Anthropic(api_key=api_key)
    temperature = None if args.no_temperature else args.temperature

    written = 0
    for row in rows:
        sid = int(row.get("signal_id", -1))
        if sid in skip:
            continue
        annotated = annotate_row(
            row,
            client=client,
            model=args.model,
            provenance=args.provenance,
            max_tokens=args.max_tokens,
            temperature=temperature,
            retries=args.retries,
            backoff_seconds=args.backoff_seconds,
        )
        _append_jsonl(args.output, annotated)
        written += 1
        print(
            f"signal_id={sid} decision={annotated['annotator_decision']} "
            f"scope={annotated['annotator_scope']} attempts={annotated['annotator_attempts']} "
            f"error={annotated['annotator_error']}",
            file=sys.stderr,
        )

    print(json.dumps({
        "input": str(args.input),
        "output": str(args.output),
        "rows_written": written,
        "model": args.model,
        "provenance": args.provenance,
    }, indent=2))


if __name__ == "__main__":
    main()
