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
    positions, anchors, M = _project_universe(vectors, cats)

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
    _, _, M = _project_universe(vectors, ["x", "x", "x"])
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
    _, _, M = _project_universe(vectors, ["c"] * 8)
    edges, _ = _nearest_edges(M, [f"n{i}" for i in range(8)], k=3)
    keys = {tuple(sorted((e["a"], e["b"]))) for e in edges}
    assert len(keys) == len(edges)  # no duplicate pair in either direction
