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
