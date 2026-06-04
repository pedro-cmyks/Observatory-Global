#!/usr/bin/env python3
"""Read-only GDELT weak-support audit for dynamic Narrative Threads.

GDELT themes are broad and biased, so this script does not treat them as truth.
It measures whether those themes weakly support, contradict, or fragment the
current dynamic-topic label and reports language/source/country bias slices.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg


SCHEMA_VERSION = "atlas-gdelt-weak-support-v1"

GLOBAL_NORTH = {
    "AD", "AT", "AU", "BE", "CA", "CH", "DE", "DK", "ES", "FI", "FR", "GB",
    "GR", "IE", "IS", "IT", "JP", "KR", "LU", "MC", "NL", "NO", "NZ", "PT",
    "SE", "US",
}

DOMAIN_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("conflict", ("conflict", "violence", "war", "military", "armed", "attack", "strike", "peacekeeping", "fragility")),
    ("policy", ("policy", "politics", "diplomacy", "election", "government", "legislation", "justice", "dispute", "russia", "ukraine")),
    ("rights", ("rights", "freedom", "discrimination", "gender", "minority", "labor")),
    ("economy", ("economic", "economy", "finance", "inflation", "food", "fuel", "housing", "trade", "market")),
    ("health", ("health", "disease", "epidemic", "pandemic", "hospital", "medicine")),
    ("migration", ("migration", "refugee", "border", "displacement", "asylum")),
    ("environment", ("environment", "climate", "water", "drought", "flood", "wildfire", "mining")),
    ("technology", ("technology", "digital", "cyber", "ai", "ict")),
    ("media_social", ("media_social", "social media", "media social", "online")),
    ("public_safety", ("crime", "police", "public safety", "security", "accident", "crash")),
    ("disaster", ("disaster", "earthquake", "storm", "explosion", "emergency")),
]

PREFIX_DOMAINS: list[tuple[str, tuple[str, ...]]] = [
    ("MEDIA_SOCIAL", ("media_social",)),
    ("USPEC_POLICY", ("policy",)),
    ("USPEC_POLITICS", ("policy",)),
    ("UNGP_FREEDOM", ("rights", "policy")),
    ("UNGP_DISCRIMINATION", ("rights", "policy")),
    ("UNGP_HUMAN_RIGHTS", ("rights", "policy")),
    ("UNGP_FORESTS", ("environment",)),
    ("WB_2432", ("conflict",)),
    ("WB_2471", ("conflict", "policy")),
    ("WB_840", ("policy",)),
    ("WB_843", ("policy",)),
    ("TAX_DISEASE", ("health",)),
    ("HEALTH_", ("health",)),
    ("ENV_", ("environment",)),
    ("ECON_", ("economy",)),
    ("EPU_", ("policy", "economy")),
    ("CRISISLEX_", ("disaster", "conflict")),
]


DYNAMIC_TOPICS_SQL = """
SELECT
    dt.id,
    dt.label,
    dt.agg_n_signals,
    dt.noise_rate,
    dt.mean_cohesion,
    ARRAY(
        SELECT DISTINCT code
        FROM dynamic_topic_members dtm
        JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec.top_country_codes, ARRAY[]::text[])) AS code
        WHERE dtm.dynamic_topic_id = dt.id
        LIMIT 20
    ) AS top_country_codes,
    ARRAY(
        SELECT DISTINCT sid
        FROM dynamic_topic_members dtm
        JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec.sample_signal_ids, ARRAY[]::bigint[])) AS sid
        WHERE dtm.dynamic_topic_id = dt.id
        LIMIT 256
    ) AS sample_signal_ids
FROM dynamic_topics dt
WHERE dt.state = 'active'
ORDER BY dt.agg_n_signals DESC NULLS LAST, dt.id
LIMIT $1;
"""

SIGNALS_SQL = """
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


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _contains_keyword(text: str, keyword: str) -> bool:
    if " " in keyword or "_" in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def theme_domains(theme: str | None) -> set[str]:
    """Map a raw GDELT theme code to coarse audit domains."""
    if not theme:
        return set()
    raw = str(theme).strip()
    upper = raw.upper()
    if upper.startswith("TAX_WORLDLANGUAGES_") or upper.startswith("WORLDLANGUAGES_"):
        return set()
    normalized = upper.replace("_", " ").replace("-", " ").lower()
    domains: set[str] = set()

    for prefix, mapped in PREFIX_DOMAINS:
        if upper.startswith(prefix):
            domains.update(mapped)

    for domain, keywords in DOMAIN_KEYWORDS:
        if any(_contains_keyword(normalized, keyword) for keyword in keywords):
            domains.add(domain)

    return domains


def infer_expected_domains(label: str | None) -> set[str]:
    """Infer expected domains from the thread label only.

    This is deliberately hand-written and conservative so GDELT does not grade
    itself. Unknown labels return an empty set and are audited as ambiguous.
    """
    text = (label or "").replace("-", " ").replace("_", " ").lower()
    domains: set[str] = set()
    for domain, keywords in DOMAIN_KEYWORDS:
        if any(_contains_keyword(text, keyword) for keyword in keywords):
            domains.add(domain)
    return domains


def normalized_entropy(counts: dict[str, int]) -> float:
    total = sum(max(0, int(v)) for v in counts.values())
    positive = [int(v) for v in counts.values() if int(v) > 0]
    if total <= 0 or len(positive) <= 1:
        return 0
    entropy = -sum((v / total) * math.log(v / total) for v in positive)
    return round(entropy / math.log(len(positive)), 4)


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        value = getattr(row, key, default)
    return default if value is None else value


def _country_group(country_code: str | None) -> str:
    code = (country_code or "").upper()
    if not code:
        return "unknown"
    return "global_north" if code in GLOBAL_NORTH else "global_south_or_other"


def _empty_slice() -> dict[str, int]:
    return {"rows": 0, "supported": 0, "contradicted": 0, "ambiguous": 0}


def _finalize_slices(slices: dict[str, dict[str, int]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for key, counts in sorted(slices.items()):
        rows = counts["rows"]
        result[key] = {
            **counts,
            "support_rate": _ratio(counts["supported"], rows),
            "contradiction_rate": _ratio(counts["contradicted"], rows),
            "ambiguous_rate": _ratio(counts["ambiguous"], rows),
        }
    return result


def _example(row: Any, domains: set[str], status: str) -> dict[str, Any]:
    return {
        "signal_id": int(_row_value(row, "signal_id", 0)),
        "headline": _row_value(row, "headline", ""),
        "country_code": _row_value(row, "country_code"),
        "source_name": _row_value(row, "source_name"),
        "source_lang": _row_value(row, "source_lang"),
        "source_family": _row_value(row, "source_family"),
        "themes": list(_row_value(row, "themes", []) or [])[:8],
        "domains": sorted(domains),
        "status": status,
    }


def _recommendation(
    *,
    support_pct: float,
    contradiction_pct: float,
    entropy: float,
    expected_domains: set[str],
    rows: int,
) -> str:
    if rows == 0:
        return "keep_current"
    if not expected_domains:
        return "label_review"
    if contradiction_pct >= 0.45:
        return "split_thread" if entropy >= 0.65 else "label_review"
    if support_pct >= 0.65 and entropy <= 0.65:
        return "expand_candidate_pool"
    if entropy >= 0.8:
        return "split_thread"
    return "keep_current"


def build_thread_audit(thread: dict[str, Any], rows: list[Any]) -> dict[str, Any]:
    expected = infer_expected_domains(str(thread.get("label") or ""))
    domain_counts: Counter[str] = Counter()
    theme_counts: Counter[str] = Counter()
    supported = 0
    contradicted = 0
    ambiguous = 0
    examples = {"supported": [], "contradicted": [], "ambiguous": []}
    by_source_lang: dict[str, dict[str, int]] = defaultdict(_empty_slice)
    by_source_family: dict[str, dict[str, int]] = defaultdict(_empty_slice)
    by_country_group: dict[str, dict[str, int]] = defaultdict(_empty_slice)

    for row in rows:
        themes = list(_row_value(row, "themes", []) or [])
        row_domains: set[str] = set()
        for theme in themes:
            theme_counts[str(theme)] += 1
            row_domains.update(theme_domains(str(theme)))
        for domain in row_domains:
            domain_counts[domain] += 1

        if not expected or not row_domains:
            status = "ambiguous"
            ambiguous += 1
        elif expected & row_domains:
            status = "supported"
            supported += 1
        else:
            status = "contradicted"
            contradicted += 1

        for slice_map, key in (
            (by_source_lang, str(_row_value(row, "source_lang", "unknown") or "unknown")),
            (by_source_family, str(_row_value(row, "source_family", "unknown") or "unknown")),
            (by_country_group, _country_group(_row_value(row, "country_code"))),
        ):
            slice_map[key]["rows"] += 1
            slice_map[key][status] += 1

        if len(examples[status]) < 5:
            examples[status].append(_example(row, row_domains, status))

    total = len(rows)
    support_pct = _ratio(supported, total)
    contradiction_pct = _ratio(contradicted, total)
    entropy = normalized_entropy(dict(domain_counts))

    return {
        "thread_id": str(thread.get("thread_id") or f"dynamic-topic-{thread.get('id')}"),
        "label": thread.get("label"),
        "signal_count": int(thread.get("signal_count") or thread.get("agg_n_signals") or 0),
        "country_count": int(thread.get("country_count") or len(thread.get("top_country_codes") or [])),
        "source_count": int(thread.get("source_count") or 0),
        "noise_rate": thread.get("noise_rate"),
        "expected_domains": sorted(expected),
        "top_gdelt_themes": [
            {"theme": theme, "count": count, "domains": sorted(theme_domains(theme))}
            for theme, count in theme_counts.most_common(12)
        ],
        "top_domains": [
            {"domain": domain, "count": count}
            for domain, count in domain_counts.most_common()
        ],
        "metrics": {
            "sample_rows": total,
            "weak_support_pct": support_pct,
            "weak_contradiction_pct": contradiction_pct,
            "ambiguous_pct": _ratio(ambiguous, total),
            "theme_entropy": entropy,
        },
        "bias": {
            "by_source_lang": _finalize_slices(by_source_lang),
            "by_source_family": _finalize_slices(by_source_family),
            "by_country_group": _finalize_slices(by_country_group),
        },
        "examples": examples,
        "recommendation": _recommendation(
            support_pct=support_pct,
            contradiction_pct=contradiction_pct,
            entropy=entropy,
            expected_domains=expected,
            rows=total,
        ),
    }


async def fetch_thread_audits(conn: asyncpg.Connection, *, hours: int, limit: int) -> list[dict[str, Any]]:
    topics = await conn.fetch(DYNAMIC_TOPICS_SQL, limit)
    audits: list[dict[str, Any]] = []
    for topic in topics:
        sample_ids = [int(x) for x in (_row_value(topic, "sample_signal_ids", []) or [])]
        rows = await conn.fetch(SIGNALS_SQL, sample_ids) if sample_ids else []
        thread = {
            "id": int(topic["id"]),
            "thread_id": f"dynamic-topic-{topic['id']}",
            "label": topic["label"],
            "agg_n_signals": int(topic["agg_n_signals"] or 0),
            "country_count": len(topic["top_country_codes"] or []),
            "top_country_codes": list(topic["top_country_codes"] or []),
            "noise_rate": float(topic["noise_rate"]) if topic["noise_rate"] is not None else None,
            "mean_cohesion": float(topic["mean_cohesion"]) if topic["mean_cohesion"] is not None else None,
        }
        audits.append(build_thread_audit(thread, list(rows)))
    return audits


def build_report(*, hours: int, limit: int, audits: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": hours,
        "limit": limit,
        "thread_count": len(audits),
        "audits": audits,
        "interpretation": {
            "weak_support_pct": "share of sampled rows whose GDELT theme domains overlap expected domains inferred from the thread label",
            "weak_contradiction_pct": "share of sampled rows whose GDELT domains do not overlap the expected label domains",
            "theme_entropy": "0 means concentrated domains; 1 means maximally mixed among observed domains",
            "bias": "support/contradiction slices by language, source family, and global-north vs other country grouping",
            "promotion_rule": "GDELT weak support can recommend inspection or candidate expansion; it cannot verify evidence alone",
        },
    }


async def run(*, database_url: str, hours: int, limit: int, output: Path) -> dict[str, Any]:
    conn = await asyncpg.connect(database_url)
    try:
        audits = await fetch_thread_audits(conn, hours=hours, limit=limit)
    finally:
        await conn.close()
    report = build_report(hours=hours, limit=limit, audits=audits)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only GDELT weak-support audit for dynamic topics.")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/research/topic-quality/gdelt-weak-support/2026-06-04-live.json"),
    )
    return parser.parse_args()


async def amain() -> None:
    args = parse_args()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    report = await run(database_url=database_url, hours=args.hours, limit=args.limit, output=args.output)
    print(json.dumps({
        "schema_version": report["schema_version"],
        "thread_count": report["thread_count"],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(amain())
