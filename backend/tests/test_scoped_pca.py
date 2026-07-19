"""#229 — PCA-dim reduction flag on the R1 scoped per-country clustering path.

Freezes the "make Atlas lighter" seam: when ATLAS_CLUSTER_PCA_DIM /
--pca-dim > 0, `_country_clusters` feeds HDBSCAN the per-country PCA-reduced
coordinates (numpy SVD, renormalized — archive-engine PCA-128 precedent),
applied AFTER any whitening, while `_cluster_stats` (centroids/cohesion) and
`_apply_gate` (precision gate) keep receiving the RAW e5 embeddings. dim=0
(default) is a byte-identical passthrough (the nightly cron is untouched).

Also freezes the --as-of frozen-window plumbing the PCA harness pair relies on
(same corpus for both arms of a control/treated dry-run pair).

NOTE: run_scoped_snapshot imports emergent_poc which imports hdbscan at module
level — these tests run in the M1 mlvenv (which has hdbscan) and skip cleanly
in the API .venv.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("hdbscan")
pytest.importorskip("asyncpg")

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import backend.scripts.run_scoped_snapshot as rss  # noqa: E402
from backend.scripts.emergent_poc import (  # noqa: E402
    fit_pca_reduce, pca_reduce, whiten_all_but_top,
)


def _unit_rows(n: int = 24, dim: int = 16, seed: int = 229) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((n, dim)).astype(np.float32)
    return (x / np.linalg.norm(x, axis=1, keepdims=True)).astype(np.float32)


# ---------------------------------------------------------------- env parsing

def test_env_pca_dim_default_is_zero(monkeypatch):
    monkeypatch.delenv("ATLAS_CLUSTER_PCA_DIM", raising=False)
    assert rss._env_pca_dim() == 0


def test_env_pca_dim_parses_positive(monkeypatch):
    monkeypatch.setenv("ATLAS_CLUSTER_PCA_DIM", "128")
    assert rss._env_pca_dim() == 128


def test_env_pca_dim_garbage_and_negative_fall_to_zero(monkeypatch):
    monkeypatch.setenv("ATLAS_CLUSTER_PCA_DIM", "banana")
    assert rss._env_pca_dim() == 0
    monkeypatch.setenv("ATLAS_CLUSTER_PCA_DIM", "-128")
    assert rss._env_pca_dim() == 0


# ------------------------------------------------------------- the transform

def test_dim0_is_identity_passthrough():
    embs = _unit_rows()
    out = rss._pca_input(embs, 0)
    assert out is embs  # same object — zero-cost, byte-identical default path


def test_dim_ge_input_dim_is_noop():
    embs = _unit_rows(n=24, dim=16)
    assert pca_reduce(embs, 16) is embs
    assert pca_reduce(embs, 32) is embs


def test_n_le_dim_is_noop():
    # centered rank <= n-1 <= dim: pure rotation, zero speed win — skip.
    embs = _unit_rows(n=8, dim=16)
    assert pca_reduce(embs, 8) is embs
    assert pca_reduce(embs, 12) is embs


def test_reduction_shape_and_unit_norm():
    embs = _unit_rows(n=24, dim=16)
    out = rss._pca_input(embs, 8)
    assert out is not embs
    assert out.shape == (24, 8)
    assert out.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(out, axis=1), 1.0, atol=1e-5)


def test_fitted_components_are_orthonormal():
    embs = _unit_rows(n=24, dim=16)
    _mean, comps = fit_pca_reduce(embs, 8)
    assert comps.shape == (8, 16)
    np.testing.assert_allclose(comps @ comps.T, np.eye(8), atol=1e-5)


def test_matches_reference_svd_recipe():
    """The wired transform must be exactly: mean-center, project onto the
    top-dim principal directions (numpy SVD), L2-renormalize."""
    embs = _unit_rows(n=24, dim=16)
    mean = embs.mean(axis=0)
    x = embs - mean
    _, _, vt = np.linalg.svd(x, full_matrices=False)
    ref = x @ vt[:8].T
    n = np.linalg.norm(ref, axis=1, keepdims=True)
    n[n == 0] = 1.0
    ref = (ref / n).astype(np.float32)
    np.testing.assert_allclose(rss._pca_input(embs, 8), ref, atol=1e-5)


def test_lossless_dim_preserves_cosine_order():
    """When dim captures the full centered rank minus nothing meaningful
    (data generated inside a low-dim subspace), neighbor ORDER survives the
    reduction — the property HDBSCAN's euclidean-on-unit-sphere relies on."""
    rng = np.random.default_rng(7)
    basis, _ = np.linalg.qr(rng.standard_normal((16, 6)))
    coords = rng.standard_normal((30, 6)).astype(np.float32)
    embs = (coords @ basis.T.astype(np.float32))
    embs = (embs / np.linalg.norm(embs, axis=1, keepdims=True)).astype(np.float32)
    out = pca_reduce(embs, 8)  # 8 >= intrinsic dim 6 → lossless projection
    assert out.shape == (30, 8)
    # nearest-neighbor (excluding self) identical before/after
    def nn(m):
        sims = m @ m.T
        np.fill_diagonal(sims, -np.inf)
        return sims.argmax(axis=1)
    ref = embs - embs.mean(axis=0)
    ref = ref / np.linalg.norm(ref, axis=1, keepdims=True)
    np.testing.assert_array_equal(nn(out.astype(np.float64)),
                                  nn(ref.astype(np.float64)))


def test_composes_with_whitening():
    """--whiten-k and --pca-dim together: PCA applies AFTER whitening."""
    embs = _unit_rows(n=24, dim=16)
    composed = rss._pca_input(rss._whiten_input(embs, 1), 8)
    ref = pca_reduce(whiten_all_but_top(embs, 1), 8)
    assert composed.shape == (24, 8)
    np.testing.assert_allclose(composed, ref, atol=1e-6)


# --------------------------------------------- _country_clusters space wiring

class _FakeConn:
    """Models the keyset-paginated pull: one short (full-corpus) page — the
    `_fetch_country_embeddings` loop terminates after a single statement."""

    def __init__(self, recs):
        self._recs = recs
        self.calls: list[tuple] = []

    async def fetch(self, *args):
        self.calls.append(args)
        return self._recs


def _fake_records(n: int = 24, dim: int = 16):
    embs = _unit_rows(n, dim)
    recs = []
    for i in range(n):
        recs.append({
            "id": i + 1,
            "headline": f"Distinct scoped-cluster fixture headline number {i} for testing",
            "country_code": "US",
            "source_name": f"src-{i}",
            "timestamp": None,
            "emb": [float(v) for v in embs[i]],
        })
    return recs, embs


def _run_country_clusters(monkeypatch, whiten_k: int, pca_dim: int):
    recs, raw = _fake_records()
    seen: dict[str, np.ndarray] = {}

    def fake_cluster(embs, mcs, ms, sel):
        seen["cluster_input"] = embs
        return np.zeros(len(embs), dtype=int)  # one cluster, no noise

    def fake_stats(labels, embs, rows, top_k):
        seen["stats_embs"] = embs
        return [{"cluster_id": 0, "top_signal_idxs": [0]}]

    def fake_gate(clusters, embs, gate, min_kept, top_k):
        seen["gate_embs"] = embs
        return clusters

    monkeypatch.setattr(rss, "_cluster", fake_cluster)
    monkeypatch.setattr(rss, "_cluster_stats", fake_stats)
    monkeypatch.setattr(rss, "_apply_gate", fake_gate)

    res = asyncio.run(rss._country_clusters(
        _FakeConn(recs), "US", 168, 0, 3, 2, gate={}, min_kept=1, top_n=0,
        whiten_k=whiten_k, pca_dim=pca_dim))
    assert res is not None
    clusters, embs_out, rows = res
    return seen, embs_out, raw


def test_country_clusters_dim0_feeds_hdbscan_raw(monkeypatch):
    seen, embs_out, _raw = _run_country_clusters(monkeypatch, whiten_k=0, pca_dim=0)
    # HDBSCAN, stats and gate ALL see the same raw matrix object.
    assert seen["cluster_input"] is embs_out
    assert seen["stats_embs"] is embs_out
    assert seen["gate_embs"] is embs_out


def test_country_clusters_pca_reduces_hdbscan_input_only(monkeypatch):
    seen, embs_out, _raw = _run_country_clusters(monkeypatch, whiten_k=0, pca_dim=8)
    # HDBSCAN input is the reduced matrix...
    assert seen["cluster_input"].shape == (24, 8)
    np.testing.assert_allclose(seen["cluster_input"], pca_reduce(embs_out, 8),
                               atol=1e-5)
    # ...while stats (centroids) and the precision gate stay on RAW embeddings.
    assert seen["stats_embs"] is embs_out
    assert seen["gate_embs"] is embs_out


def test_country_clusters_whiten_then_pca_composition(monkeypatch):
    seen, embs_out, _raw = _run_country_clusters(monkeypatch, whiten_k=1, pca_dim=8)
    assert seen["cluster_input"].shape == (24, 8)
    np.testing.assert_allclose(
        seen["cluster_input"], pca_reduce(whiten_all_but_top(embs_out, 1), 8),
        atol=1e-5)
    assert seen["stats_embs"] is embs_out
    assert seen["gate_embs"] is embs_out


def test_country_clusters_returns_raw_embeddings(monkeypatch):
    """The returned embs (used downstream for _prepare_snapshot_rows →
    persisted centroid_vec) must be the raw parsed vectors, reduced or not."""
    for k, d in ((0, 0), (0, 8), (1, 8)):
        seen, embs_out, raw = _run_country_clusters(monkeypatch, whiten_k=k,
                                                    pca_dim=d)
        np.testing.assert_allclose(embs_out, raw, atol=1e-5)


# --------------------------------------------------- --as-of frozen window

def test_fetch_uses_as_of_as_cursor_and_cutoff():
    recs, _ = _fake_records(n=3)
    conn = _FakeConn(recs)
    as_of = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)
    asyncio.run(rss._fetch_country_embeddings(conn, "US", 168, 0, 500,
                                              as_of=as_of))
    (_sql, _cc, cutoff, _limit, last_ts, _last_id) = conn.calls[0]
    assert last_ts == as_of                      # keyset upper bound frozen
    assert cutoff == as_of - timedelta(hours=168)  # window lower bound frozen


def test_fetch_default_keeps_open_sentinel():
    recs, _ = _fake_records(n=3)
    conn = _FakeConn(recs)
    before = datetime.now(timezone.utc)
    asyncio.run(rss._fetch_country_embeddings(conn, "US", 168, 0, 500))
    (_sql, _cc, cutoff, _limit, last_ts, _last_id) = conn.calls[0]
    assert last_ts.year == 9999                  # open upper bound (live)
    assert cutoff >= before - timedelta(hours=168, seconds=5)
