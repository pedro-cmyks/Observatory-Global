"""Unified narrative-thread ranking (Pedro, 2026-06-24).

Drops the living/aggregate hierarchy: dynamic clusters and atlas topics are all
narrative threads and rank by the SAME score — no source bias. A persistent
atlas topic that keeps growing is a live thread, not a second-class aggregate.

Score blends three min-max-normalised components across the candidate set:

  score = 0.45·volume(log-damped) + 0.35·movement(relative) + 0.20·coherence

- volume = log1p(signal_count): damped so a 3,000-signal category cannot bury a
  50-signal story by raw count alone.
- movement = changed_10h / signal_count: relative acceleration, so "what's
  heating now" rises regardless of absolute size.
- coherence = avg_confidence: tips near-ties toward real stories over loose
  category bins (the guardrail — keeps raw taxonomy from dominating).

Weights are a calibratable v1; tune against live orderings, not in the abstract.
"""
from __future__ import annotations

import math

from app.services.daily_edition import global_breadth_signal
from app.services.stream_relevance import classify_stream_lane

# L2 shares the L1 consequence signal: raw volume is damped hard (a local firehose
# must not lead) and cross-language + multi-country breadth carries the weight a
# genuinely global event earns. Same global_breadth_signal as the daily selector.
_W_VOLUME = 0.30
_W_MOVEMENT = 0.25
_W_COHERENCE = 0.20
_W_BREADTH = 0.25

# Editorial-lane DAMP (2026-06-29, spec §4.0/§4(b)). The "Las Vegas Travel Guide
# ranks #1" pathology is low-news-value lifestyle/sport/entertainment copy, NOT
# syndication (measure-first disproved headline_diversity). A thread whose LABEL
# classifies into a noise lane is multiplicatively damped — it still appears
# (input, never a gate), it just stops out-ranking real news. Real-news labels
# carry no sports/lifestyle keyword → "general"/"analyst" → multiplier 1.0.
# Damp hard: a World Cup match or a celebrity meal is genuinely covered in many
# languages and countries, so the breadth signal PROMOTES it — only a firm
# semantic damp keeps non-news off the front page however globally it is covered.
_LANE_RANK_MULTIPLIER = {
    "sports": 0.15,
    "entertainment": 0.15,
    "lifestyle": 0.20,
}


# #246 (2026-07-01): the label-keyword lane missed "Hannah St Hotel Review"
# (#3-4 global) while the served R3.1 category — 'Health & Lifestyle' — knew.
# The damp now consumes the thread's OWN category first: crisis_relevant=False
# AND a lifestyle-family category → damp; otherwise fall back to label lanes.
# Conservative token set: business/politics/obituary emergent domains are NOT
# damped (news); crisis_relevant None (untyped) never damps by category.
_NON_NEWS_CATEGORY_TOKENS = (
    "lifestyle", "sport", "entertainment", "travel", "tourism", "cuisine",
    "food", "celebrit", "fashion", "music", "gaming", "hotel", "recipe",
    "football", "soccer", "world cup",
)


def lane_rank_multiplier(thread: dict) -> float:
    """Damp factor in (0, 1] — the served category (R3.1) first, then the
    label's editorial lane as fallback (a v1 the keyword sets can grow)."""
    if thread.get("crisis_relevant") is False:
        cat = str(thread.get("parent_domain") or thread.get("category") or "").lower()
        if cat and any(tok in cat for tok in _NON_NEWS_CATEGORY_TOKENS):
            return _LANE_RANK_MULTIPLIER["lifestyle"]
    lane = classify_stream_lane([], str(thread.get("label") or ""))
    return _LANE_RANK_MULTIPLIER.get(lane, 1.0)

# A thread needs at least this many signals before its relative movement is
# fully trusted. A huge swing on a tiny base (e.g. a 28-signal syndicated story
# whose changed_10h reads 53) is noise/amplification, not a real surge — so it
# must not out-rank a 766-signal accelerating story for the front-page lead.
_MOVEMENT_VOL_FLOOR = 80.0


def _minmax(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1.0
    return [(v - lo) / rng for v in values]


def thread_score_components(thread: dict) -> tuple[float, float, float, float]:
    """Raw (pre-normalisation) volume / movement / coherence / breadth for one
    thread. Breadth is the shared consequence signal (cross-language + multi-
    country), zero when the thread carries no breadth fields."""
    sc = max(int(thread.get("signal_count") or 0), 0)
    ch = int(thread.get("changed_10h") or 0)
    conf = float(thread.get("avg_confidence") or 0.0)
    volume = math.log1p(sc)
    # Relative acceleration, clamped (changed_10h can exceed signal_count, #214)
    # and volume-confidence-damped so a freak swing on a tiny base can't lead.
    movement_raw = max(-2.0, min(2.0, ch / sc)) if sc > 0 else 0.0
    movement = movement_raw * min(1.0, sc / _MOVEMENT_VOL_FLOOR)
    breadth = global_breadth_signal(
        int(thread.get("language_count") or 0),
        int(thread.get("country_count") or 0),
    )
    return volume, movement, conf, breadth


def rank_threads(threads: list[dict]) -> list[dict]:
    """Return threads ordered by the unified score (best first). Source-agnostic
    and deterministic: ties fall back to volume then label so order is stable."""
    if not threads:
        return []
    comps = [thread_score_components(t) for t in threads]
    nv = _minmax([c[0] for c in comps])
    nm = _minmax([c[1] for c in comps])
    nc = _minmax([c[2] for c in comps])
    nb = _minmax([c[3] for c in comps])
    scored = []
    for idx, (t, v, m, c, b) in enumerate(zip(threads, nv, nm, nc, nb)):
        score = _W_VOLUME * v + _W_MOVEMENT * m + _W_COHERENCE * c + _W_BREADTH * b
        # Editorial-lane damp: lifestyle/sport/entertainment threads stop
        # out-ranking real news (still present — input, not gate).
        score *= lane_rank_multiplier(t)
        # deterministic tie-break: score, then raw volume, then label
        scored.append((score, comps[idx][0], str(t.get("label") or ""), t))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return [t for _, _, _, t in scored]
