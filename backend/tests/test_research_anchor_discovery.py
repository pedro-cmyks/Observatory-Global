"""Phase 1a — multi-lane anchor discovery (automated forcing-case fixtures).

Spec acceptance (docs/specs/2026-06-09-research-thread-builder-workbench.md):
1. Topic research: "Iran climate water drought" returns anchors, at least one
   opening to a non-empty thread detail.
2. Claim verification: "manipulación de clima Irán ..." surfaces country IR,
   climate threads, a public-discussion lane entry, the US-bases/satellite
   branch, and a coverage-gap note where evidence is taxonomy-only.

Fetchers are stubbed: no DB, no network.
"""
from __future__ import annotations

import asyncio

from app.services.research_anchor_discovery import discover_anchors
from app.services.research_plan import parse_research_intent


def _thread(thread_id: str, label: str, slugs: list[str], signal_count: int) -> dict:
    return {
        "thread_id": thread_id,
        "label": label,
        "anchor_topics": slugs,
        "signal_count": signal_count,
        "confidence": {"band": "medium"},
    }


IR_THREADS = [
    _thread("flood-landslide-disaster--ir", "Flood & Landslide Disaster — Iran",
            ["flood-landslide-disaster"], 133),
    _thread("armed-conflict-escalation--ir", "Armed Conflict Escalation — Iran",
            ["armed-conflict-escalation"], 88),
    _thread("economy-sanctions--ir", "Economy & Sanctions — Iran",
            ["economy-sanctions"], 45),
]

GLOBAL_THREADS = [
    _thread("drought-water-stress--ir-iq", "Drought & Water Stress — Iran, Iraq",
            ["drought-water-stress"], 210),
    _thread("celebrity-gossip--us", "Celebrity Gossip — United States",
            ["celebrity-gossip"], 999),
]


def _fetchers(attention_items: list[dict] | None = None):
    async def fetch_threads_fn(*, hours: int, limit: int, country_codes=None):
        return IR_THREADS if country_codes else GLOBAL_THREADS

    async def fetch_attention_fn(*, country_code: str, hours: int):
        return attention_items or []

    return fetch_threads_fn, fetch_attention_fn


def test_topic_research_iran_returns_openable_anchors():
    intent = parse_research_intent("Iran climate water drought")
    fetch_threads_fn, fetch_attention_fn = _fetchers()

    plan = asyncio.run(discover_anchors(
        intent, hours=72,
        fetch_threads_fn=fetch_threads_fn,
        fetch_attention_fn=fetch_attention_fn,
    ))

    anchors = plan["anchors"]
    assert len(anchors) >= 4  # country + threads + (weak/gap)

    # at least one direct-evidence thread anchor opens to a non-empty detail
    direct = [a for a in anchors
              if a["anchor_type"] == "thread" and a["evidence_label"] == "direct_evidence"]
    assert direct, "expected direct-evidence thread anchors"
    assert any(a["signal_count"] > 0 for a in direct)
    assert all(a["open"]["surface"] == "thread_detail" for a in direct)
    # drought thread matches the query lexically
    assert any("drought" in a["matched_terms"] for a in direct)

    # flood thread is reachable via the climate expansion dictionary
    flood = [a for a in anchors if a["id"] == "flood-landslide-disaster--ir"]
    assert flood and flood[0]["evidence_label"] in ("direct_evidence", "context")

    # country anchor for IR present and openable
    country = [a for a in anchors if a["anchor_type"] == "country"]
    assert country and country[0]["open"]["params"]["country_code"] == "IR"

    # off-topic global thread must NOT appear as an anchor
    assert not any(a.get("id") == "celebrity-gossip--us" for a in anchors)

    # every anchor carries an evidence label from the fixed vocabulary
    assert all(a["evidence_label"] in
               ("direct_evidence", "context", "weak_support", "gap") for a in anchors)

    assert plan["pin_candidates"]
    assert plan["suggested_next_steps"]


def test_claim_verification_compound_surfaces_branch_and_gap():
    intent = parse_research_intent(
        "manipulación de clima Irán y ataques a bases estadounidenses satélite"
    )
    fetch_threads_fn, fetch_attention_fn = _fetchers(
        attention_items=[{"keyword": "robo de lluvia iran", "rank": 3},
                         {"keyword": "futbol resultados", "rank": 1}],
    )

    plan = asyncio.run(discover_anchors(
        intent, hours=72,
        fetch_threads_fn=fetch_threads_fn,
        fetch_attention_fn=fetch_attention_fn,
    ))
    anchors = plan["anchors"]

    # country IR anchor
    assert any(a["anchor_type"] == "country" and
               a["open"]["params"]["country_code"] == "IR" for a in anchors)

    # climate/conflict threads surfaced
    assert any(a["anchor_type"] == "thread" for a in anchors)

    # public-discussion lane entry matched on expansion/query terms only
    attention = [a for a in anchors if a["anchor_type"] == "public_attention"]
    assert attention and attention[0]["evidence_label"] == "weak_support"
    assert not any("futbol" in (a["label"] or "") for a in attention)

    # US-bases/satellite branch suggested
    assert any(a["anchor_type"] == "related_branch" and
               "us bases" in a["label"] for a in anchors)

    # coverage gap: no thread covers conflict_infrastructure lexically in fixture
    gap_axes = {g.get("axis") for g in plan["coverage_gaps"]}
    assert "conflict_infrastructure" in gap_axes
    assert any(a["evidence_label"] == "gap" for a in anchors)
    # gap is explained, not hidden
    assert any("taxonomy-only" in (g["note"]) for g in plan["coverage_gaps"]
               if g.get("axis") == "conflict_infrastructure")


def test_degraded_thread_lane_yields_gap_not_error():
    intent = parse_research_intent("Iran drought")

    async def broken_threads(**kwargs):
        raise RuntimeError("db down")

    plan = asyncio.run(discover_anchors(
        intent, hours=24, fetch_threads_fn=broken_threads, fetch_attention_fn=None,
    ))

    assert any(g["gap_type"] == "lane_degraded" for g in plan["coverage_gaps"])
    # country anchor still present; no exception propagated
    assert any(a["anchor_type"] == "country" for a in plan["anchors"])


def test_unmatched_query_returns_safe_empty_plan():
    intent = parse_research_intent("local football transfer rumours")

    async def no_threads(**kwargs):
        return GLOBAL_THREADS

    plan = asyncio.run(discover_anchors(
        intent, hours=24, fetch_threads_fn=no_threads, fetch_attention_fn=None,
    ))

    # no geo, no axes -> no fabricated anchors beyond gaps
    assert not any(a["anchor_type"] in ("country", "related_branch")
                   for a in plan["anchors"])
    assert plan["pin_candidates"] == []


# ── W2 (research-plan-v1, L3 review 2026-07-05) ──────────────────────────────

def test_contract_is_v1():
    from app.services.research_anchor_discovery import CONTRACT
    assert CONTRACT == "research-plan-v1"


def test_substrate_guard_suppresses_centroid_basis_with_visible_gap():
    """W2a: a collapsed centroid pool (< threshold) must suppress the
    member-centroid basis and say so — never serve pool-noise matches."""
    intent = parse_research_intent("water crisis Iran")

    async def no_threads(**kwargs):
        return []

    async def tiny_pool():
        # 2 active centroids — the post-collapse regime
        return [
            {"topic_id": 1, "label": "Water Stress", "n_signals": 10,
             "centroid_vec": [1.0] + [0.0] * 767},
            {"topic_id": 2, "label": "Sports", "n_signals": 5,
             "centroid_vec": [0.0, 1.0] + [0.0] * 766},
        ]

    plan = asyncio.run(discover_anchors(
        intent, hours=72,
        fetch_threads_fn=no_threads, fetch_attention_fn=None,
        embed_query_fn=lambda _t: [1.0] + [0.0] * 767,
        fetch_centroids_fn=tiny_pool,
        substrate_min_centroids=80,
    ))

    assert not any(a.get("match_basis") == "member_centroid" for a in plan["anchors"])
    gap = [g for g in plan["coverage_gaps"]
           if g["gap_type"] == "lane_degraded" and g["lane"] == "semantic"]
    assert gap and "2 active" in gap[0]["note"]


def test_substrate_guard_off_by_default_for_injected_fixtures():
    """Tests and fixtures inject small pools deliberately — default 0 = off."""
    intent = parse_research_intent("water crisis Iran")

    async def no_threads(**kwargs):
        return []

    async def tiny_pool():
        return [{"topic_id": 1, "label": "Water Stress", "n_signals": 10,
                 "centroid_vec": [1.0] + [0.0] * 767}]

    plan = asyncio.run(discover_anchors(
        intent, hours=72,
        fetch_threads_fn=no_threads, fetch_attention_fn=None,
        embed_query_fn=lambda _t: [1.0] + [0.0] * 767,
        fetch_centroids_fn=tiny_pool,
    ))
    assert any(a.get("match_basis") == "member_centroid" for a in plan["anchors"])


def test_movement_enrichment_kalman_with_changed10h_fallback():
    """W2c: thread anchors carry the shared Kalman field when available;
    changed_10h fallback names its source. Ranking lineage unchanged."""
    intent = parse_research_intent("election dispute Colombia")

    async def threads(**kwargs):
        return [
            {"thread_id": "dynamic-topic-9", "label": "Election Dispute",
             "signal_count": 40, "source_count": 5, "changed_10h": 7,
             "category": "election-legitimacy", "crisis_relevant": True},
            {"thread_id": "dynamic-topic-10", "label": "Election Audits",
             "signal_count": 12, "source_count": 3, "changed_10h": 2,
             "category": "election-legitimacy", "crisis_relevant": True},
        ]

    async def movement(topic_ids):
        assert "dynamic-topic-9" in topic_ids
        return {"dynamic-topic-9": {"velocity": 1.25, "surprise": 0.4, "trend": "surging"}}

    plan = asyncio.run(discover_anchors(
        intent, hours=72,
        fetch_threads_fn=threads, fetch_attention_fn=None,
        fetch_movement_fn=movement,
    ))
    by_id = {a["id"]: a for a in plan["anchors"] if a["anchor_type"] == "thread"}
    assert by_id["dynamic-topic-9"]["movement"]["source"] == "kalman-topic-movement"
    assert by_id["dynamic-topic-9"]["movement"]["trend"] == "surging"
    assert by_id["dynamic-topic-10"]["movement"] == {"changed_10h": 2, "source": "changed_10h"}


def test_category_lens_passthrough_and_summary():
    """W2d: thread anchors carry the R3 category; the plan summarizes it."""
    intent = parse_research_intent("election dispute Colombia")

    async def threads(**kwargs):
        return [
            {"thread_id": "dynamic-topic-9", "label": "Election Dispute",
             "signal_count": 40, "source_count": 5, "changed_10h": 7,
             "category": "election-legitimacy", "crisis_relevant": True},
        ]

    plan = asyncio.run(discover_anchors(
        intent, hours=72, fetch_threads_fn=threads, fetch_attention_fn=None,
    ))
    anchor = next(a for a in plan["anchors"] if a["anchor_type"] == "thread")
    assert anchor["category"] == "election-legitimacy"
    assert anchor["crisis_relevant"] is True
    assert plan["category_summary"] == {"election-legitimacy": 1}
