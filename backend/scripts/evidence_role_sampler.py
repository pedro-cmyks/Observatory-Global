#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
from pathlib import Path
from typing import Any

from scripts.evidence_role_schema import write_jsonl


PACKET_SCHEMA_VERSION = "atlas-evidence-role-packet-v1"

SAMPLE_SQL = """
WITH latest AS (
    SELECT MAX(snapshot_at) AS snapshot_at
    FROM emergent_clusters
    WHERE snapshot_at > NOW() - ($1::int * INTERVAL '1 hour')
),
clusters AS (
    SELECT ec.*
    FROM emergent_clusters ec
    JOIN latest l ON l.snapshot_at = ec.snapshot_at
    ORDER BY ec.n_signals DESC, ec.raw_signal_count DESC
    LIMIT $2
),
cluster_signals AS (
    SELECT
        ec.id AS cluster_pk,
        ec.snapshot_at,
        ec.label AS cluster_label,
        ec.description AS cluster_description,
        ec.raw_signal_count,
        ec.n_signals,
        ec.cohesion,
        unnest(ec.sample_signal_ids) AS signal_id
    FROM clusters ec
),
candidate AS (
    SELECT DISTINCT ON (sta.signal_id)
        sta.signal_id,
        at.slug AS candidate_topic_slug,
        at.label AS candidate_topic_label,
        sta.confidence AS candidate_confidence,
        sta.gate_score,
        sta.gate_kept,
        COALESCE(sta.evidence->'matched_terms', '[]'::jsonb) AS matched_terms
    FROM cluster_signals cs
    LEFT JOIN signal_topic_assignments sta ON sta.signal_id = cs.signal_id
    JOIN atlas_topics at ON at.id = sta.topic_id
    WHERE sta.method = 'lexicon'
      AND sta.model_version = 'theme-hint-lex-v2'
    ORDER BY sta.signal_id, sta.gate_score DESC NULLS LAST, sta.confidence DESC
)
SELECT
    cs.cluster_pk,
    cs.snapshot_at,
    cs.cluster_label,
    cs.cluster_description,
    cs.raw_signal_count,
    cs.n_signals,
    cs.cohesion,
    s.id AS signal_id,
    s.headline,
    s.source_name,
    s.source_lang,
    s.country_code,
    c.candidate_topic_slug,
    c.candidate_topic_label,
    c.candidate_confidence,
    c.gate_score,
    c.gate_kept,
    c.matched_terms,
    'sample_signal_id'::text AS sample_reason
FROM cluster_signals cs
JOIN signals_v2 s ON s.id = cs.signal_id
LEFT JOIN candidate c ON c.signal_id = s.id
ORDER BY cs.n_signals DESC, cs.cluster_pk, s.id
LIMIT $3;
"""


def build_cluster_id(snapshot_at: Any, cluster_pk: int) -> str:
    if hasattr(snapshot_at, "isoformat"):
        snapshot_value = snapshot_at.isoformat()
    else:
        snapshot_value = str(snapshot_at)
    return f"{snapshot_value}/{cluster_pk}"


def _text_value(value: Any) -> str | None:
    if value is None:
        return None
    return html.unescape(str(value))


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        return json.loads(value)
    return value


def build_teacher_packet_row(row: dict[str, Any]) -> dict[str, Any]:
    matched_terms = _json_value(row.get("matched_terms"), [])
    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "signal_id": int(row["signal_id"]),
        "headline": _text_value(row.get("headline")),
        "source_name": row.get("source_name"),
        "source_lang": row.get("source_lang"),
        "country_code": row.get("country_code"),
        "cluster_id": build_cluster_id(row["snapshot_at"], int(row["cluster_pk"])),
        "cluster_pk": int(row["cluster_pk"]),
        "snapshot_at": build_cluster_id(row["snapshot_at"], int(row["cluster_pk"])).rsplit("/", 1)[0],
        "cluster_label": _text_value(row.get("cluster_label")),
        "cluster_description": _text_value(row.get("cluster_description")),
        "raw_signal_count": int(row.get("raw_signal_count") or 0),
        "n_signals": int(row.get("n_signals") or 0),
        "cohesion": float(row["cohesion"]) if row.get("cohesion") is not None else None,
        "candidate_topic_slug": row.get("candidate_topic_slug"),
        "candidate_topic_label": row.get("candidate_topic_label"),
        "candidate_confidence": (
            float(row["candidate_confidence"])
            if row.get("candidate_confidence") is not None
            else None
        ),
        "gate_score": float(row["gate_score"]) if row.get("gate_score") is not None else None,
        "gate_kept": bool(row["gate_kept"]) if row.get("gate_kept") is not None else None,
        "matched_terms": matched_terms,
        "sample_reason": row.get("sample_reason", "sample_signal_id"),
        "teacher_role": None,
        "teacher_rationale": None,
    }


async def run(args: argparse.Namespace) -> list[dict[str, Any]]:
    import asyncpg

    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch(SAMPLE_SQL, args.hours, args.clusters, args.limit)
    finally:
        await conn.close()
    return [build_teacher_packet_row(dict(row)) for row in rows]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sample cluster/signal rows for evidence-role teacher labeling."
    )
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--clusters", type=int, default=30)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = asyncio.run(run(args))
    write_jsonl(args.output, rows)
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
