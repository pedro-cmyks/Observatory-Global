"""Deterministic research intent parser for the research workflow (Phase 1a).

Pure module: no DB, no FastAPI, no external services, no LLM. It turns a natural
(multilingual) investigation query into structured intent the research-plan
endpoint can use to discover anchors over existing Atlas surfaces.

Design notes:
- Matching runs over the accent-folded, lowercased query (`normalize_search_text`)
  so Spanish/English variants ("clima"/"climate", "Irán"/"Iran") collapse.
- Axis dictionaries are intentionally small and explainable. Over-recall is a
  known risk (spec Open Problem 1); the semantic lane (Phase 1.5) widens recall
  later. v1 stays deterministic and inspectable.
- The expansion dictionary feeds sibling evidence terms the bare query lacks,
  which is how a query like "Iran climate water drought" can reach reservoir/dam
  evidence. Corpus-mined vocabulary (#185) can extend these dicts later.
"""
from __future__ import annotations

from app.core.search_normalization import normalize_search_text


# name/alias -> ISO 3166-1 alpha-2. Small seed; extend as forcing cases grow.
COUNTRY_ALIASES: dict[str, str] = {
    "iran": "IR",
    "iraq": "IQ",
    "israel": "IL",
    "qatar": "QA",
    "kuwait": "KW",
    "bahrain": "BH",
    "uae": "AE",
    "emirates": "AE",
    "saudi": "SA",
    "saudi arabia": "SA",
    "jordan": "JO",
    "colombia": "CO",
    "united states": "US",
    "usa": "US",
}

# axis -> trigger terms (matched as whole-word tokens on the normalized query).
AXIS_TRIGGERS: dict[str, set[str]] = {
    "climate": {
        "climate", "clima", "weather", "drought", "sequia", "heat", "heatwave",
        "calor", "rain", "lluvia", "dust", "flood", "inundacion",
        "manipulacion",  # "manipulación de(l) clima" claim phrasing
    },
    "water": {
        "water", "agua", "drought", "sequia", "reservoir", "embalse", "dam",
        "dams", "presa", "aquifer", "groundwater", "rationing",
    },
    "conflict_infrastructure": {
        "base", "bases", "attack", "attacks", "ataque", "ataques", "strike",
        "strikes", "missile", "misil", "radar", "satellite", "satelite",
        "communications", "comunicaciones", "microwave", "microondas", "drone",
        "war", "guerra",
    },
}

# axis -> sibling evidence terms the bare query may not contain.
AXIS_EXPANSIONS: dict[str, list[str]] = {
    "climate": [
        "drought", "heatwave", "water scarcity", "dust storm", "flood",
        "rainfall", "reservoir",
    ],
    "water": [
        "drought", "reservoir", "dam", "aquifer", "groundwater", "rationing",
        "water scarcity",
    ],
    "conflict_infrastructure": [
        "us base", "radar", "radome", "satellite communications", "air defense",
        "missile strike",
    ],
}

# axis -> research subquestions (the "qué quiero responder" frame).
AXIS_SUBQUESTIONS: dict[str, list[str]] = {
    "climate": [
        "What is happening with drought, heat, rainfall, and water stress?",
    ],
    "water": [
        "How are reservoirs, dams, groundwater, and rationing affected?",
    ],
    "conflict_infrastructure": [
        "What infrastructure (bases, radar, satellite, communications) is involved and who is targeted?",
    ],
}

_WHO_SAYS_WHAT = "Who is talking about it, how are they framing it, and after what?"


def _tokens(normalized: str) -> set[str]:
    return set(normalized.split())


def _detect_geo(normalized: str, tokens: set[str]) -> list[str]:
    detected: list[str] = []
    for alias, code in COUNTRY_ALIASES.items():
        # multi-word alias -> substring; single word -> token match
        hit = alias in normalized if " " in alias else alias in tokens
        if hit and code not in detected:
            detected.append(code)
    return detected


def parse_research_intent(
    query: str,
    *,
    geo_scope: list[str] | None = None,
) -> dict:
    """Parse a natural query into structured research intent.

    Never raises on unmatched input: returns a usable, mostly-empty structure.
    """
    normalized = normalize_search_text(query or "")
    tokens = _tokens(normalized)

    geo = _detect_geo(normalized, tokens)
    for code in geo_scope or []:
        if code not in geo:
            geo.append(code)

    topic_axes: list[str] = []
    expanded_terms: dict[str, list[str]] = {}
    subquestions: list[str] = []
    for axis, triggers in AXIS_TRIGGERS.items():
        if tokens & triggers:
            topic_axes.append(axis)
            expanded_terms[axis] = AXIS_EXPANSIONS.get(axis, [])
            subquestions.extend(AXIS_SUBQUESTIONS.get(axis, []))

    if topic_axes:
        subquestions.append(_WHO_SAYS_WHAT)

    branches: list[str] = []
    if "conflict_infrastructure" in topic_axes:
        branches.append("us-bases-satellite-communications")

    return {
        "main_intent": normalized or (query or "").strip(),
        "geo_scope": geo,
        "topic_axes": topic_axes,
        "expanded_terms": expanded_terms,
        "subquestions": subquestions,
        "branches": branches,
        "excluded_noise": [],
    }
