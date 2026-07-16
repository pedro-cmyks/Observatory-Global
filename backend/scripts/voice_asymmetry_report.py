#!/usr/bin/env python3
"""C7 read-only voice-asymmetry pilot over active dynamic topics.

This measures the information sphere Atlas captured. It does not infer real-
world consensus, origin, causality, or subject geography. Until #238 lands,
the subject country is explicitly a cluster-primary COVERAGE proxy.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import voice_mix


UNKNOWN_ORIGINS = {"", "(NULL)", "NULL", "NONE", "XX", "UN", "UND"}
MIN_SIGNALS = 20
MIN_SOURCES = 3
MIN_ATTRIBUTION_SHARE = 0.50
HIT_THRESHOLD = 60.0
MEMBER_CAP_PER_TOPIC = 500


@dataclass(frozen=True)
class TopicVoiceInput:
    topic_id: int
    label: str
    signal_count: int
    distinct_sources: int
    subject_country: str | None
    subject_country_method: str | None
    language_counts: dict[str, int]
    origin_counts: dict[str, int]
    public_count: int = 0


def _normalized_hhi(counts: list[int]) -> float:
    positive = [n for n in counts if n > 0]
    total = sum(positive)
    if not positive or total <= 0:
        return 0.0
    if len(positive) == 1:
        return 1.0
    hhi = sum((n / total) ** 2 for n in positive)
    floor = 1.0 / len(positive)
    return max(0.0, min(1.0, (hhi - floor) / (1.0 - floor)))


def score_topic_voice_asymmetry(topic: TopicVoiceInput) -> dict[str, Any]:
    base: dict[str, Any] = {
        "dynamic_topic_id": topic.topic_id,
        "label": topic.label,
        "subject_country": topic.subject_country,
        "subject_country_method": topic.subject_country_method,
        "signal_count": topic.signal_count,
        "distinct_sources": topic.distinct_sources,
        "public_count": topic.public_count,
    }
    if not topic.subject_country:
        return {
            **base,
            "eligible": False,
            "is_hit": False,
            "voice_asymmetry_score": None,
            "reason_codes": ["insufficient_subject_geo"],
        }

    reasons: list[str] = []
    if topic.signal_count < MIN_SIGNALS:
        reasons.append("insufficient_volume")
    if topic.distinct_sources < MIN_SOURCES:
        reasons.append("insufficient_source_diversity")

    known_langs = {
        (lang or "").lower(): int(n)
        for lang, n in topic.language_counts.items()
        if (lang or "").lower() not in voice_mix.UNKNOWN_LANGS and int(n) > 0
    }
    known_origins = {
        str(origin).strip().upper(): int(n)
        for origin, n in topic.origin_counts.items()
        if origin is not None
        and str(origin).strip().upper() not in UNKNOWN_ORIGINS
        and int(n) > 0
    }
    lang_known = sum(known_langs.values())
    origin_known = sum(known_origins.values())
    attributable = max(lang_known, origin_known)
    attribution_share = attributable / topic.signal_count if topic.signal_count else 0.0
    if attributable < MIN_SIGNALS or attribution_share < MIN_ATTRIBUTION_SHARE:
        reasons.append("insufficient_attribution")
    if attribution_share < 0.65:
        reasons.append("high_unattributed_share")

    if any(r.startswith("insufficient_") for r in reasons):
        return {
            **base,
            "eligible": False,
            "is_hit": False,
            "voice_asymmetry_score": None,
            "attribution_share": round(attribution_share, 4),
            "reason_codes": reasons,
        }

    subject = topic.subject_country.upper()
    dominant_origin = None
    dominant_origin_share = 0.0
    if known_origins:
        dominant_origin, dominant_n = max(
            known_origins.items(), key=lambda item: (item[1], item[0])
        )
        dominant_origin_share = dominant_n / origin_known
    subject_voice_share = known_origins.get(subject, 0) / origin_known if origin_known else 0.0

    primary = voice_mix.primary_langs(subject)
    primary_language_share: float | None = None
    if primary and lang_known:
        primary_language_share = sum(known_langs.get(lang, 0) for lang in primary) / lang_known

    concentration = _normalized_hhi(list(known_origins.values()))
    components: list[tuple[float, float]] = [
        (dominant_origin_share if dominant_origin != subject else 0.0, 0.35),
        (1.0 - subject_voice_share, 0.30),
        (concentration, 0.15),
    ]
    if primary_language_share is not None:
        components.append((1.0 - primary_language_share, 0.20))
    weight = sum(w for _, w in components)
    score = 100.0 * sum(value * w for value, w in components) / weight

    if dominant_origin != subject and dominant_origin_share >= 0.50:
        reasons.append("dominant_outside_origin")
    if subject_voice_share <= 0.05:
        reasons.append("subject_voice_absent")
    if primary_language_share is not None and primary_language_share <= 0.10:
        reasons.append("primary_language_absent")
    if topic.public_count / max(topic.signal_count, 1) < 0.02:
        reasons.append("thin_public_lane")
    if topic.subject_country_method == "cluster_primary_coverage_proxy":
        reasons.append("subject_geo_is_coverage_proxy")

    rounded_score = round(score, 1)
    return {
        **base,
        "eligible": True,
        "is_hit": rounded_score >= HIT_THRESHOLD,
        "voice_asymmetry_score": rounded_score,
        "attribution_share": round(attribution_share, 4),
        "dominant_origin": dominant_origin,
        "dominant_origin_share": round(dominant_origin_share, 4),
        "subject_voice_share": round(subject_voice_share, 4),
        "primary_languages": list(primary),
        "primary_language_share": (
            round(primary_language_share, 4) if primary_language_share is not None else None
        ),
        "outside_voice_concentration": round(concentration, 4),
        "reason_codes": reasons,
    }


def build_report(topics: list[TopicVoiceInput], *, hours: int) -> dict[str, Any]:
    scored = [score_topic_voice_asymmetry(topic) for topic in topics]
    scored.sort(
        key=lambda row: (
            row["voice_asymmetry_score"] is not None,
            row["voice_asymmetry_score"] or -1,
            row["signal_count"],
        ),
        reverse=True,
    )
    return {
        "report_type": "c7-voice-asymmetry-pilot",
        "model_version": "voice-asymmetry-v0",
        "read_only": True,
        "window_hours": hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "subject_country_guardrail": (
            "receipt_subject_inference_verified = subject named in >=2 receipts/"
            ">=2 outlets (serving inference, person-proxy demoted, dominance-"
            "capped); cluster_primary_coverage_proxy = who covered the story, "
            "not verified subject geography — labeled fallback, discounted"
        ),
        "truth_guardrail": (
            "scores describe Atlas corpus coverage and are not real-world truth or consensus"
        ),
        "member_cap_per_topic": MEMBER_CAP_PER_TOPIC,
        "topic_count": len(scored),
        "eligible_count": sum(1 for row in scored if row["eligible"]),
        "hit_count": sum(1 for row in scored if row["is_hit"]),
        "topics": scored,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# C7 Voice-Asymmetry Pilot",
        "",
        f"**Model:** `{report['model_version']}` · **Window:** {report['window_hours']}h",
        "**Mode:** read-only; no lifecycle, ranking, database, cron, or UI writes.",
        (
            f"**Result:** {report['topic_count']} topics inspected; "
            f"{report['eligible_count']} eligible; {report['hit_count']} review hits."
        ),
        "",
        f"> Subject-country guardrail: {report['subject_country_guardrail']}.",
        f"> Truth guardrail: {report['truth_guardrail']}.",
        "> Live conclusion: the coverage proxy produced obvious subject-country mismatches; #238 must land before promotion.",
        "",
        "| topic | proxy | score | dominant origin | subject voice | primary language | reasons |",
        "|---|---|---:|---|---:|---:|---|",
    ]
    for row in report["topics"]:
        score = "—" if row["voice_asymmetry_score"] is None else f"{row['voice_asymmetry_score']:.1f}"
        dominant = row.get("dominant_origin") or "—"
        subject_share = row.get("subject_voice_share")
        lang_share = row.get("primary_language_share")
        lines.append(
            "| {label} | {subject} | {score} | {dominant} | {subject_share} | "
            "{lang_share} | {reasons} |".format(
                label=str(row["label"]).replace("|", "\\|"),
                subject=row.get("subject_country") or "—",
                score=score,
                dominant=dominant,
                subject_share="—" if subject_share is None else f"{subject_share:.0%}",
                lang_share="—" if lang_share is None else f"{lang_share:.0%}",
                reasons=", ".join(row["reason_codes"]) or "none",
            )
        )
    lines.extend([
        "",
        "Interpretation: rank hits for human review only. The coverage proxy and",
        "source/language mix are properties of Atlas's information sphere, not real-world truth.",
    ])
    return "\n".join(lines) + "\n"


MEMBER_SQL = f"""
WITH candidates AS MATERIALIZED (
    SELECT id, label, agg_n_signals
    FROM dynamic_topics
    WHERE state = 'active' AND is_junk IS NOT TRUE
    ORDER BY agg_n_signals DESC, last_seen DESC
    LIMIT $2
),
latest AS (
    SELECT dtm.dynamic_topic_id, MAX(dtm.snapshot_at) AS snap
    FROM dynamic_topic_members dtm
    JOIN candidates c ON c.id = dtm.dynamic_topic_id
    GROUP BY dtm.dynamic_topic_id
),
subject_proxy AS (
    SELECT dtm.dynamic_topic_id,
           (ARRAY_AGG(ec.top_country_codes[1] ORDER BY ec.n_signals DESC NULLS LAST))[1]
             AS subject_country
    FROM dynamic_topic_members dtm
    JOIN latest l ON l.dynamic_topic_id = dtm.dynamic_topic_id AND l.snap = dtm.snapshot_at
    JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
    GROUP BY dtm.dynamic_topic_id
),
member_ids AS (
    SELECT DISTINCT dtm.dynamic_topic_id, sid::bigint AS signal_id
    FROM dynamic_topic_members dtm
    JOIN latest l ON l.dynamic_topic_id = dtm.dynamic_topic_id AND l.snap = dtm.snapshot_at
    JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
    CROSS JOIN LATERAL unnest(COALESCE(ec.sample_signal_ids, ARRAY[]::bigint[])) sid
    UNION
    SELECT DISTINCT c.id, tm.signal_id
    FROM candidates c
    JOIN topic_members tm ON tm.topic_id = 'dynamic-topic-' || c.id::text
    WHERE tm.engine_version = 'unified-v2' AND tm.role = 'evidence'
      AND tm.member_kind = 'signal' AND tm.signal_id IS NOT NULL
),
ranked AS (
    SELECT m.dynamic_topic_id, m.signal_id,
           ROW_NUMBER() OVER (PARTITION BY m.dynamic_topic_id ORDER BY s.timestamp DESC, m.signal_id) rn
    FROM member_ids m
    JOIN signals_v2 s ON s.id = m.signal_id
    WHERE s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
)
SELECT c.id AS topic_id, c.label, sp.subject_country,
       s.id AS signal_id, s.headline, s.source_name, s.source_lang,
       s.source_origin_country
FROM candidates c
LEFT JOIN subject_proxy sp ON sp.dynamic_topic_id = c.id
JOIN ranked r ON r.dynamic_topic_id = c.id AND r.rn <= {MEMBER_CAP_PER_TOPIC}
JOIN signals_v2 s ON s.id = r.signal_id
ORDER BY c.id, s.timestamp DESC
"""


PUBLIC_SQL = """
SELECT split_part(topic_id, '-', 3)::bigint AS topic_id, COUNT(*)::int AS n
FROM topic_members
WHERE topic_id LIKE 'dynamic-topic-%'
  AND role IN ('discussion', 'mood')
  AND assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
GROUP BY 1
"""


def resolve_topic_subject(
    receipts: list[dict[str, Any]],
    proxy_code: str | None,
) -> tuple[str | None, str | None]:
    """C7 geo-source swap (2026-07-16 reconsideration): subject country comes
    from the SERVING receipt-subject inference (person-proxy demotion +
    dominance cap included) when it VERIFIES; the cluster coverage proxy
    survives only as a labeled fallback that the scorer already discounts
    (subject_geo_is_coverage_proxy). 71% of the 07-12 hits carried proxy
    mismatches; the serving inference measured 86.7% precision."""
    if receipts:
        from app.services.subject_geography import infer_receipt_subject_geography
        inference = infer_receipt_subject_geography(receipts)
        verified = list(inference.get("verified_subject_countries") or [])
        if inference.get("status") == "verified" and verified:
            return str(verified[0]).upper(), "receipt_subject_inference_verified"
    if proxy_code:
        return str(proxy_code).upper(), "cluster_primary_coverage_proxy"
    return None, None


async def load_topic_inputs(conn: Any, *, hours: int, limit: int) -> list[TopicVoiceInput]:
    rows = await conn.fetch(MEMBER_SQL, hours, limit, timeout=30)
    public_rows = await conn.fetch(PUBLIC_SQL, hours, timeout=15)
    public_by_topic = {int(row["topic_id"]): int(row["n"]) for row in public_rows}
    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        topic_id = int(row["topic_id"])
        item = grouped.setdefault(topic_id, {
            "label": str(row["label"]),
            "subject_country": row["subject_country"],
            "signal_ids": set(),
            "sources": set(),
            "languages": {},
            "origins": {},
            "receipts": [],
        })
        item["signal_ids"].add(int(row["signal_id"]))
        if row["headline"]:
            item["receipts"].append({
                "headline": str(row["headline"]),
                "source_name": str(row["source_name"] or ""),
            })
        if row["source_name"]:
            item["sources"].add(str(row["source_name"]))
        lang = str(row["source_lang"] or "(null)").strip().lower() or "(null)"
        origin = str(row["source_origin_country"] or "(null)").strip().upper() or "(null)"
        item["languages"][lang] = item["languages"].get(lang, 0) + 1
        item["origins"][origin] = item["origins"].get(origin, 0) + 1
    inputs: list[TopicVoiceInput] = []
    for topic_id, item in grouped.items():
        subject_code, subject_method = resolve_topic_subject(
            item["receipts"],
            str(item["subject_country"]).upper() if item["subject_country"] else None,
        )
        inputs.append(TopicVoiceInput(
            topic_id=topic_id,
            label=item["label"],
            signal_count=len(item["signal_ids"]),
            distinct_sources=len(item["sources"]),
            subject_country=subject_code,
            subject_country_method=subject_method,
            language_counts=item["languages"],
            origin_counts=item["origins"],
            public_count=public_by_topic.get(topic_id, 0),
        ))
    return inputs


async def run(args: argparse.Namespace) -> dict[str, Any]:
    import asyncpg

    database_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL required")
    conn = await asyncpg.connect(database_url)
    try:
        topics = await load_topic_inputs(conn, hours=args.hours, limit=args.limit)
    finally:
        await conn.close()
    return build_report(topics, hours=args.hours)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only C7 voice-asymmetry report")
    parser.add_argument("--hours", type=int, default=168)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = asyncio.run(run(args))
    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_md).write_text(render_markdown(report), encoding="utf-8")
    if not args.output_json and not args.output_md:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
