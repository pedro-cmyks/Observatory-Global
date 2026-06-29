"""Analyst-grade relevance scoring and lane classification for the Signal Stream.

The default `Notable` stream mixes crisis/conflict/economic items with sports,
celebrity, and lifestyle noise. This module assigns each signal to a lane and a
0..1 relevance score so the stream can promote analyst-grade items and visibly
separate entertainment/sports.

Lane signal sources:
- ``analyst``  — crisis themes (``is_crisis_theme``) or security/economy/politics
  taxonomy categories. Theme-driven and authoritative.
- ``sports`` / ``entertainment`` — headline keyword heuristics, because the
  observed noise (e.g. "Vikings 2026 Undrafted Free Agents", "Eurovision Song
  Contest 2026") usually carries generic or empty GDELT themes.
- ``general`` — everything else.

Analyst themes override headline keywords: a crisis theme on a sport-sounding
headline (e.g. a stadium attack) is still analyst.

Pure functions — no DB.
"""
from __future__ import annotations

from app.config.crisis_themes import calculate_severity, is_crisis_theme
from app.core.gdelt_taxonomy import get_theme_category

_ANALYST_CATEGORIES = {"security", "economy", "politics"}

# Whole-word-ish keyword sets. Matched case-insensitively against the headline.
_SPORTS_KEYWORDS = {
    "nfl", "nba", "mlb", "nhl", "vikings", "undrafted", "free agents",
    "golf", "tournament", "playoff", "playoffs", "match", "fixture",
    "league", "championship", "quarterback", "striker", "midfielder",
    "fifa", "uefa", "premier league", "super bowl", "world cup",
    "olympics", "athlete", "coach fired", "transfer window",
}
_ENTERTAINMENT_KEYWORDS = {
    "eurovision", "song contest", "biopic", "trailer", "box office",
    "celebrity", "red carpet", "grammy", "oscars", "billboard",
    "album", "concert tour", "netflix series", "tv show", "movie premiere",
    "reality show", "michael jackson", "taylor swift", "kardashian",
}
# Travel / lifestyle / service-journalism filler. Added 2026-06-29: the "Las
# Vegas Travel Guide ranks #1" pathology is low-news-value lifestyle copy, not a
# syndication problem (measure-first disproved headline_diversity — spec §4.0).
# Phrase-level keys to avoid catching real news (e.g. "travel guide", not "travel").
_LIFESTYLE_KEYWORDS = {
    "travel guide", "things to do", "best restaurants", "where to eat",
    "where to stay", "best hotels", "best beaches", "tourist guide",
    "city guide", "getaway", "staycation", "bucket list", "hidden gems",
    "day trip", "holiday destination", "best places to visit", "weekend break",
    "things to know before", "ultimate guide to",
}

_SEVERITY_BOOST = {"critical": 0.3, "high": 0.2, "medium": 0.1, "low": 0.0}

_LANE_BASE_SCORE = {
    "analyst": 0.7,
    "general": 0.4,
    "sports": 0.15,
    "entertainment": 0.12,
    "lifestyle": 0.12,
}


def _has_analyst_theme(themes: list[str]) -> bool:
    for theme in themes or []:
        if is_crisis_theme(theme):
            return True
        if get_theme_category(theme) in _ANALYST_CATEGORIES:
            return True
    return False


def _headline_matches(headline: str, keywords: set[str]) -> bool:
    text = (headline or "").lower()
    return any(kw in text for kw in keywords)


def classify_stream_lane(themes: list[str], headline: str | None) -> str:
    """Return the stream lane for a signal.

    Order matters: analyst themes win over headline keywords.
    """
    if _has_analyst_theme(themes):
        return "analyst"
    if _headline_matches(headline or "", _SPORTS_KEYWORDS):
        return "sports"
    if _headline_matches(headline or "", _ENTERTAINMENT_KEYWORDS):
        return "entertainment"
    if _headline_matches(headline or "", _LIFESTYLE_KEYWORDS):
        return "lifestyle"
    return "general"


def stream_relevance_score(themes: list[str], headline: str | None) -> float:
    """Return a 0..1 relevance score; analyst items rank above noise."""
    lane = classify_stream_lane(themes, headline)
    score = _LANE_BASE_SCORE[lane]
    if lane == "analyst":
        score += _SEVERITY_BOOST.get(calculate_severity(themes or []), 0.0)
    return max(0.0, min(1.0, round(score, 3)))


def score_stream_signal(themes: list[str], headline: str | None) -> dict:
    """Combined helper for the router: lane + relevance score."""
    lane = classify_stream_lane(themes, headline)
    score = _LANE_BASE_SCORE[lane]
    if lane == "analyst":
        score += _SEVERITY_BOOST.get(calculate_severity(themes or []), 0.0)
    return {"lane": lane, "relevanceScore": max(0.0, min(1.0, round(score, 3)))}
