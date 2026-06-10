"""Calibration harness for research ranking weights + normalizers (#154 follow-on).

Why this exists instead of "seed weights from the source-quality audit":
a source audit measures source properties (dominance, syndication, NLP
coverage) — that informs at most ``source_actor_value`` and ``noise_risk``.
It cannot tell you how to trade ``intent_match`` against ``evidence_strength``.
There is no ground-truth mapping from source quality to component weights.

What CAN be grounded:

1. **Normalization midpoints** — the saturation midpoints for signal counts,
   source counts, and movement are empirical claims about live thread
   distributions. We calibrate them from real percentiles (median of the live
   population maps to 0.5).
2. **Weights** — without user relevance judgments, the honest proxy is the
   spec's own acceptance criteria expressed as pairwise ordering constraints
   ("a direct match must outrank an unmatched giant", "coherent beats
   roundup", ...). We search the weight simplex for vectors that satisfy all
   constraints with maximum margin. Deterministic (seeded), reproducible, and
   re-runnable when real preference data (or #154 audit data) arrives.

Pure module: no DB, no network. The runner script feeds it live thread rows
and live forcing-case anchors.
"""
from __future__ import annotations

import random
import statistics
from typing import Any

from app.services.research_ranking import RANKING_WEIGHTS, score_anchor

POSITIVE_COMPONENTS = [
    "intent_match", "thread_coherence", "evidence_strength", "answerability",
    "movement_signal", "source_actor_value", "geo_entity_fit",
    "novelty_or_gap_value",
]
PENALTY_COMPONENTS = [
    "noise_risk_adjustment", "unsupported_claim_adjustment",
    "list_detail_mismatch_adjustment",
]

# Spec guardrail: cheap-to-score components must not dominate the
# expensive-but-important ones. Candidate weight vectors violating these are
# rejected before constraint evaluation.
WEIGHT_GUARDRAILS = [
    ("evidence_strength", "geo_entity_fit"),
    ("evidence_strength", "movement_signal"),
    ("answerability", "geo_entity_fit"),
]


def _score(anchor: dict[str, Any], intent: dict[str, Any],
           weights: dict[str, float]) -> float:
    return score_anchor(anchor, intent, weights=weights)["investigative_score"]


def evaluate_constraints(
    weights: dict[str, float],
    constraints: list[dict[str, Any]],
) -> dict[str, Any]:
    """A constraint is {id, intent, winner, loser, description}. Satisfied when
    score(winner) > score(loser). Returns satisfaction count, violations, and
    the minimum margin across satisfied constraints (tiebreaker for search)."""
    violations: list[str] = []
    margins: list[float] = []
    for c in constraints:
        margin = (
            _score(c["winner"], c["intent"], weights)
            - _score(c["loser"], c["intent"], weights)
        )
        if margin <= 0:
            violations.append(c["id"])
        else:
            margins.append(margin)
    return {
        "satisfied": len(constraints) - len(violations),
        "total": len(constraints),
        "violations": violations,
        "min_margin": round(min(margins), 4) if margins else 0.0,
    }


def _respects_guardrails(weights: dict[str, float]) -> bool:
    return all(weights[hi] >= weights[lo] for hi, lo in WEIGHT_GUARDRAILS)


def sample_weight_vector(
    rng: random.Random,
    *,
    baseline: dict[str, float] | None = None,
) -> dict[str, float]:
    """One candidate. With ``baseline``: trust-region sample (multiplicative
    jitter 0.5–2.0x around baseline, renormalized) so few constraints cannot
    drag any component to a degenerate near-zero weight. Without: free
    Dirichlet exploration. Penalties sampled in [0.05, 0.15]."""
    if baseline is not None:
        raws = [
            baseline[name] * rng.uniform(0.5, 2.0) for name in POSITIVE_COMPONENTS
        ]
    else:
        raws = [rng.gammavariate(2.0, 1.0) for _ in POSITIVE_COMPONENTS]
    total = sum(raws)
    weights = {
        name: round(raw / total, 4)
        for name, raw in zip(POSITIVE_COMPONENTS, raws)
    }
    for name in PENALTY_COMPONENTS:
        weights[name] = round(rng.uniform(0.05, 0.15), 4)
    return weights


def _distance(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(abs(a[k] - b[k]) for k in POSITIVE_COMPONENTS)


def search_weights(
    constraints: list[dict[str, Any]],
    *,
    n_samples: int = 3000,
    seed: int = 42,
) -> dict[str, Any]:
    """Seeded random search over the weight simplex: half trust-region samples
    around the production baseline, half free exploration. Selection key:
    most constraints satisfied, then larger min margin (rounded — margin is a
    tiebreaker, not an objective), then closeness to baseline so we never
    drift to degenerate weights without a constraint forcing it."""
    rng = random.Random(seed)
    baseline = dict(RANKING_WEIGHTS)

    def _key(weights: dict[str, float], result: dict[str, Any]) -> tuple:
        return (
            result["satisfied"],
            round(result["min_margin"], 2),
            -_distance(weights, baseline),
        )

    best_weights = baseline
    best_eval = evaluate_constraints(baseline, constraints)
    baseline_eval = dict(best_eval)
    best_key = _key(baseline, best_eval)

    for i in range(n_samples):
        candidate = sample_weight_vector(
            rng, baseline=baseline if i % 2 == 0 else None
        )
        if not _respects_guardrails(candidate):
            continue
        result = evaluate_constraints(candidate, constraints)
        key = _key(candidate, result)
        if key > best_key:
            best_weights, best_eval, best_key = candidate, result, key

    return {
        "weights": best_weights,
        "evaluation": best_eval,
        "baseline_evaluation": baseline_eval,
        "improved_over_baseline": best_weights is not baseline,
        "n_samples": n_samples,
        "seed": seed,
    }


def recommend_midpoints(thread_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Empirical normalizer calibration: the live median maps to 0.5 on each
    saturating scale. Falls back to current values on thin samples."""
    def _median(key: str, floor: float) -> float:
        values = [
            abs(int(row.get(key) or 0))
            for row in thread_rows
            if row.get(key) is not None
        ]
        values = [v for v in values if v > 0]
        if len(values) < 5:
            return floor
        return max(floor, float(statistics.median(values)))

    return {
        "evidence_signals": _median("signal_count", 10.0),
        "source_count": _median("source_count", 3.0),
        "movement_changed_10h": _median("changed_10h", 3.0),
        "sample_size": len(thread_rows),
    }


# ── Gold ordering constraints (spec-derived, synthetic anchors) ──────────────

def _anchor(evidence_label: str, *, signal_count: int = 30, source_count: int = 4,
            changed_10h: int = 0, band: str = "medium", country: str = "IR",
            matched: int = 1, quality: dict | None = None,
            label: str = "Synthetic thread", raw_total: int | None = None,
            anchor_type: str = "thread", anchor_id: str = "synthetic") -> dict:
    return {
        "anchor_type": anchor_type,
        "id": anchor_id,
        "label": label,
        "evidence_label": evidence_label,
        "matched_terms": ["term"] * matched if evidence_label != "weak_support" else [],
        "signal_count": signal_count,
        "source_count": source_count,
        "changed_10h": changed_10h,
        "confidence": {"band": band},
        "quality": quality or {},
        "raw_total": raw_total,
        "open": {"surface": "thread_detail", "params": {"country_code": country}},
    }


_GOLD_INTENT = {"geo_scope": ["IR"], "topic_axes": ["climate", "water"]}


def build_gold_constraints() -> list[dict[str, Any]]:
    return [
        {
            "id": "direct_small_beats_unmatched_giant",
            "description": "A small direct match must outrank a huge thread "
                           "that does not match the investigation.",
            "intent": _GOLD_INTENT,
            "winner": _anchor("direct_evidence", signal_count=8, source_count=2,
                              band="thin", matched=2),
            "loser": _anchor("weak_support", signal_count=400, source_count=40,
                             changed_10h=30, band="high"),
        },
        {
            "id": "context_match_beats_unmatched_giant",
            "description": "An expansion-term match must outrank an unmatched "
                           "giant.",
            "intent": _GOLD_INTENT,
            "winner": _anchor("context", signal_count=120, source_count=15,
                              changed_10h=10, matched=1),
            "loser": _anchor("weak_support", signal_count=400, source_count=40,
                             changed_10h=30, band="high"),
        },
        {
            "id": "direct_beats_weak_same_size",
            "description": "Same-size threads: direct match wins.",
            "intent": _GOLD_INTENT,
            "winner": _anchor("direct_evidence", matched=2),
            "loser": _anchor("weak_support"),
        },
        {
            "id": "coherent_beats_incoherent",
            "description": "Same match, same size: high-confidence coherent "
                           "thread beats low-confidence one.",
            "intent": _GOLD_INTENT,
            "winner": _anchor("context", band="high"),
            "loser": _anchor("context", band="low"),
        },
        {
            "id": "moving_beats_stale",
            "description": "Same match, same size: a moving story beats a "
                           "stale one.",
            "intent": _GOLD_INTENT,
            "winner": _anchor("direct_evidence", changed_10h=15, matched=2),
            "loser": _anchor("direct_evidence", changed_10h=0, matched=2),
        },
        {
            "id": "clean_counts_beat_mismatch",
            "description": "List/detail mismatch is penalized against an "
                           "otherwise identical thread.",
            "intent": _GOLD_INTENT,
            "winner": _anchor("context"),
            "loser": _anchor("context", raw_total=120, signal_count=30),
        },
        {
            "id": "evidence_match_beats_sports_giant",
            "description": "Sports-lane material never outranks a real match, "
                           "however big.",
            "intent": _GOLD_INTENT,
            "winner": _anchor("context", signal_count=20, source_count=3),
            "loser": _anchor("weak_support", signal_count=500, source_count=50,
                             changed_10h=40, band="high",
                             label="Sports roundup weekly football recap"),
        },
        {
            "id": "direct_thread_beats_country_framing",
            "description": "A solid direct-evidence thread outranks the "
                           "country framing anchor.",
            "intent": _GOLD_INTENT,
            "winner": _anchor("direct_evidence", signal_count=60,
                              source_count=8, changed_10h=6, matched=2),
            "loser": _anchor("context", anchor_type="country",
                             anchor_id="country-ir", label="Iran",
                             signal_count=0, source_count=0),
        },
        {
            "id": "country_framing_beats_tiny_weak",
            "description": "The country surface outranks an unmatched thin "
                           "thread.",
            "intent": _GOLD_INTENT,
            "winner": _anchor("context", anchor_type="country",
                              anchor_id="country-ir", label="Iran",
                              signal_count=0, source_count=0),
            "loser": _anchor("weak_support", signal_count=6, source_count=1,
                             band="thin"),
        },
    ]
