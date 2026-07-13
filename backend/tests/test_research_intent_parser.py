"""Phase 1a — deterministic research intent parser (pure, no DB, no LLM).

Covers both forcing cases from the spec:
1. Topic research: "Iran climate water drought".
2. Claim verification: "manipulación de clima Irán ... ataques a bases satélite".

The parser turns a natural (multilingual) query into structured intent:
geo scope, topic axes, expanded terms, subquestions, and related branches.
"""
from __future__ import annotations

from app.services.research_plan import parse_research_intent


def test_topic_research_iran_climate_water():
    intent = parse_research_intent("Iran climate water drought")

    assert "IR" in intent["geo_scope"]
    assert "climate" in intent["topic_axes"]
    assert "water" in intent["topic_axes"]
    # expansion brings sibling evidence terms the bare query lacks
    expanded = {t for terms in intent["expanded_terms"].values() for t in terms}
    assert "drought" in expanded
    assert any("reservoir" in t or "dam" in t for t in expanded)
    assert intent["subquestions"]  # non-empty research questions


def test_claim_verification_spanish_compound():
    intent = parse_research_intent(
        "manipulación de clima Irán agua sequía y ataques a bases estadounidenses satélite"
    )

    assert "IR" in intent["geo_scope"]
    assert "climate" in intent["topic_axes"]
    # the bases/satellite leg must register a conflict-infrastructure axis
    assert "conflict_infrastructure" in intent["topic_axes"]
    # and surface the US-bases/satellite related branch
    assert "us-bases-satellite-communications" in intent["branches"]


def test_geo_scope_merges_caller_hint_without_duplicates():
    intent = parse_research_intent("rain theft Iran", geo_scope=["IR", "ME"])

    assert intent["geo_scope"].count("IR") == 1
    assert "ME" in intent["geo_scope"]
    assert "climate" in intent["topic_axes"]  # "rain" maps to climate axis


def test_plain_infrastructure_escalation_query_opens_conflict_branch():
    intent = parse_research_intent("Iran regional escalation and infrastructure")
    assert "conflict_infrastructure" in intent["topic_axes"]
    assert "us-bases-satellite-communications" in intent["branches"]
    expanded = set(intent["expanded_terms"]["conflict_infrastructure"])
    assert {"attack", "attacks"} <= expanded


def test_unmatched_query_is_safe_not_empty():
    intent = parse_research_intent("local football transfer rumours")

    assert intent["geo_scope"] == []
    assert intent["topic_axes"] == []
    assert intent["branches"] == []
    # still returns a usable structure, never raises
    assert intent["main_intent"]
    assert "expanded_terms" in intent
