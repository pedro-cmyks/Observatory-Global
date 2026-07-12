#!/usr/bin/env python3
"""Read-only, math-first subject-geography inference for dynamic topics.

Stage 1 of GitHub #238. Coverage geography and outlet origin are comparison
dimensions only; neither can create a subject-country candidate. No LLM calls,
database writes, lifecycle changes, or serving changes occur here.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
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
