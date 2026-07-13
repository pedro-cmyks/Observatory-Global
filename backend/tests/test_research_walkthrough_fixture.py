"""Walkthrough E2E fixture — the #213 exit criterion (spec amendment D4/S2).

Reproduces the spec's 8-step walkthrough for BOTH forcing cases at the
service layer: parse → discover (all lanes) → rank → open contract →
pin candidates → branch → coverage gaps. Stubbed fetchers carry realistic
live-shaped data (mirroring the 2026-06-10 production responses), so the
fixture asserts the full route a user takes, not one layer.

The browser-level click-through lives in the frontend walkthrough test
(frontend-v2/src/lib/walkthrough.test.ts) over the same plan shape, and the
live route is covered by scripts/research_walkthrough_smoke.py.
"""
from __future__ import annotations

import asyncio

from app.services.research_anchor_discovery import discover_anchors
from app.services.research_plan import parse_research_intent
from app.services.research_ranking import rank_plan


def _thread(thread_id, label, slugs, signal_count, **extra):
    return {
        "thread_id": thread_id,
        "label": label,
        "anchor_topics": slugs,
        "signal_count": signal_count,
        "source_count": extra.get("source_count", 6),
        "changed_10h": extra.get("changed_10h", 4),
        "confidence": {"band": extra.get("band", "medium")},
        "quality": {},
    }


IR_THREADS = [
    _thread("water-stress-drought--ir", "Water stress and drought in Iran",
            ["water-stress-drought"], 41, band="high", changed_10h=9),
    _thread("flood-landslide-disaster--ir", "Flood and landslide disaster in Iran",
            ["flood-landslide-disaster"], 133),
    _thread("armed-conflict-escalation--ir", "Armed conflict escalation in Iran",
            ["armed-conflict-escalation"], 88, changed_10h=22),
]

ATTENTION = [{"keyword": "robo de lluvia iran", "rank": 2},
             {"keyword": "partido futbol hoy", "rank": 1}]


def _walkthrough(query: str) -> dict:
    intent = parse_research_intent(query)

    async def fetch_threads_fn(*, hours, limit, country_codes=None):
        return IR_THREADS if country_codes else []

    async def fetch_attention_fn(*, country_code, hours):
        return ATTENTION

    plan = asyncio.run(discover_anchors(
        intent, hours=168,
        fetch_threads_fn=fetch_threads_fn,
        fetch_attention_fn=fetch_attention_fn,
    ))
    return rank_plan(plan)


def _assert_openable(anchor: dict) -> None:
    """Every non-gap anchor must resolve to a real Atlas surface."""
    surface = (anchor.get("open") or {}).get("surface")
    params = (anchor.get("open") or {}).get("params") or {}
    assert surface in ("thread_detail", "country_brief", "public_attention", "research_plan")
    if surface == "thread_detail":
        assert params.get("thread_id")
    elif surface == "country_brief":
        assert len(str(params.get("country_code"))) == 2
    elif surface == "research_plan":
        assert params.get("query")


def test_walkthrough_topic_research_iran():
    """Forcing case 1: steps 1-4 — search, anchors, open, pin candidates."""
    plan = _walkthrough("Iran climate water drought")
    anchors = plan["anchors"]

    # Step 1-2: search produced an interpreted intent + openable anchor menu
    assert plan["intent"]["geo_scope"] == ["IR"]
    assert {"climate", "water"} <= set(plan["intent"]["topic_axes"])
    assert len(anchors) >= 3
    for anchor in anchors:
        if anchor["anchor_type"] != "coverage_gap":
            _assert_openable(anchor)

    # Step 3: at least one direct-evidence thread opens to non-empty detail
    direct = [a for a in anchors if a["evidence_label"] == "direct_evidence"]
    assert direct and all(a["signal_count"] > 0 for a in direct)

    # Step 4: pin candidates point at primary anchors, best first
    assert plan["pin_candidates"]
    primary_ids = {a["id"] for a in anchors}
    assert set(plan["pin_candidates"]) <= primary_ids

    # Transparency: ledger reconciles, nothing silently dropped
    ledger = plan["downranking_ledger"]
    assert ledger["candidate_count"] == (
        ledger["shown_count"] + ledger["downranked_count"] + ledger["omitted_count"]
    )


def test_walkthrough_claim_verification_compound():
    """Forcing case 2: steps 5-8 — branch, who-says-what entry points, gaps."""
    plan = _walkthrough(
        "manipulación de clima Irán y ataques a bases estadounidenses satélite"
    )
    anchors = plan["anchors"]

    # Step 5: the compound query suggests the bases/satellite branch, openable
    branches = [a for a in anchors if a["anchor_type"] == "related_branch"]
    assert branches and branches[0]["open"]["surface"] == "research_plan"

    # Public-discussion lane: the viral claim is visible as attention,
    # labeled weak_support (never verified evidence). Unmatched discussion is
    # retained in the low-confidence tray rather than erased.
    attention = [a for a in anchors + plan["low_confidence_tray"]
                 if a["anchor_type"] == "public_attention"]
    assert attention and all(a["evidence_label"] == "weak_support" for a in attention)
    futbol = next(a for a in attention if "futbol" in a["label"])
    assert futbol["visibility"] == "downranked"

    # Step 8: the unsupported axis is a visible gap with honest language,
    # and gaps stay primary regardless of score
    gaps = [a for a in anchors if a["evidence_label"] == "gap"]
    assert any("conflict_infrastructure" in (g.get("id") or "") for g in gaps)
    assert any("taxonomy-only" in g["note"] for g in plan["coverage_gaps"]
               if g.get("axis") == "conflict_infrastructure")

    # Next steps tell the user to treat the claim as unverified
    assert any("unverified" in s for s in plan["suggested_next_steps"])


def test_walkthrough_branch_round_trip():
    """Step 5-6: opening the suggested branch produces its own useful plan."""
    first = _walkthrough("manipulación de clima Irán ataques a bases satélite")
    branch = next(a for a in first["anchors"] if a["anchor_type"] == "related_branch")
    branch_query = str(branch["open"]["params"]["query"])

    second = _walkthrough(branch_query)
    # the branch plan has conflict_infrastructure focus and its own anchors
    assert "conflict_infrastructure" in second["intent"]["topic_axes"]
    assert second["anchors"], "branch plan must not be a dead end"
