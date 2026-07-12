"""Content-based topic junk classifier (2026-07-09 useful-coverage gate).

The clustering recall fix (9d1b04e7) took story coverage 0.04% -> ~40% but the
relaxed promotion gate admitted JUNK grab-bags as active anchors. Measured on the
2026-07-09 prod unified-v2 state (docs/state/2026-07-09-useful-coverage-gate.md):
25 of 154 served topics are junk and eat 30% of assigned coverage.

WHY NOT the existing signals:
  - cohesion / whitened cohesion: DISPROVED (clustering-recall doc) — grab-bags are
    topically tight; build_unified_topics assigns members at >=0.82 cosine so every
    member is close to the centroid by construction. Junk cohesion is HIGH.
  - noise_rate: does NOT separate ("Celebrity Emotional Statements" 0.74 but
    "Full list of Welsh beaches" 0.27, "Who is Ser Torrhen Manderly?" 0.00).
  - subject_concentration (content-entropy, #224): CONFOUNDED here — Cyrillic/Greek
    morphology and the >=0.82 assign-vacuum drag good events down to junk levels
    (Ukraine 0.12, DR Congo Ebola 0.13 vs Welsh beaches 0.07). Kept upstream for
    single-outlet emergent roundups; unreliable as the primary unified-v2 signal.
  - label regexes alone: 8/597 recall (measured). Too brittle.

WHAT DOES separate (measured 2026-07-09), a UNION of three content signals:
  1. JUNK CATEGORY — the R3.1 DeepSeek typer already made the per-topic
     useful/entertainment/grab-bag judgment; its `category` is the strongest
     separator (Welsh beaches -> "Local & Community", Celebrity -> "Celebrity &
     Sports Drama", the "Mixed:" roundups -> "Daily News Roundups").
  2. LISTICLE / self-declared-grab-bag LABEL — catches listicles the typer put in
     an otherwise-real category ("Mixed: UK warnings and recalls" in Business &
     Markets, "WM 2026 Live Streams" in Sports).
  3. FEED-DUMP by source diversity — a LARGE topic carried by very FEW outlets is
     one outlet's feed dumped into a gravity well (Indonesian antaranews 1607
     members / 5 sources, Korean k-pop mislabeled "AI Policy" 1879/7, "Marcha para
     Jesus" 1222/5). Catches the mislabeled dumps the category typer trusts.

GUARD (must-survive real stories): sports is NOT a junk category — World Cup match
results/updates are real events (Pedro: World Cup must survive; damp in ranking,
not gate). Politics & Governance / Business & Markets / Science & Technology stay
useful. The feed-dump floor (>=150 members AND <=8 sources) never touches genuine
small regional stories. Verified: NATO/Ebola/Ukraine/Heatwave/real-World-Cup/
elections all pass.

Pure + importable by build_unified_topics, project_dynamic_topics, flag_junk_topics.
"""
from __future__ import annotations

import html as _html
import re

# Category vocabulary from the R3.1 typer (scripts/compute_category_typing.py /
# grow_atlas_categories). These are the grab-bag / entertainment-fluff / lifestyle
# / residual buckets — measured against the 2026-07-09 active population as the
# NON-useful classes. Sports*/World Cup*/Football*/Tennis*/Motorsport* are
# deliberately EXCLUDED (real events, damped in ranking not gated). Politics &
# Governance, Business & Markets, Science & Technology, the crisis categories, and
# Cultural Events stay useful (few-source dumps inside them are caught by rule 3).
JUNK_CATEGORIES = frozenset({
    "Daily News Roundups",        # the labeler's own "Mixed: <theme>" grab-bags
    "Celebrity & Sports Drama",
    "Celebrity & Entertainment",
    "Entertainment & Culture",
    "Travel Scams / Lifestyle",
    "Local & Community",          # Welsh-beaches / Köln-pool local roundups
    "Other",                      # typer residual/uncertain bucket (CentralAsia grab-bag)
    "Obituary & Tribute",
})

# High-precision listicle / self-declared-grab-bag markers. "Mixed:" is emitted by
# build_unified_topics' own label prompt for grab-bags (self-declared). Generic
# words ("results", "guide", "explained") are DELIBERATELY excluded — they fire on
# real news ("election results") — the category + dump signals carry the recall.
LISTICLE_LABEL = re.compile(
    r"(^\s*mixed:|\bfull list\b|\bwho is .+\?|\blive stream|\bmatch schedule|"
    r"\bfixtures?\b|\bhow to watch\b|\bwhat time\b|\bwhere to watch\b|"
    r"\bmeet the\b|\blistings?\b|\bhoroscopes?\b|\brecipes?\b|\bstarting (xi|11)\b)",
    re.IGNORECASE,
)

# Feed-dump signature: a topic this LARGE carried by this FEW distinct outlets is
# one source's feed dumped as a gravity well, not a corroborated narrative. Floors
# chosen (measured 2026-07-09): junk dumps sit at 1-7 distinct sources across
# 1000+ members; every real event of comparable size spans >=12 outlets
# (DR Congo Ebola 47, NATO 12, Ukraine 19). The member floor spares genuine small
# regional stories (a 20-member 3-outlet local story is untouched).
DUMP_MIN_MEMBERS = 150
DUMP_MAX_SOURCES = 8


def classify_topic_junk(
    category: str | None,
    label: str | None,
    member_count: int,
    distinct_sources: int | None,
) -> str | None:
    """Return a semicolon-joined junk reason, or None if the topic is useful.

    distinct_sources is the count over a sample of the topic's assigned members
    (unified-v2); pass None when unavailable (then the feed-dump rule is skipped —
    the category/label rules still apply).
    """
    reasons: list[str] = []
    if category and category in JUNK_CATEGORIES:
        reasons.append(f"category:{category}")
    if label and LISTICLE_LABEL.search(_html.unescape(label)):
        reasons.append("listicle-label")
    if (
        distinct_sources is not None
        and member_count >= DUMP_MIN_MEMBERS
        and distinct_sources <= DUMP_MAX_SOURCES
    ):
        reasons.append(f"feed-dump:{distinct_sources}src/{member_count}mem")
    return ";".join(reasons) if reasons else None
