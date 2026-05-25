#!/usr/bin/env python3
"""Generate and score atlas topic benchmark labels.

The harness is deliberately simple:
- `sample` creates JSONL records that an analyst can label.
- `score` reads labeled JSONL and reports precision gates.

No writes are performed. Persisting labels into `topic_learning_examples` should
come after the review workflow is accepted.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import asyncpg


BENCHMARK_SCHEMA_VERSION = "atlas-topic-benchmark-v2"
MODEL_VERSION = "theme-hint-lex-v2"
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


SAMPLE_SQL = """
WITH target_topics AS (
    SELECT id, slug, label
    FROM atlas_topics
    WHERE is_active = TRUE
      AND ($3::text[] IS NULL OR slug = ANY($3::text[]))
),
scoped AS (
    SELECT
        sta.signal_id,
        tt.slug,
        tt.label,
        s.headline,
        s.source_name,
        s.source_family,
        s.source_lang,
        s.country_code,
        sta.confidence,
        sta.evidence,
        CASE
            WHEN COALESCE((sta.evidence->>'lex_count')::int, 0) > 0
                 AND sta.confidence >= 0.75 THEN 'lex_high_conf'
            WHEN COALESCE((sta.evidence->>'lex_count')::int, 0) > 0
                 THEN 'lex_low_conf'
            WHEN sta.confidence >= 0.75 THEN 'theme_high_conf'
            ELSE 'theme_low_conf'
        END AS sample_bucket,
        ROW_NUMBER() OVER (
            PARTITION BY tt.slug,
                         CASE
                             WHEN COALESCE((sta.evidence->>'lex_count')::int, 0) > 0
                                  AND sta.confidence >= 0.75 THEN 'lex_high_conf'
                             WHEN COALESCE((sta.evidence->>'lex_count')::int, 0) > 0
                                  THEN 'lex_low_conf'
                             WHEN sta.confidence >= 0.75 THEN 'theme_high_conf'
                             ELSE 'theme_low_conf'
                         END
            ORDER BY md5(sta.signal_id::text)
        ) AS rn
    FROM signal_topic_assignments sta
    JOIN target_topics tt ON tt.id = sta.topic_id
    JOIN signals_v2 s ON s.id = sta.signal_id
    WHERE sta.model_version = $1
      AND sta.assigned_at >= NOW() - ($2::int * INTERVAL '1 hour')
      AND s.headline IS NOT NULL
)
SELECT
    signal_id,
    slug,
    label,
    headline,
    source_name,
    source_family,
    source_lang,
    country_code,
    confidence,
    evidence,
    sample_bucket
FROM scoped
WHERE rn <= $4
ORDER BY slug, sample_bucket, rn;
"""


@dataclass(frozen=True)
class PrecisionGate:
    minimum: float = 0.85
    target: float = 0.90

    def classify(self, precision: float | None) -> str:
        if precision is None or precision < self.minimum:
            return "fail"
        if precision >= self.target:
            return "pass_target"
        return "pass_minimum"


def build_benchmark_item(
    *,
    signal_id: int,
    topic_slug: str,
    topic_label: str,
    headline: str,
    source_name: str | None,
    source_family: str | None,
    source_lang: str | None,
    country_code: str | None,
    confidence: float | None,
    evidence: dict[str, Any] | str | None,
    sample_bucket: str,
) -> dict[str, Any]:
    if isinstance(evidence, str):
        try:
            evidence_payload: dict[str, Any] = json.loads(evidence)
        except json.JSONDecodeError:
            evidence_payload = {}
    else:
        evidence_payload = evidence or {}

    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "signal_id": int(signal_id),
        "assigned_topic_slug": topic_slug,
        "assigned_topic_label": topic_label,
        "headline": headline,
        "source_name": source_name,
        "source_family": source_family,
        "source_lang": source_lang,
        "country_code": country_code,
        "confidence": round(float(confidence or 0), 4),
        "sample_bucket": sample_bucket,
        "evidence": evidence_payload,
        "gold_decision": None,
        "gold_topic_slug": None,
        "gold_error_type": None,
        "gold_scope": None,
        "gold_evidence_role": None,
        "gold_parent_thread": None,
        "gold_child_thread": None,
        "gold_supported_questions": [],
        "notes": None,
    }


def _coerce_item(item: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(item, str):
        return json.loads(item)
    return item


def _empty_counts() -> dict[str, int]:
    return {"labeled": 0, "correct": 0, "incorrect": 0, "unclear": 0}


def _summarize_counts(counts: dict[str, int], gate: PrecisionGate) -> dict[str, Any]:
    denominator = counts["correct"] + counts["incorrect"]
    precision = round(counts["correct"] / denominator, 4) if denominator else None
    return {
        "labeled": denominator,
        "correct": counts["correct"],
        "incorrect": counts["incorrect"],
        "unclear": counts["unclear"],
        "precision": precision,
        "gate": gate.classify(precision),
    }


def _count_value(target: dict[str, int], value: str | None) -> None:
    if value:
        target[value] = target.get(value, 0) + 1


def _validate_optional_label(
    *,
    item: dict[str, Any],
    field: str,
    valid_values: set[str],
) -> str | None:
    value = item.get(field)
    if value is None:
        return None
    if value not in valid_values:
        raise ValueError(f"Invalid {field}: {value!r}")
    return value


def _validate_supported_questions(item: dict[str, Any]) -> list[str]:
    raw_questions = item.get("gold_supported_questions")
    if raw_questions is None:
        return []
    if not isinstance(raw_questions, list):
        raise ValueError("gold_supported_questions must be a list")

    questions: list[str] = []
    for question in raw_questions:
        if question not in VALID_SUPPORTED_QUESTIONS:
            raise ValueError(f"Invalid gold_supported_questions value: {question!r}")
        questions.append(question)
    return questions


def score_labeled_items(
    items: Iterable[dict[str, Any] | str],
    *,
    gate: PrecisionGate | None = None,
) -> dict[str, Any]:
    active_gate = gate or PrecisionGate()
    overall = _empty_counts()
    by_topic_counts: dict[str, dict[str, int]] = {}
    by_error_type: dict[str, int] = {}
    by_scope: dict[str, int] = {}
    by_evidence_role: dict[str, int] = {}
    by_supported_question: dict[str, int] = {}

    for raw in items:
        item = _coerce_item(raw)
        decision = item.get("gold_decision")
        if decision is None:
            continue
        if decision not in VALID_DECISIONS:
            raise ValueError(f"Invalid gold_decision: {decision!r}")
        error_type = item.get("gold_error_type")
        if error_type is not None and error_type not in VALID_ERROR_TYPES:
            raise ValueError(f"Invalid gold_error_type: {error_type!r}")
        scope = _validate_optional_label(
            item=item,
            field="gold_scope",
            valid_values=VALID_SCOPES,
        )
        evidence_role = _validate_optional_label(
            item=item,
            field="gold_evidence_role",
            valid_values=VALID_EVIDENCE_ROLES,
        )
        supported_questions = _validate_supported_questions(item)

        topic_slug = item.get("assigned_topic_slug") or "unknown"
        topic_counts = by_topic_counts.setdefault(topic_slug, _empty_counts())
        _count_value(by_scope, scope)
        _count_value(by_evidence_role, evidence_role)
        for question in supported_questions:
            by_supported_question[question] = by_supported_question.get(question, 0) + 1

        if decision == "unclear":
            overall["unclear"] += 1
            topic_counts["unclear"] += 1
            if error_type:
                by_error_type[error_type] = by_error_type.get(error_type, 0) + 1
            continue
        overall[decision] += 1
        topic_counts[decision] += 1
        if decision == "incorrect" and error_type:
            by_error_type[error_type] = by_error_type.get(error_type, 0) + 1

    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "gate": {"minimum": active_gate.minimum, "target": active_gate.target},
        "overall": _summarize_counts(overall, active_gate),
        "by_topic": {
            slug: _summarize_counts(counts, active_gate)
            for slug, counts in sorted(by_topic_counts.items())
        },
        "by_error_type": dict(sorted(by_error_type.items())),
        "by_scope": dict(sorted(by_scope.items())),
        "by_evidence_role": dict(sorted(by_evidence_role.items())),
        "by_supported_question": dict(sorted(by_supported_question.items())),
    }


async def fetch_sample(
    *,
    database_url: str,
    hours: int,
    topics: list[str] | None,
    per_bucket: int,
) -> list[dict[str, Any]]:
    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch(
            SAMPLE_SQL,
            MODEL_VERSION,
            hours,
            topics if topics else None,
            per_bucket,
        )
    finally:
        await conn.close()

    return [
        build_benchmark_item(
            signal_id=row["signal_id"],
            topic_slug=row["slug"],
            topic_label=row["label"],
            headline=row["headline"],
            source_name=row["source_name"],
            source_family=row["source_family"],
            source_lang=row["source_lang"],
            country_code=row["country_code"],
            confidence=row["confidence"],
            evidence=row["evidence"],
            sample_bucket=row["sample_bucket"],
        )
        for row in rows
    ]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    )


def _read_jsonl(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if line.strip()]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas topic benchmark harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sample = subparsers.add_parser("sample", help="Generate label-ready JSONL sample")
    sample.add_argument("--database-url", default=os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"))
    sample.add_argument("--hours", type=int, default=24)
    sample.add_argument("--topic", action="append", default=[])
    sample.add_argument("--per-bucket", type=int, default=8)
    sample.add_argument("--output", type=Path, required=True)

    score = subparsers.add_parser("score", help="Score labeled JSONL sample")
    score.add_argument("--input", type=Path, required=True)
    score.add_argument("--output", type=Path)
    score.add_argument("--minimum", type=float, default=0.85)
    score.add_argument("--target", type=float, default=0.90)

    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.command == "sample":
        if not args.database_url:
            raise SystemExit("DATABASE_URL or SUPABASE_DB_URL required")
        rows = asyncio.run(
            fetch_sample(
                database_url=args.database_url,
                hours=args.hours,
                topics=args.topic,
                per_bucket=args.per_bucket,
            )
        )
        _write_jsonl(args.output, rows)
        print(f"Wrote {len(rows)} benchmark rows to {args.output}")
        return

    report = score_labeled_items(
        _read_jsonl(args.input),
        gate=PrecisionGate(minimum=args.minimum, target=args.target),
    )
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n")
        print(f"Wrote benchmark score to {args.output}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
