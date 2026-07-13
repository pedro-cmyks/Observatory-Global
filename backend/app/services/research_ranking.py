"""Investigative ranking + transparency ledger for research plans (Phase 1b).

Scores each Phase 1a anchor with a weighted, normalized ``investigative_score``
(spec: docs/specs/2026-06-09-research-thread-builder-workbench.md, "Ranking by
investigative usefulness"). Pure module: deterministic, no DB, no LLM.

Hard rules from the spec ("No Silent Filtering"):
- Penalties are inspectable risk adjustments, never hidden removal.
- Material matching the investigation is downranked into a visible tray, not
  omitted. Only discovery-level skips (off-topic global threads, unmatched
  attention keywords) count as omitted, and those carry reason codes in the
  ledger via ``skipped_candidates``.

Weights are PROVISIONAL until the #154 source-quality audit seeds calibration.
They live in ``RANKING_WEIGHTS`` (env-overridable via ``RESEARCH_RANKING_WEIGHTS``
JSON) so tuning never requires a code change.
"""
from __future__ import annotations

import json
import os
from typing import Any

from app.core.search_normalization import normalize_search_text

# Deliberately NOT equal-weight. Calibrated 2026-06-10 by
# backend/scripts/calibrate_research_ranking.py against the gold ordering
# constraints (spec acceptance criteria) + live forcing-case constraints:
# 21/21 satisfied vs 20/21 for the hand-tuned baseline. See
# docs/research/ranking-calibration/2026-06-10-ranking-calibration.md.
# Rerun the script when data shifts or user relevance judgments arrive.
RANKING_WEIGHTS: dict[str, float] = {
    "intent_match": 0.2321,
    "thread_coherence": 0.1232,
    "evidence_strength": 0.1462,
    "answerability": 0.1518,
    "movement_signal": 0.07,
    "source_actor_value": 0.068,
    "geo_entity_fit": 0.1051,
    "novelty_or_gap_value": 0.1036,
    # adjustments (subtracted after weighting)
    "noise_risk_adjustment": 0.1152,
    "unsupported_claim_adjustment": 0.1356,
    "list_detail_mismatch_adjustment": 0.1378,
}

# Anchors below this score move to the low-confidence tray (still visible).
DOWNRANK_THRESHOLD = 0.30

# Saturation midpoints for count→[0,1) normalization (midpoint maps to 0.5).
# Calibrated from live thread distributions by
# backend/scripts/calibrate_research_ranking.py — see the report under
# docs/research/ranking-calibration/. Rerun the script after data shifts.
NORMALIZATION_MIDPOINTS: dict[str, float] = {
    "evidence_signals": 10.0,
    "source_count": 4.0,
    "movement_changed_10h": 3.0,
}

_EVIDENCE_LABEL_INTENT = {
    "direct_evidence": 1.0,
    "context": 0.6,
    "weak_support": 0.25,
    "gap": 0.0,
}

_CONFIDENCE_BAND = {"high": 1.0, "medium": 0.6, "low": 0.3, "thin": 0.2}

# Noise lanes (spec: downrank with reason codes, never blind-exclude — sports
# can be politically relevant via boycotts/protests, so it stays inspectable).
_NOISE_LANE_TOKENS = {
    "sports": {"sports", "sport", "football", "soccer", "league", "match",
               "tournament", "olympic", "olympics", "cup"},
    "entertainment": {"celebrity", "gossip", "entertainment", "showbiz",
                      "movie", "music", "lifestyle", "fashion"},
    "roundup": {"roundup", "briefing", "digest", "headlines", "recap"},
}


def _noise_lanes(anchor: dict[str, Any]) -> list[str]:
    tokens = set(str(anchor.get("label") or "").lower().split())
    tokens |= set(str(anchor.get("id") or "").lower().replace("-", " ").split())
    return [lane for lane, terms in _NOISE_LANE_TOKENS.items() if tokens & terms]

APPEAL_ACTION = (
    "Inspect the complete low_confidence_tray; every discovered candidate "
    "remains accessible with its score and reason codes. Refine the query or "
    "time window to change relevance, not to reveal hidden material."
)


def load_weights() -> dict[str, float]:
    raw = os.getenv("RESEARCH_RANKING_WEIGHTS")
    if not raw:
        return dict(RANKING_WEIGHTS)
    try:
        override = json.loads(raw)
        merged = dict(RANKING_WEIGHTS)
        merged.update({k: float(v) for k, v in override.items() if k in merged})
        return merged
    except (ValueError, TypeError):
        return dict(RANKING_WEIGHTS)


def _saturating(value: float, midpoint: float) -> float:
    """Normalize an unbounded count to [0, 1); midpoint maps to 0.5."""
    if value <= 0:
        return 0.0
    return value / (value + midpoint)


def _confidence_value(anchor: dict[str, Any]) -> float:
    confidence = anchor.get("confidence")
    if isinstance(confidence, dict):  # tolerate both shapes across thread paths
        band = str(confidence.get("band") or "")
    else:
        band = str(confidence or "")
    return _CONFIDENCE_BAND.get(band.lower(), 0.5)


def score_anchor(
    anchor: dict[str, Any],
    intent: dict[str, Any],
    *,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Score one anchor. Returns components, reason codes, and final score."""
    w = weights or load_weights()
    anchor_type = anchor.get("anchor_type")
    evidence_label = anchor.get("evidence_label") or "gap"
    quality = anchor.get("quality") or {}
    geo = intent.get("geo_scope") or []

    # ── components, each in [0, 1] ────────────────────────────────────────
    matched = anchor.get("matched_terms") or []
    intent_match = min(
        1.0, _EVIDENCE_LABEL_INTENT.get(evidence_label, 0.0) + 0.05 * len(matched)
    )
    semantic_sim = anchor.get("semantic_similarity")
    if semantic_sim is not None:
        # e5 cosines compress into a high band; rescale to [0, 1] so a strong
        # semantic match competes with a lexical direct match instead of being
        # read off the weak_support floor. The two match bases have different
        # live distributions (see research_semantic threshold notes), so each
        # gets its own scale.
        if anchor.get("match_basis") == "topic_description":
            scaled = (float(semantic_sim) - 0.755) / 0.045
        else:  # member_centroid
            scaled = (float(semantic_sim) - 0.75) / 0.20
        intent_match = max(intent_match, max(0.0, min(1.0, scaled)))

    if anchor_type == "thread":
        thread_coherence = _confidence_value(anchor)
        if quality.get("dominant_source_is_aggregator"):
            thread_coherence = min(thread_coherence, 0.4)
    else:
        thread_coherence = 0.5  # not thread-shaped; neutral

    signal_count = int(anchor.get("signal_count") or 0)
    if anchor_type == "thread":
        evidence_strength = _saturating(
            signal_count, midpoint=NORMALIZATION_MIDPOINTS["evidence_signals"]
        )
    elif anchor_type == "country":
        evidence_strength = 0.5  # opens a full surface, evidence behind it
    elif anchor_type == "public_attention":
        evidence_strength = 0.15  # discussion, never verified evidence
    else:
        evidence_strength = 0.0

    if anchor_type == "thread":
        answerability = 0.3
        if signal_count > 0:
            answerability += 0.3
        if int(anchor.get("source_count") or 0) > 1:
            answerability += 0.2
        if anchor.get("changed_10h"):
            answerability += 0.2
    elif anchor_type == "country":
        answerability = 0.7  # who-covers / from-where / voice mix
    elif anchor_type == "related_branch":
        answerability = 0.4
    else:
        answerability = 0.2

    movement_signal = _saturating(
        abs(int(anchor.get("changed_10h") or 0)),
        midpoint=NORMALIZATION_MIDPOINTS["movement_changed_10h"],
    )

    source_actor_value = _saturating(
        int(anchor.get("source_count") or 0),
        midpoint=NORMALIZATION_MIDPOINTS["source_count"],
    )
    if anchor_type == "country":
        source_actor_value = 0.7

    open_params = (anchor.get("open") or {}).get("params") or {}
    anchor_country = open_params.get("country_code")
    coverage_countries = set(anchor.get("coverage_countries") or [])
    subject_verified = anchor.get("subject_status") == "verified"
    if not geo:
        geo_entity_fit = 0.5
    elif anchor_type == "country" or anchor_type in ("related_branch",):
        geo_entity_fit = 1.0
    elif subject_verified and anchor_country in geo:
        geo_entity_fit = 1.0
    elif coverage_countries.intersection(geo):
        # Coverage country is useful discovery context, but is not proof that
        # the story is about that country (#238).
        geo_entity_fit = 0.55
    else:
        geo_entity_fit = 0.4  # global-lane thread: relevant but unscoped

    if anchor_type == "coverage_gap":
        novelty_or_gap_value = 1.0
    elif anchor_type == "public_attention":
        novelty_or_gap_value = 0.7  # attention/media mismatch direction
    elif anchor_type == "related_branch":
        novelty_or_gap_value = 0.6
    else:
        novelty_or_gap_value = 0.2

    noise_risk = 0.0
    if quality.get("dominant_source_is_aggregator"):
        noise_risk += 0.5
    if quality.get("do_not_promote_roundup") or quality.get("roundup"):
        noise_risk += 0.5
    noise_lanes = _noise_lanes(anchor) if anchor_type == "thread" else []
    if noise_lanes:
        # downrank hard unless the anchor lexically matched the investigation
        noise_risk += 0.5 if evidence_label == "direct_evidence" else 1.0
    noise_risk = min(noise_risk, 1.0)

    unsupported_claim = 0.5 if evidence_label == "weak_support" else 0.0

    raw_total = anchor.get("raw_total")
    mismatch = 0.0
    if raw_total is not None and signal_count and int(raw_total) != signal_count:
        mismatch = min(1.0, abs(int(raw_total) - signal_count) / max(int(raw_total), 1))

    components = {
        "intent_match": round(intent_match, 3),
        "thread_coherence": round(thread_coherence, 3),
        "evidence_strength": round(evidence_strength, 3),
        "answerability": round(answerability, 3),
        "movement_signal": round(movement_signal, 3),
        "source_actor_value": round(source_actor_value, 3),
        "geo_entity_fit": round(geo_entity_fit, 3),
        "novelty_or_gap_value": round(novelty_or_gap_value, 3),
        "noise_risk_adjustment": round(-noise_risk, 3),
        "unsupported_claim_adjustment": round(-unsupported_claim, 3),
        "list_detail_mismatch_adjustment": round(-mismatch, 3),
    }

    score = (
        w["intent_match"] * intent_match
        + w["thread_coherence"] * thread_coherence
        + w["evidence_strength"] * evidence_strength
        + w["answerability"] * answerability
        + w["movement_signal"] * movement_signal
        + w["source_actor_value"] * source_actor_value
        + w["geo_entity_fit"] * geo_entity_fit
        + w["novelty_or_gap_value"] * novelty_or_gap_value
        - w["noise_risk_adjustment"] * noise_risk
        - w["unsupported_claim_adjustment"] * unsupported_claim
        - w["list_detail_mismatch_adjustment"] * mismatch
    )
    score = max(0.0, min(1.0, score))

    # Relevance gate: a big, fast-moving thread that does NOT match the
    # investigation (weak_support) must not bury the actual match. The gate
    # scales the additive score by intent relevance and is exposed in the
    # explanation so the downranking is inspectable, not silent.
    relevance_gate = round(0.5 + 0.5 * intent_match, 3)
    score *= relevance_gate

    reason_codes: list[str] = []
    if evidence_label == "direct_evidence":
        reason_codes.append("direct_intent_match")
    elif evidence_label == "context":
        reason_codes.append("expansion_match")
    elif evidence_label == "weak_support":
        reason_codes.append("weak_intent_match")
    if geo_entity_fit >= 1.0 and geo:
        reason_codes.append("strong_geo_fit")
    elif coverage_countries.intersection(geo) and not subject_verified:
        reason_codes.append("coverage_geo_not_subject")
    if anchor.get("target_geo_relation") == "coverage_only":
        reason_codes.append("coverage_geo_context_only")
    elif anchor.get("target_geo_relation") == "missing":
        reason_codes.append("target_geo_connection_missing")
    if evidence_strength >= 0.5:
        reason_codes.append("strong_evidence")
    elif anchor_type == "thread" and evidence_strength < 0.2:
        reason_codes.append("thin_evidence")
    if movement_signal >= 0.5:
        reason_codes.append("story_moving")
    if noise_risk > 0:
        reason_codes.append("noise_risk")
    for lane in noise_lanes:
        reason_codes.append(f"{lane}_lane")
    if unsupported_claim > 0:
        reason_codes.append("unsupported_claim_risk")
    if mismatch > 0:
        reason_codes.append("list_detail_mismatch")
    if anchor_type == "coverage_gap":
        reason_codes.append("coverage_gap")
    if anchor_type == "public_attention":
        reason_codes.append("public_discussion_lane")
    if semantic_sim is not None:
        reason_codes.append("semantic_match")

    if relevance_gate < 0.7:
        reason_codes.append("low_relevance_gated")
    if evidence_label == "weak_support":
        reason_codes.append("weak_support_not_primary")

    return {
        "anchor_id": anchor.get("id"),
        "investigative_score": round(score, 4),
        "relevance_gate": relevance_gate,
        "score_components": components,
        "reason_codes": reason_codes,
    }


def rank_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Rank a Phase 1a plan in place: sorted primary anchors, low-confidence
    tray, ranking explanations, and the downranking/omission ledger."""
    weights = load_weights()
    intent = plan.get("intent") or {}
    anchors = plan.get("anchors") or []
    skipped = plan.get("skipped_candidates") or []

    explanations: list[dict[str, Any]] = []
    scored: list[tuple[float, dict[str, Any]]] = []
    for anchor in anchors:
        explanation = score_anchor(anchor, intent, weights=weights)
        anchor["investigative_score"] = explanation["investigative_score"]
        explanations.append(explanation)
        scored.append((explanation["investigative_score"], anchor))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    explanation_by_id = {e["anchor_id"]: e for e in explanations}
    noise_codes = {f"{lane}_lane" for lane in _NOISE_LANE_TOKENS}

    primary: list[dict[str, Any]] = []
    tray: list[dict[str, Any]] = []
    primary_thread_labels: set[str] = set()
    for score, anchor in scored:
        codes = set(explanation_by_id.get(anchor.get("id"), {}).get("reason_codes", []))
        in_noise_lane = bool(codes & noise_codes)
        normalized_thread_label = (
            normalize_search_text(str(anchor.get("label") or ""))
            if anchor.get("anchor_type") == "thread"
            else ""
        )
        duplicate_current_label = bool(
            normalized_thread_label
            and normalized_thread_label in primary_thread_labels
        )
        # Gaps are findings, not noise: they stay primary regardless of score.
        # Noise-lane material without a direct intent match goes to the tray
        # even above the score threshold (visible, never deleted).
        if anchor.get("anchor_type") == "coverage_gap":
            anchor["visibility"] = "primary"
            primary.append(anchor)
        elif (
            anchor.get("evidence_label") != "weak_support"
            and score >= DOWNRANK_THRESHOLD
            and not duplicate_current_label
            and not (
                in_noise_lane and "direct_intent_match" not in codes
            )
        ):
            anchor["visibility"] = "primary"
            primary.append(anchor)
            if normalized_thread_label:
                primary_thread_labels.add(normalized_thread_label)
        else:
            if duplicate_current_label:
                explanation = explanation_by_id.get(anchor.get("id"))
                if explanation is not None:
                    explanation["reason_codes"].append("duplicate_current_label")
            anchor["visibility"] = "downranked"
            tray.append(anchor)

    reason_counts: dict[str, int] = {}
    for item in skipped:
        code = item.get("reason_code") or "unspecified"
        reason_counts[code] = reason_counts.get(code, 0) + 1
    for anchor in tray:
        codes = set(explanation_by_id.get(anchor.get("id"), {}).get("reason_codes", []))
        lane_hits = sorted(codes & noise_codes)
        disposition_hits = sorted(codes & {"duplicate_current_label"})
        for key in lane_hits or disposition_hits or ["below_score_threshold"]:
            reason_counts[key] = reason_counts.get(key, 0) + 1

    plan["anchors"] = primary
    plan["low_confidence_tray"] = tray
    plan["ranking_explanations"] = explanations
    plan["ranking_weights"] = weights
    discovery_completion = plan.get("discovery_completion") or {}
    complete = bool(
        discovery_completion.get("thread_universe_complete", True)
    ) and not skipped
    plan["downranking_ledger"] = {
        "candidate_count": len(anchors) + len(skipped),
        "shown_count": len(primary),
        "primary_count": len(primary),
        "downranked_count": len(tray),
        "omitted_count": len(skipped),
        "accessible_count": len(primary) + len(tray) + len(skipped),
        "complete": complete,
        "semantic_ceiling": False,
        "reason_codes": reason_counts,
        "skipped_candidates": skipped,
        "appeal_action": APPEAL_ACTION,
    }
    plan.pop("skipped_candidates", None)

    # pin candidates re-ordered by score, primaries only
    order = {a["id"]: a["investigative_score"] for a in primary}
    plan["pin_candidates"] = [
        pid for pid in sorted(
            (p for p in plan.get("pin_candidates") or [] if p in order),
            key=lambda pid: order[pid],
            reverse=True,
        )
    ]
    return plan
