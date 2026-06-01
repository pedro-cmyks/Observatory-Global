from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


EVIDENCE_ROLE_SCHEMA_VERSION = "atlas-evidence-role-teacher-v1"

ROLES = {
    "primary_evidence",
    "context",
    "reaction",
    "analysis",
    "entity_reference",
    "noise",
}

REASON_CODES = {
    "direct_event_match",
    "same_actor",
    "same_place",
    "same_time_window",
    "causal_update",
    "official_action",
    "public_reaction",
    "analysis_frame",
    "background_only",
    "entity_only",
    "generic_roundup",
    "off_topic",
    "insufficient_context",
}

REQUIRED_TEACHER_FIELDS = {
    "signal_id",
    "cluster_id",
    "headline",
    "cluster_label",
    "role",
    "role_confidence",
    "belongs_to_cluster",
    "supports_cluster_claim",
    "reason_codes",
    "rationale",
    "teacher_model",
    "teacher_vendor",
}


def normalize_reason_codes(codes: Iterable[str]) -> list[str]:
    normalized = sorted({str(code).strip() for code in codes if str(code).strip()})
    invalid = [code for code in normalized if code not in REASON_CODES]
    if invalid:
        raise ValueError(f"invalid reason code(s): {', '.join(invalid)}")
    return normalized


def validate_teacher_label(row: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_TEACHER_FIELDS - set(row))
    if missing:
        raise ValueError(f"missing teacher field(s): {', '.join(missing)}")

    role = str(row["role"]).strip()
    if role not in ROLES:
        raise ValueError(f"invalid evidence role: {role}")

    confidence = float(row["role_confidence"])
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("role_confidence must be between 0 and 1")

    validated = dict(row)
    validated["schema_version"] = row.get("schema_version", EVIDENCE_ROLE_SCHEMA_VERSION)
    validated["role"] = role
    validated["role_confidence"] = round(confidence, 4)
    validated["belongs_to_cluster"] = bool(row["belongs_to_cluster"])
    validated["supports_cluster_claim"] = bool(row["supports_cluster_claim"])
    validated["reason_codes"] = normalize_reason_codes(row.get("reason_codes") or [])
    return validated


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
