#!/usr/bin/env python3
"""Read-only recall pilot using GDELT weak-support themes.

The pilot asks: if a dynamic Narrative Thread has compatible GDELT themes, how
many additional recent signals would those themes surface for review? It does
not write to the database and does not promote candidates into the product.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.gdelt_weak_support_audit import (
    DYNAMIC_TOPICS_SQL,
    SCHEMA_VERSION as AUDIT_SCHEMA_VERSION,
    build_thread_audit,
    fetch_thread_audits,
    theme_domains,
)


SCHEMA_VERSION = "atlas-gdelt-weak-recall-pilot-v1"

OVERBROAD_EXPANSION_PREFIXES = (
    "GENERAL_",
    "TAX_FNCACT_",
    "TAX_WORLDLANGUAGES_",
    "WORLDLANGUAGES_",
)

OVERBROAD_EXPANSION_THEMES = {
    "CRISISLEX_C07_SAFETY",
    "CRISISLEX_T11_UPDATESSYMPATHY",
}

GENERIC_LABEL_TERMS = {
    "and", "the", "for", "from", "with", "into", "over", "under",
    "updates", "headlines", "local", "news", "politics", "policy",
    "policies", "public", "global", "topic", "dynamic", "thread",
    "sale", "listings", "victory", "portfolio", "war",
}

CANDIDATE_SQL = """
SELECT
    id AS signal_id,
    headline,
    themes,
    country_code,
    source_lang,
    source_family,
    source_name,
    timestamp
FROM signals_v2
WHERE timestamp >= NOW() - ($1::int * INTERVAL '1 hour')
  AND themes && $2::text[]
  AND NOT (id = ANY($3::bigint[]))
ORDER BY timestamp DESC
LIMIT $4;
"""

SIGNALS_BY_ID_SQL = """
SELECT
    id AS signal_id,
    headline,
    themes,
    country_code,
    source_lang,
    source_family,
    source_name,
    timestamp
FROM signals_v2
WHERE id = ANY($1::bigint[])
ORDER BY timestamp DESC;
"""


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        value = getattr(row, key, default)
    return default if value is None else value


def select_expansion_themes(
    audit: dict[str, Any],
    *,
    min_count: int = 3,
    max_themes: int = 8,
) -> list[str]:
    expected = set(audit.get("expected_domains") or [])
    if not expected:
        return []

    selected: list[str] = []
    for item in audit.get("top_gdelt_themes") or []:
        theme = str(item.get("theme") or "")
        upper_theme = theme.upper()
        count = int(item.get("count") or 0)
        if upper_theme in OVERBROAD_EXPANSION_THEMES:
            continue
        if any(upper_theme.startswith(prefix) for prefix in OVERBROAD_EXPANSION_PREFIXES):
            continue
        domains = theme_domains(theme)
        if count < min_count:
            continue
        if not domains:
            continue
        if not (domains & expected):
            continue
        selected.append(theme)
        if len(selected) >= max_themes:
            break
    return selected


def label_anchor_terms(label: str | None) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", (label or "").lower())
    return {w for w in words if w not in GENERIC_LABEL_TERMS}


def _candidate_matches_anchor(row: Any, anchors: set[str]) -> bool:
    if not anchors:
        return False
    text_parts = [
        str(_row_value(row, "headline", "") or ""),
        " ".join(str(t) for t in (_row_value(row, "themes", []) or [])),
    ]
    text = " ".join(text_parts).replace("_", " ").replace("-", " ").lower()
    return any(re.search(rf"\b{re.escape(anchor)}\b", text) for anchor in anchors)


def build_candidate_item(row: Any, *, expected_domains: set[str]) -> dict[str, Any]:
    themes = list(_row_value(row, "themes", []) or [])
    domains: set[str] = set()
    for theme in themes:
        domains.update(theme_domains(str(theme)))

    if not expected_domains or not domains:
        status = "ambiguous"
    elif expected_domains & domains:
        status = "supported"
    else:
        status = "contradicted"

    ts = _row_value(row, "timestamp")
    return {
        "signal_id": int(_row_value(row, "signal_id", 0)),
        "headline": _row_value(row, "headline", ""),
        "country_code": _row_value(row, "country_code"),
        "source_name": _row_value(row, "source_name"),
        "source_lang": _row_value(row, "source_lang"),
        "source_family": _row_value(row, "source_family"),
        "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else ts,
        "themes": themes[:10],
        "domains": sorted(domains),
        "weak_status": status,
    }


def summarize_expansion(
    *,
    audit: dict[str, Any],
    expansion_themes: list[str],
    current_sample_ids: set[int],
    candidates: list[Any],
    review_limit: int,
) -> dict[str, Any]:
    expected = set(audit.get("expected_domains") or [])
    anchors = label_anchor_terms(str(audit.get("label") or ""))
    if not anchors:
        return {
            "thread_id": audit.get("thread_id"),
            "label": audit.get("label"),
            "current_signal_count": int(audit.get("signal_count") or 0),
            "current_sample_rows": int((audit.get("metrics") or {}).get("sample_rows") or 0),
            "expected_domains": list(audit.get("expected_domains") or []),
            "label_anchor_terms": [],
            "expansion_themes": expansion_themes,
            "added_candidate_count": 0,
            "added_country_count": 0,
            "added_source_count": 0,
            "weak_status_counts": {},
            "review_sample": [],
            "recommendation": "label_review_before_expansion",
        }
    added_items = [
        build_candidate_item(row, expected_domains=expected)
        for row in candidates
        if int(_row_value(row, "signal_id", 0)) not in current_sample_ids
        and _candidate_matches_anchor(row, anchors)
    ]
    status_counts = Counter(item["weak_status"] for item in added_items)
    countries = {item["country_code"] for item in added_items if item.get("country_code")}
    sources = {item["source_name"] for item in added_items if item.get("source_name")}

    return {
        "thread_id": audit.get("thread_id"),
        "label": audit.get("label"),
        "current_signal_count": int(audit.get("signal_count") or 0),
        "current_sample_rows": int((audit.get("metrics") or {}).get("sample_rows") or 0),
        "expected_domains": list(audit.get("expected_domains") or []),
        "label_anchor_terms": sorted(anchors),
        "expansion_themes": expansion_themes,
        "added_candidate_count": len(added_items),
        "added_country_count": len(countries),
        "added_source_count": len(sources),
        "weak_status_counts": dict(status_counts),
        "review_sample": added_items[:review_limit],
        "recommendation": "manual_review" if added_items else "no_candidates",
    }


async def _current_sample_ids_by_topic(conn: asyncpg.Connection, *, limit: int) -> dict[str, set[int]]:
    rows = await conn.fetch(DYNAMIC_TOPICS_SQL, limit)
    result: dict[str, set[int]] = {}
    for row in rows:
        thread_id = f"dynamic-topic-{row['id']}"
        result[thread_id] = {int(x) for x in (row["sample_signal_ids"] or [])}
    return result


async def fetch_candidates(
    conn: asyncpg.Connection,
    *,
    hours: int,
    expansion_themes: list[str],
    current_sample_ids: set[int],
    candidate_limit: int,
) -> list[Any]:
    if not expansion_themes:
        return []
    return list(
        await conn.fetch(
            CANDIDATE_SQL,
            hours,
            expansion_themes,
            sorted(current_sample_ids),
            candidate_limit,
        )
    )


async def run_pilot(
    conn: asyncpg.Connection,
    *,
    hours: int,
    limit: int,
    candidate_limit: int,
    review_limit: int,
) -> list[dict[str, Any]]:
    audits = await fetch_thread_audits(conn, hours=hours, limit=limit)
    current_ids = await _current_sample_ids_by_topic(conn, limit=limit)
    results: list[dict[str, Any]] = []

    for audit in audits:
        expansion_themes = select_expansion_themes(audit)
        sample_ids = current_ids.get(str(audit.get("thread_id")), set())
        candidates = await fetch_candidates(
            conn,
            hours=hours,
            expansion_themes=expansion_themes,
            current_sample_ids=sample_ids,
            candidate_limit=candidate_limit,
        )
        results.append(
            summarize_expansion(
                audit=audit,
                expansion_themes=expansion_themes,
                current_sample_ids=sample_ids,
                candidates=candidates,
                review_limit=review_limit,
            )
        )
    return results


def build_report(
    *,
    hours: int,
    limit: int,
    candidate_limit: int,
    review_limit: int,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_audit_schema": AUDIT_SCHEMA_VERSION,
        "window_hours": hours,
        "thread_limit": limit,
        "candidate_limit_per_thread": candidate_limit,
        "review_limit_per_thread": review_limit,
        "thread_count": len(results),
        "results": results,
        "interpretation": {
            "added_candidate_count": "recent signals matching compatible GDELT themes but not already in the dynamic-topic sample ids",
            "manual_review": "candidate rows are for inspection only; they are not promoted into threads by this report",
            "stop_rule": "if added candidates do not improve answerability or mostly add context/noise, keep them out of the visible thread layer",
        },
    }


async def run(*, database_url: str, hours: int, limit: int, candidate_limit: int, review_limit: int, output: Path) -> dict[str, Any]:
    conn = await asyncpg.connect(database_url)
    try:
        results = await run_pilot(
            conn,
            hours=hours,
            limit=limit,
            candidate_limit=candidate_limit,
            review_limit=review_limit,
        )
    finally:
        await conn.close()

    report = build_report(
        hours=hours,
        limit=limit,
        candidate_limit=candidate_limit,
        review_limit=review_limit,
        results=results,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only GDELT weak-support recall pilot.")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--candidate-limit", type=int, default=500)
    parser.add_argument("--review-limit", type=int, default=20)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/research/topic-quality/gdelt-weak-support/2026-06-04-recall-pilot.json"),
    )
    return parser.parse_args()


async def amain() -> None:
    args = parse_args()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    report = await run(
        database_url=database_url,
        hours=args.hours,
        limit=args.limit,
        candidate_limit=args.candidate_limit,
        review_limit=args.review_limit,
        output=args.output,
    )
    print(json.dumps({
        "schema_version": report["schema_version"],
        "thread_count": report["thread_count"],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(amain())
