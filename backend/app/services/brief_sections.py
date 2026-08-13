"""The Brief's two measured sections: LO QUE SUBE and EL VACÍO (T3.2).

Spec: `docs/superpowers/specs/2026-08-12-puerta-y-carpetas-design.md` §3b.
Bars: `docs/research/brief-daily/2026-08-12-m0-measurement.md` §b.4 and §c.4 —
frozen here, unchanged from the measurement, with each witness pinned as a test
fixture. Prose is TEMPLATE over measured fields; this module makes ZERO LLM
calls and opens no network connection, so the nightly seal stays autonomous
(G-SELLO).

ONE function per section serves BOTH consumers — the live briefing payload
(`routers/briefing.py`) and the sealed edition (`services/daily_publication.py`)
— so the front page and the artifact can never drift apart.

Two honesty rules are structural here, not decorative:

1. **The 0.5 sentinel never becomes a fact.** `country_heat_v2.local_voice_ratio`
   answers a literal `0.5` when `known_origin_n < 50` (migration 017), i.e. "too
   few origin-attributable signals to judge" wearing the costume of a ratio —
   five of the measurement day's top-ten anomalies carried it. EL VACÍO
   therefore does NOT read that column at all: it counts ownership from
   `signals_v2` for the handful of pre-filtered candidates, so a country it
   cannot judge comes back `None` with a reason. (Same rule that killed
   silent-risk on 2026-07-22: press silence must be MEASURED, never assumed
   from absence.)
2. **The ledger is written whether or not anything clears.** M0 §b.1 measured
   that the joint attention/self-voice rate is NOT reconstructible backwards
   (7-day hot retention + the archive lane hard-coding `local_voice_ratio =
   None`). Forward logging of every daily candidate is the only path to a
   validated bar, so `brief_gap_candidates` is written on every computation and
   the bar is served flagged `provisional` until two weeks of it exist.
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

from app.core.iso_country_names import ISO_COUNTRY_NAMES
from app.services import ingest_basis, stat_phrases

logger = logging.getLogger(__name__)

RISING_CONTRACT = "brief-rising-v1"
GAP_CONTRACT = "brief-gap-v1"

_M0 = "docs/research/brief-daily/2026-08-12-m0-measurement.md"

# ── (c) LO QUE SUBE — the frozen acceleration bar (M0 §c.4) ─────────────────
# surprise >= 2.5 AND velocity > 0 AND volume >= 20, over ACTIVE top-level
# stories, reading the latest movement-kalman-v1 run. 15/15 measured days yield
# >= 2 items (median 10, min 2); ~p99 of the surprise distribution. `v > 0` is
# semantically load-bearing — a surprise spike on a COOLING story is not rising.
RISING_BAR: dict[str, Any] = {
    "surprise_min": 2.5,
    "velocity_min_exclusive": 0.0,
    "volume_min": 20,
    "source": "topic_movement (movement-kalman-v1), latest run",
    # The Kalman state runs on ln(1+n) over 3h buckets with dt in 6h units, so
    # velocity is NOT signals-per-hour and the prose must never say it is.
    "velocity_basis": "change in log-volume per 6 h step (Kalman state, not a forecast)",
    "volume_basis": "signals in the movement window (7 d)",
    "frozen_by": f"{_M0} §c.4",
    "confidence": "high",
}
RISING_MAX_ITEMS = 3
RISING_MIN_ITEMS = 2
RISING_RECEIPTS_PER_ITEM = 3

# ── (b) EL VACÍO — the provisional divergence bar (M0 §b.4) ─────────────────
# The anomaly side is measured (6/7 days clear >= 3.0x); the JOINT rate with
# the voice condition is BOUNDED, not measured. Lowest-confidence of the three
# bars by the measurement's own verdict, and it says so in the payload.
GAP_BAR: dict[str, Any] = {
    "multiplier_min": 3.0,
    "self_voice_max": 0.20,
    "volume_min": 20,
    "known_origin_min": 50,
    "baseline": "leave-one-out mean of the country's other retained days (>= 3)",
    "self_voice": "outlet OWNERSHIP: source_origin_country == subject country",
    # Not part of the frozen bar — a cost guard carried over from the M0 probe,
    # published here because a threshold nobody can see is a silent filter.
    "prefilter_max_daily_volume": None,   # filled at import from the env knob
    "frozen_by": f"{_M0} §b.4",
    "confidence": "provisional",
    "confidence_note": (
        "the joint rate was inferred, not measured — 7-day hot retention and a "
        "NULL archive column make it irretro-measurable; every daily candidate "
        "is logged so this bar can be re-derived from two weeks of real data"
    ),
}
GAP_BASELINE_MIN_DAYS = 3
GAP_RECEIPTS = 3
# Pre-filter before the (narrow, country-indexed) ownership count: only rows
# that could possibly clear the bar are ever asked about. Volume ceiling keeps
# the giants (US/GB/RU) out of the voice query — EL VACÍO is about a country
# surging above ITS OWN baseline, not about the loudest field.
GAP_PREFILTER_MAX_VOLUME = int(os.getenv("ATLAS_GAP_MAX_VOLUME", "3000"))
GAP_BAR["prefilter_max_daily_volume"] = GAP_PREFILTER_MAX_VOLUME


# ── shared helpers ─────────────────────────────────────────────────────────

def _f(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _i(value: Any) -> int:
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def country_name(code: str) -> str:
    code = (code or "").strip().upper()
    return ISO_COUNTRY_NAMES.get(code, code)


# ── (c) LO QUE SUBE ────────────────────────────────────────────────────────

def rising_why_now_measured(*, surprise: float, velocity: float,
                            volume: int) -> str:
    """The measured half of the why-now, as a template. No provider, no
    adjectives we cannot defend: `surprise` is a σ against the story's OWN
    Kalman baseline, `velocity` is the smoothed slope in log-volume per 6 h
    step."""
    return (
        f"surprise {surprise:.1f}σ over its own baseline, "
        f"velocity {velocity:+.2f} (log-volume per 6 h) "
        f"on {volume} signals in the movement window"
    )


def rising_why_now(*, surprise: float, velocity: float, volume: int) -> str:
    """The why-now: the plain reading FIRST, then the numbers that back it.

    X4 (2026-08-13). This template's previous form was one of the blind
    college's C5 witnesses — four of eight personas, the entire non-analyst
    range, could not parse "surprise 2.6σ over its own baseline, velocity +0.59
    (log-volume per 6 h)". The panel's structural note is why the fix is not
    cosmetic: a reader who cannot parse the grading system takes the honesty on
    faith, so the jargon disables the trust mechanism the receipts provide.

    Both halves ship. Deleting the numbers would trade the analyst and
    news-junkie personas — who named them as the differentiator — for the four
    who could not read them, and the plain clause alone is not checkable.
    """
    measured = rising_why_now_measured(surprise=surprise, velocity=velocity,
                                       volume=volume)
    plain = stat_phrases.rising_plain(surprise=surprise, velocity=velocity)
    return f"{plain} — {measured}." if plain else measured


def _unpresentable_reason(row: dict[str, Any]) -> str | None:
    """Why this story cannot be PRINTED, independent of whether it is rising.

    These sit on TOP of the frozen bar and never loosen it:

    - no label: nothing to headline (the seal takes the same position —
      `daily_edition.DailyCandidate.label` is nullable by design and unnamed
      candidates are skipped and counted);
    - junk / roundup: a service roundup that surges is volume, not news;
    - `label_status = 'too_broad'`: the Label Court's own verdict that NO single
      label can describe the topic — it is a fusion (migration 096). Printing
      "X is rising" under a name the court has ruled cannot name it is a false
      claim, and the receipts prove it: measured 2026-08-12, dt-4257
      "Government Initiatives and Infrastructure" cleared the bar carrying an
      Argentine supermarket launch and a drawing-class notice.

    `failed` / `partial` verdicts are NOT excluded — the project's standing
    stance for those is mark, don't hide (the "LABEL UNDER REVIEW" chip), so
    the verdict rides in the item for the renderer.
    """
    if not (row.get("label") or "").strip():
        return "unlabelled"
    if row.get("is_junk"):
        return "junk"
    if row.get("is_roundup"):
        return "roundup"
    if row.get("label_status") == "too_broad":
        return "label_court_too_broad"
    return None


def _clears_bar(row: dict[str, Any]) -> bool:
    return (
        _f(row.get("surprise")) >= RISING_BAR["surprise_min"]
        and _f(row.get("velocity")) > RISING_BAR["velocity_min_exclusive"]
        and _i(row.get("volume")) >= RISING_BAR["volume_min"]
    )


def count_rising_exclusions(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    """What the bar admitted and presentability then dropped, by reason.

    No silent filtering: a story removed after clearing a measured bar has to
    say why, in the payload, next to the section it did not appear in.
    """
    counts: dict[str, int] = {}
    for row in rows:
        if not _clears_bar(row):
            continue
        reason = _unpresentable_reason(row)
        if reason:
            counts[reason] = counts.get(reason, 0) + 1
    return counts


def select_rising(rows: Iterable[dict[str, Any]],
                  limit: int = RISING_MAX_ITEMS) -> list[dict[str, Any]]:
    """Apply the frozen bar and take the top `limit` by surprise."""
    picked: list[dict[str, Any]] = []
    for row in rows:
        if not _clears_bar(row) or _unpresentable_reason(row):
            continue
        surprise, velocity = _f(row.get("surprise")), _f(row.get("velocity"))
        volume = _i(row.get("volume"))
        label = (row.get("label") or "").strip()
        measured_at = row.get("window_end")
        picked.append({
            "thread_id": str(row.get("thread_id")),
            "label": label,
            "category": row.get("category"),
            # The court's verdict on THIS label rides along so the renderer can
            # stamp "LABEL UNDER REVIEW" instead of presenting a contested name
            # as settled (the chip CountryBrief/ThreadDetail already show).
            "label_status": row.get("label_status"),
            "surprise": round(surprise, 4),
            "velocity": round(velocity, 4),
            "volume": volume,
            "trend": row.get("trend"),
            "measured_at": measured_at.isoformat()
            if isinstance(measured_at, datetime) else measured_at,
            "why_now": rising_why_now(surprise=surprise, velocity=velocity,
                                      volume=volume),
            # X4: the two halves separately, so the Brief can set the plain
            # reading in reader type and the statistics as a stat line without
            # re-parsing a sentence client-side.
            "why_now_plain": stat_phrases.rising_plain(surprise=surprise,
                                                       velocity=velocity),
            "why_now_measured": rising_why_now_measured(
                surprise=surprise, velocity=velocity, volume=volume),
            "receipts": [],
        })
    picked.sort(key=lambda item: (-item["surprise"], item["thread_id"]))
    return picked[:limit]


def build_rising_payload(items: Sequence[dict[str, Any]], *,
                         candidates: int,
                         excluded: dict[str, int] | None = None,
                         reason: str | None = None,
                         measured_at: datetime | None = None) -> dict[str, Any]:
    """Serve what exists. Nothing above the bar IS the state, with its reason."""
    served = [
        {**item, "receipts": item.get("receipts") or [],
         "receipt_status": "ok" if item.get("receipts") else "unavailable",
         "receipt_basis": item.get("receipt_basis")}
        for item in items
    ]
    if not served:
        status = "unavailable" if reason else "empty"
        reason = reason or "no_story_cleared_the_bar"
    elif len(served) < RISING_MIN_ITEMS:
        status, reason = "partial", reason or "fewer_than_two_cleared_the_bar"
    else:
        status = "ok"
    return {
        "contract": RISING_CONTRACT,
        "bar": dict(RISING_BAR),
        "items": served,
        "candidates": candidates,
        # Cleared the bar, then could not be printed — and why.
        "excluded_after_bar": excluded or {},
        "status": status,
        "reason": reason,
        "measured_at": (measured_at or datetime.now(timezone.utc)).isoformat(),
    }


# ── (b) EL VACÍO ───────────────────────────────────────────────────────────

def resolve_self_voice(*, domestic_n: int,
                       known_origin_n: int) -> tuple[float | None, str, str | None]:
    """Self-voice from raw ownership counts — or an honest `None`.

    Returns `(ratio, status, reason)`. Below the attribution floor the answer is
    `(None, "unknown", "known_origin_below_50")`: the SAME floor migration 017
    uses, but reported as ignorance instead of collapsed into a 0.5 that reads
    like "half local".
    """
    known = _i(known_origin_n)
    if known < GAP_BAR["known_origin_min"]:
        return None, "unknown", "known_origin_below_50"
    return round(_i(domestic_n) / known, 4), "measured", None


def _score_gap_candidate(row: dict[str, Any]) -> dict[str, Any]:
    multiplier = _f(row.get("multiplier"))
    volume = _i(row.get("volume"))
    known_origin_n = _i(row.get("known_origin_n"))
    domestic_n = _i(row.get("domestic_n"))
    self_voice, self_voice_status, self_voice_reason = resolve_self_voice(
        domestic_n=domestic_n, known_origin_n=known_origin_n,
    )
    failed: list[str] = []
    if multiplier < GAP_BAR["multiplier_min"]:
        failed.append(f"multiplier_below_{GAP_BAR['multiplier_min']}")
    if volume < GAP_BAR["volume_min"]:
        failed.append(f"volume_below_{GAP_BAR['volume_min']}")
    if self_voice is None:
        failed.append(self_voice_reason or "known_origin_below_50")
    elif self_voice > GAP_BAR["self_voice_max"]:
        failed.append(f"self_voice_above_{GAP_BAR['self_voice_max']}")
    return {
        "country_code": str(row.get("country_code") or "").upper(),
        "volume": volume,
        "baseline": round(_f(row.get("baseline")), 2),
        "baseline_days": _i(row.get("baseline_days")),
        "multiplier": round(multiplier, 3),
        "domestic_n": domestic_n,
        "known_origin_n": known_origin_n,
        "total_n": _i(row.get("total_n")),
        "self_voice_ratio": self_voice,
        "self_voice_status": self_voice_status,
        "failed": failed,
        "cleared": not failed,
    }


def select_gap(rows: Iterable[dict[str, Any]]
               ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Score every candidate, return `(chosen, scored)`.

    `scored` carries the near-misses WITH their failure reasons — it is both the
    no-silent-filtering ledger the project requires of any ranking, and the
    substrate that re-derives this bar in two weeks.
    """
    scored = [_score_gap_candidate(row) for row in rows]
    scored.sort(key=lambda row: (-row["multiplier"], row["country_code"]))
    chosen = next((row for row in scored if row["cleared"]), None)
    return chosen, scored


def gap_prose(candidate: dict[str, Any]) -> str:
    """The finding as a sentence, entirely from measured fields.

    The base is IN the sentence (X1, 2026-08-13). This template's previous form
    said "of the 53 signals whose outlet home country is known, none came from
    Timor-Leste's own press" — every word true, and read by the blind panel as
    "that country's press said nothing". On the Colombia earthquake that reading
    was flatly false: El Tiempo, Caracol and El Colombiano were covering it
    massively; what Atlas had measured was a hole in its own feed set.

    So the qualification now arrives BEFORE the claim rather than as a footnote
    after it, and a zero carries its own refusal (`absence_caveat`) instead of
    leaving the silence inference to the reader.

    X4 (2026-08-13) then took the second half of the same sentence: "11.2× its
    own daily baseline" is the same unparseable class the blind college's C5
    named in the rising why-now. The ratio stays — it is what makes the claim
    checkable — behind the plain reading of it.
    """
    name = country_name(candidate["country_code"])
    known = candidate["known_origin_n"]
    domestic = candidate["domestic_n"]
    own = (
        f"none came from {name}'s own press"
        if domestic == 0
        else f"{domestic} of the {known} came from {name}'s own press"
    )
    closer = (
        ingest_basis.absence_caveat(name)
        if domestic == 0
        else ingest_basis.share_caveat()
    )
    surge = stat_phrases.times_phrase(candidate["multiplier"],
                                      of="its usual day")
    return (
        f"{ingest_basis.IN_INGEST}, {name} ran {surge} "
        f"({candidate['multiplier']:g}×) — {candidate['volume']} signals on a "
        f"day it usually runs about {candidate['baseline']:g}. Of the {known} "
        f"signals whose outlet home country is known, {own}. {closer}"
    )


def build_gap_payload(chosen: dict[str, Any] | None,
                      scored: Sequence[dict[str, Any]], *,
                      day: date,
                      day_complete: bool,
                      receipts: Sequence[dict[str, Any]] | None = None,
                      concentration: dict[str, Any] | None = None,
                      reason: str | None = None,
                      measured_at: datetime | None = None) -> dict[str, Any]:
    """`gap` for the payload. A day with no divergence over the bar SAYS SO."""
    payload: dict[str, Any] = {
        "contract": GAP_CONTRACT,
        "bar": dict(GAP_BAR),
        "confidence": GAP_BAR["confidence"],
        "confidence_note": GAP_BAR["confidence_note"],
        "day": day.isoformat(),
        # A partial UTC day under-states the multiplier against full-day
        # baselines — the bar therefore errs toward silence, never toward a
        # fabricated finding.
        "day_complete": day_complete,
        # The population this whole section is measured over — served as data so
        # the renderer's copy cannot drift from it (X1).
        "basis": ingest_basis.basis_field(),
        "candidates_scored": len(scored),
        "candidates_cleared": sum(1 for row in scored if row["cleared"]),
        "measured_at": (measured_at or datetime.now(timezone.utc)).isoformat(),
    }
    if chosen is None:
        payload.update({
            "status": "unavailable" if reason else "empty",
            "reason": reason or "no_country_cleared_the_bar",
            "country": None,
            "measured": None,
            "prose": None,
            "caveat": None,
            "receipts": [],
        })
        return payload
    payload.update({
        "status": "ok",
        "reason": None,
        "country": {"code": chosen["country_code"],
                    "name": country_name(chosen["country_code"])},
        "measured": {
            "volume": chosen["volume"],
            "baseline": chosen["baseline"],
            "baseline_days": chosen["baseline_days"],
            "multiplier": chosen["multiplier"],
            "self_voice_ratio": chosen["self_voice_ratio"],
            "self_voice_status": chosen["self_voice_status"],
            "known_origin_n": chosen["known_origin_n"],
            "domestic_n": chosen["domestic_n"],
            "unattributed_n": max(chosen["total_n"] - chosen["known_origin_n"], 0),
            "reprint_concentration": concentration,
        },
        "prose": gap_prose(chosen),
        # Measured, not editorialised: how much of the surge is one piece under
        # many mastheads. `None` when the day's coverage is not reprint-dominated.
        "caveat": reprint_caveat(concentration),
        "receipts": list(receipts or []),
    })
    return payload


def gap_ledger_rows(scored: Sequence[dict[str, Any]],
                    chosen: dict[str, Any] | None, *,
                    day: date,
                    source: str) -> list[tuple]:
    """Rows for `brief_gap_candidates`, in the INSERT's column order.

    Every scored candidate is logged, cleared or not — the near-misses are the
    half of the distribution that tells us whether 3.0× was the right bar.
    """
    chosen_cc = chosen["country_code"] if chosen else None
    return [
        (
            day, row["country_code"], row["multiplier"], row["volume"],
            row["self_voice_ratio"], row["self_voice_status"],
            row["known_origin_n"], row["domestic_n"],
            row["country_code"] == chosen_cc, source,
            ",".join(row["failed"]) or None,
            row["baseline"], row["baseline_days"],
            # Only ever measured for the served country (it costs a receipts
            # query), so NULL here means "not measured", not "not syndicated".
            row.get("top_reprint_share"),
        )
        for row in scored
    ]


# ── DB path (shared by the live briefing and the seal) ─────────────────────

RISING_MOVEMENT_SQL = """
WITH latest AS (
    SELECT DISTINCT ON (tm.topic_id)
           tm.topic_id, tm.window_end, tm.velocity, tm.surprise,
           tm.volume, tm.trend
    FROM topic_movement tm
    WHERE tm.engine_version = 'movement-kalman-v1'
      AND tm.window_end > $1::timestamptz - INTERVAL '2 days'
      AND tm.window_end <= $1::timestamptz
    ORDER BY tm.topic_id, tm.window_end DESC
)
SELECT ('dynamic-topic-' || dt.id::text) AS thread_id,
       dt.id                             AS topic_numeric_id,
       dt.label, dt.category, dt.is_junk, dt.is_roundup, dt.label_status,
       l.velocity::float                 AS velocity,
       l.surprise::float                 AS surprise,
       l.volume::int                     AS volume,
       l.trend, l.window_end
FROM latest l
JOIN dynamic_topics dt ON ('dynamic-topic-' || dt.id::text) = l.topic_id
WHERE dt.state = 'active'
  AND dt.parent_id IS NULL
  AND l.surprise >= $2::float
  AND l.velocity > $3::float
  AND l.volume >= $4::int
ORDER BY l.surprise DESC
LIMIT 40
"""

# Day-level country volume from the matview (M0 §b: wide signals_v2 aggregates
# are not viable on this pooler; the matview is).
GAP_VOLUME_SQL = """
SELECT date_trunc('day', hour)::date AS day,
       country_code                  AS country_code,
       SUM(signal_count)::int        AS volume
FROM country_hourly_v2
WHERE hour >= $1::timestamptz - INTERVAL '9 days'
  AND hour < $1::timestamptz
  AND country_code IS NOT NULL
GROUP BY 1, 2
"""

# Ownership counts for the pre-filtered candidates only — narrow and
# country-indexed (idx_signals_v2_country_time), measured ~11 ms per day.
# `bpchar[]` matters: signals_v2.country_code is CHAR(2), and a `text[]` cast
# loses the index.
GAP_VOICE_SQL = """
SELECT country_code AS country_code,
       COUNT(*) FILTER (WHERE source_origin_country IS NOT NULL)::int AS known_origin_n,
       COUNT(*) FILTER (WHERE source_origin_country = country_code)::int AS domestic_n,
       COUNT(*)::int AS total_n
FROM signals_v2
WHERE country_code = ANY($1::bpchar[])
  AND timestamp >= $2::timestamptz
  AND timestamp < $3::timestamptz
GROUP BY 1
"""

# Receipts for a country-scoped finding: one per outlet, most recent first,
# alive by construction (they ARE signals_v2 rows, never ids pointing at pruned
# signals — the day-5 starvation lesson). Deliberately over-fetched: one row per
# OUTLET is not one row per STORY, and the first live run of this section
# returned the same AU wire piece under three mastheads. `pick_receipts` folds
# reprints out of the slice.
GAP_RECEIPTS_SQL = """
SELECT id, headline, source_name, source_url, source_lang,
       source_origin_country, timestamp
FROM (
    SELECT DISTINCT ON (s.source_name)
           s.id, s.headline, s.source_name, s.source_url, s.source_lang,
           s.source_origin_country, s.timestamp
    FROM signals_v2 s
    WHERE s.country_code = $1::bpchar
      AND s.timestamp >= $2::timestamptz
      AND s.timestamp < $3::timestamptz
      AND s.headline IS NOT NULL
      AND s.source_name IS NOT NULL
    ORDER BY s.source_name, s.timestamp DESC
) one_per_outlet
ORDER BY timestamp DESC
LIMIT $4::int
"""
# Outlets scanned before folding reprints down to K. Measured 2026-08-12: the
# witness's own day carried ONE wire piece across 22 mastheads, which filled a
# 24-outlet scan almost entirely — the slice has to be wide enough to reach the
# other stories AND to measure how much of the surge is one piece.
GAP_RECEIPTS_SCAN = 60

# ENGINE-AGNOSTIC fallback for a rising story the edition lane cannot serve.
#
# Measured 2026-08-12 on both stories that cleared the bar: `_DAILY_EVIDENCE_SQL`
# returned ZERO receipts for each, while the same topics carried 187 and 40
# fresh `unified-v2` evidence members from that very day. The edition query pins
# `engine_version = 'v1-compat'`, whose projection for these topics was 2-3 days
# stale (19 and 3 rows, newest 08-10 / 08-09). This is the standing v1-compat ‖
# unified-v2 split (F4 is the cutover), and the project has already been bitten
# by it once in exactly this way — the 2026-07-01 relationship endpoint asserted
# "press-only" because it read one regime. The rule that came out of that:
# consumers UNION, they do not pick a lane.
#
# Same guarantees as the edition query: rows are joined THROUGH to signals_v2
# (so every id is alive — a stored sample id can outlive its signal, a join
# cannot), windowed, and ordered deterministically. It skips the umbrella
# resolution and the edition-cluster columns, which this section does not use.
RISING_RECEIPTS_FALLBACK_SQL = """
SELECT ('dynamic-topic-' || tm_topic.topic_numeric_id::text) AS topic_id,
       s.id, s.headline, s.source_name, s.source_url, s.source_lang,
       s.source_origin_country, s.country_code, s.timestamp
FROM (
    SELECT DISTINCT ON (tm.topic_id, tm.signal_id)
           tm.topic_id, tm.signal_id,
           split_part(tm.topic_id, 'dynamic-topic-', 2)::bigint AS topic_numeric_id
    FROM topic_members tm
    WHERE tm.topic_id = ANY($1::text[])
      AND tm.role = 'evidence'
      AND tm.quarantined IS NOT TRUE
    ORDER BY tm.topic_id, tm.signal_id, tm.assigned_at DESC
) tm_topic
JOIN signals_v2 s ON s.id = tm_topic.signal_id
WHERE s.timestamp >= $2::timestamptz - ($3::int * INTERVAL '1 hour')
  AND s.timestamp <= $2::timestamptz
  AND s.headline IS NOT NULL
ORDER BY tm_topic.topic_id, s.timestamp DESC, s.id DESC
"""

GAP_LEDGER_SQL = """
INSERT INTO brief_gap_candidates
    (day, country_code, multiplier, volume, self_voice_ratio, self_voice_status,
     known_origin_n, domestic_n, chosen, computed_by, failed_reasons,
     baseline, baseline_days, top_reprint_share)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
ON CONFLICT (day, country_code) DO UPDATE SET
    multiplier = EXCLUDED.multiplier,
    volume = EXCLUDED.volume,
    self_voice_ratio = EXCLUDED.self_voice_ratio,
    self_voice_status = EXCLUDED.self_voice_status,
    known_origin_n = EXCLUDED.known_origin_n,
    domestic_n = EXCLUDED.domestic_n,
    chosen = EXCLUDED.chosen,
    computed_by = EXCLUDED.computed_by,
    failed_reasons = EXCLUDED.failed_reasons,
    baseline = EXCLUDED.baseline,
    baseline_days = EXCLUDED.baseline_days,
    top_reprint_share = COALESCE(EXCLUDED.top_reprint_share,
                                 brief_gap_candidates.top_reprint_share),
    updated_at = now()
"""


def _serialize_receipt(row: Any) -> dict[str, Any]:
    get = row.get if isinstance(row, dict) else row.__getitem__
    try:
        timestamp = get("timestamp")
    except (KeyError, TypeError):
        timestamp = None
    return {
        "signal_id": get("id") if _has(row, "id") else None,
        "headline": get("headline") if _has(row, "headline") else None,
        "source": get("source_name") if _has(row, "source_name") else None,
        "url": get("source_url") if _has(row, "source_url") else None,
        "lang": get("source_lang") if _has(row, "source_lang") else None,
        "origin_country": get("source_origin_country")
        if _has(row, "source_origin_country") else None,
        "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime)
        else timestamp,
    }


def pick_receipts(rows: Iterable[Any],
                      k: int = GAP_RECEIPTS) -> list[dict[str, Any]]:
    """K receipts that are K different STORIES, not one wire piece K times.

    Measured on the first live run of this section: the day's three
    outlet-distinct Timor-Leste receipts were the SAME Australian wire piece
    under three mastheads. `thread_ranking._norm_headline` is the repaired
    reprint key (T3.1: script-safe fold + dash-masthead strip), so it folds
    exactly that family. A country whose surge really is one syndicated story
    then serves ONE receipt — which is the honest picture of that surge, not a
    shortfall.
    """
    from app.services.thread_ranking import _norm_headline

    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        receipt = _serialize_receipt(row)
        key = _norm_headline(receipt.get("headline") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        picked.append(receipt)
        if len(picked) >= k:
            break
    return picked


def measure_reprint_concentration(rows: Sequence[Any],
                                  scan_limit: int = GAP_RECEIPTS_SCAN
                                  ) -> dict[str, Any] | None:
    """How much of a country's day is ONE piece wearing many mastheads.

    Measured on the witness's own day (2026-08-12): 22 of the 24 Timor-Leste
    outlets in the slice ran the identical Australian wire headline. A blindspot
    finding that stayed silent about that would be selling syndication as
    coverage — the same mechanism T3.1 froze a lead veto against, seen from the
    other side. So it is MEASURED (with the same repaired reprint key) and
    DISCLOSED, not vetoed: the bar the measurement froze has no syndication arm
    and this build does not invent one.

    Denominator is OUTLETS in the scanned slice (the query is one row per
    outlet), so `scan_truncated` matters: at the cap the share is a floor.
    """
    from app.services.thread_ranking import _norm_headline

    keys = [
        key for row in rows
        if (key := _norm_headline(
            (_serialize_receipt(row).get("headline") or "")))
    ]
    if not keys:
        return None
    families: dict[str, int] = {}
    for key in keys:
        families[key] = families.get(key, 0) + 1
    top_key, top_n = max(families.items(), key=lambda item: (item[1], item[0]))
    return {
        "outlets_scanned": len(keys),
        "distinct_stories": len(families),
        "top_story_outlets": top_n,
        "share_of_scanned_outlets": round(top_n / len(keys), 3),
        "scan_truncated": len(rows) >= scan_limit,
        "basis": "reprint key = thread_ranking._norm_headline over one row per outlet",
    }


def reprint_caveat(concentration: dict[str, Any] | None) -> str | None:
    """The caveat sentence, only when the reprint family actually dominates."""
    if not concentration or concentration["top_story_outlets"] < 2:
        return None
    if concentration["share_of_scanned_outlets"] < 0.5:
        return None
    floor = " at least" if concentration["scan_truncated"] else ""
    return (
        f"Much of that is one piece under many mastheads:{floor} "
        f"{concentration['top_story_outlets']} of the "
        f"{concentration['outlets_scanned']} outlets in the sample ran the same "
        f"headline."
    )


def _has(row: Any, key: str) -> bool:
    try:
        row[key]
        return True
    except (KeyError, IndexError, TypeError):
        return False


async def fetch_rising(conn, *, hours: int = 24,
                       window_end: datetime | None = None,
                       receipts_by_thread: dict[str, list[dict[str, Any]]] | None = None,
                       timeout: float = 8.0) -> dict[str, Any]:
    """LO QUE SUBE for the payload. Never raises — a failed lane is a served
    reason, never a missing key and never a 500."""
    window_end = window_end or datetime.now(timezone.utc)
    try:
        rows = await conn.fetch(
            RISING_MOVEMENT_SQL, window_end,
            RISING_BAR["surprise_min"], RISING_BAR["velocity_min_exclusive"],
            RISING_BAR["volume_min"], timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 — degrade openly
        logger.warning("brief rising degraded: %s: %s", type(exc).__name__,
                       str(exc)[:200])
        return build_rising_payload([], candidates=0, reason="movement_unavailable")

    candidates = [dict(row) for row in rows]
    items = select_rising(candidates)
    if items:
        await _attach_rising_receipts(
            conn, items, hours=hours, window_end=window_end,
            receipts_by_thread=receipts_by_thread, timeout=timeout,
        )
    return build_rising_payload(items, candidates=len(candidates),
                                excluded=count_rising_exclusions(candidates),
                                measured_at=window_end)


async def _attach_rising_receipts(conn, items: list[dict[str, Any]], *,
                                  hours: int, window_end: datetime,
                                  receipts_by_thread: dict[str, list[dict[str, Any]]] | None,
                                  timeout: float) -> None:
    """Receipts through the SAME machinery the edition uses.

    `_DAILY_EVIDENCE_SQL` joins topic_members -> signals_v2 inside the edition
    window, so every id it returns is an ALIVE row (the day-5 starvation class —
    a stored sample_signal_id can outlive its signal; a join cannot) and the
    order is deterministic (timestamp DESC, id DESC), sliced not sampled.
    Imported lazily: `daily_publication` imports this module.
    """
    if receipts_by_thread:
        for item in items:
            frozen = receipts_by_thread.get(item["thread_id"])
            if frozen:
                item["receipts"] = pick_receipts(frozen, RISING_RECEIPTS_PER_ITEM)
                item["receipt_basis"] = "edition_receipts"
    missing = [item for item in items if not item["receipts"]]
    if not missing:
        return
    numeric_ids = [
        int(item["thread_id"].removeprefix("dynamic-topic-"))
        for item in missing
        if item["thread_id"].removeprefix("dynamic-topic-").isdigit()
    ]
    if not numeric_ids:
        return
    try:
        from app.services.daily_publication import _DAILY_EVIDENCE_SQL
        rows = await conn.fetch(_DAILY_EVIDENCE_SQL, numeric_ids, hours,
                                window_end, timeout=timeout)
        _fill_receipts(missing, rows, basis="edition_evidence_v1_compat")
    except Exception as exc:  # noqa: BLE001 — receipts are additive
        logger.warning("brief rising receipts degraded: %s: %s",
                       type(exc).__name__, str(exc)[:200])

    # UNION, don't pick a lane: whatever the v1-compat projection could not
    # serve gets one engine-agnostic pass. Reason-coded per item so a reader
    # (and the next measurement) can see which regime answered.
    still_missing = [item for item in missing if not item["receipts"]]
    if not still_missing:
        return
    try:
        rows = await conn.fetch(
            RISING_RECEIPTS_FALLBACK_SQL,
            [item["thread_id"] for item in still_missing], window_end, hours,
            timeout=timeout,
        )
        _fill_receipts(still_missing, rows, basis="unified_membership_fallback")
    except Exception as exc:  # noqa: BLE001 — receipts are additive
        logger.warning("brief rising receipts fallback degraded: %s: %s",
                       type(exc).__name__, str(exc)[:200])


def _fill_receipts(items: Sequence[dict[str, Any]], rows: Iterable[Any], *,
                   basis: str) -> None:
    by_thread: dict[str, list[Any]] = {}
    for row in rows:
        by_thread.setdefault(str(row["topic_id"]), []).append(row)
    for item in items:
        if item["receipts"]:
            continue
        picked = pick_receipts(by_thread.get(item["thread_id"], []),
                               RISING_RECEIPTS_PER_ITEM)
        if picked:
            item["receipts"] = picked
            item["receipt_basis"] = basis


def _leave_one_out_candidates(volume_rows: Iterable[Any],
                              day: date) -> list[dict[str, Any]]:
    """Per-country multiplier for `day` against the mean of its OTHER days."""
    by_country: dict[str, dict[date, int]] = {}
    for row in volume_rows:
        code = str(row["country_code"] or "").strip().upper()
        if not code:
            continue
        by_country.setdefault(code, {})[row["day"]] = _i(row["volume"])
    candidates: list[dict[str, Any]] = []
    for code, per_day in by_country.items():
        today = per_day.get(day)
        if today is None or today < GAP_BAR["volume_min"]:
            continue
        if today > GAP_PREFILTER_MAX_VOLUME:
            continue
        others = [n for other_day, n in per_day.items() if other_day != day]
        if len(others) < GAP_BASELINE_MIN_DAYS:
            continue
        baseline = sum(others) / len(others)
        if baseline <= 0:
            continue
        multiplier = today / baseline
        if multiplier < GAP_BAR["multiplier_min"]:
            continue
        candidates.append({
            "country_code": code, "volume": today,
            "baseline": baseline, "baseline_days": len(others),
            "multiplier": multiplier,
        })
    candidates.sort(key=lambda row: (-row["multiplier"], row["country_code"]))
    return candidates


async def fetch_gap(conn, *, window_end: datetime | None = None,
                    computed_by: str = "live",
                    timeout: float = 8.0,
                    write_ledger: bool = True) -> dict[str, Any]:
    """EL VACÍO for the payload, plus the daily ledger write.

    Three bounded queries, each guarded: the day-level matview aggregate, one
    narrow ownership count over the pre-filtered candidates, and the receipts
    of the chosen country. Any failure degrades to a served reason.
    """
    window_end = window_end or datetime.now(timezone.utc)
    day_start = window_end.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)
    day = day_start.date()
    day_complete = (window_end - day_start) >= timedelta(hours=24)
    try:
        volume_rows = await conn.fetch(GAP_VOLUME_SQL, day_start + timedelta(days=1),
                                       timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        logger.warning("brief gap degraded (volume): %s: %s", type(exc).__name__,
                       str(exc)[:200])
        return build_gap_payload(None, [], day=day, day_complete=day_complete,
                                 reason="anomaly_lane_unavailable",
                                 measured_at=window_end)
    prefiltered = _leave_one_out_candidates(volume_rows, day)
    if not prefiltered:
        return build_gap_payload(None, [], day=day, day_complete=day_complete,
                                 measured_at=window_end)
    try:
        voice_rows = await conn.fetch(
            GAP_VOICE_SQL, [row["country_code"] for row in prefiltered],
            day_start, day_start + timedelta(days=1), timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("brief gap degraded (voice): %s: %s", type(exc).__name__,
                       str(exc)[:200])
        # Without ownership counts the silence is UNMEASURED. Serving the
        # anomaly alone would be exactly the silent-risk error.
        return build_gap_payload(None, [], day=day, day_complete=day_complete,
                                 reason="voice_lane_unavailable",
                                 measured_at=window_end)
    voice_by_country = {
        str(row["country_code"]).strip().upper(): row for row in voice_rows
    }
    enriched = []
    for row in prefiltered:
        voice = voice_by_country.get(row["country_code"])
        enriched.append({
            **row,
            "known_origin_n": _i(voice["known_origin_n"]) if voice else 0,
            "domestic_n": _i(voice["domestic_n"]) if voice else 0,
            "total_n": _i(voice["total_n"]) if voice else 0,
        })
    chosen, scored = select_gap(enriched)

    receipts: list[dict[str, Any]] = []
    concentration: dict[str, Any] | None = None
    if chosen is not None:
        try:
            rows = await conn.fetch(GAP_RECEIPTS_SQL, chosen["country_code"],
                                    day_start, day_start + timedelta(days=1),
                                    GAP_RECEIPTS_SCAN, timeout=timeout)
            receipts = pick_receipts(rows)
            concentration = measure_reprint_concentration(rows)
            chosen["top_reprint_share"] = (
                concentration["share_of_scanned_outlets"] if concentration else None
            )
        except Exception as exc:  # noqa: BLE001 — receipts are additive
            logger.warning("brief gap receipts degraded: %s: %s",
                           type(exc).__name__, str(exc)[:200])
    if write_ledger:
        await log_gap_candidates(conn, scored, chosen, day=day,
                                 computed_by=computed_by, timeout=timeout)
    return build_gap_payload(chosen, scored, day=day, day_complete=day_complete,
                             receipts=receipts, concentration=concentration,
                             measured_at=window_end)


async def log_gap_candidates(conn, scored: Sequence[dict[str, Any]],
                             chosen: dict[str, Any] | None, *,
                             day: date, computed_by: str,
                             timeout: float = 5.0) -> int:
    """Write the day's candidates to `brief_gap_candidates` (best-effort).

    The bar cannot be validated retrospectively (M0 §b.1), so this write IS the
    instrument. It must never cost the reader a section: any failure is logged
    and the payload ships unchanged.
    """
    rows = gap_ledger_rows(scored, chosen, day=day, source=computed_by)
    if not rows:
        return 0
    try:
        await conn.executemany(GAP_LEDGER_SQL, rows, timeout=timeout)
        return len(rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("brief gap ledger write skipped: %s: %s",
                       type(exc).__name__, str(exc)[:200])
        return 0
