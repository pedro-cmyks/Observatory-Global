#!/usr/bin/env python3
"""Read-only, math-first subject-geography inference for dynamic topics.

Stage 1 of GitHub #238. Coverage geography and outlet origin are comparison
dimensions only; neither can create a subject-country candidate. No LLM calls,
database writes, lifecycle changes, or serving changes occur here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from app.services.ingest_rss import _COUNTRY_PATTERNS, _NATIVE_COUNTRY_PATTERNS


_PROJECT_TO_ISO = {"GZ": "PS", "WE": "PS"}
_COMPONENT_WEIGHTS = {
    "headline_geo_support": 0.35,
    "native_pattern_support": 0.20,
    "ner_gazetteer_support": 0.15,
    "member_consensus": 0.15,
    "embedding_neighborhood_consistency": 0.10,
    "temporal_stability": 0.05,
}

TOPIC_PAGE_SQL = """
SELECT id, label, state, is_junk, last_seen
FROM dynamic_topics
WHERE id > $1 AND state = ANY($2::text[])
ORDER BY id
LIMIT $3
"""

MEMBER_BATCH_SQL = """
/* subject-geo member loader */
WITH selected_topics AS (
    SELECT id, centroid_vec
    FROM dynamic_topics
    WHERE id = ANY($1::bigint[])
), latest AS (
    SELECT dtm.dynamic_topic_id, MAX(dtm.snapshot_at) AS snapshot_at
    FROM dynamic_topic_members dtm
    JOIN selected_topics st ON st.id = dtm.dynamic_topic_id
    GROUP BY dtm.dynamic_topic_id
), member_signals AS (
    SELECT DISTINCT dtm.dynamic_topic_id AS topic_id, sid::bigint AS signal_id
    FROM dynamic_topic_members dtm
    JOIN latest l ON l.dynamic_topic_id = dtm.dynamic_topic_id
                 AND l.snapshot_at = dtm.snapshot_at
    JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
    CROSS JOIN LATERAL unnest(
        COALESCE(ec.sample_signal_ids, ARRAY[]::bigint[])
    ) sid
    UNION
    SELECT DISTINCT st.id, tm.signal_id
    FROM selected_topics st
    JOIN topic_members tm ON tm.topic_id = 'dynamic-topic-' || st.id::text
    WHERE tm.engine_version = 'unified-v2'
      AND tm.role = 'evidence'
      AND tm.member_kind = 'signal'
      AND tm.signal_id IS NOT NULL
)
SELECT
    ms.topic_id,
    s.id AS signal_id,
    s.headline,
    s.source_lang AS language,
    s.country_code AS coverage_country,
    s.source_family,
    s.timestamp AS published_at,
    s.nlp_persons,
    s.nlp_persons_xlm,
    CASE
      WHEN se.vec IS NOT NULL AND cardinality(st.centroid_vec) = 768
      THEN 1 - (se.vec::vector <=> st.centroid_vec::vector)
      ELSE NULL
    END AS embedding_similarity
FROM member_signals ms
JOIN selected_topics st ON st.id = ms.topic_id
JOIN signals_v2 s ON s.id = ms.signal_id
LEFT JOIN signal_embeddings se ON se.signal_id = s.id
WHERE s.timestamp >= now() - make_interval(hours => $2)
ORDER BY ms.topic_id, s.timestamp DESC, s.id
"""

ARCHIVE_PROXY_SQL = """
SELECT id, day, label, samples, top_cc
FROM archive_story_units
ORDER BY id
"""


@dataclass(frozen=True)
class SignalSubjectInput:
    signal_id: int
    headline: str
    language: str | None
    coverage_country: str | None
    source_family: str | None
    published_at: datetime | None
    ner_places: tuple[str, ...] = ()
    embedding_similarity: float | None = None


def _canonical_country(code: str) -> str:
    code = str(code or "").strip().upper()
    return _PROJECT_TO_ISO.get(code, code)


def _record_get(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    try:
        return record[key]
    except (KeyError, TypeError):
        return default


def _parse_ner_places(*values: Any) -> tuple[str, ...]:
    places: list[str] = []
    for value in values:
        if not value:
            continue
        if isinstance(value, str):
            try:
                import json

                value = json.loads(value)
            except (TypeError, ValueError):
                continue
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str):
                places.append(item)
            elif isinstance(item, dict) and str(item.get("type", "")).upper() in {
                "GPE", "LOC", "FAC"
            }:
                text = item.get("text") or item.get("name") or item.get("value")
                if text:
                    places.append(str(text))
    return tuple(dict.fromkeys(places))


def extract_headline_country_evidence(headline: str) -> list[dict[str, object]]:
    """Return every country pattern found in a headline with method provenance."""
    if not headline:
        return []
    methods: dict[str, set[str]] = defaultdict(set)
    for pattern, code in _COUNTRY_PATTERNS:
        if pattern.search(headline):
            methods[_canonical_country(code)].add("headline_pattern")
    for pattern, code in _NATIVE_COUNTRY_PATTERNS:
        if pattern.search(headline):
            methods[_canonical_country(code)].add("native_pattern")
    return [
        {"country": country, "methods": sorted(country_methods)}
        for country, country_methods in sorted(methods.items())
    ]


def _normalized_entropy(distribution: dict[str, float]) -> float:
    values = [p for p in distribution.values() if p > 0]
    if len(values) <= 1:
        return 0.0
    raw = -sum(p * math.log2(p) for p in values)
    return max(0.0, min(1.0, raw / math.log2(len(values))))


def score_subject_candidates(
    signals: Sequence[SignalSubjectInput],
    *,
    disabled_components: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Aggregate explainable subject evidence and abstain when it is ambiguous."""
    signal_count = len(signals)
    support_ids: dict[str, set[int]] = defaultdict(set)
    headline_ids: dict[str, set[int]] = defaultdict(set)
    native_ids: dict[str, set[int]] = defaultdict(set)
    ner_ids: dict[str, set[int]] = defaultdict(set)
    families: dict[str, set[str]] = defaultdict(set)
    days: dict[str, set[str]] = defaultdict(set)
    similarities: dict[str, list[float]] = defaultdict(list)
    provenance: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for signal in signals:
        per_signal: dict[str, set[str]] = defaultdict(set)
        for item in extract_headline_country_evidence(signal.headline):
            country = str(item["country"])
            per_signal[country].update(str(m) for m in item["methods"])
        for place in signal.ner_places:
            for item in extract_headline_country_evidence(place):
                country = str(item["country"])
                per_signal[country].add("ner_gazetteer")

        for country, methods in per_signal.items():
            support_ids[country].add(signal.signal_id)
            if methods & {"headline_pattern", "native_pattern"}:
                headline_ids[country].add(signal.signal_id)
            if "native_pattern" in methods:
                native_ids[country].add(signal.signal_id)
            if "ner_gazetteer" in methods:
                ner_ids[country].add(signal.signal_id)
            if signal.source_family:
                families[country].add(signal.source_family)
            if signal.published_at:
                days[country].add(signal.published_at.date().isoformat())
            if signal.embedding_similarity is not None:
                similarities[country].append(
                    max(0.0, min(1.0, float(signal.embedding_similarity)))
                )
            provenance[country].append({
                "signal_id": signal.signal_id,
                "methods": sorted(methods),
                "language": signal.language,
                "coverage_country": signal.coverage_country,
                "source_family": signal.source_family,
            })

    total_support = sum(len(ids) for ids in support_ids.values())
    distribution = {
        country: round(len(ids) / total_support, 6)
        for country, ids in sorted(support_ids.items())
    } if total_support else {}
    total_days = len({
        s.published_at.date().isoformat() for s in signals if s.published_at
    })
    total_families = len({s.source_family for s in signals if s.source_family})

    candidates: list[dict[str, Any]] = []
    for country, ids in support_ids.items():
        n = max(signal_count, 1)
        components = {
            "headline_geo_support": len(headline_ids[country]) / n,
            "native_pattern_support": len(native_ids[country]) / n,
            "ner_gazetteer_support": len(ner_ids[country]) / n,
            "member_consensus": distribution[country],
            "embedding_neighborhood_consistency": (
                sum(similarities[country]) / len(similarities[country])
                if similarities[country] else 0.0
            ),
            "temporal_stability": (
                len(days[country]) / total_days if total_days else 0.0
            ),
        }
        score = sum(
            value * _COMPONENT_WEIGHTS[name]
            for name, value in components.items()
            if name not in disabled_components
        )
        candidates.append({
            "country": country,
            "score": round(score, 6),
            "components": {k: round(v, 6) for k, v in components.items()},
            "supporting_signal_ids": sorted(ids),
            "supporting_signal_count": len(ids),
            "source_family_breadth": round(
                len(families[country]) / total_families, 6
            ) if total_families else 0.0,
            "provenance": provenance[country],
        })
    candidates.sort(
        key=lambda row: (
            float(row["score"]),
            float(distribution.get(str(row["country"]), 0)),
            int(row["supporting_signal_count"]),
            str(row["country"]),
        ),
        reverse=True,
    )

    shares = sorted(distribution.values(), reverse=True)
    margin = shares[0] - shares[1] if len(shares) > 1 else (shares[0] if shares else 0.0)
    entropy = _normalized_entropy(distribution)
    primary: str | None = None
    reasons: list[str] = []
    if not candidates:
        reasons.append("insufficient_subject_evidence")
    else:
        leader = candidates[0]
        share = distribution[str(leader["country"])]
        if (
            int(leader["supporting_signal_count"]) >= 2
            and float(leader["score"]) >= 0.45
            and share >= 0.60
            and margin >= 0.20
            and entropy <= 0.75
        ):
            primary = str(leader["country"])
            if share >= 0.75:
                reasons.append("headline_geo_consensus")
        else:
            reasons.append("ambiguous_subject_geo")
    if primary is None and candidates and "ambiguous_subject_geo" not in reasons:
        reasons.append("insufficient_subject_evidence")

    return {
        "primary_country": primary,
        "candidate_distribution": distribution,
        "candidates": candidates,
        "entropy": round(entropy, 6),
        "top_two_margin": round(margin, 6),
        "reason_codes": reasons,
        "coverage_countries_observed": sorted({
            _canonical_country(str(s.coverage_country))
            for s in signals if s.coverage_country
        }),
    }


async def load_topic_signals(
    conn: Any,
    topic_ids: Sequence[int],
    *,
    hours: int,
) -> dict[int, list[SignalSubjectInput]]:
    """Load the evidence members for one operational batch, never a universe cap."""
    grouped: dict[int, list[SignalSubjectInput]] = defaultdict(list)
    if not topic_ids:
        return grouped
    records = await conn.fetch(MEMBER_BATCH_SQL, list(topic_ids), hours)
    for record in records:
        topic_id = int(_record_get(record, "topic_id"))
        grouped[topic_id].append(SignalSubjectInput(
            signal_id=int(_record_get(record, "signal_id")),
            headline=str(_record_get(record, "headline") or ""),
            language=_record_get(record, "language"),
            coverage_country=_record_get(record, "coverage_country"),
            source_family=_record_get(record, "source_family"),
            published_at=_record_get(record, "published_at"),
            ner_places=_parse_ner_places(
                _record_get(record, "nlp_persons"),
                _record_get(record, "nlp_persons_xlm"),
            ),
            embedding_similarity=_record_get(record, "embedding_similarity"),
        ))
    return grouped


async def run_complete_universe(
    conn: Any,
    *,
    batch_size: int,
    states: Sequence[str],
    hours: int,
    resume_cursor: int = 0,
    max_retries: int = 2,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Cursor through every selected topic or return an explicitly partial run."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    cursor = int(resume_cursor)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    retries = 0
    batches = 0
    complete = False

    while True:
        attempts = 0
        while True:
            try:
                topic_page = await conn.fetch(
                    TOPIC_PAGE_SQL, cursor, list(states), batch_size
                )
                break
            except Exception as exc:  # preserves a resumable cursor and receipt
                if attempts >= max_retries:
                    failures.append({"cursor": cursor, "reason": str(exc)})
                    topic_page = None
                    break
                attempts += 1
                retries += 1
        if topic_page is None:
            break
        if not topic_page:
            complete = True
            break

        batches += 1
        topic_ids = [int(_record_get(topic, "id")) for topic in topic_page]
        try:
            signals_by_topic = await load_topic_signals(
                conn, topic_ids, hours=hours
            )
        except Exception as exc:
            failures.append({"cursor": cursor, "reason": str(exc)})
            break

        for topic in topic_page:
            topic_id = int(_record_get(topic, "id"))
            signals = signals_by_topic.get(topic_id, [])
            inference = score_subject_candidates(signals)
            structural_evaluation = evaluate_invariants(signals)
            component_ablations = run_ablations([signals])["components"]
            rows.append({
                "dynamic_topic_id": topic_id,
                "label": _record_get(topic, "label"),
                "state": _record_get(topic, "state"),
                "is_junk": bool(_record_get(topic, "is_junk", False)),
                "last_seen": _record_get(topic, "last_seen"),
                "signal_count": len(signals),
                "quality_lane": (
                    "junk" if _record_get(topic, "is_junk", False)
                    else "inferred" if inference["primary_country"]
                    else "abstained"
                ),
                "inference": inference,
                "structural_evaluation": structural_evaluation,
                "component_ablations": component_ablations,
            })
        cursor = max(topic_ids)

    state_counts: dict[str, int] = defaultdict(int)
    lane_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        state_counts[str(row["state"])] += 1
        lane_counts[str(row["quality_lane"])] += 1
    meta = {
        "complete_universe": complete,
        "resume_cursor": int(resume_cursor),
        "last_cursor": cursor,
        "states": list(states),
        "hours": hours,
        "batch_size": batch_size,
        "batches": batches,
        "retries": retries,
        "rows_discovered": len(rows),
        "rows_processed": len(rows),
        "rows_emitted": len(rows),
        "by_lifecycle_state": dict(sorted(state_counts.items())),
        "by_quality_lane": dict(sorted(lane_counts.items())),
        "failures": failures,
    }
    return rows, meta


def _leading_country(subject: dict[str, float]) -> str | None:
    if not subject:
        return None
    return max(subject.items(), key=lambda item: (float(item[1]), item[0]))[0]


def compare_proxies(
    *,
    subject: dict[str, float],
    coverage: Sequence[str],
    archive: Sequence[str],
) -> dict[str, str]:
    """Compare non-gold proxies without recasting disagreement as an error."""
    leader = _leading_country(subject)
    coverage_set = {_canonical_country(code) for code in coverage if code}
    archive_set = {_canonical_country(code) for code in archive if code}

    def relation(values: set[str], *, missing_label: str) -> str:
        if leader is None:
            return "no_subject_candidate"
        if not values:
            return "proxy_unavailable"
        return "agrees_with_candidate" if leader in values else missing_label

    return {
        "coverage_relation": relation(
            coverage_set, missing_label="subject_missing_from_coverage"
        ),
        "archive_relation": relation(
            archive_set, missing_label="proxy_disagreement"
        ),
        "truth_status": "not_gold",
    }


def evaluate_invariants(signals: Sequence[SignalSubjectInput]) -> dict[str, Any]:
    """Evaluate stability transformations that require no semantic judge."""
    baseline = score_subject_candidates(signals)
    baseline_primary = baseline["primary_country"]

    family_rows: list[dict[str, Any]] = []
    families = sorted({signal.source_family for signal in signals if signal.source_family})
    for family in families:
        result = score_subject_candidates([
            signal for signal in signals if signal.source_family != family
        ])
        family_rows.append({
            "removed_source_family": family,
            "primary_country": result["primary_country"],
            "matches_baseline": result["primary_country"] == baseline_primary,
            "abstained": result["primary_country"] is None,
        })

    language_rows: list[dict[str, Any]] = []
    languages = sorted({signal.language for signal in signals if signal.language})
    for language in languages:
        result = score_subject_candidates([
            signal for signal in signals if signal.language == language
        ])
        language_rows.append({
            "language": language,
            "primary_country": result["primary_country"],
            "candidate_distribution": result["candidate_distribution"],
        })
    language_candidates = {
        row["primary_country"] for row in language_rows if row["primary_country"]
    }

    ordered = sorted(
        signals,
        key=lambda signal: (
            signal.published_at.timestamp() if signal.published_at else float("-inf")
        ),
    )
    split = max(1, len(ordered) // 2)
    adjacent_rows = []
    for name, subset in (("early", ordered[:split]), ("late", ordered[split:])):
        result = score_subject_candidates(subset)
        adjacent_rows.append({"window": name, "primary_country": result["primary_country"]})
    adjacent_primaries = {
        row["primary_country"] for row in adjacent_rows if row["primary_country"]
    }

    return {
        "baseline_primary_country": baseline_primary,
        "leave_one_source_family_out": {
            "stable": bool(family_rows) and all(
                row["matches_baseline"] for row in family_rows
            ),
            "runs": family_rows,
        },
        "cross_language_consistency": {
            "stable_among_resolved": len(language_candidates) <= 1,
            "runs": language_rows,
        },
        "adjacent_snapshot_stability": {
            "stable_among_resolved": len(adjacent_primaries) <= 1,
            "runs": adjacent_rows,
        },
    }


def run_ablations(
    topics: Sequence[Sequence[SignalSubjectInput]],
) -> dict[str, Any]:
    """Measure component dependence over all supplied topics."""
    baselines = [score_subject_candidates(signals) for signals in topics]
    baseline_abstentions = sum(
        result["primary_country"] is None for result in baselines
    )
    components: dict[str, dict[str, Any]] = {}
    for component in _COMPONENT_WEIGHTS:
        ablated = [
            score_subject_candidates(
                signals, disabled_components=frozenset({component})
            )
            for signals in topics
        ]
        components[component] = {
            "topics_evaluated": len(topics),
            "primary_changed": sum(
                before["primary_country"] != after["primary_country"]
                for before, after in zip(baselines, ablated, strict=True)
            ),
            "abstentions": sum(
                result["primary_country"] is None for result in ablated
            ),
            "abstention_delta": sum(
                result["primary_country"] is None for result in ablated
            ) - baseline_abstentions,
        }
    return {
        "topics_evaluated": len(topics),
        "baseline_abstentions": baseline_abstentions,
        "components": components,
    }


def evaluate_known_fixtures() -> list[dict[str, Any]]:
    """Small deterministic fixtures test mechanics; they are not corpus gold."""
    fixture_days = [
        datetime(2026, 7, day, tzinfo=timezone.utc) for day in (1, 2, 3)
    ]
    fixtures = [
        ("multilingual_venezuela", "VE", [
            SignalSubjectInput(1, "Venezuela earthquake response", "en", None, "wire", fixture_days[0], embedding_similarity=0.9),
            SignalSubjectInput(2, "Terremoto en Venezuela", "es", None, "press", fixture_days[1], embedding_similarity=0.9),
            SignalSubjectInput(3, "Venezuela recibe ayuda tras el sismo", "es", None, "state", fixture_days[2], embedding_similarity=0.9),
        ]),
        ("ambiguous_iran_israel", None, [
            SignalSubjectInput(4, "Iran and Israel resume talks", "en", None, "wire", None),
            SignalSubjectInput(5, "Israel and Iran trade accusations", "en", None, "press", None),
        ]),
    ]
    rows = []
    for name, expected, signals in fixtures:
        result = score_subject_candidates(signals)
        rows.append({
            "fixture": name,
            "expected_primary_country": expected,
            "observed_primary_country": result["primary_country"],
            "passes": result["primary_country"] == expected,
            "truth_status": "deterministic_fixture",
        })
    return rows


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[^\W\d_]{3,}", (text or "").casefold())
        if token not in {"the", "and", "for", "with", "from", "sobre", "para", "con"}
    }


def match_archive_proxy(
    label: str,
    units: Sequence[Any],
    *,
    threshold: float = 0.45,
) -> dict[str, Any]:
    """Weak lexical archive bridge; embedding spaces are intentionally not mixed."""
    query = _tokens(label)
    matches: list[dict[str, Any]] = []
    for unit in units:
        candidate = _tokens(str(_record_get(unit, "label") or ""))
        union = query | candidate
        similarity = len(query & candidate) / len(union) if union else 0.0
        if similarity >= threshold:
            matches.append({
                "archive_story_unit_id": int(_record_get(unit, "id")),
                "label": _record_get(unit, "label"),
                "day": _record_get(unit, "day"),
                "similarity": round(similarity, 6),
                "top_cc": list(_record_get(unit, "top_cc") or []),
            })
    matches.sort(
        key=lambda row: (float(row["similarity"]), int(row["archive_story_unit_id"])),
        reverse=True,
    )
    selected = matches[:5]
    countries = sorted({
        _canonical_country(code)
        for row in selected for code in row["top_cc"] if code
    })
    return {
        "method": "label_token_jaccard",
        "strength": "weak_proxy",
        "truth_status": "not_gold",
        "threshold": threshold,
        "countries": countries,
        "matches": selected,
    }


def attach_proxy_comparisons(
    rows: Sequence[dict[str, Any]],
    archive_units: Sequence[Any],
) -> None:
    for row in rows:
        archive_proxy = match_archive_proxy(str(row.get("label") or ""), archive_units)
        inference = row["inference"]
        row["archive_proxy"] = archive_proxy
        row["proxy_comparison"] = compare_proxies(
            subject=inference["candidate_distribution"],
            coverage=inference["coverage_countries_observed"],
            archive=archive_proxy["countries"],
        )


def build_ablation_report(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    aggregate = {
        component: {
            "topics_evaluated": 0,
            "primary_changed": 0,
            "abstentions": 0,
            "abstention_delta": 0,
        }
        for component in _COMPONENT_WEIGHTS
    }
    for row in rows:
        for component, metrics in row.get("component_ablations", {}).items():
            for key in aggregate[component]:
                aggregate[component][key] += int(metrics[key])
    return {
        "read_only": True,
        "no_llm_classification": True,
        "topics_evaluated": len(rows),
        "components": aggregate,
    }


def build_report(
    rows: Sequence[dict[str, Any]],
    *,
    completion: dict[str, Any],
) -> dict[str, Any]:
    inferred = sum(row.get("inference", {}).get("primary_country") is not None for row in rows)
    proxy_disagreements = sum(
        "proxy_disagreement" in {
            row.get("proxy_comparison", {}).get("coverage_relation"),
            row.get("proxy_comparison", {}).get("archive_relation"),
        }
        or row.get("proxy_comparison", {}).get("coverage_relation") == "subject_missing_from_coverage"
        for row in rows
    )
    return {
        "generated_at": datetime.now(timezone.utc),
        "stage": "github-238-subject-geography-stage-1",
        "read_only": True,
        "no_llm_classification": True,
        "coverage_is_not_subject": True,
        "complete_universe": bool(completion.get("complete_universe")),
        **completion,
        "summary": {
            "topics": len(rows),
            "inferred": inferred,
            "abstained": len(rows) - inferred,
            "inference_rate": round(inferred / len(rows), 6) if rows else 0.0,
            "proxy_disagreements": proxy_disagreements,
            "known_fixture_passes": sum(
                row["passes"] for row in evaluate_known_fixtures()
            ),
            "known_fixture_total": len(evaluate_known_fixtures()),
        },
        "known_fixtures": evaluate_known_fixtures(),
        "topics": list(rows),
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Subject Geography Complete-Universe Report",
        "",
        f"Generated: `{report.get('generated_at')}`",
        "",
        "This is a read-only, deterministic Stage 1 report. It makes no LLM calls, "
        "does not write lifecycle or serving state, and does not treat coverage geography "
        "or archive matches as ground truth.",
        "",
        "## Completion receipt",
        "",
        f"- Complete universe: `{str(report.get('complete_universe', False)).lower()}`",
        f"- Rows discovered / processed: `{report.get('rows_discovered', 0)}` / `{report.get('rows_processed', 0)}`",
        f"- Cursor batches: `{report.get('batches', 0)}`; last cursor: `{report.get('last_cursor')}`",
        f"- Failures: `{len(report.get('failures', []))}`",
        "",
        "## Summary",
        "",
        f"- Topics: `{summary.get('topics', 0)}`",
        f"- Inferred / abstained: `{summary.get('inferred', 0)}` / `{summary.get('abstained', 0)}`",
        f"- Inference rate: `{summary.get('inference_rate', 0):.1%}`",
        f"- Proxy disagreement rows: `{summary.get('proxy_disagreements', 0)}`",
        f"- Deterministic fixture checks: `{summary.get('known_fixture_passes', 0)}/{summary.get('known_fixture_total', 0)}`",
        "",
        "Proxy disagreement means the deterministic candidate and a non-gold comparison "
        "dimension differ. It is a review signal, not a ground-truth error.",
        "",
        "## Topic ledger",
        "",
        "| ID | State | Topic | Primary | Signals | Lane | Reasons |",
        "|---:|---|---|---|---:|---|---|",
    ]
    for row in report.get("topics", []):
        inference = row.get("inference", {})
        label = str(row.get("label") or "").replace("|", "\\|")
        reasons = ", ".join(inference.get("reason_codes", []))
        lines.append(
            f"| {row.get('dynamic_topic_id')} | {row.get('state')} | {label} | "
            f"{inference.get('primary_country') or 'abstain'} | {row.get('signal_count', 0)} | "
            f"{row.get('quality_lane')} | {reasons} |"
        )
    return "\n".join(lines) + "\n"


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _write_json(path: str, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default) + "\n",
        encoding="utf-8",
    )


def _write_text(path: str, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--states", default="active,candidate")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--hours", type=int, default=336)
    parser.add_argument("--resume-cursor", type=int, default=0)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-ablation", required=True)
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    import asyncpg

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    conn = await asyncpg.connect(database_url, command_timeout=120)
    try:
        await conn.execute("SET default_transaction_read_only = on")
        rows, completion = await run_complete_universe(
            conn,
            batch_size=args.batch_size,
            states=tuple(state.strip() for state in args.states.split(",") if state.strip()),
            hours=args.hours,
            resume_cursor=args.resume_cursor,
            max_retries=args.max_retries,
        )
        archive_units = await conn.fetch(ARCHIVE_PROXY_SQL)
        attach_proxy_comparisons(rows, archive_units)
    finally:
        await conn.close()
    report = build_report(rows, completion=completion)
    _write_json(args.output_json, report)
    _write_text(args.output_md, render_markdown(report))
    _write_json(args.output_ablation, build_ablation_report(rows))
    print(json.dumps({
        "complete_universe": report["complete_universe"],
        "rows_discovered": report["rows_discovered"],
        "rows_processed": report["rows_processed"],
        "last_cursor": report["last_cursor"],
        "failures": report["failures"],
        "summary": report["summary"],
    }, default=_json_default))
    return 0 if report["complete_universe"] else 2


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(_async_main(build_arg_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
