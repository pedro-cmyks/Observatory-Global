"""Universe view (universe-v0) — pure projection + edge contract.

Spec: docs/specs/2026-07-02-universe-view.md. Edges must be measured in
FULL space (never the projection); positions land in [0,1]^2 with
same-category bodies pulled together.
"""
import numpy as np

import app.main_v2  # noqa: F401 — initialize app + routers first
from app.routers.universe import _nearest_edges, _project_universe


def _unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def test_projection_normalized_and_category_pulled():
    rng = np.random.default_rng(7)
    # two well-separated category directions in 768-dim
    a, b = _unit(rng.normal(size=768)), _unit(rng.normal(size=768))
    vectors = [
        (a + 0.05 * rng.normal(size=768)).tolist() for _ in range(6)
    ] + [
        (b + 0.05 * rng.normal(size=768)).tolist() for _ in range(6)
    ]
    cats = ["alpha"] * 6 + ["beta"] * 6
    positions, anchors, M, basis = _project_universe(vectors, cats)

    assert positions.shape == (12, 3)  # top-3 PCA: z = rotatable depth (spec §7.2)
    assert positions.min() >= 0 and positions.max() <= 1
    assert set(anchors) == {"alpha", "beta"}
    assert len(anchors["alpha"]) == 3
    # same-category spread < cross-category anchor separation
    alpha_spread = np.linalg.norm(positions[:6] - positions[:6].mean(axis=0), axis=1).mean()
    anchor_gap = np.linalg.norm(np.array(anchors["alpha"]) - np.array(anchors["beta"]))
    assert alpha_spread < anchor_gap


def test_edges_come_from_full_space_not_projection():
    rng = np.random.default_rng(3)
    base = _unit(rng.normal(size=768))
    twin = _unit(base + 0.01 * rng.normal(size=768))       # true neighbor
    stranger = _unit(rng.normal(size=768))
    vectors = [base.tolist(), twin.tolist(), stranger.tolist()]
    _, _, M, _ = _project_universe(vectors, ["x", "x", "x"])
    edges, nn_sims = _nearest_edges(M, ["n0", "n1", "n2"], k=1)
    top = edges[0]
    assert {top["a"], top["b"]} == {"n0", "n1"}
    assert top["sim"] > 0.9
    # nn_sim marks orphans: the twins are near, the stranger is isolated
    assert nn_sims[0] > 0.9
    assert nn_sims[2] < nn_sims[0]


def test_edges_are_deduped_undirected():
    rng = np.random.default_rng(5)
    vectors = [_unit(rng.normal(size=768)).tolist() for _ in range(8)]
    _, _, M, _ = _project_universe(vectors, ["c"] * 8)
    edges, _ = _nearest_edges(M, [f"n{i}" for i in range(8)], k=3)
    keys = {tuple(sorted((e["a"], e["b"]))) for e in edges}
    assert len(keys) == len(edges)  # no duplicate pair in either direction


def test_history_projects_into_current_frame():
    from app.routers.universe import _project_history
    rng = np.random.default_rng(11)
    a, b = _unit(rng.normal(size=768)), _unit(rng.normal(size=768))
    vectors = [(a + 0.05 * rng.normal(size=768)).tolist() for _ in range(5)] + [
        (b + 0.05 * rng.normal(size=768)).tolist() for _ in range(5)
    ]
    cats = ["alpha"] * 5 + ["beta"] * 5
    positions, _, _, basis = _project_universe(vectors, cats)
    # projecting a CURRENT vector through the history path lands on (about)
    # its own layout position — same frame, so trajectories are comparable
    replayed = _project_history(vectors[0], "alpha", basis)
    assert replayed is not None
    assert abs(replayed[0] - float(positions[0][0])) < 0.02
    assert abs(replayed[1] - float(positions[0][1])) < 0.02
    # zero vector -> honest None
    assert _project_history([0.0] * 768, "alpha", basis) is None


# ---------------------------------------------------------------------------
# The endpoint is a PURE ARTIFACT READ (2026-07-27). The build measures 75.5s —
# longer than the Fly proxy holds a request — so a request-path build could
# never finish, the cache could never fill, and /api/v2/universe sat at 0%
# availability. Now `scripts/build_universe_field.py` stores the field and the
# endpoint only reads it: always fast, honest about the artifact's age, and
# honest about its absence.
# ---------------------------------------------------------------------------
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg
import pytest
from fastapi import Response

from app import db
from app.routers import universe as universe_mod
from app.services import universe_field


def _good_payload(n=5):
    return {
        "contract": "universe-v0",
        "nodes": [{"id": f"dynamic-topic-{i}"} for i in range(n)],
        "edges": [{"a": "dynamic-topic-0", "b": "dynamic-topic-1", "sim": 0.9}],
        "anchors": [],
        "meta": {"topic_count": n, "timeline_days": 30, "bounded": False},
    }


def _fake_pool(rows, *, capture=None):
    """A pool whose fetchrow returns queued rows (one per call)."""
    queue = list(rows)

    class Conn:
        async def fetchrow(self, query, *args, timeout=None):
            if capture is not None:
                capture.append(query)
            return queue.pop(0) if queue else None

    class Acquire:
        async def __aenter__(self):
            return Conn()

        async def __aexit__(self, *args):
            return False

    class Pool:
        def acquire(self):
            return Acquire()

    return Pool()


def _artifact_row(payload, *, days=30, generated_at=None, build_seconds=75.5):
    return {
        "days": days,
        "generated_at": generated_at or datetime.now(timezone.utc),
        "contract": "universe-v0",
        "node_count": len(payload["nodes"]),
        "edge_count": len(payload["edges"]),
        "build_seconds": build_seconds,
        # Stored as JSONB; asyncpg hands it back as text, so the reader must
        # parse it (the daily-edition reader has the same contract).
        "payload": json.dumps(payload),
        "updated_at": generated_at or datetime.now(timezone.utc),
    }


def test_classify_failure_maps_statement_timeout():
    assert universe_mod._classify_failure(
        asyncpg.exceptions.QueryCanceledError("canceling statement due to statement timeout")
    ) == "db_timeout"
    assert universe_mod._classify_failure(TimeoutError()) == "db_timeout"
    assert universe_mod._classify_failure(RuntimeError("boom")) == "error"


# --- artifact present → served ---------------------------------------------

@pytest.mark.asyncio
async def test_stored_artifact_is_served_and_endpoint_never_builds(monkeypatch):
    payload = _good_payload(7)
    captured: list[str] = []
    monkeypatch.setattr(db, "pool", _fake_pool([_artifact_row(payload)], capture=captured))

    async def _never(days):
        raise AssertionError("the endpoint must NEVER build in-request")
    monkeypatch.setattr(universe_field, "build_universe_payload", _never)

    resp = Response()
    out = await universe_mod.get_universe(resp, days=30)

    assert len(out["nodes"]) == 7
    assert out["edges"], "edges must survive the round trip"
    assert out.get("reason") is None
    assert out["meta"]["source"] == "precomputed_artifact"
    assert out["meta"]["build_seconds"] == 75.5
    # ONE cheap indexed read of the artifact table — no topic/centroid query.
    assert len(captured) == 1
    assert "universe_field_artifacts" in captured[0]
    assert "dynamic_topics" not in captured[0]


@pytest.mark.asyncio
async def test_fresh_artifact_is_not_marked_stale(monkeypatch):
    payload = _good_payload()
    fresh = datetime.now(timezone.utc) - timedelta(hours=2)
    monkeypatch.setattr(
        db, "pool", _fake_pool([_artifact_row(payload, generated_at=fresh)]))

    out = await universe_mod.get_universe(Response(), days=30)
    assert out["stale"] is False
    assert out["meta"]["stale"] is False
    assert 1.9 < out["meta"]["age_hours"] < 2.1
    assert out["generated_at"] == fresh.isoformat()


# --- staleness marker -------------------------------------------------------

@pytest.mark.asyncio
async def test_old_artifact_is_served_but_honestly_marked_stale(monkeypatch):
    """A missed nightly must not blank the field — serve it, say it is old."""
    payload = _good_payload(4)
    old = datetime.now(timezone.utc) - timedelta(hours=50)
    monkeypatch.setattr(
        db, "pool", _fake_pool([_artifact_row(payload, generated_at=old)]))

    out = await universe_mod.get_universe(Response(), days=30)
    assert len(out["nodes"]) == 4, "a stale field is still the real field"
    assert out["stale"] is True
    assert out["meta"]["stale"] is True
    assert out["meta"]["age_hours"] > universe_field.STALE_AFTER_HOURS
    assert out["meta"]["stale_after_hours"] == universe_field.STALE_AFTER_HOURS


def test_age_hours_is_computed_against_the_generation_time():
    now = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
    assert universe_field._age_hours(
        datetime(2026, 7, 27, 6, 0, tzinfo=timezone.utc), now=now) == 6.0
    # A naive timestamp is read as UTC rather than crashing the serving path.
    assert universe_field._age_hours(
        datetime(2026, 7, 27, 6, 0), now=now) == 6.0
    # Clock skew must never produce a negative age.
    assert universe_field._age_hours(
        datetime(2026, 7, 27, 18, 0, tzinfo=timezone.utc), now=now) == 0.0


@pytest.mark.asyncio
async def test_mismatched_window_names_the_gap_instead_of_pretending(monkeypatch):
    """No artifact for the requested window → serve the one we have, labeled."""
    payload = _good_payload()
    monkeypatch.setattr(
        db, "pool",
        # first fetchrow (exact window) misses, second (freshest any) hits
        _fake_pool([None, _artifact_row(payload, days=30)]),
    )
    out = await universe_mod.get_universe(Response(), days=90)
    assert out["nodes"], "a real field beats an empty one"
    assert out["meta"]["days_requested"] == 90
    assert out["meta"]["days_served"] == 30


# --- artifact absent → honest empty with reason -----------------------------

@pytest.mark.asyncio
async def test_absent_artifact_is_an_honest_empty_with_reason(monkeypatch):
    monkeypatch.setattr(db, "pool", _fake_pool([None, None]))
    resp = Response()
    out = await universe_mod.get_universe(resp, days=30)

    assert out["nodes"] == []
    assert out["edges"] == []
    # "the builder has not run here yet" is a DIFFERENT fact from "the db is
    # unwell" — the reason must not launder one into the other.
    assert out["reason"] == "not_precomputed"
    assert out["retry_after_s"] == universe_mod.RETRY_AFTER_S
    assert resp.headers.get("Retry-After") == str(universe_mod.RETRY_AFTER_S)


@pytest.mark.asyncio
async def test_no_db_pool_is_honest_not_a_crash(monkeypatch):
    monkeypatch.setattr(db, "pool", None)
    out = await universe_mod.get_universe(Response(), days=30)
    assert out["nodes"] == []
    assert out["reason"] == "no_db"


@pytest.mark.asyncio
async def test_read_failure_states_reason_and_retry_after(monkeypatch):
    async def _boom(days):
        raise asyncpg.exceptions.QueryCanceledError("statement timeout")
    monkeypatch.setattr(universe_mod, "fetch_stored_universe", _boom)

    resp = Response()
    out = await universe_mod.get_universe(resp, days=30)
    assert out["nodes"] == []
    assert out["reason"] == "db_timeout"
    assert resp.headers.get("Retry-After") == str(universe_mod.RETRY_AFTER_S)


@pytest.mark.asyncio
async def test_generic_read_failure_reason_is_error(monkeypatch):
    async def _boom(days):
        raise RuntimeError("boom")
    monkeypatch.setattr(universe_mod, "fetch_stored_universe", _boom)
    out = await universe_mod.get_universe(Response(), days=30)
    assert out["reason"] == "error"


# --- the build must stay OFF the request path ------------------------------

def test_router_holds_no_build_and_no_in_request_cache():
    """The regression that caused 0% availability: a 75s build in a request.

    Frozen structurally — if a build or a request-path cache is reintroduced
    here, this fails.
    """
    src = Path(universe_mod.__file__).read_text()
    assert "SET statement_timeout" not in src
    assert "_cache" not in src
    assert "asyncio.create_task" not in src


def test_migration_creates_the_artifact_table():
    sql = (Path(__file__).parents[1] / "migrations/091_universe_field_artifacts.sql").read_text()
    assert "universe_field_artifacts" in sql
    assert "PRIMARY KEY" in sql
