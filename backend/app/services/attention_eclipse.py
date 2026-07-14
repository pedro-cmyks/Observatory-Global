"""Attention-eclipse / under-the-radar detection — pure logic (no DB, no network).

WHAT IT ANSWERS. During a World-Cup-final-scale attention eclipse, "while everyone
watches the final, what ELSE consequential is slipping under the radar?" — surface
the consequential stories drowned out when coverage concentrates on one dominant
event.

HOW IT RELATES TO THE REST OF ATLAS (the shared story-state, read three ways):
  - CONSEQUENCE = spatial/linguistic spread. Reuses daily_edition.global_breadth_signal
    (language x country breadth). "How globally consequential is this story?" — an
    ABSOLUTE per-story reading, importance that is NOT raw volume.
  - MOVEMENT = temporal derivative. topic_movement Kalman velocity/surprise. "Is it
    rising / off-baseline right now?" — an ABSOLUTE per-story reading.
  - ATTENTION SHARE = field-relative reading (the one nothing else computes): this
    story's slice of the WINDOW's total coverage. "How much of the room is it taking
    vs everyone else?"
  Eclipse = high consequence (breadth, optionally rising) + LOW attention share,
  gated on the field being concentrated on a dominant event. Same shared state,
  a new RELATIVE reading — no parallel truth model.

WHY IT DEPENDS ON CLASSIFICATION QUALITY. Breadth, movement, and attention-share are
all computed OVER a story's member set. If an event is fragmented across topics (the
gap-2 problem) its breadth is undercounted and its attention-share is split, so it
looks quieter than it is; if members are mislabeled (grab-bag / wrong lane) the gates
misfire. Correct event-grouping + correct labels upstream directly sharpen this
signal — the two are the same thread.

HONESTY. This measures COVERAGE-VOLUME concentration, a PROXY for attention — Atlas
cannot measure audience eyeballs (wiki/trends are decoupled from stories, top-N,
stale). The signal RANKS candidates for an analyst; it does not CERTIFY that an
individual story is real news. Every candidate carries a reason-coded ledger row —
nothing is silently filtered; sports/entertainment are LABELED, not dropped.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.daily_edition import global_breadth_signal


# ── (a) eclipse detector — window-level coverage concentration ───────────────

def attention_concentration(volumes: list[int], *, eclipse_top1: float = 0.20) -> dict:
    """Concentration of coverage volume across the window's stories.

    Returns top1/top3 share, HHI, the dominant story index, and whether the window
    is ECLIPSED (top-1 share >= threshold). An empty/zero window is never an eclipse.
    """
    total = sum(v for v in volumes if v and v > 0)
    if total <= 0:
        return {"total": 0, "top1_share": 0.0, "top3_share": 0.0, "hhi": 0.0,
                "dominant_index": None, "eclipse": False}
    shares = [max(0, v) / total for v in volumes]
    order = sorted(range(len(shares)), key=lambda i: -shares[i])
    top1_share = shares[order[0]]
    top3_share = sum(shares[i] for i in order[:3])
    hhi = sum(s * s for s in shares)
    return {
        "total": total,
        "top1_share": round(top1_share, 6),
        "top3_share": round(top3_share, 6),
        "hhi": round(hhi, 6),
        "dominant_index": order[0],
        "eclipse": top1_share >= eclipse_top1,
    }


# ── (c) consequence proxy — breadth (reused) + movement ──────────────────────

def consequence_score(*, language_breadth: int, country_breadth: int,
                      velocity: float = 0.0, surprise: float = 0.0) -> float:
    """Consequence = 0.6*global_breadth + 0.25*|velocity| + 0.15*surprise, in [0,1].

    Breadth (the dominant term) reuses global_breadth_signal verbatim so consequence
    means the same thing here as in the daily edition. Velocity sign is irrelevant —
    a fast decay is movement too. Bounded to the unit interval.
    """
    breadth = global_breadth_signal(language_breadth, country_breadth)
    mv = min(1.0, abs(velocity or 0.0))
    sp = min(1.0, max(0.0, surprise or 0.0))
    score = 0.6 * breadth + 0.25 * mv + 0.15 * sp
    return round(max(0.0, min(1.0, score)), 6)


# ── lane typing — DeepSeek category first, NOT the buggy keyword classifier ──

_SOFT_SPORT_HINTS = (
    "world cup", "fifa", "football", "soccer", "olympic", "nba", "uefa",
    "premier league", "super bowl", "la liga", "champions league", "grand prix",
)
_SOFT_ENT_HINTS = (
    "box office", "netflix", "grammy", "oscars", "album", "concert", "tour dates",
    "red carpet", "streaming premiere",
)


def lane_of(category: str | None, label: str) -> str:
    """Editorial lane from the DeepSeek-typed `dynamic_topics.category`, falling back
    to a soft label keyword only when no category is typed. Deliberately NOT
    stream_relevance.classify_stream_lane, which mislabels bare hard-news category
    labels (measured: 'armed-conflict-escalation' -> 'sports')."""
    cat = (category or "").lower()
    if "sport" in cat:
        return "sports"
    if any(k in cat for k in ("entertainment", "celebrity", "culture", "music",
                              "film", "arts", "showbiz")):
        return "entertainment"
    low = (label or "").lower()
    if any(k in low for k in _SOFT_SPORT_HINTS):
        return "sports"
    if any(k in low for k in _SOFT_ENT_HINTS):
        return "entertainment"
    return "general"


# ── (b)+(d) under-radar candidate + selection ───────────────────────────────

class EclipseCandidate(BaseModel):
    topic_id: str
    label: str
    attention: int = 0
    language_breadth: int = 0
    country_breadth: int = 0
    velocity: float = 0.0
    surprise: float = 0.0
    category: str | None = None
    crisis_relevant: bool | None = None
    mean_cohesion: float | None = None
    is_junk: bool = False
    is_roundup: bool = False


class EclipseLedgerRow(BaseModel):
    topic_id: str
    label: str
    status: Literal["selected", "labeled_out", "below_floor", "dominant", "suppressed"]
    attention_share: float
    consequence: float
    lane: str
    reason_codes: list[str]
    components: dict[str, Any]


class EclipseSelection(BaseModel):
    contract: str = "attention-eclipse-v0"
    eclipse: bool
    selected_ids: list[str]
    dominant: dict[str, Any]
    ledger: list[EclipseLedgerRow]
    window: dict[str, Any]
    method: dict[str, Any]


_ROUNDUP_LABEL_HINTS = (
    "front page", "naslovne", "portada", "roundup", "round-up", "briefing",
    "digest", "news from", "noticias", "schlagzeilen", "titulares", "headlines for",
)


def select_under_radar(
    candidates: list[EclipseCandidate],
    *,
    eclipse_on: bool,
    min_langs: int = 3,
    min_countries: int = 8,
    cohesion_floor: float = 0.55,
    display_limit: int = 8,
) -> EclipseSelection:
    """Rank the consequential-but-quiet stories under an eclipse.

    Among stories that clear a CONSEQUENCE FLOOR (multi-language AND multi-country)
    and QUALITY GATES (not junk/roundup, cohesion floor, lane=general), the ones with
    the LOWEST attention share are surfaced — ordered by lowest share first. When the
    window is not eclipsed nothing is surfaced (the signal stays quiet), but every
    candidate still gets a ledger row so nothing is silently dropped.

    Not a raw consequence/attention ratio: that explodes on tiny denominators and
    surfaces local trivia. The floor + low-share ordering is the correct instrument.
    """
    total = sum(max(0, c.attention) for c in candidates)
    dominant_id: str | None = None
    dominant_info: dict[str, Any] = {}
    if candidates:
        dom = max(candidates, key=lambda c: c.attention)
        dominant_id = dom.topic_id
        dominant_info = {
            "topic_id": dom.topic_id,
            "label": dom.label,
            "attention": dom.attention,
            "share": round(dom.attention / total, 6) if total else 0.0,
            "lane": lane_of(dom.category, dom.label),
        }

    eligible: list[tuple[EclipseCandidate, EclipseLedgerRow]] = []
    ledger: list[EclipseLedgerRow] = []

    for c in candidates:
        share = round(c.attention / total, 6) if total else 0.0
        cons = consequence_score(language_breadth=c.language_breadth,
                                 country_breadth=c.country_breadth,
                                 velocity=c.velocity, surprise=c.surprise)
        lane = lane_of(c.category, c.label)
        reasons: list[str] = []

        is_dominant = c.topic_id == dominant_id
        # Quality gates (labeled, never silently hidden).
        if c.is_junk:
            reasons.append("junk_quality_lane")
        if c.is_roundup:
            reasons.append("roundup_flag")
        low = (c.label or "").lower()
        if any(k in low for k in _ROUNDUP_LABEL_HINTS):
            reasons.append("roundup_label")
        if c.mean_cohesion is not None and float(c.mean_cohesion) < cohesion_floor:
            reasons.append(f"low_cohesion({float(c.mean_cohesion):.2f})")
        if lane != "general":
            reasons.append(f"labeled_lane:{lane}")
        gated = bool(reasons)
        # Consequence floor.
        below_floor = c.language_breadth < min_langs or c.country_breadth < min_countries
        if below_floor:
            reasons.append("below_consequence_floor")

        components = {
            "attention": c.attention,
            "attention_share": share,
            "consequence": cons,
            "language_breadth": c.language_breadth,
            "country_breadth": c.country_breadth,
            "velocity": round(c.velocity, 4),
            "surprise": round(c.surprise, 4),
            "lane": lane,
        }

        # Status precedence: suppressed (no eclipse) > dominant > labeled_out > below_floor > eligible.
        if not eclipse_on:
            reasons.append("no_eclipse_window")
            status: Any = "suppressed"
        elif is_dominant:
            reasons.insert(0, "dominant_event")
            status = "dominant"
        elif gated:
            status = "labeled_out"
        elif below_floor:
            status = "below_floor"
        else:
            status = "selected"  # provisional; trimmed to display_limit below

        row = EclipseLedgerRow(
            topic_id=c.topic_id, label=c.label, status=status,
            attention_share=share, consequence=cons, lane=lane,
            reason_codes=reasons, components=components,
        )
        ledger.append(row)
        if status == "selected":
            eligible.append((c, row))

    # Order eligible by LOWEST attention share first, cap at display_limit; the rest
    # are demoted to below_floor-style disclosure (kept in the ledger, reason-coded).
    eligible.sort(key=lambda pair: pair[0].attention)
    selected_ids: list[str] = []
    for i, (cand, row) in enumerate(eligible):
        if i < max(0, display_limit):
            row.reason_codes.append("under_radar_selected")
            selected_ids.append(cand.topic_id)
        else:
            row.status = "below_floor"
            row.reason_codes.append("under_radar_overflow")

    window = {
        "total_coverage": total,
        "candidate_count": len(candidates),
        "dominant_share": dominant_info.get("share", 0.0),
        "eclipse": eclipse_on,
    }
    method = {
        "contract": "attention-eclipse-v0",
        "consequence": "0.6*global_breadth_signal + 0.25*|kalman_velocity| + 0.15*kalman_surprise",
        "attention_proxy": "coverage-volume share of window (NOT audience eyeballs)",
        "consequence_floor": {"min_langs": min_langs, "min_countries": min_countries},
        "cohesion_floor": cohesion_floor,
        "ordering": "lowest attention share first, gated on eclipse window",
        "no_silent_filtering": True,
        "certifies_individual_story": False,
        "display_limit": display_limit,
    }
    return EclipseSelection(
        eclipse=eclipse_on,
        selected_ids=selected_ids,
        dominant=dominant_info,
        ledger=ledger,
        window=window,
        method=method,
    )


def assemble_eclipse(rows: list[dict], *, eclipse_top1: float = 0.20,
                     min_langs: int = 3, min_countries: int = 8,
                     cohesion_floor: float = 0.55, display_limit: int = 8) -> EclipseSelection:
    """DB rows -> concentration detector -> eclipse-gated under-radar selection.

    `rows` are per-topic dicts (topic_id, label, attention, langs, countries,
    velocity, surprise, category, crisis_relevant, mean_cohesion, is_junk,
    is_roundup). This is the one impure-input seam between the SQL and the pure
    logic; the router just runs the query and calls this.
    """
    conc = attention_concentration([int(r.get("attention", 0) or 0) for r in rows],
                                   eclipse_top1=eclipse_top1)
    candidates = [
        EclipseCandidate(
            topic_id=r["topic_id"], label=r.get("label") or r["topic_id"],
            attention=int(r.get("attention", 0) or 0),
            language_breadth=int(r.get("langs", 0) or 0),
            country_breadth=int(r.get("countries", 0) or 0),
            velocity=float(r.get("velocity") or 0.0),
            surprise=float(r.get("surprise") or 0.0),
            category=r.get("category"), crisis_relevant=r.get("crisis_relevant"),
            mean_cohesion=(None if r.get("mean_cohesion") is None else float(r["mean_cohesion"])),
            is_junk=bool(r.get("is_junk")), is_roundup=bool(r.get("is_roundup")),
        )
        for r in rows
    ]
    sel = select_under_radar(candidates, eclipse_on=conc["eclipse"],
                             min_langs=min_langs, min_countries=min_countries,
                             cohesion_floor=cohesion_floor, display_limit=display_limit)
    sel.window.update({
        "top1_share": conc["top1_share"],
        "top3_share": conc["top3_share"],
        "hhi": conc["hhi"],
        "eclipse_top1_threshold": eclipse_top1,
    })
    return sel
