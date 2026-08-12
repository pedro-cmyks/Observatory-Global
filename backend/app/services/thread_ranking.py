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

import html
import math
import os
import re
import unicodedata

from app.services.corroboration import cluster_syndicated
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

# --------------------------------------------------------------------------
# RANK V2 (2026-07-18, Lane C). Three glass-box adjustments, all damps (never
# gates — every thread stays listed) behind ONE kill-switch:
#   ATLAS_RANK_V2=off  → byte-identical to the pre-v2 ranking.
#
# 1. COURT DAMP — the Label Court verdict (label_status, mig 080) multiplies
#    the final score: a thread whose label FAILED entailment against its own
#    receipts ("Armed conflict escalation" blob serving book reviews) sinks
#    hard; "partial" dips mildly. The thread stays listed and the
#    LabelReviewChip explains why it sank. NULL (unjudged) / entailed = 1.0.
# 2. SYNDICATION DAMP — headline_diversity (the Jun-29 term, now measured as
#    needed: fresh single-family AU wire bursts out-rank Ukraine). Distinct
#    outlet/headline ratio over evidence_samples damps the VOLUME term only —
#    25 reprints of one wire piece stop counting as 25 independent outlets,
#    while movement/coherence/breadth stay untouched. Clamped to a 0.4 floor
#    (damp, never erase); threads with <3 receipts are not judged (1.0).
# 3. CRISIS LENS NUDGE — crisis_relevant=true gets a mild +10% tiebreak (the
#    harm lens). Never a gate: farándula stays listed, "you decide".
# --------------------------------------------------------------------------

_COURT_DAMP = {"failed": 0.5, "partial": 0.85}
_CRISIS_NUDGE = 1.10
_DIVERSITY_FLOOR = 0.4
_DIVERSITY_MIN_SAMPLES = 3
# Min-max normalisation sends the bottom of every component to 0, so a pure
# multiplicative damp cannot bite on a 0 score. v2 adds this small baseline
# BEFORE the multiplicative damps — an additive constant preserves the
# damp-free ordering exactly (monotonic shift) while letting court/lane/crisis
# multipliers still differentiate threads at the normalisation floor.
_V2_SCORE_BASELINE = 0.05


def rank_v2_enabled() -> bool:
    """ATLAS_RANK_V2 kill-switch — default ON; off/false/0/no reverts to the
    byte-identical old ranking (serving-order changes stay env-reversible)."""
    return os.getenv("ATLAS_RANK_V2", "on").strip().lower() not in {
        "off", "false", "0", "no",
    }


def _fold_headline(text: str) -> str:
    """Accent-fold + casefold + collapse non-word runs, keeping letters of
    EVERY script. `normalize_search_text`'s `[^a-z0-9]` class deletes non-Latin
    letters outright — measured 2026-07-30: 10.6% of resolved signals reduced
    to a degenerate key ('Атака РФ по АТБ у Чернігові 26 липня' → '26'), so
    two different ru/uk/ar/fa headlines sharing a number deduped as one story.
    Search keeps its own Latin-only normalizer (its LIKE patterns run against
    indexed expressions); this fold exists only for reprint keying."""
    decomposed = unicodedata.normalize("NFKD", text)
    accentless = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    words = re.sub(r"[\W_]+", " ", accentless.casefold())
    return re.sub(r"\s+", " ", words).strip()


def _degenerate_key(key: str) -> bool:
    """A key with no letters (digit/punctuation residue) cannot identify a
    story — every such key would share one bucket."""
    return not key or not any(ch.isalpha() for ch in key)


# A masthead stamp is also delivered on a DASH (measured 2026-08-12, M0
# §a.1): the live witness `dynamic-topic-11877` carries 22 copies of one wire
# piece as "<story> – <masthead>" across 22 US mastheads, and the pipe-only
# strip folded none of them. Unlike "|", a dash is ordinary prose punctuation
# (subtitles, ranges, em-dash asides), so the strip is guarded: it fires only
# when a LONG story side carries a SHORT stamp. Conservative by construction —
# an unstripped headline stays its own honest key, which is the safe error.
_DASH_SEP_RE = re.compile(r"\s+[–—]\s+|\s+-\s+")
_MASTHEAD_MAX_TOKENS = 5      # "Wilkes-Barre Citizens' Voice" folds to 4
_MASTHEAD_MIN_STORY_TOKENS = 8  # the story side must read like a headline


def _dash_masthead_key(text: str) -> str | None:
    """Fold key for a dash-stamped masthead, or None when the dash is prose.

    Tries the suffix stamp first (the measured signature) then the prefix, and
    keeps a side only if the stamp is short, the story is long, and the story
    out-tokens the stamp at least 2:1."""
    parts = _DASH_SEP_RE.split(text)
    if len(parts) < 2:
        return None
    for story_parts, stamp in ((parts[:-1], parts[-1]), (parts[1:], parts[0])):
        story_key = _fold_headline(" ".join(story_parts))
        stamp_key = _fold_headline(stamp)
        if _degenerate_key(story_key):
            continue
        story_n = len(story_key.split())
        stamp_n = len(stamp_key.split())
        if not stamp_n or stamp_n > _MASTHEAD_MAX_TOKENS:
            continue
        if story_n < _MASTHEAD_MIN_STORY_TOKENS or story_n < 2 * stamp_n:
            continue
        return story_key
    return None


def _norm_headline(text: str) -> str:
    """Normalise a headline for reprint detection. The measured live
    syndication signature (2026-07-18, AU Community Media) is the identical
    wire headline + a per-masthead suffix: "<same story> | Katherine Times" /
    "... | Blayney Chronicle" across 24 distinct .com.au domains — so strip
    the LAST "|"-separated segment (the outlet stamp) before comparing.
    Genuine distinct stories stay distinct; 24 masthead reprints collapse
    to one.

    Unescape first: 46.4% of the stored press corpus is HTML-entity-encoded
    (measured 2026-07-22) and 4,355 headline texts exist in BOTH forms, so
    without this an encoded and a plain copy of one wire story read as two
    stories — inflating the volume term that ranks the front page.

    Degenerate keys fall back instead of colliding (measured 2026-07-30):
    a masthead-PREFIXED headline ("BlackSeaNews | <story>") used to collapse
    to the bare outlet name (df 15), so the strip now folds BOTH the
    drop-last and drop-first candidates and keeps the token-richer one — the
    outlet stamp is always shorter than the story it stamps. A key with no
    letters at all (digit/punctuation residue) falls back to the full
    casefolded headline — an honest per-headline key beats a shared
    degenerate bucket."""
    text = html.unescape(text)
    full = _fold_headline(text)
    parts = text.split("|")
    if len(parts) >= 2:
        # strip the masthead stamp BEFORE folding — the fold turns "|" into
        # whitespace, which would make the split unfindable.
        suffix_kept = _fold_headline("|".join(parts[:-1]))
        prefix_kept = _fold_headline("|".join(parts[1:]))
        candidates = [k for k in (suffix_kept, prefix_kept)
                      if not _degenerate_key(k)]
        if candidates:
            # the story side out-tokens the stamp side; tie keeps the
            # measured suffix-strip (AU Community Media signature).
            return max(candidates, key=lambda k: len(k.split()))
    # The dash-delimited masthead (M0 §a.1, the jalapeño witness) — guarded,
    # because a dash is prose punctuation where a pipe is a stamp.
    dashed = _dash_masthead_key(text)
    if dashed:
        return dashed
    if not _degenerate_key(full):
        return full
    return " ".join(text.casefold().split())


def _reprint_weight(sample: dict) -> int:
    """How many raw signals one served receipt stands for. The evidence SQL
    de-duplicates on LOWER(headline) and reports the fold size as
    `syndication_count`; lanes that do not de-duplicate serve 1."""
    try:
        return max(1, int(sample.get("syndication_count") or 1))
    except (TypeError, ValueError):
        return 1


def headline_diversity(thread: dict) -> float:
    """Distinct-outlet/headline ratio over the thread's evidence receipts,
    clamped to [0.4, 1.0]. 25 near-identical reprints of one wire piece score
    the floor; genuinely multi-outlet coverage scores 1.0. Honest defaults:
    no receipts, or fewer than 3, cannot be judged → 1.0 (no damp).

    DENOMINATOR (repaired 2026-08-12, M0 §a.2/§a.7): the atlas evidence SQL is
    `DISTINCT ON (LOWER(s.headline))`, so a wire piece that ran on 20 outlets
    arrives as ONE receipt carrying `syndication_count = 20`. Counting rows
    made the ratio saturate at 1.0 by construction — the reprints had already
    been folded away before the damp could see them. The headline denominator
    is now the RAW signals those rows stand for. Lanes that serve
    `syndication_count = 1` (the dynamic sample) are byte-identical to before.

    Honest residual: the served sample is the only population reachable on the
    request path — a raw-membership join over `topic_members` measured 72 s
    cold / 5.7 s warm for 41 topics (2026-08-12), far outside the 15 s serving
    budget. Threads whose amplification lives only in raw membership are
    judged by `syndication_family_share` on the lead path instead."""
    samples = thread.get("evidence_samples") or []
    if len(samples) < _DIVERSITY_MIN_SAMPLES:
        return 1.0
    outlets: set[str] = set()
    headlines: set[str] = set()
    counted = 0
    raw_signals = 0
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        counted += 1
        raw_signals += _reprint_weight(sample)
        source = str(sample.get("source") or "").strip().lower()
        if source:
            outlets.add(source)
        headline = _norm_headline(str(sample.get("headline") or ""))
        if headline:
            headlines.add(headline)
    if counted < _DIVERSITY_MIN_SAMPLES:
        return 1.0
    outlet_ratio = len(outlets) / counted if outlets else 1.0
    headline_ratio = len(headlines) / raw_signals if headlines else 1.0
    # The binding constraint wins: one family reprinting (low outlet ratio) OR
    # one wire headline everywhere (low headline ratio) both mean the volume
    # is amplification, not independent coverage.
    diversity = min(outlet_ratio, headline_ratio)
    return max(_DIVERSITY_FLOOR, min(1.0, diversity))


# --------------------------------------------------------------------------
# LEAD-SLOT SYNDICATION VETO (T3.1 iii, 2026-08-12).
#
# `headline_diversity` damps the VOLUME term; it cannot stop a story whose
# other components (movement, breadth, coherence) carry it to the front page
# anyway. The measured witness did exactly that: `dynamic-topic-11877`
# "Jalapeño Salmonella Outbreak" held live `top_threads[0]` while 22 of its 26
# raw 24h members were ONE wire piece across 22 US mastheads.
#
# The bar was proposed in M0 §a.5 and RE-MEASURED after the (i)+(ii) repairs
# over the same 950-topic universe (docs/research/brief-daily/
# 2026-08-12-m0-measurement.md):
#
#   bin      repaired   M0        p50 0.091 · p90 0.222 · p95 0.300 · p99 0.600
#   [0.5,0.6)      5     11       ≥0.70 fires on 6 topics = 0.63% of the universe
#   [0.6,0.7)      4      3       all 6 hand-checked: template spam, single-
#   [0.7,0.8)      0      0  <--  outlet feeds, or one wire piece × N mastheads
#   [0.8,0.9)      2      2       nearest real story: 0.667 (Urban One arrest)
#   [0.9,1.0]      4      6       witness: 0.846 — clears by +0.146
#
# The empty [0.70,0.80) bin survived the repair: no topic in the universe
# scores between 0.667 and 0.846, so the bar falls in natural separation
# rather than through a cluster. The repair moved the tail the right way —
# the three fabricated Cyrillic families M0 warned about collapsed from
# 0.529-0.552 to 0.035-0.118, and two Japanese single-outlet feeds fell from
# ~0.90 to ~0.05 (their "family" was a digit artifact of the Latin-only
# tokenizer; that class needs an OUTLET-concentration signal, which this one
# honestly is not).
#
# It is a VETO OF THE SLOT, never a filter: the story keeps its place in the
# list one rank below, and `quality.lead_veto` says why.
# --------------------------------------------------------------------------

SYNDICATION_VETO_SHARE = 0.70
SYNDICATION_VETO_MIN_FAMILY = 8
# M0 hand-checked the family bar at Jaccard 0.5 over 950 topics; the
# corroboration lane keeps its own measured 0.6 for a different question.
SYNDICATION_VETO_TAU = 0.5
# Clustering is O(n·families); the population is capped so a 4,000-member
# topic cannot cost the front page a second. The share is a ratio, so a
# capped prefix still measures it.
_SYNDICATION_POPULATION_CAP = 400


def _syndication_population(thread: dict) -> list[dict]:
    """The headline population to judge, best available first.

    `raw_headline_sample` is the honest denominator (raw 24h membership,
    attached off the request path). Without it, the served receipts are
    expanded by their `syndication_count` so the reprints the evidence SQL
    de-duplicated still count as the raw signals they were."""
    raw = thread.get("raw_headline_sample")
    if isinstance(raw, list) and raw:
        titles = [str(h) for h in raw if h][:_SYNDICATION_POPULATION_CAP]
        return [{"title": title} for title in titles]
    population: list[dict] = []
    for sample in thread.get("evidence_samples") or []:
        if not isinstance(sample, dict):
            continue
        headline = str(sample.get("headline") or "")
        if not headline:
            continue
        for _ in range(_reprint_weight(sample)):
            population.append({"title": headline})
            if len(population) >= _SYNDICATION_POPULATION_CAP:
                return population
    return population


def syndication_family_share(thread: dict) -> tuple[float, int, int]:
    """(share, largest family size, population size) for one thread.

    A "family" is a Jaccard@0.5 cluster of headline token sets — the matcher
    M0 hand-checked, script-safe and deterministic since the corroborate-v2
    repair. A population we cannot judge returns (0.0, 0, n): no signal, and
    therefore no veto."""
    population = _syndication_population(thread)
    if len(population) < SYNDICATION_VETO_MIN_FAMILY:
        return 0.0, 0, len(population)
    families = cluster_syndicated(population, tau=SYNDICATION_VETO_TAU)
    largest = max((len(f) for f in families), default=0)
    return largest / len(population), largest, len(population)


def lead_syndication_veto(thread: dict) -> bool:
    """True when this story's coverage is one amplified family and it must not
    hold the lead slot. Both bars are required: the SHARE (is the coverage
    mostly one text?) and the absolute FAMILY SIZE (is there enough of it to
    call amplification?). A 7-member topic that is 100% one wire copy is a
    thin story, not a front-page distortion — and staying silent on what we
    cannot judge is the safe error for a demotion."""
    share, family_n, _ = syndication_family_share(thread)
    return share >= SYNDICATION_VETO_SHARE and family_n >= SYNDICATION_VETO_MIN_FAMILY


def _measure_lead_syndication(thread: dict) -> bool:
    """Measure one lead candidate and stamp the verdict on its serving row.

    The stamp must ride EVERY measured candidate, not only a demoted
    ex-leader: the front page's eligibility gate falls back to the best
    eligible row when the ranks above it lack a court stamp, so a wire
    family that natively ranks #2 re-takes the lead through that fallback
    unless its own row carries the veto (G-JALAPEÑO live regression,
    2026-08-12: dt-11877 served at #2 with syndication_family_share null
    and led the page under an unstamped #1)."""
    share, family_n, _ = syndication_family_share(thread)
    is_veto = (share >= SYNDICATION_VETO_SHARE
               and family_n >= SYNDICATION_VETO_MIN_FAMILY)
    quality = thread.get("quality")
    if isinstance(quality, dict):
        quality["syndication_family_share"] = round(share, 3)
        if is_veto:
            quality["lead_veto"] = "syndicated_family"
            quality["lead_veto_family_size"] = family_n
    return is_veto


def _apply_lead_syndication_veto(ranked: list[dict]) -> list[dict]:
    """Stamp every measurable lead candidate, then move a vetoed leader to
    just below the best story that is not vetoed. Every other position is
    preserved, and nothing is ever removed. If the whole field is syndicated
    there is no honest lead to promote, so the ORDER stands — but the stamps
    still ride the rows, so the serving gate renders its honest empty-lead
    state instead of promoting a wire family the backend measured."""
    if not ranked:
        return ranked
    vetoed: dict[int, bool] = {}
    for idx, thread in enumerate(ranked):
        # Rows carrying a raw membership sample are the serving layer's
        # lead-candidate window (top-N, attached off the request path); the
        # leader is measured regardless, via the evidence-sample fallback,
        # exactly as before. Cost: ≤ top-N clusterings of ≤150 titles.
        if idx == 0 or thread.get("raw_headline_sample"):
            vetoed[idx] = _measure_lead_syndication(thread)
    if len(ranked) < 2 or not vetoed[0]:
        return ranked
    for idx in range(1, len(ranked)):
        if idx not in vetoed:
            vetoed[idx] = _measure_lead_syndication(ranked[idx])
        if vetoed[idx]:
            continue
        return [*ranked[1:idx + 1], ranked[0], *ranked[idx + 1:]]
    return ranked


def court_rank_multiplier(thread: dict) -> float:
    """Label Court damp: failed 0.5, partial 0.85, entailed/NULL 1.0."""
    status = str(thread.get("label_status") or "").strip().lower()
    return _COURT_DAMP.get(status, 1.0)


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
    v2 = rank_v2_enabled()
    comps = [thread_score_components(t) for t in threads]
    if v2:
        # SYNDICATION DAMP (v2): the volume term carries a diversity factor —
        # single-wire reprint volume stops counting as independent coverage.
        # The factor is WRITTEN BACK into each thread's quality dict so the
        # damp is explainable in the served payload (verify-gate note: a damp
        # with no served explanation hook is a silent judgment).
        divs = [headline_diversity(t) for t in threads]
        for t, dv in zip(threads, divs):
            q = t.get("quality")
            if isinstance(q, dict):
                q["headline_diversity"] = round(dv, 3)
        volumes = [c[0] * dv for dv, c in zip(divs, comps)]
    else:
        volumes = [c[0] for c in comps]
    nv = _minmax(volumes)
    nm = _minmax([c[1] for c in comps])
    nc = _minmax([c[2] for c in comps])
    nb = _minmax([c[3] for c in comps])
    scored = []
    for idx, (t, v, m, c, b) in enumerate(zip(threads, nv, nm, nc, nb)):
        score = _W_VOLUME * v + _W_MOVEMENT * m + _W_COHERENCE * c + _W_BREADTH * b
        if v2:
            # Baseline so multiplicative damps bite at the min-max floor;
            # additive shift never reorders the damp-free ranking.
            score += _V2_SCORE_BASELINE
        # Editorial-lane damp: lifestyle/sport/entertainment threads stop
        # out-ranking real news (still present — input, not gate).
        score *= lane_rank_multiplier(t)
        if v2:
            # COURT DAMP: a label the court failed against its own receipts
            # sinks (0.5) — still listed, chip explains. Partial dips (0.85).
            score *= court_rank_multiplier(t)
            # CRISIS LENS NUDGE: mild harm-lens tiebreak, never a gate.
            if t.get("crisis_relevant") is True:
                score *= _CRISIS_NUDGE
        # deterministic tie-break: score, then raw volume, then label
        scored.append((score, comps[idx][0], str(t.get("label") or ""), t))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    ranked = [t for _, _, _, t in scored]
    if v2:
        # LEAD-SLOT VETO: an amplified single wire family may rank, but it may
        # not be the front page's lead. Runs last, on the final order.
        ranked = _apply_lead_syndication_veto(ranked)
    return ranked
