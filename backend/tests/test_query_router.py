"""`POST /api/v3/query` — the wire contract.

Fake-conn integration tests mirroring `test_edge_diff.py`'s
`_FakeConn`/`_FakePool` pattern (SQL-substring dispatch), so the whole handler
runs without a database.

What is frozen here is the half of the protocol that makes it trustworthy: a
verb that could not be measured must be structurally impossible to read as a
measured zero, every result must carry window + basis + population, and the
caps must announce themselves when they bite.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest

import app.main_v2  # noqa: F401 — initialize app + routers FIRST (the
                     # partial-module circular-import trap the sibling router
                     # tests document).
from app import db
from app.routers import query as query_router
from app.services import query_verbs as qv


def _run(coro):
    return asyncio.run(coro)


# NOW must track the real clock: the router computes the retention shortfall
# against datetime.now(), so a FROZEN date here is a time bomb — the original
# datetime(2026, 8, 14) passed until the real 14-day window slid past the
# fake OLDEST, then `fully_covered` flipped and the test failed by calendar
# (caught 2026-08-20, first run in the new repo home). Relative dates keep
# the fixture meaning what its comment says: "9 days of hot corpus".
NOW = datetime.now(timezone.utc)
OLDEST = NOW - timedelta(days=9)


class _FakeConn:
    """Routes each fetch by a distinguishing SQL substring."""

    def __init__(self, *, retention=OLDEST, member_rows=None, label_rows=None,
                 geo_rows=None, resolvability=None, counts=None,
                 landing_rows=None, sample_rows=None, voice_rows=None,
                 fail_on=None, fail_with=None):
        self.retention = retention
        self.member_rows = member_rows or []
        self.label_rows = label_rows or []
        self.geo_rows = geo_rows or []
        self.resolvability = resolvability
        self.counts = counts
        self.landing_rows = landing_rows or []
        self.sample_rows = sample_rows or []
        self.voice_rows = voice_rows or []
        self.fail_on = fail_on or ()
        self.fail_with = fail_with or asyncpg.exceptions.QueryCanceledError
        self.executed: list[str] = []

    async def execute(self, sql, *a):
        self.executed.append(sql)

    async def fetch(self, sql, *params):
        for marker in self.fail_on:
            if marker in sql:
                raise self.fail_with("boom")
        if "MIN(timestamp)" in sql:
            return [{"oldest": self.retention}]
        if "matched_members" in sql:
            return self.member_rows
        if "FROM dynamic_topics dt" in sql and "state = ANY" in sql:
            return self.label_rows
        if "GROUP BY 1, 2, 3" in sql:
            return self.geo_rows
        if "COUNT(s.id)::int AS resolvable" in sql:
            return [self.resolvability] if self.resolvability else []
        if "AS unassigned" in sql:
            return [self.counts] if self.counts else []
        if "mem.n" in sql:
            return self.landing_rows
        if "s.headline" in sql and "NOT EXISTS" in sql:
            return self.sample_rows
        if "source_lang, s.source_origin_country" in sql:
            return self.voice_rows
        return []


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self, *a, **kw):
        conn = self._conn

        class _Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *exc):
                return False

        return _Ctx()


@pytest.fixture
def fake_db(monkeypatch):
    def _install(conn):
        monkeypatch.setattr(db, "pool", _FakePool(conn))
        return conn
    return _install


# --------------------------------------------------------------- validation

class TestRequestValidation:
    def test_empty_ask_is_400_with_a_reason_code(self, fake_db):
        fake_db(_FakeConn())
        resp = _run(query_router.post_query({"ask": []}))
        assert resp.status_code == 400
        assert b"empty_ask" in resp.body

    def test_unknown_verb_names_the_verbs_that_do_exist(self, fake_db):
        fake_db(_FakeConn())
        resp = _run(query_router.post_query({"ask": [{"siblings": {}}]}))
        assert resp.status_code == 400
        assert b"unknown_verb" in resp.body

    def test_composition_reference_is_refused_not_silently_literal(self, fake_db):
        fake_db(_FakeConn())
        resp = _run(query_router.post_query(
            {"ask": [{"receipt_geography": {"topic_id": "$1"}}]}))
        assert resp.status_code == 400
        assert b"composition_not_supported" in resp.body

    def test_response_states_composition_is_unsupported(self, fake_db):
        fake_db(_FakeConn(counts={"matched": 0, "unassigned": 0}))
        out = _run(query_router.post_query(
            {"ask": [{"unclustered_signals": {"terms": ["golan"]}}]}))
        assert out["composition"]["supported"] is False


class TestNoPoolIsNeverAZero:
    def test_missing_pool_degrades_every_verb_with_a_named_reason(self, monkeypatch):
        monkeypatch.setattr(db, "pool", None)
        resp = _run(query_router.post_query(
            {"ask": [{"voice_mix": {"country": "CO"}}]}))
        assert resp.status_code == 200
        body = resp.body.decode()
        assert "no_pool" in body
        # The load-bearing absence: no `data` key anywhere.
        assert '"data"' not in body


# --------------------------------------------------- identities_covering

def _member_row(**kw):
    base = {"topic_id": "dynamic-topic-12927", "matched_members": 40,
            "dt_id": 12927, "label": "Colombia Declares Disaster After Deadly Earthquake",
            "state": "active", "label_status": "entailed", "is_umbrella": True,
            "parent_id": None, "first_seen": NOW - timedelta(days=44),
            "agg_n_signals": 2257}
    base.update(kw)
    return base


class TestIdentitiesCovering:
    def test_merges_both_bases_and_tags_how_each_matched(self, fake_db):
        fake_db(_FakeConn(
            member_rows=[_member_row()],
            label_rows=[{"dt_id": 12910, "label": "Colombia Earthquake Death Toll Rises to 132",
                         "state": "active", "label_status": "entailed",
                         "is_umbrella": True, "parent_id": None,
                         "first_seen": NOW, "agg_n_signals": 1277}],
        ))
        out = _run(query_router.post_query({"ask": [{"identities_covering": {
            "terms": ["earthquake"], "window_days": 7}}]}))
        data = out["results"][0]["data"]
        assert data["summary"]["identity_count"] == 2
        by_id = {i["topic_id"]: i for i in data["identities"]}
        assert by_id["dynamic-topic-12927"]["matched_by"] == ["members"]
        assert by_id["dynamic-topic-12910"]["matched_by"] == ["label"]

    def test_an_identity_found_by_both_bases_is_one_row_tagged_twice(self, fake_db):
        fake_db(_FakeConn(
            member_rows=[_member_row()],
            label_rows=[{"dt_id": 12927, "label": "Colombia Declares Disaster",
                         "state": "active", "label_status": "entailed",
                         "is_umbrella": True, "parent_id": None,
                         "first_seen": NOW, "agg_n_signals": 2257}],
        ))
        out = _run(query_router.post_query({"ask": [{"identities_covering": {
            "terms": ["earthquake"]}}]}))
        data = out["results"][0]["data"]
        assert data["summary"]["identity_count"] == 1
        assert data["identities"][0]["matched_by"] == ["members", "label"]

    def test_duplicate_labels_are_surfaced_as_the_dispersion_signal(self, fake_db):
        # Three of the nine Colombia identities said "Death Toll Rises...".
        dup = "Colombia Earthquake Death Toll Rises"
        fake_db(_FakeConn(label_rows=[
            {"dt_id": 248, "label": dup, "state": "active", "label_status": "entailed",
             "is_umbrella": False, "parent_id": None, "first_seen": NOW,
             "agg_n_signals": 778},
            {"dt_id": 1787, "label": dup, "state": "active", "label_status": "partial",
             "is_umbrella": False, "parent_id": None, "first_seen": NOW,
             "agg_n_signals": 284},
        ]))
        out = _run(query_router.post_query({"ask": [{"identities_covering": {
            "terms": ["earthquake"]}}]}))
        summary = out["results"][0]["data"]["summary"]
        assert summary["duplicate_labels"] == [dup.lower()]
        assert summary["court_failed"] == 0

    def test_kinds_are_distinguished_not_collapsed_into_one_list(self, fake_db):
        """An atlas slug is a CATEGORY, and a member row whose identity is gone
        is an ORPHAN. Both were found on the first live run (`armed-conflict-
        escalation` held 19 earthquake signals; `dynamic-topic-11581` held 28
        and has no `dynamic_topics` row). Calling either an "identity" repeats
        a settled confusion."""
        fake_db(_FakeConn(member_rows=[
            _member_row(),
            {"topic_id": "armed-conflict-escalation", "matched_members": 19,
             "dt_id": None, "label": None, "state": None, "label_status": None,
             "is_umbrella": None, "parent_id": None, "first_seen": None,
             "agg_n_signals": None},
            {"topic_id": "dynamic-topic-11581", "matched_members": 28,
             "dt_id": None, "label": None, "state": None, "label_status": None,
             "is_umbrella": None, "parent_id": None, "first_seen": None,
             "agg_n_signals": None},
        ]))
        out = _run(query_router.post_query({"ask": [{"identities_covering": {
            "terms": ["earthquake"]}}]}))
        data = out["results"][0]["data"]
        kinds = {i["topic_id"]: i["kind"] for i in data["identities"]}
        assert kinds["dynamic-topic-12927"] == qv.KIND_DYNAMIC
        assert kinds["armed-conflict-escalation"] == qv.KIND_ATLAS
        assert kinds["dynamic-topic-11581"] == qv.KIND_ORPHAN
        assert data["summary"]["by_kind"] == {
            qv.KIND_DYNAMIC: 1, qv.KIND_ATLAS: 1, qv.KIND_ORPHAN: 1}

    def test_a_label_lane_hit_proves_the_identity_exists_and_clears_orphan(self, fake_db):
        fake_db(_FakeConn(
            member_rows=[{"topic_id": "dynamic-topic-242", "matched_members": 5,
                          "dt_id": None, "label": None, "state": None,
                          "label_status": None, "is_umbrella": None,
                          "parent_id": None, "first_seen": None,
                          "agg_n_signals": None}],
            label_rows=[{"dt_id": 242, "label": "7.4-Magnitude Earthquake",
                         "state": "active", "label_status": "entailed",
                         "is_umbrella": False, "parent_id": None,
                         "first_seen": NOW, "agg_n_signals": 323}]))
        out = _run(query_router.post_query({"ask": [{"identities_covering": {
            "terms": ["earthquake"]}}]}))
        ident = out["results"][0]["data"]["identities"][0]
        assert ident["kind"] == qv.KIND_DYNAMIC
        assert ident["matched_by"] == ["members", "label"]

    def test_country_scope_declares_that_the_label_basis_cannot_honour_it(self, fake_db):
        fake_db(_FakeConn())
        out = _run(query_router.post_query({"ask": [{"identities_covering": {
            "terms": ["earthquake"], "country": "CO"}}]}))
        reasons = {c["reason"] for c in out["results"][0]["could_not_measure"]}
        assert "no_country_dimension" in reasons

    def test_rejected_terms_are_reported_not_dropped(self, fake_db):
        fake_db(_FakeConn())
        out = _run(query_router.post_query({"ask": [{"identities_covering": {
            "terms": ["earthquake", "co"]}}]}))
        assert out["results"][0]["rejected_terms"][0]["reason"] == "term_too_short"

    def test_all_terms_unusable_is_a_named_degradation_not_an_empty_list(self, fake_db):
        fake_db(_FakeConn())
        out = _run(query_router.post_query({"ask": [{"identities_covering": {
            "terms": ["co"]}}]}))
        result = out["results"][0]
        assert result["status"] == qv.STATUS_DEGRADED
        assert result["reason"] == "no_usable_terms"
        assert "data" not in result

    def test_both_lanes_down_marks_the_verb_degraded(self, fake_db):
        fake_db(_FakeConn(fail_on=("matched_members", "state = ANY")))
        out = _run(query_router.post_query({"ask": [{"identities_covering": {
            "terms": ["earthquake"]}}]}))
        result = out["results"][0]
        assert result["status"] == qv.STATUS_DEGRADED
        assert result["reason"] == "db_busy"

    def test_one_lane_down_still_serves_the_other_and_says_which_failed(self, fake_db):
        fake_db(_FakeConn(fail_on=("matched_members",), label_rows=[
            {"dt_id": 242, "label": "7.4-Magnitude Earthquake Kills Dozens in Colombia",
             "state": "active", "label_status": "entailed", "is_umbrella": False,
             "parent_id": None, "first_seen": NOW, "agg_n_signals": 323}]))
        out = _run(query_router.post_query({"ask": [{"identities_covering": {
            "terms": ["earthquake"]}}]}))
        result = out["results"][0]
        assert result["status"] == qv.STATUS_LIVE
        assert result["data"]["summary"]["identity_count"] == 1
        assert result["lane_status"]["identities_members"] == "degraded"
        assert any(c["reason"] == "db_busy" for c in result["could_not_measure"])


# ----------------------------------------------------- receipt_geography

class TestReceiptGeography:
    def _conn(self, **kw):
        defaults = {
            "geo_rows": [
                {"country_code": "VE", "source_lang": "xx", "origin": "(unknown)", "n": 22},
                {"country_code": "DE", "source_lang": "de", "origin": "DE", "n": 18},
                {"country_code": "DE", "source_lang": "xx", "origin": "(unknown)", "n": 6},
                {"country_code": "VE", "source_lang": "es", "origin": "VE", "n": 2},
            ],
            "resolvability": {"members": 48, "resolvable": 48},
        }
        defaults.update(kw)
        return _FakeConn(**defaults)

    def test_serves_three_labelled_dimensions(self, fake_db):
        fake_db(self._conn())
        out = _run(query_router.post_query({"ask": [{"receipt_geography": {
            "topic_id": "dt-12927"}}]}))
        data = out["results"][0]["data"]
        assert data["subject_countries"][0] == {"cc": "VE", "n": 24, "pct": 0.5}
        assert data["languages"][0]["lang"] == "xx"
        # subject country != outlet origin: conflating them is the ingest_basis error.
        assert "what the story is ABOUT" in data["dimensions"]["subject_countries"]
        assert "where the OUTLET is based" in data["dimensions"]["outlet_origins"]

    def test_pruned_members_are_reported_as_unmeasurable_not_absent(self, fake_db):
        fake_db(self._conn(resolvability={"members": 83, "resolvable": 48}))
        out = _run(query_router.post_query({"ask": [{"receipt_geography": {
            "topic_id": "dt-12927"}}]}))
        result = out["results"][0]
        assert result["data"]["members_pruned"] == 35
        assert any(c["reason"] == "receipts_pruned" for c in result["could_not_measure"])

    def test_topic_ref_accepts_all_three_spellings(self, fake_db):
        for ref in ("12927", "dt-12927", "dynamic-topic-12927"):
            fake_db(self._conn())
            out = _run(query_router.post_query({"ask": [{"receipt_geography": {
                "topic_id": ref}}]}))
            assert out["results"][0]["population"]["topic_id"] == "dynamic-topic-12927"

    def test_missing_topic_id_is_a_named_degradation(self, fake_db):
        fake_db(self._conn())
        out = _run(query_router.post_query({"ask": [{"receipt_geography": {}}]}))
        assert out["results"][0]["reason"] == "missing_topic_id"

    def test_degraded_lane_carries_no_data_key(self, fake_db):
        fake_db(self._conn(fail_on=("GROUP BY 1, 2, 3",)))
        result = _run(query_router.post_query({"ask": [{"receipt_geography": {
            "topic_id": "dt-1"}}]}))["results"][0]
        assert result["status"] == qv.STATUS_DEGRADED
        assert "data" not in result
        assert result["reason"] == "db_busy"


# --------------------------------------------------- unclustered_signals

class TestUnclusteredSignals:
    def _conn(self, **kw):
        defaults = {
            "counts": {"matched": 72, "unassigned": 60},
            "landing_rows": [
                {"topic_id": "dynamic-topic-3967", "n": 2, "label": "Earthquakes in Mexico",
                 "state": "active", "label_status": "failed"},
                {"topic_id": "dynamic-topic-9", "n": 1, "label": "Merz Rentenreform Kritik",
                 "state": "active", "label_status": "entailed"},
            ],
            "sample_rows": [{"id": 1, "headline": "De la Espriella se posesiona",
                             "source_name": "pulzo.com", "country_code": "CO",
                             "source_lang": "es", "timestamp": NOW}],
        }
        defaults.update(kw)
        return _FakeConn(**defaults)

    def test_counts_the_signals_that_became_nothing(self, fake_db):
        fake_db(self._conn())
        data = _run(query_router.post_query({"ask": [{"unclustered_signals": {
            "terms": ["espriella"], "window_hours": 24}}]}))["results"][0]["data"]
        assert data["matched_signals"] == 72
        assert data["unassigned_signals"] == 60
        assert data["assigned_signals"] == 12
        assert data["unassigned_share"] == pytest.approx(0.8333, abs=1e-4)

    def test_reports_where_the_assigned_ones_landed(self, fake_db):
        fake_db(self._conn())
        data = _run(query_router.post_query({"ask": [{"unclustered_signals": {
            "terms": ["espriella"]}}]}))["results"][0]["data"]
        labels = [r["label"] for r in data["landed_in"]]
        assert "Merz Rentenreform Kritik" in labels

    def test_scan_cap_is_declared_when_the_counts_are_only_a_floor(self, fake_db):
        fake_db(self._conn(counts={"matched": qv.SCAN_CAP, "unassigned": 10}))
        result = _run(query_router.post_query({"ask": [{"unclustered_signals": {
            "terms": ["the"]}}]}))["results"][0]
        assert any(c["reason"] == "scan_cap_reached" for c in result["could_not_measure"])

    def test_zero_matches_is_a_measured_zero_and_says_so(self, fake_db):
        fake_db(self._conn(counts={"matched": 0, "unassigned": 0},
                           landing_rows=[], sample_rows=[]))
        result = _run(query_router.post_query({"ask": [{"unclustered_signals": {
            "terms": ["zzzznothing"]}}]}))["results"][0]
        assert result["status"] == qv.STATUS_LIVE
        assert result["data"]["matched_signals"] == 0
        assert result["data"]["unassigned_share"] is None

    def test_count_lane_failure_degrades_the_whole_verb(self, fake_db):
        fake_db(self._conn(fail_on=("AS unassigned",)))
        result = _run(query_router.post_query({"ask": [{"unclustered_signals": {
            "terms": ["espriella"]}}]}))["results"][0]
        assert result["status"] == qv.STATUS_DEGRADED
        assert "data" not in result


# ------------------------------------------------------------- voice_mix

class TestVoiceMix:
    def test_topic_scope_reuses_the_served_thread_voice_aggregation(self, fake_db):
        fake_db(_FakeConn(voice_rows=[
            {"source_lang": "ru", "source_origin_country": "BY", "country_code": "CO"},
            {"source_lang": "ru", "source_origin_country": "BY", "country_code": "CO"},
        ]))
        result = _run(query_router.post_query({"ask": [{"voice_mix": {
            "topic_id": "dt-12910"}}]}))["results"][0]
        assert result["data"]["available"] is True
        assert result["data"]["origins"] == [{"cc": "BY", "n": 2}]
        assert result["data"]["subject_country"] == "CO"
        # Same function the product surface uses — they cannot drift.
        assert "/api/v2/topic/{id}/voice" in result["population"]["served_by"]

    def test_no_members_is_available_false_with_a_reason(self, fake_db):
        fake_db(_FakeConn(voice_rows=[]))
        result = _run(query_router.post_query({"ask": [{"voice_mix": {
            "topic_id": "dt-1"}}]}))["results"][0]
        assert result["data"]["available"] is False
        assert any(c["reason"] == "no_members_in_window"
                   for c in result["could_not_measure"])

    def test_country_scope_runs_after_the_pool_connection_is_released(self, fake_db):
        """`voice_mix {country}` reuses the served endpoint function, which
        acquires its OWN connection. Running it while the handler holds one is
        self-inflicted contention — measured 2026-08-14: the lane degraded
        inside the protocol while the identical direct call succeeded in 2.1s
        against its own 2.5s budget. So it must be deferred."""
        assert query_router._defers_to_own_connection("voice_mix", {"country": "CO"})
        assert not query_router._defers_to_own_connection(
            "voice_mix", {"topic_id": "dt-1"})
        assert not query_router._defers_to_own_connection(
            "receipt_geography", {"topic_id": "dt-1"})

    def test_deferred_verb_keeps_its_position_in_the_results(self, fake_db, monkeypatch):
        fake_db(_FakeConn(geo_rows=[{"country_code": "CO", "source_lang": "es",
                                     "origin": "CO", "n": 3}],
                          resolvability={"members": 3, "resolvable": 3,
                                         "distinct_sources": 3}))

        async def _fake_country_mix(hours=168, country=None):
            return {"total_signals": 7, "distinct_sources": 2}

        monkeypatch.setattr("app.routers.voice_mix.get_voice_mix", _fake_country_mix)
        out = _run(query_router.post_query({"ask": [
            {"voice_mix": {"country": "CO"}},
            {"receipt_geography": {"topic_id": "dt-242"}},
        ]}))
        # Asked country-first; the deferred verb must still come back first.
        assert [r["verb"] for r in out["results"]] == ["voice_mix", "receipt_geography"]
        assert out["results"][0]["data"]["total_signals"] == 7

    def test_scope_must_be_exactly_one_of_topic_or_country(self, fake_db):
        fake_db(_FakeConn())
        assert _run(query_router.post_query({"ask": [{"voice_mix": {}}]})
                    )["results"][0]["reason"] == "missing_scope"
        assert _run(query_router.post_query({"ask": [{"voice_mix": {
            "topic_id": "dt-1", "country": "CO"}}]})
        )["results"][0]["reason"] == "ambiguous_scope"


# ------------------------------------------------------------- the basics

class TestEveryResultCarriesItsBase:
    def test_window_basis_and_population_ride_on_every_live_result(self, fake_db):
        fake_db(_FakeConn(counts={"matched": 1, "unassigned": 1}))
        result = _run(query_router.post_query({"ask": [{"unclustered_signals": {
            "terms": ["espriella"], "window_hours": 24}}]}))["results"][0]
        assert result["window"]["requested_hours"] == 24
        assert result["basis"]["measured_over"] == "atlas_ingest"
        assert result["population"]["assignment_over"]["role"] == "evidence"
        assert result["could_not_measure"] == [] or isinstance(
            result["could_not_measure"], list)

    def test_window_declares_the_retention_shortfall(self, fake_db):
        # 14 days requested, 9 days of hot corpus -> the gap is stated.
        fake_db(_FakeConn(counts={"matched": 0, "unassigned": 0}))
        result = _run(query_router.post_query({"ask": [{"unclustered_signals": {
            "terms": ["espriella"], "window_days": 14}}]}))["results"][0]
        assert result["window"]["fully_covered"] is False
        assert result["window"]["shortfall_hours"] > 0

    def test_multiple_independent_verbs_run_in_one_request(self, fake_db):
        fake_db(_FakeConn(counts={"matched": 3, "unassigned": 3},
                          geo_rows=[{"country_code": "CO", "source_lang": "es",
                                     "origin": "CO", "n": 5}],
                          resolvability={"members": 5, "resolvable": 5}))
        out = _run(query_router.post_query({"ask": [
            {"unclustered_signals": {"terms": ["espriella"]}},
            {"receipt_geography": {"topic_id": "dt-242"}},
        ]}))
        assert out["asked"] == 2
        assert [r["verb"] for r in out["results"]] == [
            "unclustered_signals", "receipt_geography"]

    def test_verb_cap_is_enforced(self, fake_db):
        fake_db(_FakeConn())
        ask = [{"voice_mix": {"country": "CO"}}] * (qv.MAX_VERBS_PER_REQUEST + 1)
        resp = _run(query_router.post_query({"ask": ask}))
        assert resp.status_code == 400
        assert b"too_many_verbs" in resp.body
