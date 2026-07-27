"""Track C4a — the per-focus TIME-SERIES backend for the combined activity
timeline (C4b, the frontend chart, is NOT built here).

Spec: docs/superpowers/specs/2026-07-21-time-axis-versioned-relationships.md
§3 (the combined chart's channels: diverging volume/sentiment bars +
key-subject trend lines + voice-mix band) and §8 (open questions: Q2
"voice-mix per-time-bucket cost needs measuring", Q5 "the trend line must
measure the identical thing across every focus type — write it as one
shared function").

This module is the MATH — pure (stdlib only, no DB) — so the rarity-
normalized presence formula and the per-bucket voice aggregation are unit-
tested with zero I/O. The router (`app/routers/focus_timeline.py`) does the
I/O: it resolves a focus ref to a SQL scope, runs bounded/aggregate queries,
and calls the functions here to shape the response.

MEASURE-FIRST result (this track's session, timed against the live prod DB —
see the session report for the full numbers, summarized here because it
drives every design decision below):

  - THREAD focus (topic_members, typed evidence, engine-scoped): ~190-210ms
    per channel, any window, because topic_members bounds membership to a
    few hundred rows regardless of how old the topic is.
  - COUNTRY focus's volume+sentiment channel is cheap via the EXISTING
    `country_hourly_v2` matview (~200ms for a full retention-window read,
    any country) — this is the "reuse the existing timeline data source"
    win. But a RAW signals_v2 scan for the same country (needed for
    per-bucket key-subject/voice-mix breakdowns the matview doesn't carry)
    costs 24-33s for a top-volume country (US, ~155K signals in the current
    ~8-day hot retention) — confirmed via EXPLAIN ANALYZE: an index scan on
    (country_code, timestamp) still has to fetch ~155K heap pages
    (79K+ buffer misses) because the index doesn't cover sentiment/persons/
    lang/origin. The SAME query costs ~2.3s for a small country (CO, ~6.5K
    lifetime signals) — the cost scales with volume, not with the query
    being wrong.
  - PERSON focus had NO index over `signals_v2.persons` (no GIN on the
    array), so ANY unnest/ILIKE filter forced a full sequential scan of the
    whole table REGARDLESS of the requested window (Postgres must still
    visit every row to test the EXISTS(unnest...) predicate): 8-33s
    measured even at a 24h window. This was the clearest MEASURE-FIRST
    negative result of the track.
    SUPERSEDED 2026-07-27: migration 090 added a GIN trigram index on
    `f_unaccent(lower(f_arr_text(persons)))`, and the router now spells the
    person predicate as that exact expression, so all three person channels
    take a Bitmap Index Scan (prod EXPLAIN, 168h window: cost 319,329 ->
    3,020). The self-healing the paragraph below anticipated is what
    happened — no change was needed in this module.

Design consequence (honest degradation, never a blanket "this kind is
broken"): every DB-bound channel is wrapped by the router in ONE bounded-
attempt-then-degrade pattern (the `voice_mix.py` `_DB_BUSY_ERRORS`
precedent) with a tight per-block statement_timeout. A thread, person or
small-country focus mostly succeeds live today; a big-country focus mostly
degrades today — but the code never special-cases a focus kind as
permanently unavailable, which is exactly why the person kind self-healed
with a one-line predicate swap once the index landed. A degraded channel
reports its own `reason`; the rest of the payload still serves (never a
500, spec §7 honesty model).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from app.services.constellation_walk import (
    ACTOR_WEIGHT_BASE,
    ACTOR_WEIGHT_SPAN,
    norm_rarity,
)
from app.services.focus_filters import thread_focus_filter
from app.services.voice_mix import UNKNOWN_LANGS, shannon_norm

TIMELINE_CONTRACT = "focus-timeline-v0"

# Top-k curated (spec §3: "top-k curated" trend lines — all channels at once
# is noise). Matches the existing key_subjects panels' display cut
# (`build_key_subjects(..., limit=8)`); slightly tighter here (6) because a
# time-series chart has less room per line than a static list.
DEFAULT_KEY_SUBJECTS_LIMIT = 6

FocusKind = str  # "thread" | "country" | "person"


def detect_focus_kind(ref: str) -> FocusKind:
    """Auto-detect a focus ref's kind from its shape alone (no DB) — the
    same three lenses the product already distinguishes (FocusContext.tsx
    `FocusType`; this module only needs the three that carry a time series
    here): a thread id (`dynamic-topic-<n>` / an `identity_key` / a served
    `<slug>--<cc>` id — anything `thread_focus_filter` recognizes as a
    thread), a bare 2-letter ISO country code, or — the residual case —
    a person name. Callers may still override via an explicit `focus_type`
    query param; this is only the default when none is given."""
    bare = (ref or "").strip()
    if thread_focus_filter(bare) is not None:
        return "thread"
    if len(bare) == 2 and bare.isalpha():
        return "country"
    return "person"


# ---------------------------------------------------------------- rarity
def subject_rarity_weight(df: int, df_max: int) -> float:
    """The SAME rarity formula the walked constellation and the entity
    backbone already use (spec §7: "rarity everywhere ... the SAME formula
    everywhere"): `0.30 + 0.68*norm_rarity` (`constellation_walk.py`,
    #234/spec-2.4 LOCKED). A subject mentioned in every signal of the
    candidate pool (df == df_max, the most ubiquitous member of THIS
    focus's own actor set) still carries the 0.30 floor — presence is a
    continuous magnitude, not a gate, so it is never fully zeroed by
    ubiquity alone. A subject mentioned once (df == 1, df_max > 1) carries
    the ceiling ~0.98."""
    return round(ACTOR_WEIGHT_BASE + ACTOR_WEIGHT_SPAN * norm_rarity(df, df_max), 6)


def build_key_subject_series(
    subjects: Sequence[Mapping[str, Any]],
    bucket_keys: Sequence[str],
    bucket_mentions: Mapping[str, Mapping[str, int]],
    bucket_totals: Mapping[str, int],
    *,
    df_max: Optional[int] = None,
) -> dict[str, list[dict]]:
    """ONE shared function (spec §8 Q5): the rarity-normalized presence of a
    focus's key subjects, per time bucket — identical math whichever focus
    type called it (thread / country / person / theme all funnel through
    this). A globally famous actor barely present IN THIS FOCUS still
    reads low here, by construction: presence is `rarity_weight *
    bucket_share`, and bucket_share is already tiny for an actor who rarely
    appears in the bucket's signals; rarity_weight additionally thins an
    actor who dominates the FOCUS's own candidate pool (ubiquitous within
    this story, not just globally), so "Trump never pins every line high"
    even inside a Trump-adjacent story.

    ``subjects``: the `build_key_subjects()` output for the WHOLE focus
    window — each row's `signal_count` IS its document-frequency (df)
    *within this focus* (already syndication-deduped upstream by distinct
    headline/outlet — the #176 discipline `build_key_subjects` already
    applies). ``df_max`` defaults to the max signal_count across
    ``subjects``; a caller with a WIDER candidate pool than the displayed
    top-k (e.g. 40 candidates trimmed to a top-6 display) should pass the
    pool's true max explicitly so a subject just outside the display cut
    still sets the ceiling honestly — otherwise a displayed subject can look
    artificially MORE ubiquitous (floor rarity_weight) than it really is,
    simply because a more-common candidate existed in the wider pool but was
    trimmed away before this function ever saw it.

    presence(subject, bucket) = rarity_weight(subject) * (mentions of
    subject in this bucket / total focus volume in this bucket) — 0.0 when
    the bucket has no volume or the subject has no mention that bucket (a
    genuine "the line reads zero here", never a fabricated point; the
    frontend reads a trailing run of zeros as "the connection ended", spec
    §3 — this function only ever supplies the honest per-bucket magnitude).

    Returns bucket_key -> [{name, type, unverified, rarity_weight,
    mentions, presence}], subjects always in the SAME order (descending
    rarity_weight, then name) across every bucket, so a frontend's
    per-entity color assignment stays stable across the whole series.
    """
    if not subjects:
        return {b: [] for b in bucket_keys}

    dfs = [max(1, int(s.get("signal_count") or 0)) for s in subjects]
    resolved_df_max = int(df_max) if df_max is not None else max(dfs)

    weighted: list[dict] = []
    for s, df in zip(subjects, dfs):
        weighted.append({
            "name": s["name"],
            "type": s.get("type"),
            "unverified": bool(s.get("unverified", False)),
            "df": df,
            "rarity_weight": subject_rarity_weight(df, resolved_df_max),
        })
    weighted.sort(key=lambda s: (-s["rarity_weight"], s["name"]))

    out: dict[str, list[dict]] = {}
    for bucket in bucket_keys:
        total = int(bucket_totals.get(bucket) or 0)
        mentions = bucket_mentions.get(bucket) or {}
        row = []
        for s in weighted:
            n = int(mentions.get(s["name"]) or 0)
            share = (n / total) if total > 0 else 0.0
            presence = round(s["rarity_weight"] * share, 6)
            row.append({
                "name": s["name"],
                "type": s["type"],
                "unverified": s["unverified"],
                "rarity_weight": s["rarity_weight"],
                "mentions": n,
                "presence": presence,
            })
        out[bucket] = row
    return out


# ---------------------------------------------------------------- voice mix
def voice_mix_bucket_from_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict]:
    """Group (bucket, lang, origin, n) AGGREGATE count rows — never raw
    per-signal rows, see the module docstring's measured-cost section — into
    a per-bucket voice snapshot: top languages/origins + normalized entropy,
    using the SAME `shannon_norm` the country Voice Mix already uses (one
    formula, so this can never silently drift from `voice_mix.compute()`).

    Deliberately lighter than `voice_mix.compute()`: no state_media /
    distinct_sources counts (not measured per-bucket here — mindful, this
    is additive to the existing windowed Voice Mix, not a duplicate of it;
    a caller wanting the full diversity_score should still call the
    existing `/api/v2/voice-mix` or `/api/v2/topic/{id}/voice`).

    ``rows``: mappings with ``bucket`` (any hashable bucket key, typically
    an ISO timestamp string), ``lang``, ``origin``, ``n`` — the shape a
    `GROUP BY bucket, lang, origin` SQL query returns directly (no raw-row
    fetch needed at any focus scale, thread or country).
    """
    buckets: dict[str, dict[str, dict[str, int]]] = {}
    for r in rows:
        b = str(r["bucket"])
        slot = buckets.setdefault(b, {"lang": {}, "origin": {}})
        lang = (str(r.get("lang") or "")).strip().lower()
        origin = (str(r.get("origin") or "")).strip().upper()
        n = int(r.get("n") or 0)
        if lang and lang not in UNKNOWN_LANGS and lang != "(null)":
            slot["lang"][lang] = slot["lang"].get(lang, 0) + n
        if origin and origin not in ("(NULL)", ""):
            slot["origin"][origin] = slot["origin"].get(origin, 0) + n

    out: dict[str, dict] = {}
    for b, groups in buckets.items():
        langs = groups["lang"]
        origins = groups["origin"]
        out[b] = {
            "top_languages": [
                {"lang": l, "n": n}
                for l, n in sorted(langs.items(), key=lambda kv: -kv[1])[:6]
            ],
            "top_origins": [
                {"cc": c, "n": n}
                for c, n in sorted(origins.items(), key=lambda kv: -kv[1])[:6]
            ],
            "language_entropy_norm": round(shannon_norm(list(langs.values())), 4),
            "origin_entropy_norm": round(shannon_norm(list(origins.values())), 4),
        }
    return out


# ---------------------------------------------------------------- rebucketing
def _day_bucket_key(bucket: Any) -> str:
    """Truncate a (possibly tz-aware) datetime to midnight and format it the
    SAME way asyncpg's `date_trunc('day', ...)` result would isoformat —
    callers merge this bucket-key space with channels computed directly in
    SQL (the subject/voice-mix channels), so the two MUST agree byte-for-
    byte or the per-bucket merge silently drops rows."""
    if hasattr(bucket, "replace"):
        return bucket.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    return str(bucket)[:10]


def rebucket_hourly_to_day(rows: Sequence[Mapping[str, Any]]) -> list[dict]:
    """Re-bucket already-hourly (bucket, n, avg_sent) rows into DAY buckets
    with a volume-weighted sentiment average — pure Python over at most a
    few hundred hourly rows (the `country_hourly_v2` matview's per-request
    yield), never a second DB round trip. Used only when the caller asked
    for day granularity but the cheap pre-aggregated source is hourly."""
    days: dict[str, dict[str, float]] = {}
    for r in rows:
        day_key = _day_bucket_key(r["bucket"])
        slot = days.setdefault(day_key, {"n": 0.0, "sent_sum": 0.0})
        n = float(r.get("n") or 0)
        avg_sent = r.get("avg_sent")
        slot["n"] += n
        if avg_sent is not None:
            slot["sent_sum"] += float(avg_sent) * n
    return [
        {
            "bucket": day_key,
            "n": int(slot["n"]),
            "avg_sent": round(slot["sent_sum"] / slot["n"], 4) if slot["n"] > 0 else None,
        }
        for day_key, slot in sorted(days.items())
    ]
