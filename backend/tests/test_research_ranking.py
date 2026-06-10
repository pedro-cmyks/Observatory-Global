"""Phase 1b — investigative ranking + transparency ledger (#216).

Spec acceptance:
- Output explains why anchors were ranked, downranked, or omitted.
- No material matching the investigation is silently omitted: downranked items
  land in a visible tray, discovery skips land in the ledger with reason codes.
"""
from __future__ import annotations

import asyncio

from app.services.research_anchor_discovery import discover_anchors
from app.services.research_plan import parse_research_intent
from app.services.research_ranking import (
    DOWNRANK_THRESHOLD,
    RANKING_WEIGHTS,
    rank_plan,
    score_anchor,
)


def _thread(thread_id: str, label: str, slugs: list[str], signal_count: int,
            **extra) -> dict:
    return {
        "thread_id": thread_id,
        "label": label,
        "anchor_topics": slugs,
        "signal_count": signal_count,
        "source_count": extra.get("source_count", 4),
        "changed_10h": extra.get("changed_10h", 0),
        "confidence": {"band": extra.get("band", "medium")},
        "quality": extra.get("quality", {}),
    }


IR_THREADS = [
    _thread("water-stress-drought--ir", "Water stress and drought in Iran",
            ["water-stress-drought"], 210, changed_10h=14, band="high"),
    _thread("flood-landslide-disaster--ir", "Flood and landslide disaster in Iran",
            ["flood-landslide-disaster"], 133),
    _thread("fuel-subsidy-unrest--ir", "Fuel subsidy unrest in Iran",
            ["fuel-subsidy-unrest"], 30, band="low"),
    _thread("housing-cost-pressure--ir", "Housing cost pressure in Iran",
            ["housing-cost-pressure"], 12, band="low", source_count=1),
    _thread("sports-roundup--ir", "Sports roundup in Iran",
            ["sports-roundup"], 50),
]

GLOBAL_THREADS = [
    _thread("celebrity-gossip--us", "Celebrity Gossip — United States",
            ["celebrity-gossip"], 999),
]


def _plan(query: str = "Iran climate water drought") -> dict:
    intent = parse_research_intent(query)

    async def fetch_threads_fn(*, hours, limit, country_codes=None):
        return IR_THREADS if country_codes else GLOBAL_THREADS

    return asyncio.run(discover_anchors(
        intent, hours=72, fetch_threads_fn=fetch_threads_fn,
        fetch_attention_fn=None,
    ))


def test_weights_are_not_equal_sum():
    positive = [v for k, v in RANKING_WEIGHTS.items() if "adjustment" not in k]
    assert len(set(positive)) > 1, "spec forbids an equal-weight sum"
    # evidence outweighs the cheap lexical/geo components
    assert RANKING_WEIGHTS["evidence_strength"] > RANKING_WEIGHTS["intent_match"]
    assert RANKING_WEIGHTS["evidence_strength"] > RANKING_WEIGHTS["geo_entity_fit"]


def test_direct_evidence_outranks_weak_support():
    plan = rank_plan(_plan())
    by_id = {a["id"]: a for a in plan["anchors"] + plan["low_confidence_tray"]}
    direct = by_id["water-stress-drought--ir"]
    weak = by_id["housing-cost-pressure--ir"]
    assert direct["investigative_score"] > weak["investigative_score"]
    # primary anchors come back sorted by score
    scores = [a["investigative_score"] for a in plan["anchors"]
              if a["anchor_type"] != "coverage_gap"]
    assert scores == sorted(scores, reverse=True)


def test_every_anchor_has_explanation_and_reason_codes():
    plan = rank_plan(_plan())
    all_anchors = plan["anchors"] + plan["low_confidence_tray"]
    explained = {e["anchor_id"] for e in plan["ranking_explanations"]}
    assert {a["id"] for a in all_anchors} <= explained
    for e in plan["ranking_explanations"]:
        assert e["reason_codes"], f"anchor {e['anchor_id']} has no reason codes"
        assert set(e["score_components"]) == set(RANKING_WEIGHTS)


def test_no_silent_omission_ledger_reconciles():
    plan = rank_plan(_plan())
    ledger = plan["downranking_ledger"]
    assert ledger["candidate_count"] == (
        ledger["shown_count"] + ledger["downranked_count"] + ledger["omitted_count"]
    )
    # off-topic global thread was skipped at discovery WITH a reason code
    skipped_ids = {s["candidate_id"] for s in ledger["skipped_candidates"]}
    assert "celebrity-gossip--us" in skipped_ids
    assert all(s["reason_code"] for s in ledger["skipped_candidates"])
    assert ledger["appeal_action"]


def test_downranked_material_lands_in_visible_tray():
    plan = rank_plan(_plan())
    assert plan["low_confidence_tray"], "fixture must exercise the tray"
    for anchor in plan["low_confidence_tray"]:
        assert anchor["visibility"] == "downranked"
    for anchor in plan["anchors"]:
        assert anchor["visibility"] == "primary"


def test_sports_lane_downranked_with_reason_codes_not_excluded():
    plan = rank_plan(_plan())
    tray_ids = {a["id"] for a in plan["low_confidence_tray"]}
    assert "sports-roundup--ir" in tray_ids, "sports must be downranked, not primary"
    explanation = next(e for e in plan["ranking_explanations"]
                       if e["anchor_id"] == "sports-roundup--ir")
    assert "sports_lane" in explanation["reason_codes"]
    assert "noise_risk" in explanation["reason_codes"]
    # visible in tray + counted in ledger — never silently excluded
    assert plan["downranking_ledger"]["reason_codes"].get("sports_lane", 0) >= 1


def test_coverage_gaps_never_downranked():
    plan = rank_plan(_plan(
        "manipulación de clima Irán y ataques a bases estadounidenses satélite"
    ))
    gap_anchors = [a for a in plan["anchors"] if a["anchor_type"] == "coverage_gap"]
    assert gap_anchors, "gap finding must stay primary regardless of score"
    assert not any(a["anchor_type"] == "coverage_gap"
                   for a in plan["low_confidence_tray"])


def test_weak_support_carries_unsupported_claim_penalty():
    intent = parse_research_intent("Iran climate water drought")
    anchor = {
        "anchor_type": "thread", "id": "x", "evidence_label": "weak_support",
        "matched_terms": [], "signal_count": 20, "source_count": 3,
        "confidence": {"band": "medium"},
        "open": {"surface": "thread_detail", "params": {"country_code": "IR"}},
    }
    explanation = score_anchor(anchor, intent)
    assert explanation["score_components"]["unsupported_claim_adjustment"] < 0
    assert "unsupported_claim_risk" in explanation["reason_codes"]


def test_pin_candidates_filtered_to_primary_and_sorted():
    plan = rank_plan(_plan())
    primary_ids = {a["id"] for a in plan["anchors"]}
    assert all(pid in primary_ids for pid in plan["pin_candidates"])
    scores = [
        next(a["investigative_score"] for a in plan["anchors"] if a["id"] == pid)
        for pid in plan["pin_candidates"]
    ]
    assert scores == sorted(scores, reverse=True)
