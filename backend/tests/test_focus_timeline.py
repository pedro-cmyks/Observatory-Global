"""Track C4a — the per-focus activity-timeline backend: tests.

Spec: docs/superpowers/specs/2026-07-21-time-axis-versioned-relationships.md
§3 (the combined chart's channels) + §8 (Q5: "the trend line must measure
the identical thing across every focus type — write it as one shared
function").

The pure math (`app.services.focus_timeline`) is exercised directly with
synthetic rows — no DB, mirroring `test_edge_diff.py` / `test_thread_voice.py`'s
style for the sibling C1-C3 tracks. The router
(`app.routers.focus_timeline`) gets an honest-empty smoke pass (no DB) plus
one fake-conn integration test for the thread path, mirroring
`test_edge_diff.py`'s `_FakeConn`/`_FakePool` pattern.
"""
from __future__ import annotations

import asyncio

import app.main_v2  # noqa: F401 — initialize app + routers FIRST. `app.routers.
                     # focus_timeline` does `from app.main_v2 import app` (the
                     # geo.py/threads.py/edges.py cache-access idiom); importing
                     # the full app module here avoids the partial-module
                     # circular-import trap.
from app import db
from app.routers import focus_timeline as router_mod
from app.services.focus_timeline import (
    build_key_subject_series,
    detect_focus_kind,
    rebucket_hourly_to_day,
    subject_rarity_weight,
    voice_mix_bucket_from_counts,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _call(ref, *, focus_type=None, hours=168, granularity="day", key_subjects_limit=6):
    """Invoke the route function directly (test_edge_diff.py's style) — NOT
    through FastAPI's ASGI cycle, so every `Query(...)`-defaulted parameter
    MUST be passed explicitly here. Outside a real request, an omitted
    parameter resolves to the `Query` sentinel object itself (truthy, not its
    declared default), which silently breaks any code that inspects the
    value before a request ever reaches it — a real footgun this helper
    exists specifically to avoid reintroducing at every call site."""
    return router_mod.focus_timeline(
        ref=ref, focus_type=focus_type, hours=hours,
        granularity=granularity, key_subjects_limit=key_subjects_limit,
    )


# ============================================================== detect_focus_kind
class TestDetectFocusKind:
    def test_dynamic_topic_id_is_thread(self):
        assert detect_focus_kind("dynamic-topic-31") == "thread"

    def test_slug_with_country_suffix_is_thread(self):
        assert detect_focus_kind("some-story--US") == "thread"

    def test_bare_identity_key_is_thread(self):
        # thread_focus_filter treats any hyphenated value as a thread ref —
        # an identity_key (`dyn-2026-06-01T...-9`) qualifies.
        assert detect_focus_kind("dyn-2026-06-01T23:00:06-9") == "thread"

    def test_two_letter_code_is_country(self):
        assert detect_focus_kind("US") == "country"
        assert detect_focus_kind("co") == "country"

    def test_bare_name_is_person(self):
        assert detect_focus_kind("trump") == "person"
        assert detect_focus_kind("Volodymyr Zelenskyy") == "person"


# ============================================================== rarity weight
class TestSubjectRarityWeight:
    def test_most_ubiquitous_in_pool_hits_the_floor(self):
        # df == df_max: the most-mentioned actor in THIS focus's own pool —
        # never fully zeroed, presence is a magnitude not a gate.
        assert subject_rarity_weight(29, 29) == 0.30

    def test_rarest_actor_approaches_the_ceiling(self):
        w = subject_rarity_weight(1, 29)
        assert w > 0.9
        assert w <= 0.98

    def test_degenerate_pool_of_one_hits_the_ceiling_not_a_division_error(self):
        # df_max <= 1 (a candidate pool of exactly one subject, df=1):
        # norm_rarity's own guard treats this as maximally rare (1.0) rather
        # than dividing by zero — the weight sits at the ceiling.
        assert subject_rarity_weight(1, 1) == 0.98

    def test_monotonic_in_rarity(self):
        w_common = subject_rarity_weight(20, 20)
        w_rare = subject_rarity_weight(2, 20)
        w_rarest = subject_rarity_weight(1, 20)
        assert w_common < w_rare < w_rarest


# ============================================================== key-subject series
class TestBuildKeySubjectSeries:
    def _subjects(self):
        # A ubiquitous wire-story name (mentioned in every signal of the
        # pool) vs a rare, distinctive one — the exact "Trump never pins
        # every line high" case from the spec.
        return [
            {"name": "donald trump", "type": "person", "unverified": True, "signal_count": 29},
            {"name": "ali khamenei", "type": "person", "unverified": True, "signal_count": 2},
        ]

    def test_ubiquitous_subject_reads_lower_than_rare_one_at_equal_share(self):
        subjects = self._subjects()
        buckets = ["b1"]
        # Both subjects mentioned in ALL of the bucket's volume (share=1.0) —
        # isolates the rarity term: the ubiquitous one must still read lower.
        mentions = {"b1": {"donald trump": 10, "ali khamenei": 10}}
        totals = {"b1": 10}
        out = build_key_subject_series(subjects, buckets, mentions, totals)
        by_name = {e["name"]: e["presence"] for e in out["b1"]}
        assert by_name["donald trump"] < by_name["ali khamenei"]

    def test_presence_is_zero_when_bucket_has_no_mentions(self):
        subjects = self._subjects()
        buckets = ["b1", "b2"]
        mentions = {"b1": {"ali khamenei": 5}, "b2": {}}
        totals = {"b1": 10, "b2": 8}
        out = build_key_subject_series(subjects, buckets, mentions, totals)
        b2 = {e["name"]: e["presence"] for e in out["b2"]}
        assert b2["ali khamenei"] == 0.0
        assert b2["donald trump"] == 0.0

    def test_presence_is_zero_when_bucket_has_no_volume(self):
        subjects = self._subjects()
        out = build_key_subject_series(subjects, ["b1"], {"b1": {"ali khamenei": 3}}, {"b1": 0})
        assert all(e["presence"] == 0.0 for e in out["b1"])

    def test_empty_subjects_returns_empty_lists_per_bucket(self):
        out = build_key_subject_series([], ["b1", "b2"], {}, {"b1": 5, "b2": 5})
        assert out == {"b1": [], "b2": []}

    def test_subject_order_is_stable_across_buckets(self):
        subjects = self._subjects()
        buckets = ["b1", "b2"]
        mentions = {"b1": {"donald trump": 1}, "b2": {"ali khamenei": 1}}
        totals = {"b1": 10, "b2": 10}
        out = build_key_subject_series(subjects, buckets, mentions, totals)
        names_b1 = [e["name"] for e in out["b1"]]
        names_b2 = [e["name"] for e in out["b2"]]
        assert names_b1 == names_b2  # same order regardless of which had mentions

    def test_explicit_df_max_reflects_the_true_wider_pool_context(self):
        # In isolation (default df_max = its own count, 3) this subject looks
        # like the MOST ubiquitous thing in view -> the floor weight. Told the
        # TRUE wider pool had a candidate at 40, the same df=3 is genuinely
        # rarer by comparison -> a HIGHER weight, not lower. The whole point
        # of passing the true df_max is that trimming the display list must
        # never make a subject look artificially more common than it is.
        subjects = [{"name": "x", "type": "person", "unverified": True, "signal_count": 3}]
        out_default = build_key_subject_series(subjects, ["b1"], {"b1": {"x": 3}}, {"b1": 3})
        out_wide = build_key_subject_series(
            subjects, ["b1"], {"b1": {"x": 3}}, {"b1": 3}, df_max=40)
        assert out_default["b1"][0]["rarity_weight"] == 0.30  # df == df_max in isolation
        assert out_wide["b1"][0]["rarity_weight"] > out_default["b1"][0]["rarity_weight"]


# ============================================================== voice-mix bucketing
class TestVoiceMixBucketFromCounts:
    def test_groups_by_bucket_and_ranks_top_languages_and_origins(self):
        rows = [
            {"bucket": "b1", "lang": "en", "origin": "US", "n": 10},
            {"bucket": "b1", "lang": "es", "origin": "CO", "n": 4},
            {"bucket": "b2", "lang": "fr", "origin": "FR", "n": 2},
        ]
        out = voice_mix_bucket_from_counts(rows)
        assert set(out) == {"b1", "b2"}
        assert out["b1"]["top_languages"][0] == {"lang": "en", "n": 10}
        assert out["b1"]["top_origins"][0] == {"cc": "US", "n": 10}
        assert out["b2"]["top_languages"] == [{"lang": "fr", "n": 2}]

    def test_unknown_lang_and_null_origin_are_excluded_honestly(self):
        rows = [
            {"bucket": "b1", "lang": "xx", "origin": "(null)", "n": 5},
            {"bucket": "b1", "lang": "en", "origin": "US", "n": 3},
        ]
        out = voice_mix_bucket_from_counts(rows)
        assert out["b1"]["top_languages"] == [{"lang": "en", "n": 3}]
        assert out["b1"]["top_origins"] == [{"cc": "US", "n": 3}]

    def test_single_language_bucket_has_zero_entropy(self):
        rows = [{"bucket": "b1", "lang": "en", "origin": "US", "n": 9}]
        out = voice_mix_bucket_from_counts(rows)
        assert out["b1"]["language_entropy_norm"] == 0.0


# ============================================================== rebucketing
class TestRebucketHourlyToDay:
    def test_sums_volume_and_weights_sentiment_by_volume(self):
        from datetime import datetime, timezone
        rows = [
            {"bucket": datetime(2026, 7, 20, 3, tzinfo=timezone.utc), "n": 10, "avg_sent": 1.0},
            {"bucket": datetime(2026, 7, 20, 15, tzinfo=timezone.utc), "n": 30, "avg_sent": -1.0},
        ]
        out = rebucket_hourly_to_day(rows)
        assert len(out) == 1
        assert out[0]["n"] == 40
        # weighted: (10*1 + 30*-1) / 40 = -0.5
        assert out[0]["avg_sent"] == -0.5
        assert out[0]["bucket"].startswith("2026-07-20T00:00:00")

    def test_days_kept_separate_and_sorted(self):
        from datetime import datetime, timezone
        rows = [
            {"bucket": datetime(2026, 7, 21, 1, tzinfo=timezone.utc), "n": 1, "avg_sent": 0.0},
            {"bucket": datetime(2026, 7, 20, 1, tzinfo=timezone.utc), "n": 2, "avg_sent": 0.0},
        ]
        out = rebucket_hourly_to_day(rows)
        assert [r["bucket"][:10] for r in out] == ["2026-07-20", "2026-07-21"]

    def test_null_sentiment_rows_do_not_poison_the_average(self):
        from datetime import datetime, timezone
        rows = [
            {"bucket": datetime(2026, 7, 20, 1, tzinfo=timezone.utc), "n": 5, "avg_sent": None},
            {"bucket": datetime(2026, 7, 20, 2, tzinfo=timezone.utc), "n": 5, "avg_sent": 1.0},
        ]
        out = rebucket_hourly_to_day(rows)
        assert out[0]["n"] == 10
        assert out[0]["avg_sent"] == 0.5  # only the non-null row contributes to sent_sum


# ============================================================== router: honest-empty
class TestRouterHonestEmptyNoDb:
    def test_thread_ref_no_db(self, monkeypatch):
        monkeypatch.setattr(db, "pool", None, raising=False)
        out = _run(_call(ref="dynamic-topic-31"))
        assert out["contract"] == "focus-timeline-v0"
        assert out["focus_type"] == "thread"
        assert out["reason"] == "db_unavailable"
        assert out["buckets"] == []
        assert out["channels"] == {
            "volume": "unavailable", "key_subjects": "unavailable", "voice_mix": "unavailable",
        }

    def test_country_ref_no_db(self, monkeypatch):
        monkeypatch.setattr(db, "pool", None, raising=False)
        out = _run(_call(ref="US"))
        assert out["focus_type"] == "country"
        assert out["reason"] == "db_unavailable"

    def test_person_ref_no_db(self, monkeypatch):
        monkeypatch.setattr(db, "pool", None, raising=False)
        out = _run(_call(ref="trump"))
        assert out["focus_type"] == "person"
        assert out["reason"] == "db_unavailable"

    def test_explicit_focus_type_overrides_autodetect(self, monkeypatch):
        monkeypatch.setattr(db, "pool", None, raising=False)
        # "US" would auto-detect as country; force person.
        out = _run(_call(ref="US", focus_type="person"))
        assert out["focus_type"] == "person"


# ============================================================== router: fake-conn wiring
class _FakeConn:
    """SQL-dispatch fake mirroring `test_edge_diff.py`'s `_FakeConn` pattern —
    routes each `fetch`/`fetchrow` call by a distinguishing SQL substring so
    one fake stands in for the whole thread-focus query set."""

    def __init__(self, *, resolve_row=None, ch1_rows=None, pool_rows=None,
                 ch2_rows=None, ch3_rows=None):
        self.resolve_row = resolve_row
        self.ch1_rows = ch1_rows or []
        self.pool_rows = pool_rows or []
        self.ch2_rows = ch2_rows or []
        self.ch3_rows = ch3_rows or []

    async def execute(self, *a, **k):
        return None

    async def fetchrow(self, sql, *args):
        raise AssertionError(f"unexpected fetchrow: {sql[:80]!r}")

    async def fetch(self, sql, *args):
        # The router resolves a thread ref via `_try_query` -> `.fetch()`
        # uniformly (never `.fetchrow()`) so every channel shares the one
        # bounded-attempt-then-degrade helper; the resolve query returns a
        # single-row list (or empty when the ref doesn't exist).
        if "WHERE id = $1" in sql or "WHERE identity_key = $1" in sql:
            return [self.resolve_row] if self.resolve_row is not None else []
        if "GROUP BY p ORDER BY signal_count DESC" in sql:
            return self.pool_rows
        if "GROUP BY bucket, p ORDER BY bucket" in sql:
            return self.ch2_rows
        if "GROUP BY bucket, lang, origin" in sql:
            return self.ch3_rows
        if "GROUP BY bucket ORDER BY bucket" in sql:
            return self.ch1_rows
        raise AssertionError(f"unexpected fetch: {sql[:80]!r}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _FakePool:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    def acquire(self):
        return self._conn


def _dt(y, m, d, h=0):
    from datetime import datetime, timezone
    return datetime(y, m, d, h, tzinfo=timezone.utc)


class TestFocusTimelineThreadIntegration:
    def test_full_thread_timeline(self, monkeypatch):
        conn = _FakeConn(
            resolve_row={"id": 31, "identity_key": "dyn-31", "label": "Trump Vows Iran Strikes"},
            ch1_rows=[
                {"bucket": _dt(2026, 7, 17), "n": 5, "avg_sent": 1.2},
                {"bucket": _dt(2026, 7, 18), "n": 3, "avg_sent": -0.5},
            ],
            pool_rows=[
                {"name": "donald trump", "signal_count": 8,
                 "distinct_outlets": 4, "distinct_headlines": 5},
                {"name": "ali khamenei", "signal_count": 2,
                 "distinct_outlets": 2, "distinct_headlines": 2},
            ],
            ch2_rows=[
                {"bucket": _dt(2026, 7, 17), "name": "donald trump", "n": 5},
                {"bucket": _dt(2026, 7, 18), "name": "ali khamenei", "n": 2},
            ],
            ch3_rows=[
                {"bucket": _dt(2026, 7, 17), "lang": "en", "origin": "US", "n": 5},
                {"bucket": _dt(2026, 7, 18), "lang": "fa", "origin": "IR", "n": 3},
            ],
        )
        monkeypatch.setattr(db, "pool", _FakePool(conn), raising=False)

        out = _run(_call(ref="dynamic-topic-31"))

        assert out["contract"] == "focus-timeline-v0"
        assert out["focus_type"] == "thread"
        assert out["resolved"]["topic_id"] == "dynamic-topic-31"
        assert out["channels"] == {"volume": "live", "key_subjects": "live", "voice_mix": "live"}
        assert len(out["buckets"]) == 2
        assert "reason" not in out

        b0 = out["buckets"][0]
        assert b0["volume"]["count"] == 5
        assert b0["volume"]["avg_sentiment"] == 1.2
        subj_names = {e["name"] for e in b0["key_subjects"]}
        assert subj_names == {"donald trump", "ali khamenei"}
        # ubiquitous-in-pool (trump, df=8/8) reads a lower rarity_weight than
        # the rare one (khamenei, df=2/8) even though only trump has mentions
        # in this bucket — the rarity term is visible in the weight itself.
        by_name = {e["name"]: e for e in b0["key_subjects"]}
        assert by_name["donald trump"]["rarity_weight"] < by_name["ali khamenei"]["rarity_weight"]
        assert by_name["donald trump"]["presence"] > 0
        assert by_name["ali khamenei"]["presence"] == 0  # no mention bucket 1

        assert b0["voice_mix"]["top_languages"] == [{"lang": "en", "n": 5}]
        assert b0["voice_mix"]["top_origins"] == [{"cc": "US", "n": 5}]

        # key_subjects_candidates carries the resolved rarity_weight too.
        cand_by_name = {c["name"]: c for c in out["key_subjects_candidates"]}
        assert cand_by_name["donald trump"]["rarity_weight"] is not None

    def test_topic_not_found_is_honest_empty(self, monkeypatch):
        conn = _FakeConn(resolve_row=None)
        monkeypatch.setattr(db, "pool", _FakePool(conn), raising=False)
        out = _run(_call(ref="dynamic-topic-999999"))
        assert out["reason"] == "topic_not_found"
        assert out["buckets"] == []

    def test_no_activity_in_window_is_honest_empty(self, monkeypatch):
        conn = _FakeConn(
            resolve_row={"id": 31, "identity_key": "dyn-31", "label": "Quiet Topic"},
            ch1_rows=[],
        )
        monkeypatch.setattr(db, "pool", _FakePool(conn), raising=False)
        out = _run(_call(ref="dynamic-topic-31"))
        assert out["channels"]["volume"] == "live"
        assert out["buckets"] == []
        assert out["reason"] == "no_activity_in_window"

    def test_thread_with_no_subjects_mentioned_is_honestly_live_and_empty(self, monkeypatch):
        conn = _FakeConn(
            resolve_row={"id": 31, "identity_key": "dyn-31", "label": "Quiet Topic"},
            ch1_rows=[{"bucket": _dt(2026, 7, 17), "n": 5, "avg_sent": 0.1}],
            pool_rows=[],
        )
        monkeypatch.setattr(db, "pool", _FakePool(conn), raising=False)
        out = _run(_call(ref="dynamic-topic-31"))
        assert out["channels"]["key_subjects"] == "live"
        assert out["key_subjects_candidates"] == []
        assert out["buckets"][0]["key_subjects"] == []
