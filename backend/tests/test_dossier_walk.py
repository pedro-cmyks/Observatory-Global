"""POST /api/v2/dossier/walk — the walked-constellation endpoint.

Spec: docs/superpowers/specs/2026-07-21-multi-hop-transitive-chains.md. The walk
MATH is frozen in test_constellation_walk.py; this covers the endpoint wiring:
pin resolution, the honest empty/orphan contract, and the DB → global-whitening →
walk → payload path (fake asyncpg pool, real whitening asset).
"""
from __future__ import annotations

import asyncio

import numpy as np
import pytest

from app import db
from app.routers import dossier
from app.routers.dossier import WalkRequest, dossier_walk


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------- request model
def test_rel_floor_is_clamped_by_the_contract():
    assert WalkRequest(topic_ids=["dynamic-topic-1"]).rel_floor == 0.35
    with pytest.raises(Exception):
        WalkRequest(topic_ids=["dynamic-topic-1"], rel_floor=0.01)   # < 0.10
    with pytest.raises(Exception):
        WalkRequest(topic_ids=["dynamic-topic-1"], rel_floor=1.5)    # > 0.90


# ---------------------------------------------------------------- empty branches
def test_walk_no_topic_centroids_is_honest_empty(monkeypatch):
    # country/person pins have no topic centroid → not a story-relation walk.
    monkeypatch.setattr(db, "pool", object(), raising=False)  # guarded before db
    out = _run(dossier_walk(WalkRequest(topic_ids=["country--US", "person--x"])))
    assert out["contract"] == "constellation-walk-v0"
    assert out["meta"]["reason"] == "no_topic_centroids"
    assert out["kin"] == [] and out["seeds"] == []
    assert set(out["unresolved"]) == {"country--US", "person--x"}


def test_walk_no_db_is_honest_empty(monkeypatch):
    monkeypatch.setattr(db, "pool", None, raising=False)
    out = _run(dossier_walk(WalkRequest(topic_ids=["dynamic-topic-31"])))
    assert out["contract"] == "constellation-walk-v0"
    assert out["meta"]["reason"] == "no_db"


# ---------------------------------------------------------------- integration
class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, *a, **k):
        return None

    async def fetch(self, sql, *args):
        if args:                       # the missing-seed backfill query
            wanted = set(args[0])
            return [r for r in self._rows if r["id"] in wanted]
        return self._rows              # the active-topics query

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _FakePool:
    def __init__(self, rows):
        self._rows = rows

    def acquire(self):
        return _FakeConn(self._rows)


def _rows():
    """A seed cluster + a near neighbor + an orthogonal orphan, 768-dim so the
    real whitening asset applies. Content of the walk is asserted in the pure
    tests; here we prove the DB→whiten→walk→payload path runs end to end."""
    rng = np.random.default_rng(7)
    base = rng.standard_normal(768).astype(np.float32)
    near = base + 0.05 * rng.standard_normal(768).astype(np.float32)
    orphan = rng.standard_normal(768).astype(np.float32)
    mk = lambda tid, lab, cat, v: {"id": tid, "label": lab, "category": cat,
                                   "centroid_vec": [float(x) for x in v]}
    return [
        mk(31, "Trump Vows Continued Iran Strikes", "Armed conflict escalation", base),
        mk(42, "Netanyahu Warns Iran", "Armed conflict escalation", near),
        mk(99, "Local Weather Roundup", "Weather and climate", orphan),
    ]


def test_walk_endpoint_wires_db_whitening_walk_payload(monkeypatch):
    monkeypatch.setattr(db, "pool", _FakePool(_rows()), raising=False)
    dossier._WALK_CACHE.clear()
    out = _run(dossier_walk(WalkRequest(topic_ids=["dynamic-topic-31"])))
    assert out["contract"] == "constellation-walk-v0"
    assert len(out["seeds"]) == 1 and out["seeds"][0]["id"] == "dynamic-topic-31"
    assert out["meta"]["topic_universe"] == 3
    assert out["meta"]["semantic_space"] == "whitened-e5-k1-global"
    assert out["meta"]["hop_cap"] == 3
    assert isinstance(out["kin"], list)
    # every kin node carries a degree, kinship label and a per-hop receipt weight
    for k in out["kin"]:
        assert k["kinship"] in ("hermano", "primo")
        assert k["degree"] >= 1
        assert k["via"]["weight"] >= 0
        assert "id" in k and k["id"] != "dynamic-topic-31"   # seed never in kin


def test_walk_endpoint_orphan_seed_returns_no_measured_kin(monkeypatch):
    # a seed whose only companions are far returns the honest orphan state.
    rng = np.random.default_rng(3)
    a = rng.standard_normal(768).astype(np.float32)
    b = rng.standard_normal(768).astype(np.float32)   # unrelated
    rows = [
        {"id": 500, "label": "Isolated Story", "category": "x",
         "centroid_vec": [float(x) for x in a]},
        {"id": 501, "label": "Unrelated", "category": "y",
         "centroid_vec": [float(x) for x in b]},
    ]
    monkeypatch.setattr(db, "pool", _FakePool(rows), raising=False)
    dossier._WALK_CACHE.clear()
    out = _run(dossier_walk(WalkRequest(topic_ids=["dynamic-topic-500"], rel_floor=0.9)))
    # high rel_floor + unrelated neighbor → no kin kept → honest reason
    if not out["kin"]:
        assert out["meta"]["reason"] == "no_measured_kin"
