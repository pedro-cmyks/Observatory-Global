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
# Dark ≠ down (council N4): the endpoint must never serve a silent empty 200
# when the field actually exists — a cold rebuild blowing the statement
# timeout serves the LAST GOOD payload (honestly labeled stale), and a truly
# empty failure states its reason + Retry-After instead of a bare "error".
# ---------------------------------------------------------------------------
import asyncio

import asyncpg
import pytest
from fastapi import Response

from app.routers import universe as universe_mod


@pytest.fixture(autouse=True)
def _reset_universe_cache():
    saved = dict(universe_mod._cache)
    universe_mod._cache.update(
        {"at": 0.0, "payload": None, "failed_at": 0.0, "fail_reason": None,
         "refreshing": False})
    yield
    universe_mod._cache.clear()
    universe_mod._cache.update(saved)


def _good_payload(n=5):
    return {
        "contract": "universe-v0",
        "nodes": [{"id": f"dynamic-topic-{i}"} for i in range(n)],
        "edges": [],
        "anchors": [],
        "meta": {"topic_count": n},
    }


def test_classify_failure_maps_statement_timeout():
    assert universe_mod._classify_failure(
        asyncpg.exceptions.QueryCanceledError("canceling statement due to statement timeout")
    ) == "db_timeout"
    assert universe_mod._classify_failure(TimeoutError()) == "db_timeout"
    assert universe_mod._classify_failure(RuntimeError("boom")) == "error"


@pytest.mark.asyncio
async def test_stale_payload_served_when_rebuild_fails(monkeypatch):
    """A previously-built field outlives a failed rebuild — dark ≠ down."""
    stale = _good_payload()
    universe_mod._cache.update({
        "payload": stale,
        "at": 0.0,  # expired long ago
        "failed_at": universe_mod.time.monotonic(),  # recent failure → backoff
        "fail_reason": "db_timeout",
    })
    async def _boom(days):
        raise asyncpg.exceptions.QueryCanceledError("statement timeout")
    monkeypatch.setattr(universe_mod, "_build_universe", _boom)

    resp = Response()
    out = await universe_mod.get_universe(resp, days=30)
    assert out["nodes"], "stale nodes must be served, never an empty 200"
    assert out["meta"]["cache"] == "stale"
    assert out["meta"]["stale_reason"] == "db_timeout"


@pytest.mark.asyncio
async def test_empty_failure_states_reason_and_retry_after(monkeypatch):
    """No payload ever built + build fails → honest reason + Retry-After."""
    async def _boom(days):
        raise asyncpg.exceptions.QueryCanceledError("statement timeout")
    monkeypatch.setattr(universe_mod, "_build_universe", _boom)

    resp = Response()
    out = await universe_mod.get_universe(resp, days=30)
    assert out["nodes"] == []
    assert out["reason"] == "db_timeout"
    assert out["retry_after_s"] == universe_mod.RETRY_AFTER_S
    assert resp.headers.get("Retry-After") == str(universe_mod.RETRY_AFTER_S)


@pytest.mark.asyncio
async def test_generic_failure_reason_is_error(monkeypatch):
    async def _boom(days):
        raise RuntimeError("boom")
    monkeypatch.setattr(universe_mod, "_build_universe", _boom)
    resp = Response()
    out = await universe_mod.get_universe(resp, days=30)
    assert out["reason"] == "error"


@pytest.mark.asyncio
async def test_stale_serve_triggers_background_revalidate(monkeypatch):
    """Expired cache with no recent failure → serve stale NOW, rebuild in
    the background (nobody waits 29-46s on a request thread)."""
    stale = _good_payload(4)
    fresh = _good_payload(9)
    universe_mod._cache.update({"payload": stale, "at": 0.0, "failed_at": 0.0})
    async def _slow_build(days):
        return fresh
    monkeypatch.setattr(universe_mod, "_build_universe", _slow_build)

    resp = Response()
    out = await universe_mod.get_universe(resp, days=30)
    assert out["meta"]["topic_count"] == 4  # stale served immediately
    await asyncio.sleep(0.05)  # let the background task land
    assert universe_mod._cache["payload"]["meta"]["topic_count"] == 9


@pytest.mark.asyncio
async def test_fresh_cache_untouched(monkeypatch):
    payload = _good_payload()
    universe_mod._cache.update(
        {"payload": payload, "at": universe_mod.time.monotonic()})
    async def _never(days):
        raise AssertionError("must not rebuild a fresh cache")
    monkeypatch.setattr(universe_mod, "_build_universe", _never)
    resp = Response()
    out = await universe_mod.get_universe(resp, days=30)
    assert out is payload
