"""Track C4a — the per-focus TIME-SERIES backend for the combined activity
timeline (spec §3). Frontend chart (C4b) is NOT built here.

Spec: docs/superpowers/specs/2026-07-21-time-axis-versioned-relationships.md
§1 (every focus gets a time-section), §3 (the combined chart's channels:
volume+sentiment / key-subject presence / voice-mix), §8 (MEASURE-FIRST —
"voice-mix per-time-bucket cost needs measuring"; "one shared [rarity]
function"). Sibling: `app/services/focus_timeline.py` (the pure math this
router calls) and `app/routers/edges.py` (Track C3, the same `ref`-
resolution + honest-empty-by-construction conventions, reused here).

One endpoint: `GET /api/v2/focus/{ref}/timeline`. `ref` resolves to a
THREAD (`dynamic-topic-<n>` / a bare `identity_key` / a served
`<slug>--<cc>` id), a COUNTRY (bare 2-letter ISO code), or falls back to a
PERSON name — the same three lenses `FocusContext.tsx`'s `FocusType`
already distinguishes; an explicit `focus_type` query param overrides the
auto-detect.

MEASURE-FIRST result (this track's session — see `focus_timeline.py`'s
module docstring for the full numbers): a THREAD focus is cheap on every
channel (topic_members bounds it to a few hundred rows); a COUNTRY focus's
volume+sentiment channel is cheap via the EXISTING `country_hourly_v2`
matview but its key-subject/voice-mix channels need a raw `signals_v2` scan
that costs seconds for a small country and 24-33s for a big one. Every
raw-scan channel therefore runs under a tight, independent
`statement_timeout` and degrades to an honest `reason` on cancellation — it
NEVER blocks the rest of the payload, and never a 500.

UPDATE 2026-07-27 — the PERSON focus is no longer in that cost class. All
three of its channels used to filter with
`EXISTS (SELECT 1 FROM unnest(persons) pp WHERE LOWER(pp) LIKE LOWER($1))`,
which is unindexable, so every channel seq-scanned the whole table and all
three degraded (`volume: degraded, key_subjects/voice_mix: unavailable,
reason: db_busy` — the state prod actually served). Migration 090 shipped a
GIN trigram index on `f_unaccent(lower(f_arr_text(persons)))`, so the
predicate is now spelled as that EXACT expression and the planner uses it:
Seq Scan cost 319,329 -> Bitmap Index Scan on
`idx_signals_v2_persons_text_trgm` cost 3,020 (168h window, prod EXPLAIN).
The degradation machinery below is unchanged and still real — it just no
longer fires on every person request.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import asyncpg
from fastapi import APIRouter, Query

from app import db
from app.core.search_normalization import normalize_search_text
from app.main_v2 import app
from app.services.edge_diff import parse_dynamic_topic_id, strip_focus_suffix
from app.services.focus_timeline import (
    DEFAULT_KEY_SUBJECTS_LIMIT,
    TIMELINE_CONTRACT,
    build_key_subject_series,
    detect_focus_kind,
    rebucket_hourly_to_day,
    voice_mix_bucket_from_counts,
)
from app.services.subjects import build_key_subjects
from app.services.thread_intelligence import topic_members_engine_version

router = APIRouter()
logger = logging.getLogger(__name__)

_CACHE_TTL_S = 300  # 5 min — matches the C3 diff endpoint's bounded-scan cadence

# Cheap paths (topic_members-bounded thread queries; the country_hourly_v2
# matview): generous — these are measured at ~100-300ms, this is slack, not
# an expectation of ever needing it.
_FAST_TIMEOUT_MS = 8000
# Raw signals_v2 scans (country key-subject + voice-mix channels; the person
# channels, which are index-backed since mig 090 but still land on the heap):
# bounded tight so a big-volume focus degrades fast instead of holding a
# connection open for 24-33s (measured). Slightly above voice_mix.py's 2500ms precedent
# — a medium country's candidate-pool query measured 2.47s, close to that
# floor; 3000ms gives it room without approaching the big-country cost class.
_SCAN_TIMEOUT_MS = 3000

_DB_BUSY_ERRORS = (
    asyncpg.exceptions.QueryCanceledError,
    asyncpg.exceptions.TooManyConnectionsError,
    asyncpg.exceptions.ConnectionDoesNotExistError,
    TimeoutError,
)

_CANDIDATE_POOL_LIMIT = 40  # matches /api/v2/focus's persons_rows bound


async def _cache_get(key: str) -> Optional[dict]:
    if not hasattr(app.state, "redis") or not app.state.redis:
        return None
    try:
        raw = await app.state.redis.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug("focus timeline cache read failed: %s", exc)
        return None


async def _cache_set(key: str, payload: dict, ttl: int) -> None:
    if not hasattr(app.state, "redis") or not app.state.redis:
        return
    try:
        await app.state.redis.setex(key, ttl, json.dumps(payload, default=str))
    except Exception as exc:
        logger.debug("focus timeline cache write failed: %s", exc)


async def _try_query(sql: str, params: list, timeout_ms: int) -> tuple[Optional[list], Optional[str]]:
    """Bounded-attempt-then-degrade (the `voice_mix.py` precedent), one
    channel at a time: a fresh connection per call so a canceled statement
    in one channel never poisons another's. Returns (rows, degraded_reason)
    — rows is None exactly when degraded_reason is set."""
    if db.pool is None:
        return None, "db_unavailable"
    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f"SET statement_timeout = {timeout_ms}")
            rows = await conn.fetch(sql, *params)
            return rows, None
    except _DB_BUSY_ERRORS as exc:
        logger.warning("focus timeline channel degraded (%s): %s",
                        type(exc).__name__, str(exc)[:160])
        return None, "db_busy"
    except Exception as exc:  # pragma: no cover - defensive I/O
        logger.warning("focus timeline channel failed: %s", str(exc)[:200])
        return None, "db_error"


def _trunc(granularity: str) -> str:
    return "day" if granularity == "day" else "hour"


# The ONE person predicate, spelled EXACTLY as migration 090 indexed the
# column (`f_unaccent(lower(f_arr_text(persons)))` — `f_arr_text` is the
# IMMUTABLE array_to_string wrapper 090 had to add because array_to_string
# itself is only STABLE and cannot appear in an index expression). Same
# spelling as `search.py`'s persons branch; a trigram GIN index only serves a
# predicate that matches its expression character for character, so this
# string is load-bearing — do not "simplify" it back to unnest/ILIKE.
_PERSON_MATCH_EXPR = "persons IS NOT NULL AND f_unaccent(lower(f_arr_text(persons))) LIKE"


_LIKE_SPECIALS = re.compile(r"([\\%_])")


def _person_like_needle(name: str) -> Optional[str]:
    """Fold a person ref into the LIKE needle the mig-090 index expects.

    The indexed side is accent-folded and lowercased, so the needle must be
    too or an accented ref silently matches nothing — the "Mbappé hole"
    `search.py` documents, re-measured here against prod (12h window): the
    raw `%mbappé%` matched 0 rows, the folded `%mbappe%` matched 8. So the
    fold is `normalize_search_text`, the SAME helper /search/thread builds
    its persons/themes patterns with — one normalizer, not two.

    ONE adjustment on top of it, measured. `normalize_search_text` squashes
    every non-alphanumeric run to a SPACE, but the stored person value keeps
    its punctuation — 808 of 68,643 distinct values in a 24h window are
    hyphenated ('abdel fattah al-sisi', 'aaron taylor-johnson'), i.e. mostly
    Arabic names. A literal-space needle MISSES all of them (measured on
    'abdel fattah al-sisi': old predicate 1 row, space needle 0, so a plain
    reuse here would have been a silent recall REGRESSION for that 1.2%).
    Substituting LIKE's single-character wildcard `_` for the space bridges
    both spellings at once and still takes the index (Bitmap Index Scan,
    cost 435). It is strictly wider than the old predicate, never narrower.

    Falls back to a plain lowercase when the fold comes back empty — that
    happens for a name written wholly in a non-Latin script, where the
    squash would erase everything and leave the needle '%%', silently
    matching the entire corpus. `f_unaccent` is the identity for those
    scripts, so lower() alone already matches the indexed expression. The
    fallback escapes LIKE metacharacters because, unlike the folded path, it
    has not been through a character filter.
    """
    folded = normalize_search_text(name)
    if folded:
        return "%" + folded.replace(" ", "_") + "%"
    fallback = _LIKE_SPECIALS.sub(r"\\\1", name.strip().lower())
    return f"%{fallback}%" if fallback else None


def _bucket_iso(row_bucket: Any) -> str:
    return row_bucket.isoformat() if hasattr(row_bucket, "isoformat") else str(row_bucket)


# ---------------------------------------------------------------- resolvers
_RESOLVE_THREAD_BY_ID_SQL = "SELECT id, identity_key, label FROM dynamic_topics WHERE id = $1"
_RESOLVE_THREAD_BY_KEY_SQL = "SELECT id, identity_key, label FROM dynamic_topics WHERE identity_key = $1"


async def _resolve_thread(ref: str) -> tuple[Optional[dict], Optional[str]]:
    """Resolve a thread ref to its `dynamic_topics` row. Same convention as
    `edges.py._resolve_focus` / `/api/v2/topic/{id}/relationship`: a raw
    numeric id, a bare `identity_key`, or a served `<slug>--<cc>` id (the
    `--cc` suffix stripped). An atlas category slug legitimately resolves to
    nothing — `topic_members.topic_id` only ever holds `dynamic-topic-<n>`
    strings (a living-story identity, never a category)."""
    base = strip_focus_suffix(ref)
    numeric_id = parse_dynamic_topic_id(base)
    sql = _RESOLVE_THREAD_BY_ID_SQL if numeric_id is not None else _RESOLVE_THREAD_BY_KEY_SQL
    param = numeric_id if numeric_id is not None else base
    rows, reason = await _try_query(sql, [param], _FAST_TIMEOUT_MS)
    if reason:
        return None, reason
    if not rows:
        return None, "topic_not_found"
    return dict(rows[0]), None


# ---------------------------------------------------------------- channel SQL
def _thread_ch1_sql(gran: str) -> str:
    return f"""
        SELECT date_trunc('{_trunc(gran)}', s.timestamp) AS bucket,
               COUNT(*)::bigint AS n, AVG(s.sentiment) AS avg_sent
        FROM topic_members tm
        JOIN signals_v2 s ON s.id = tm.signal_id
        WHERE tm.topic_id = $1 AND tm.role = 'evidence' AND tm.engine_version = $2
          AND tm.quarantined IS NOT TRUE
          AND tm.assigned_at >= NOW() - ($3::int * INTERVAL '1 hour')
        GROUP BY bucket ORDER BY bucket
    """


_THREAD_POOL_SQL = """
    SELECT p AS name, COUNT(*) AS signal_count,
           COUNT(DISTINCT s.source_name) AS distinct_outlets,
           COUNT(DISTINCT s.headline) AS distinct_headlines
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id, unnest(s.persons) p
    WHERE tm.topic_id = $1 AND tm.role = 'evidence' AND tm.engine_version = $2
      AND tm.quarantined IS NOT TRUE
      AND tm.assigned_at >= NOW() - ($3::int * INTERVAL '1 hour')
      AND p <> '' AND LENGTH(p) > 3
    GROUP BY p ORDER BY signal_count DESC LIMIT %d
""" % _CANDIDATE_POOL_LIMIT


def _thread_ch2_sql(gran: str) -> str:
    return f"""
        SELECT date_trunc('{_trunc(gran)}', s.timestamp) AS bucket, p AS name, COUNT(*)::bigint AS n
        FROM topic_members tm
        JOIN signals_v2 s ON s.id = tm.signal_id, unnest(s.persons) p
        WHERE tm.topic_id = $1 AND tm.role = 'evidence' AND tm.engine_version = $2
          AND tm.quarantined IS NOT TRUE
          AND tm.assigned_at >= NOW() - ($3::int * INTERVAL '1 hour')
          AND p = ANY($4::text[])
        GROUP BY bucket, p ORDER BY bucket
    """


def _thread_ch3_sql(gran: str) -> str:
    return f"""
        SELECT date_trunc('{_trunc(gran)}', s.timestamp) AS bucket,
               COALESCE(NULLIF(TRIM(s.source_lang), ''), '(null)') AS lang,
               COALESCE(NULLIF(TRIM(s.source_origin_country), ''), '(null)') AS origin,
               COUNT(*)::bigint AS n
        FROM topic_members tm
        JOIN signals_v2 s ON s.id = tm.signal_id
        WHERE tm.topic_id = $1 AND tm.role = 'evidence' AND tm.engine_version = $2
          AND tm.quarantined IS NOT TRUE
          AND tm.assigned_at >= NOW() - ($3::int * INTERVAL '1 hour')
        GROUP BY bucket, lang, origin ORDER BY bucket
    """


_COUNTRY_HOURLY_SQL = """
    SELECT hour AS bucket, signal_count AS n, avg_sentiment AS avg_sent
    FROM country_hourly_v2
    WHERE country_code = $1 AND hour >= NOW() - ($2::int * INTERVAL '1 hour')
    ORDER BY hour
"""


def _scoped_ch1_sql(gran: str, where_clause: str) -> str:
    return f"""
        SELECT date_trunc('{_trunc(gran)}', timestamp) AS bucket,
               COUNT(*)::bigint AS n, AVG(sentiment) AS avg_sent
        FROM signals_v2
        WHERE {where_clause}
        GROUP BY bucket ORDER BY bucket
    """


def _scoped_pool_sql(where_clause: str) -> str:
    return f"""
        SELECT p AS name, COUNT(*) AS signal_count,
               COUNT(DISTINCT source_name) AS distinct_outlets,
               COUNT(DISTINCT headline) AS distinct_headlines
        FROM signals_v2, unnest(persons) p
        WHERE {where_clause} AND p <> '' AND LENGTH(p) > 3
        GROUP BY p ORDER BY signal_count DESC LIMIT {_CANDIDATE_POOL_LIMIT}
    """


def _scoped_ch2_sql(gran: str, where_clause: str, names_param: str) -> str:
    return f"""
        SELECT date_trunc('{_trunc(gran)}', timestamp) AS bucket, p AS name, COUNT(*)::bigint AS n
        FROM signals_v2, unnest(persons) p
        WHERE {where_clause} AND p = ANY({names_param}::text[])
        GROUP BY bucket, p ORDER BY bucket
    """


def _scoped_ch3_sql(gran: str, where_clause: str) -> str:
    return f"""
        SELECT date_trunc('{_trunc(gran)}', timestamp) AS bucket,
               COALESCE(NULLIF(TRIM(source_lang), ''), '(null)') AS lang,
               COALESCE(NULLIF(TRIM(source_origin_country), ''), '(null)') AS origin,
               COUNT(*)::bigint AS n
        FROM signals_v2
        WHERE {where_clause}
        GROUP BY bucket, lang, origin ORDER BY bucket
    """


def _empty_payload(ref: str, focus_type: str, reason: str) -> dict:
    return {
        "contract": TIMELINE_CONTRACT,
        "ref": ref,
        "focus_type": focus_type,
        "buckets": [],
        "key_subjects_candidates": [],
        "channels": {"volume": "unavailable", "key_subjects": "unavailable", "voice_mix": "unavailable"},
        "reason": reason,
    }


@router.get("/api/v2/focus/{ref}/timeline")
async def focus_timeline(
    ref: str,
    focus_type: Optional[str] = Query(
        None, pattern="^(thread|country|person)$",
        description="Override the auto-detected focus kind"),
    hours: int = Query(168, ge=1, le=720),
    granularity: str = Query("day", pattern="^(hour|day)$"),
    key_subjects_limit: int = Query(DEFAULT_KEY_SUBJECTS_LIMIT, ge=1, le=12),
):
    """The per-focus activity timeline (spec §1/§3): volume+sentiment bars,
    rarity-normalized key-subject presence lines, and a per-bucket voice-mix
    band — for a thread, a country, or a person. See the module docstring
    for the measured cost model and the resulting honest-degradation design.
    """
    kind = focus_type or detect_focus_kind(ref)
    cache_key = f"focus:timeline:v0:{kind}:{ref}:{hours}:{granularity}:{key_subjects_limit}"
    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached

    if db.pool is None:
        payload = _empty_payload(ref, kind, "db_unavailable")
        return payload

    resolved: dict = {}
    where_clause = ""
    where_params: list = []
    # ch1_rows is ALWAYS normalized to plain dicts with a STRING "bucket" key
    # (already isoformat'd) before this point — the one place that has to
    # reconcile two shapes (the country_hourly_v2 matview's own Records vs.
    # the pure `rebucket_hourly_to_day` dicts) does it right here, once, so
    # every branch below (and the key-subject/voice-mix merges) can treat
    # "bucket" as a plain string unconditionally.
    ch1_rows: Optional[list[dict]] = None
    ch1_reason: Optional[str] = None

    if kind == "thread":
        topic_row, resolve_reason = await _resolve_thread(ref)
        if topic_row is None:
            payload = _empty_payload(ref, kind, resolve_reason or "topic_not_found")
            await _cache_set(cache_key, payload, _CACHE_TTL_S)
            return payload
        topic_id = f"dynamic-topic-{topic_row['id']}"
        engine_version = topic_members_engine_version()
        resolved = {"topic_id": topic_id, "identity_key": topic_row["identity_key"],
                    "label": topic_row["label"]}
        rows, ch1_reason = await _try_query(
            _thread_ch1_sql(granularity), [topic_id, engine_version, hours], _FAST_TIMEOUT_MS)
        if rows is not None:
            ch1_rows = [{"bucket": _bucket_iso(r["bucket"]), "n": int(r["n"] or 0),
                         "avg_sent": r["avg_sent"]} for r in rows]
    elif kind == "country":
        cc = ref.strip().upper()
        resolved = {"country_code": cc}
        where_clause = "country_code = $1 AND timestamp > NOW() - ($2::int * INTERVAL '1 hour')"
        where_params = [cc, hours]
        # Channel 1 prefers the EXISTING pre-aggregated matview (measured
        # ~100-300ms for ANY country, vs 2-33s for the raw scan below) — the
        # "reuse the existing timeline data source" win (spec discipline).
        hourly_rows, ch1_reason = await _try_query(
            _COUNTRY_HOURLY_SQL, [cc, hours], _FAST_TIMEOUT_MS)
        if hourly_rows is not None:
            hourly_dicts = [{"bucket": r["bucket"], "n": int(r["n"] or 0), "avg_sent": r["avg_sent"]}
                            for r in hourly_rows]
            if granularity == "day":
                ch1_rows = rebucket_hourly_to_day(hourly_dicts)
            else:
                ch1_rows = [{**d, "bucket": _bucket_iso(d["bucket"])} for d in hourly_dicts]
    else:  # person
        name = ref.strip()
        resolved = {"person": name}
        needle = _person_like_needle(name)
        if needle is None:
            # A ref that folds to nothing at all (punctuation/whitespace
            # only). Refusing is the honest answer: the alternative needle
            # is '%%', which would silently serve the whole corpus as if it
            # were this person's timeline.
            payload = _empty_payload(ref, kind, "person_not_matchable")
            await _cache_set(cache_key, payload, _CACHE_TTL_S)
            return payload
        where_clause = (f"{_PERSON_MATCH_EXPR} $1"
                        " AND timestamp > NOW() - ($2::int * INTERVAL '1 hour')")
        where_params = [needle, hours]
        # Index-backed since mig 090 (see the module docstring): a bitmap
        # heap scan of the matching rows, not a full-table scan. It stays on
        # the SCAN timeout, not the fast one, because the residual cost is
        # HEAP-bound, not index-bound. Measured on prod, 168h window:
        #   maduro  410 rows /    419 heap blocks ->  271ms  (serves live)
        #   trump 26,011 rows / 23,127 heap blocks -> 6.3-8.2s (degrades)
        # — the index scan itself is 12-204ms in BOTH cases; what costs is
        # fetching tens of thousands of heap pages. Note the window does not
        # bound that: `timestamp` is a post-fetch Filter on this plan, so a
        # shorter `hours` does NOT make a ubiquitous name cheaper. A needle
        # under 3 characters is also weak (no full trigram — '%xi%' plans a
        # 202K-row bitmap). Both cases degrade honestly, as before.
        rows, ch1_reason = await _try_query(
            _scoped_ch1_sql(granularity, where_clause), where_params, _SCAN_TIMEOUT_MS)
        if rows is not None:
            ch1_rows = [{"bucket": _bucket_iso(r["bucket"]), "n": int(r["n"] or 0),
                         "avg_sent": r["avg_sent"]} for r in rows]

    volume_channel_status = "live" if ch1_rows is not None else "degraded"
    bucket_keys: list[str] = []
    bucket_totals: dict[str, int] = {}
    buckets_out: dict[str, dict] = {}
    if ch1_rows:
        for r in ch1_rows:
            bucket_key = r["bucket"]
            n = int(r["n"] or 0)
            avg_sent = r["avg_sent"]
            bucket_keys.append(bucket_key)
            bucket_totals[bucket_key] = n
            buckets_out[bucket_key] = {
                "bucket_start": bucket_key,
                # ÷10 to the frontend ±1 sentiment convention (raw GDELT/nlp tone is
                # ~±10) — else the chart's diverging bars saturate all-up/all-down.
                "volume": {"count": n, "avg_sentiment": round(float(avg_sent) / 10.0, 4) if avg_sent is not None else None},
                "key_subjects": None,
                "voice_mix": None,
            }

    # ---------------------------------------------------------------- key subjects
    key_subjects_status = "unavailable"
    key_subjects_candidates: list[dict] = []
    if bucket_keys:
        if kind == "thread":
            pool_rows, pool_reason = await _try_query(
                _THREAD_POOL_SQL, [resolved["topic_id"], topic_members_engine_version(), hours],
                _FAST_TIMEOUT_MS)
        else:
            pool_rows, pool_reason = await _try_query(
                _scoped_pool_sql(where_clause), where_params, _SCAN_TIMEOUT_MS)

        if pool_rows is not None and not pool_rows:
            # The query ran fine and this focus genuinely mentions no
            # subjects (rare, e.g. a brand-new thread with 0 persons) —
            # honestly "live", not "unavailable"/"degraded". Every bucket
            # gets an explicit empty list (never left at the initial None)
            # so "live" always means "we have an answer for every bucket".
            key_subjects_status = "live"
            for b in bucket_keys:
                buckets_out[b]["key_subjects"] = []
        elif pool_rows is not None:
            pool = [dict(r) for r in pool_rows]
            df_max = max((int(r.get("signal_count") or 0) for r in pool), default=None)
            typed = build_key_subjects(pool, limit=key_subjects_limit)
            key_subjects_candidates = [
                {"name": s["name"], "type": s["type"], "unverified": s["unverified"],
                 "signal_count": s["signal_count"],
                 "rarity_weight": None}  # filled in below once df_max is known
                for s in typed
            ]
            names = [s["name"] for s in typed]
            if names:
                if kind == "thread":
                    ch2_rows, ch2_reason = await _try_query(
                        _thread_ch2_sql(granularity),
                        [resolved["topic_id"], topic_members_engine_version(), hours, names],
                        _FAST_TIMEOUT_MS)
                else:
                    ch2_rows, ch2_reason = await _try_query(
                        _scoped_ch2_sql(granularity, where_clause, f"${len(where_params) + 1}"),
                        where_params + [names], _SCAN_TIMEOUT_MS)

                if ch2_rows is not None:
                    bucket_mentions: dict[str, dict[str, int]] = {}
                    for r in ch2_rows:
                        b = _bucket_iso(r["bucket"])
                        bucket_mentions.setdefault(b, {})[r["name"]] = int(r["n"])
                    series = build_key_subject_series(
                        typed, bucket_keys, bucket_mentions, bucket_totals, df_max=df_max)
                    for b, entries in series.items():
                        if b in buckets_out:
                            buckets_out[b]["key_subjects"] = entries
                    key_subjects_status = "live"
                    # Reflect the resolved rarity_weight on the candidates list
                    # too (legend/color assignment on the frontend — spec §3
                    # "top-k curated ... stable color per entity").
                    weight_by_name = {
                        e["name"]: e["rarity_weight"]
                        for entries in series.values() for e in entries
                    }
                    for c in key_subjects_candidates:
                        c["rarity_weight"] = weight_by_name.get(c["name"])
                else:
                    key_subjects_status = "degraded"
            else:
                key_subjects_status = "live"  # candidates existed but none typed to a subject
                for b in bucket_keys:
                    buckets_out[b]["key_subjects"] = []
        else:
            # `_try_query` never returns rows=None without a reason.
            key_subjects_status = "degraded"

    # ---------------------------------------------------------------- voice mix
    voice_mix_status = "unavailable"
    if bucket_keys:
        if kind == "thread":
            ch3_rows, ch3_reason = await _try_query(
                _thread_ch3_sql(granularity),
                [resolved["topic_id"], topic_members_engine_version(), hours], _FAST_TIMEOUT_MS)
        else:
            ch3_rows, ch3_reason = await _try_query(
                _scoped_ch3_sql(granularity, where_clause), where_params, _SCAN_TIMEOUT_MS)

        if ch3_rows is not None:
            rows_for_voice = [
                {"bucket": _bucket_iso(r["bucket"]), "lang": r["lang"], "origin": r["origin"], "n": r["n"]}
                for r in ch3_rows
            ]
            per_bucket_voice = voice_mix_bucket_from_counts(rows_for_voice)
            for b, mix in per_bucket_voice.items():
                if b in buckets_out:
                    buckets_out[b]["voice_mix"] = mix
            voice_mix_status = "live"
        else:
            voice_mix_status = "degraded"

    payload = {
        "contract": TIMELINE_CONTRACT,
        "ref": ref,
        "focus_type": kind,
        "resolved": resolved,
        "hours": hours,
        "granularity": granularity,
        "buckets": [buckets_out[b] for b in bucket_keys],
        "key_subjects_candidates": key_subjects_candidates,
        "channels": {
            "volume": volume_channel_status,
            "key_subjects": key_subjects_status,
            "voice_mix": voice_mix_status,
        },
    }
    if ch1_reason and volume_channel_status == "degraded":
        payload["reason"] = ch1_reason
    elif not bucket_keys:
        payload["reason"] = "no_activity_in_window"

    await _cache_set(cache_key, payload, _CACHE_TTL_S)
    return payload
