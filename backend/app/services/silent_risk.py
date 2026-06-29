"""Silent-risk detection (#172) — pure helpers.

A SILENT RISK = a topic with measurable PUBLIC attention (Wikipedia pageviews)
but near-zero MEDIA coverage in the same window. It is Atlas's strongest
differentiator vs GDELT wrappers: "what is the public searching for that the
press is NOT covering?" — the "what is missing" half of the product wedge.

These helpers are pure (no DB / no network) so the thresholds and noise filter
can be unit-tested. The router (`attention_threads.py`) does the DB + embed
orchestration and calls these to decide.
"""
from __future__ import annotations

import re

# Wikipedia non-article / housekeeping namespaces + obvious entertainment/list
# noise (#145 extends this). These are attention artifacts, never silent risks.
_NOISE_PREFIXES = (
    "main_page", "special:", "wikipedia:", "portal:", "category:", "template:",
    "help:", "file:", "talk:", "user:", "draft:",
)
_NOISE_SUBSTRINGS = (
    "(disambiguation)", "(film)", "(tv series)", "(song)", "(album)",
    "(video game)", "(franchise)", "list_of_", "_(season_",
    ".phtml", ".php", "index.htm", "/wiki/",  # URL/scraper artifacts
)
_ENTERTAINMENT_TOKENS = {
    "pornographic", "xxx", "deaths_in", "filmography", "discography",
}
# Latin-script test: a title with no ASCII letters is non-English (a strong
# "language barrier" hint for why_silent — the press that covers it is likely
# in another language Atlas under-ingests).
_ASCII_LETTER = re.compile(r"[A-Za-z]")


def is_noise_title(title: str) -> bool:
    """True for Wikipedia housekeeping / entertainment / list-page noise."""
    if not title:
        return True
    t = title.strip().lower()
    if any(t.startswith(p) for p in _NOISE_PREFIXES):
        return True
    if ":" in t and not t.startswith("covid"):  # namespace colon (keep 'COVID-19')
        return True
    if any(s in t for s in _NOISE_SUBSTRINGS):
        return True
    if any(tok in t for tok in _ENTERTAINMENT_TOKENS):
        return True
    return False


def normalize_title(title: str) -> str:
    """Wikipedia title -> a natural-language query string for embedding/matching.
    'Iran%E2%80%93Israel_war' -> 'Iran Israel war' (underscores, strip paren tag)."""
    t = (title or "").replace("_", " ")
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)  # trailing '(disambiguation)' etc.
    return re.sub(r"\s+", " ", t).strip()


def is_silent_risk(views: int, media_count: int, *,
                   velocity: float | None = None, surge_ratio: float = 2.0,
                   min_views: int = 1, media_floor: int = 3) -> bool:
    """SURGING public attention + near-zero media coverage.

    Velocity matters: an evergreen celebrity/sport page with steady high views is
    NOT a silent risk (it just isn't news). A page whose views SPIKE today (a real
    event the public is looking up) with no press coverage IS. When velocity is
    given, require a surge; brand-new pages (no baseline) pass by construction.
    """
    if views < min_views or media_count >= media_floor:
        return False
    if velocity is not None and velocity < surge_ratio:
        return False
    return True


# Wikipedia-category -> editorial lane. Classifying a bare entity TITLE
# ("Nico Paz", "Scarface") needs to know what the entity IS — keyword matching on
# the title can't, but the article's Wikipedia categories ("Argentine
# footballers", "1983 films") can. Classify, never drop (Pedro 2026-06-29).
_CAT_SPORTS = (
    "footballer", "football", "soccer", "basketball", "tennis", "athlete",
    "olympic", "cricket", "sport", "fifa", "national team", "rugby", "boxer",
    "cyclist", "swimmer", "golfer", "racing driver", "wrestler",
)
_CAT_ENTERTAINMENT = (
    "film", "films", "album", "song", "actor", "actress", "musician", "singer",
    "television", "video game", "novel", "band", "discography", "drama",
    "comedian", "sitcom", "rapper", "screenwriter", "soap opera", "anime",
)


def category_to_lane(categories: list[str]) -> str:
    """Map an article's Wikipedia categories to news|sports|entertainment|general.
    News wins ties only implicitly: a topic that is neither sports nor
    entertainment stays 'general' (the analyst-relevant default)."""
    blob = " ".join(categories).lower()
    if any(k in blob for k in _CAT_SPORTS):
        return "sports"
    if any(k in blob for k in _CAT_ENTERTAINMENT):
        return "entertainment"
    return "general"


def why_silent(title: str, country_code: str | None, media_count: int,
               information_desert: bool = False) -> str:
    """Suggested explanation for WHY a topic is silent (analyst hint, honest)."""
    if information_desert:
        return "information desert (country has low media baseline regardless of topic)"
    norm = normalize_title(title)
    if norm and not _ASCII_LETTER.search(norm):
        return "non-English topic — likely covered in a language Atlas under-ingests"
    if media_count == 0:
        return "no media coverage found in window"
    return "thinly covered — below the media floor"
