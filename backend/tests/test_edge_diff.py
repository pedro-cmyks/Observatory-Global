"""Track C2/C3 — the read layer over the C1 edge-snapshot store: tests.

Spec: docs/superpowers/specs/2026-07-21-time-axis-versioned-relationships.md
§4 (churn-vs-narrative), §2 (replay/diff contexts), §7 (honesty).

Track C2 (the pure classifier, `app.services.edge_diff`) is exercised
directly with synthetic snapshot rows — no DB, mirrors
test_snapshot_topic_edges.py / test_constellation_walk.py's style for the
sibling C1 store. Track C3's router (`app.routers.edges`) gets an
honest-empty smoke pass plus one full wired-fake-conn integration test,
mirroring test_dossier_walk.py's `_FakeConn`/`_FakePool` pattern.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

import app.main_v2  # noqa: F401 — initialize app + routers FIRST. `app.routers.edges`
                     # does `from app.main_v2 import app` (the geo.py/threads.py
                     # cache-access idiom); importing the full app module here
                     # avoids the partial-module circular-import trap
                     # test_threads_router.py documents (it resorts to source-text
                     # assertions instead of a direct import for exactly this reason).
from app import db
from app.routers import edges
from app.services.edge_diff import (
    DEFAULT_SNAPSHOT_INTERVAL_HOURS,
    DEFAULT_WEAKEN_DELTA,
    FORMED,
    NARRATIVE_CHANGE,
    STABLE,
    SUBSTRATE_CHURN,
    WEAKENED,
    classify_dormant_relationships,
    classify_edge_changes,
    describe_snapshot_interval,
    parse_dynamic_topic_id,
    strip_focus_suffix,
)


def _run(coro):
    # asyncio.run, not get_event_loop(): any earlier asyncio.run() in the
    # session closes the thread's loop and leaves it unset, so
    # get_event_loop() raises RuntimeError once these files run alongside
    # others. asyncio.run owns a fresh loop per call and cannot be poisoned.
    return asyncio.run(coro)


def _edge(a, b, weight, basis="semantic"):
    return {"identity_key_a": a, "identity_key_b": b, "weight": weight, "basis": basis}


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


# ============================================================== ref helpers
class TestFocusRefHelpers:
    def test_strip_focus_suffix_strips_country_scope(self):
        assert strip_focus_suffix("dynamic-topic-31--US") == "dynamic-topic-31"

    def test_strip_focus_suffix_passthrough_without_suffix(self):
        assert strip_focus_suffix("dynamic-topic-31") == "dynamic-topic-31"
        assert strip_focus_suffix("id-abcxyz") == "id-abcxyz"

    def test_parse_dynamic_topic_id(self):
        assert parse_dynamic_topic_id("dynamic-topic-31") == 31
        assert parse_dynamic_topic_id("id-abcxyz") is None
        assert parse_dynamic_topic_id("armed-conflict-escalation") is None


# ============================================================== (a) narrative vs churn
class TestNarrativeChangeVsChurn:
    def test_both_keys_active_is_narrative_change(self):
        t0 = [_edge("id-1", "id-2", 0.71)]
        t1 = []
        lifecycle = {"id-1": "active", "id-2": "active"}
        changes = classify_edge_changes(t0, t1, lifecycle)
        assert len(changes) == 1
        c = changes[0]
        assert c.change_type == NARRATIVE_CHANGE
        assert c.identity_key_a == "id-1" and c.identity_key_b == "id-2"
        assert c.weight_t0 == pytest.approx(0.71) and c.weight_t1 is None
        assert "still active" in c.reason

    def test_one_key_retired_is_substrate_churn_never_narrative(self):
        t0 = [_edge("id-1", "id-2", 0.71)]
        t1 = []
        lifecycle = {"id-1": "active", "id-2": "retired"}
        changes = classify_edge_changes(t0, t1, lifecycle)
        assert len(changes) == 1
        c = changes[0]
        assert c.change_type == SUBSTRATE_CHURN
        assert c.change_type != NARRATIVE_CHANGE
        assert "id-2 is retired" in c.reason

    def test_unresolved_key_missing_from_lifecycle_is_substrate_churn(self):
        # a merged/deleted identity_key is simply ABSENT from the lifecycle
        # map — must never be silently treated as still-active narrative change.
        t0 = [_edge("id-1", "id-9", 0.5)]
        lifecycle = {"id-1": "active"}  # id-9 unresolved
        c = classify_edge_changes(t0, [], lifecycle)[0]
        assert c.change_type == SUBSTRATE_CHURN
        assert "unresolved" in c.reason

    def test_both_deprecated_is_substrate_churn(self):
        t0 = [_edge("id-1", "id-2", 0.6)]
        lifecycle = {"id-1": "deprecated", "id-2": "deprecated"}
        c = classify_edge_changes(t0, [], lifecycle)[0]
        assert c.change_type == SUBSTRATE_CHURN

    def test_order_of_pair_in_input_does_not_matter(self):
        # canonicalization must fold a>b rows the same as a<=b rows.
        t0 = [_edge("id-9", "id-1", 0.71)]  # deliberately un-canonical order
        lifecycle = {"id-1": "active", "id-9": "active"}
        c = classify_edge_changes(t0, [], lifecycle)[0]
        assert c.identity_key_a == "id-1" and c.identity_key_b == "id-9"
        assert c.change_type == NARRATIVE_CHANGE


# ============================================================== (b) formed
class TestFormed:
    def test_new_edge_is_formed(self):
        t1 = [_edge("id-3", "id-4", 0.55, basis="shared_country")]
        c = classify_edge_changes([], t1, {})[0]
        assert c.change_type == FORMED
        assert c.weight_t0 is None
        assert c.weight_t1 == pytest.approx(0.55)
        assert c.basis == "shared_country"


# ============================================================== (c) weakened
class TestWeakened:
    def test_material_drop_is_weakened(self):
        t0 = [_edge("id-1", "id-2", 0.80)]
        t1 = [_edge("id-1", "id-2", 0.60)]
        c = classify_edge_changes(t0, t1, {"id-1": "active", "id-2": "active"})[0]
        assert c.change_type == WEAKENED
        assert c.delta == pytest.approx(-0.20)

    def test_small_drop_is_not_surfaced_by_default(self):
        t0 = [_edge("id-1", "id-2", 0.80)]
        t1 = [_edge("id-1", "id-2", 0.80 - DEFAULT_WEAKEN_DELTA / 2)]
        assert classify_edge_changes(t0, t1, {"id-1": "active", "id-2": "active"}) == []

    def test_weight_increase_is_not_weakened(self):
        t0 = [_edge("id-1", "id-2", 0.40)]
        t1 = [_edge("id-1", "id-2", 0.70)]
        assert classify_edge_changes(t0, t1, {"id-1": "active", "id-2": "active"}) == []

    def test_stable_only_surfaced_when_requested(self):
        t0 = [_edge("id-1", "id-2", 0.50)]
        t1 = [_edge("id-1", "id-2", 0.51)]
        lifecycle = {"id-1": "active", "id-2": "active"}
        assert classify_edge_changes(t0, t1, lifecycle) == []
        stable = classify_edge_changes(t0, t1, lifecycle, include_stable=True)
        assert len(stable) == 1 and stable[0].change_type == STABLE


# ============================================================== (d) dormant
class TestDormant:
    def test_backbone_alive_no_current_edge_is_dormant(self):
        backbone = [{"entity_a": "alice apple", "entity_b": "bob banana",
                     "cooccur_count": 3, "rarity_weight": 0.62}]
        entity_active = {"alice apple": {"id-1"}, "bob banana": {"id-9"}}
        out = classify_dormant_relationships(backbone, entity_active, edges_t1=[])
        assert len(out) == 1
        assert out[0].entity_a == "alice apple" and out[0].entity_b == "bob banana"
        assert "no current thread-edge" in out[0].reason

    def test_backbone_bridged_by_a_live_edge_is_not_dormant(self):
        backbone = [{"entity_a": "alice apple", "entity_b": "bob banana",
                     "cooccur_count": 3, "rarity_weight": 0.62}]
        entity_active = {"alice apple": {"id-1"}, "bob banana": {"id-2"}}
        edges_t1 = [_edge("id-1", "id-2", 0.7)]
        assert classify_dormant_relationships(backbone, entity_active, edges_t1) == []

    def test_entity_with_no_current_topics_still_reports_dormant(self):
        # an entity absent from the join has an empty identity-key set, which
        # can never be "bridged" — honest degrade, not a silent omission.
        backbone = [{"entity_a": "alice apple", "entity_b": "ghost writer",
                     "cooccur_count": 2, "rarity_weight": 0.55}]
        entity_active = {"alice apple": {"id-1"}}  # 'ghost writer' absent entirely
        out = classify_dormant_relationships(backbone, entity_active, edges_t1=[])
        assert len(out) == 1


# ============================================================== snapshot interval
class TestDescribeSnapshotInterval:
    """The 2026-07-25 gap is the forcing case: that day's snapshot was a
    half-written partial (3000 rows = 6 x BATCH_SIZE, aborted by an
    out-of-bound cosine) and was DELETED, so prod holds 07-24 08:15 ->
    07-26 08:15 = a real 48h step between consecutive stored passes. Measured
    on prod 2026-07-27: that step reads 9,789 formed edges against 6,934 and
    6,304 for the neighbouring 24h steps — ~+50%. A 48h diff rendered like
    every other 24h diff turns a storage gap into a phantom burst of
    narrative change, so the interval must travel with the diff."""

    def test_standard_nightly_step_is_standard(self):
        out = describe_snapshot_interval(
            _dt("2026-07-26T08:15:03"), _dt("2026-07-27T08:15:05"),
        )
        assert out.is_standard is True
        assert out.interval_hours == 24.0
        assert out.missing_snapshot_passes == 0
        assert out.expected_interval_hours == DEFAULT_SNAPSHOT_INTERVAL_HOURS

    def test_cron_drift_within_tolerance_stays_standard(self):
        # the writer stamps now(); a late pass must not read as a gap
        out = describe_snapshot_interval(
            _dt("2026-07-26T08:15:00"), _dt("2026-07-27T08:52:00"),
        )
        assert out.is_standard is True

    def test_the_0725_gap_is_flagged_with_the_missing_pass(self):
        out = describe_snapshot_interval(
            _dt("2026-07-24T08:15:03"), _dt("2026-07-26T08:15:03"),
        )
        assert out.interval_hours == 48.0
        assert out.is_standard is False
        assert out.missing_snapshot_passes == 1
        assert out.intermediate_snapshots == 0
        assert "48" in out.note and "24" in out.note

    def test_multi_pass_span_reports_intermediates_not_missing(self):
        # `since` far in the past: the diff aggregates real passes rather than
        # stepping over a gap — a different honesty problem, same flag
        out = describe_snapshot_interval(
            _dt("2026-07-22T08:15:00"), _dt("2026-07-27T08:15:00"),
            intermediate_snapshots=3,
        )
        assert out.interval_hours == 120.0
        assert out.is_standard is False
        assert out.intermediate_snapshots == 3
        # 5 expected passes, 3 actually present between the ends -> 1 missing
        assert out.missing_snapshot_passes == 1

    def test_shorter_than_cadence_is_not_standard_and_claims_no_missing(self):
        # prod holds these: manual T0/T1 test passes 1.42h and 0.25h apart
        out = describe_snapshot_interval(
            _dt("2026-07-21T20:24:30"), _dt("2026-07-21T21:49:58"),
        )
        assert out.is_standard is False
        assert out.missing_snapshot_passes == 0
        assert "shorter" in out.note.lower()

    def test_same_snapshot_both_ends_is_named_not_silently_standard(self):
        t = _dt("2026-07-27T08:15:05")
        out = describe_snapshot_interval(t, t)
        assert out.interval_hours == 0.0
        assert out.is_standard is False
        assert out.missing_snapshot_passes == 0
        assert "same snapshot" in out.note.lower()

    def test_intermediate_count_alone_breaks_standard(self):
        # exactly 24h apart but with a pass in between cannot happen with a
        # 24h cadence; if it does (an extra manual pass), say so
        out = describe_snapshot_interval(
            _dt("2026-07-26T08:00:00"), _dt("2026-07-27T08:00:00"),
            intermediate_snapshots=1,
        )
        assert out.is_standard is False
        assert out.intermediate_snapshots == 1


# ============================================================== router: honest-empty
class TestRouterHonestEmpty:
    def test_edges_replay_no_db(self, monkeypatch):
        monkeypatch.setattr(db, "pool", None)
        out = _run(edges.edges_replay(at="2026-06-01T00:00:00Z"))
        assert out["contract"] == "edges-replay-v0"
        assert out["reason"] == "db_unavailable"
        assert out["edges"] == []

    def test_edges_replay_bad_timestamp_is_422(self):
        with pytest.raises(HTTPException) as exc_info:
            _run(edges.edges_replay(at="not-a-date"))
        assert exc_info.value.status_code == 422

    def test_focus_edge_diff_no_db(self, monkeypatch):
        monkeypatch.setattr(db, "pool", None)
        out = _run(edges.focus_edge_diff(ref="dynamic-topic-31", since="2026-06-01T00:00:00Z"))
        assert out["contract"] == "focus-edge-diff-v0"
        assert out["reason"] == "db_unavailable"
        assert out["changes"] == [] and out["dormant"] == []

    def test_focus_edge_diff_bad_since_is_422(self, monkeypatch):
        monkeypatch.setattr(db, "pool", None)
        with pytest.raises(HTTPException) as exc_info:
            _run(edges.focus_edge_diff(ref="dynamic-topic-31", since="not-a-date"))
        assert exc_info.value.status_code == 422


# ============================================================== router: fake-conn wiring
class _FakeConn:
    """SQL-dispatch fake mirroring test_dossier_walk.py's `_FakeConn` /
    test_snapshot_topic_edges.py's `_FakeRunConn` pattern — routes each
    `fetch`/`fetchrow` call by a distinguishing SQL substring so one fake
    stands in for every query `app/routers/edges.py` issues."""

    def __init__(self, *, resolve_row=None, latest_snapshot=None,
                 nearest_snapshot=None, t0=None, t1=None,
                 edges_t0=None, edges_t1=None, lifecycle_rows=None,
                 focus_entities_rows=None, backbone_rows=None,
                 entity_active_rows=None, snapshots_between=0,
                 prev_snapshot=None, next_snapshot=None):
        self.snapshots_between = snapshots_between
        self.prev_snapshot = prev_snapshot
        self.next_snapshot = next_snapshot
        self.resolve_row = resolve_row
        self.latest_snapshot = latest_snapshot
        self.nearest_snapshot = nearest_snapshot
        self.t0, self.t1 = t0, t1
        self.edges_t0 = edges_t0 or []
        self.edges_t1 = edges_t1 or []
        self.lifecycle_rows = lifecycle_rows or []
        self.focus_entities_rows = focus_entities_rows or []
        self.backbone_rows = backbone_rows or []
        self.entity_active_rows = entity_active_rows or []

    async def execute(self, *a, **k):
        return None

    async def fetchrow(self, sql, *args):
        if "WHERE id = $1" in sql or "WHERE identity_key = $1" in sql:
            return self.resolve_row
        if "MAX(snapshot_at) AS s" in sql:
            return {"s": self.latest_snapshot}
        if "count(DISTINCT snapshot_at)" in sql:
            return {"n": self.snapshots_between}
        if "prev_at" in sql:
            return {"prev_at": self.prev_snapshot, "next_at": self.next_snapshot}
        if "GROUP BY snapshot_at" in sql:
            return {"snapshot_at": self.nearest_snapshot} if self.nearest_snapshot else None
        raise AssertionError(f"unexpected fetchrow: {sql[:80]!r}")

    async def fetch(self, sql, *args):
        if "identity_key_a = $2 OR identity_key_b = $2" in sql:
            snap_at = args[0]
            if snap_at == self.t0:
                return self.edges_t0
            if snap_at == self.t1:
                return self.edges_t1
            return []
        if "identity_key = ANY($1::text[])" in sql:
            return self.lifecycle_rows
        if "tm.topic_id = $1" in sql:
            return self.focus_entities_rows
        if "FROM entity_backbone_edges" in sql:
            return self.backbone_rows
        if "JOIN dynamic_topics dt ON tm.topic_id" in sql:
            return self.entity_active_rows
        if "GROUP BY snapshot_at" in sql or "FROM topic_edge_snapshots" in sql:
            return []  # /edges/replay's own listing query, unused by this fixture
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


class TestFocusEdgeDiffRouterHonestBranches:
    def test_topic_not_found(self, monkeypatch):
        conn = _FakeConn(resolve_row=None)
        monkeypatch.setattr(db, "pool", _FakePool(conn))
        out = _run(edges.focus_edge_diff(ref="armed-conflict-escalation",
                                         since="2026-06-01T00:00:00Z"))
        assert out["reason"] == "topic_not_found"
        assert out["changes"] == [] and out["dormant"] == []

    def test_no_snapshots_stored(self, monkeypatch):
        conn = _FakeConn(
            resolve_row={"id": 31, "identity_key": "id-A", "state": "active"},
            latest_snapshot=None,
        )
        monkeypatch.setattr(db, "pool", _FakePool(conn))
        out = _run(edges.focus_edge_diff(ref="dynamic-topic-31",
                                         since="2026-06-01T00:00:00Z"))
        assert out["reason"] == "no_snapshots_stored"


class TestFocusEdgeDiffRouterIntegration:
    """One end-to-end pass through the router wiring: ref resolution, T0/T1
    edge fetch, lifecycle lookup, the C2 classifier, and the dormant lookup —
    all four `EdgeChange` types plus one dormant relationship in a single
    scenario, via a fully-scripted fake conn (no real DB)."""

    def test_full_diff_scenario(self, monkeypatch):
        t0 = _dt("2026-07-01T00:00:00")
        t1 = _dt("2026-07-21T00:00:00")
        conn = _FakeConn(
            resolve_row={"id": 100, "identity_key": "id-A", "state": "active"},
            latest_snapshot=t1,
            nearest_snapshot=t0,
            t0=t0, t1=t1,
            # A-B dissolves (B retired -> churn); A-C weakens; A-E dissolves
            # (both active -> narrative change).
            edges_t0=[_edge("id-A", "id-B", 0.71),
                      _edge("id-A", "id-C", 0.50),
                      _edge("id-A", "id-E", 0.60)],
            # A-D is new (formed); A-C survives at a materially lower weight.
            edges_t1=[_edge("id-A", "id-C", 0.30),
                      _edge("id-A", "id-D", 0.60)],
            lifecycle_rows=[
                {"identity_key": "id-A", "state": "active"},
                {"identity_key": "id-B", "state": "retired"},
                {"identity_key": "id-C", "state": "active"},
                {"identity_key": "id-D", "state": "active"},
                {"identity_key": "id-E", "state": "active"},
            ],
            focus_entities_rows=[{"persons": ["alice apple", "bob banana"]}],
            backbone_rows=[{"entity_a": "alice apple", "entity_b": "carol carrot",
                            "cooccur_count": 4, "rarity_weight": 0.58}],
            # 'alice apple' currently lives in the focus topic itself
            # (id-A); 'carol carrot' currently lives in an UNRELATED active
            # topic (id-Z) with no live edge to id-A -> dormant.
            entity_active_rows=[
                {"identity_key": "id-A", "persons": ["alice apple"]},
                {"identity_key": "id-Z", "persons": ["carol carrot"]},
            ],
        )
        monkeypatch.setattr(db, "pool", _FakePool(conn))

        out = _run(edges.focus_edge_diff(ref="dynamic-topic-100--US",
                                         since="2026-07-02T00:00:00Z"))

        assert out["contract"] == "focus-edge-diff-v0"
        assert out["focus_identity_key"] == "id-A"
        assert "reason" not in out

        by_pair = {(c["identity_key_a"], c["identity_key_b"]): c for c in out["changes"]}
        assert len(by_pair) == 4
        assert by_pair[("id-A", "id-B")]["change_type"] == SUBSTRATE_CHURN
        assert by_pair[("id-A", "id-E")]["change_type"] == NARRATIVE_CHANGE
        assert by_pair[("id-A", "id-C")]["change_type"] == WEAKENED
        assert by_pair[("id-A", "id-C")]["delta"] == pytest.approx(-0.20)
        assert by_pair[("id-A", "id-D")]["change_type"] == FORMED

        assert len(out["dormant"]) == 1
        d = out["dormant"][0]
        assert {d["entity_a"], d["entity_b"]} == {"alice apple", "carol carrot"}
        assert "dormant_reason" not in out

    def test_same_since_and_latest_snapshot_yields_no_changes(self, monkeypatch):
        # `since` resolves to the SAME pass as the latest snapshot (e.g. only
        # one pass exists yet) — must diff cleanly to zero changes, never
        # fabricate a FORMED burst from an artificially-empty T0.
        only = _dt("2026-07-21T00:00:00")
        conn = _FakeConn(
            resolve_row={"id": 100, "identity_key": "id-A", "state": "active"},
            latest_snapshot=only,
            nearest_snapshot=only,
            t0=only, t1=only,
            edges_t1=[_edge("id-A", "id-C", 0.30)],
            lifecycle_rows=[{"identity_key": "id-A", "state": "active"},
                            {"identity_key": "id-C", "state": "active"}],
        )
        monkeypatch.setattr(db, "pool", _FakePool(conn))
        out = _run(edges.focus_edge_diff(ref="dynamic-topic-100",
                                         since="2026-01-01T00:00:00Z"))
        assert out["changes"] == []
        assert out["matched_since_snapshot_at"] == out["latest_snapshot_at"]
        assert out["interval"]["hours"] == 0.0
        assert out["interval"]["is_standard"] is False


class TestFocusEdgeDiffIntervalHonesty:
    """The compared interval must ride along with the changes. Forcing case:
    prod's 07-24 -> 07-26 pair (07-25's partial snapshot was deleted) is a 48h
    step between CONSECUTIVE stored passes; unlabeled it reads as one day."""

    def _conn(self, t0, t1, *, between=0):
        return _FakeConn(
            resolve_row={"id": 100, "identity_key": "id-A", "state": "active"},
            latest_snapshot=t1, nearest_snapshot=t0, t0=t0, t1=t1,
            edges_t0=[_edge("id-A", "id-B", 0.60)],
            edges_t1=[_edge("id-A", "id-C", 0.60)],
            lifecycle_rows=[{"identity_key": "id-A", "state": "active"},
                            {"identity_key": "id-B", "state": "active"},
                            {"identity_key": "id-C", "state": "active"}],
            snapshots_between=between,
        )

    def test_standard_nightly_pair_is_marked_standard(self, monkeypatch):
        conn = self._conn(_dt("2026-07-26T08:15:03"), _dt("2026-07-27T08:15:05"))
        monkeypatch.setattr(db, "pool", _FakePool(conn))
        out = _run(edges.focus_edge_diff(ref="dynamic-topic-100",
                                         since="2026-07-26T08:00:00Z"))
        iv = out["interval"]
        assert iv["hours"] == 24.0 and iv["is_standard"] is True
        assert iv["missing_snapshot_passes"] == 0

    def test_the_0725_gap_pair_is_flagged_not_silent(self, monkeypatch):
        conn = self._conn(_dt("2026-07-24T08:15:03"), _dt("2026-07-26T08:15:03"))
        monkeypatch.setattr(db, "pool", _FakePool(conn))
        out = _run(edges.focus_edge_diff(ref="dynamic-topic-100",
                                         since="2026-07-24T08:00:00Z"))
        iv = out["interval"]
        assert iv["hours"] == 48.0
        assert iv["is_standard"] is False
        assert iv["missing_snapshot_passes"] == 1
        assert iv["intermediate_snapshots"] == 0
        assert iv["note"]  # the receipt is never empty
        # the changes themselves are still reported — flagged, not filtered
        assert len(out["changes"]) == 2

    def test_wide_since_window_reports_aggregated_passes(self, monkeypatch):
        conn = self._conn(_dt("2026-07-22T08:15:00"), _dt("2026-07-27T08:15:00"),
                          between=3)
        monkeypatch.setattr(db, "pool", _FakePool(conn))
        out = _run(edges.focus_edge_diff(ref="dynamic-topic-100",
                                         since="2026-07-22T00:00:00Z"))
        iv = out["interval"]
        assert iv["hours"] == 120.0
        assert iv["is_standard"] is False
        assert iv["intermediate_snapshots"] == 3


class TestEdgesReplayNeighbourSteps:
    """`/edges/replay` reads one pass and does not diff — but a scrubber
    stepping pass-to-pass does, so each served pass carries the real width of
    its neighbouring steps."""

    def test_replay_reports_a_48h_previous_step(self, monkeypatch):
        served = _dt("2026-07-26T08:15:03")
        conn = _FakeConn(nearest_snapshot=served,
                         prev_snapshot=_dt("2026-07-24T08:15:03"),
                         next_snapshot=_dt("2026-07-27T08:15:05"))
        monkeypatch.setattr(db, "pool", _FakePool(conn))
        out = _run(edges.edges_replay(at="2026-07-26T09:00:00Z"))
        assert out["previous_snapshot_at"] == "2026-07-24T08:15:03+00:00"
        assert out["interval_from_previous"]["hours"] == 48.0
        assert out["interval_from_previous"]["is_standard"] is False
        assert out["interval_from_previous"]["missing_snapshot_passes"] == 1
        assert out["interval_to_next"]["hours"] == 24.0
        assert out["interval_to_next"]["is_standard"] is True

    def test_replay_edge_of_store_has_null_neighbours(self, monkeypatch):
        served = _dt("2026-07-27T08:15:05")
        conn = _FakeConn(nearest_snapshot=served, prev_snapshot=None, next_snapshot=None)
        monkeypatch.setattr(db, "pool", _FakePool(conn))
        out = _run(edges.edges_replay(at="2026-07-27T09:00:00Z"))
        assert out["previous_snapshot_at"] is None
        assert out["interval_from_previous"] is None
        assert out["interval_to_next"] is None
