"""#229 — whitening flag on the R1 scoped per-country clustering path.

Freezes the harness-measured wiring (docs/research/recall-229/
2026-07-16-whitening-recall-harness.md): when ATLAS_CLUSTER_WHITEN_K /
--whiten-k > 0, `_country_clusters` feeds HDBSCAN the all-but-top(k) whitened
embeddings, while `_cluster_stats` (centroids/cohesion) and `_apply_gate`
(precision gate) keep receiving the RAW e5 embeddings — whitening is a
clustering-geometry lever, never a scoring/identity space. k=0 (default) is
a byte-identical passthrough (the nightly cron is untouched).

NOTE: run_scoped_snapshot imports emergent_poc which imports hdbscan at module
level — these tests run in the M1 mlvenv (which has hdbscan) and skip cleanly
in the API .venv.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("hdbscan")
pytest.importorskip("asyncpg")

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import backend.scripts.run_scoped_snapshot as rss  # noqa: E402
from backend.scripts.emergent_poc import whiten_all_but_top  # noqa: E402


def _unit_rows(n: int = 12, dim: int = 16, seed: int = 229) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((n, dim)).astype(np.float32)
    return (x / np.linalg.norm(x, axis=1, keepdims=True)).astype(np.float32)


# ---------------------------------------------------------------- env parsing

def test_env_whiten_k_default_is_zero(monkeypatch):
    monkeypatch.delenv("ATLAS_CLUSTER_WHITEN_K", raising=False)
    assert rss._env_whiten_k() == 0


def test_env_whiten_k_parses_positive(monkeypatch):
    monkeypatch.setenv("ATLAS_CLUSTER_WHITEN_K", "1")
    assert rss._env_whiten_k() == 1


def test_env_whiten_k_garbage_and_negative_fall_to_zero(monkeypatch):
    monkeypatch.setenv("ATLAS_CLUSTER_WHITEN_K", "banana")
    assert rss._env_whiten_k() == 0
    monkeypatch.setenv("ATLAS_CLUSTER_WHITEN_K", "-3")
    assert rss._env_whiten_k() == 0


# ------------------------------------------------------------- the transform

def test_k0_is_identity_passthrough():
    embs = _unit_rows()
    out = rss._whiten_input(embs, 0)
    assert out is embs  # same object — zero-cost, byte-identical default path


def test_k1_differs_from_raw_and_is_unit_norm():
    embs = _unit_rows()
    out = rss._whiten_input(embs, 1)
    assert out is not embs
    assert not np.allclose(out, embs, atol=1e-3)
    np.testing.assert_allclose(np.linalg.norm(out, axis=1), 1.0, atol=1e-5)


def test_k1_matches_harness_implementation_on_fixture():
    """The wired transform must be the SAME all-but-top(k) the harness measured:
    mean-center, project out the top-1 principal direction, L2-renormalize."""
    embs = _unit_rows()
    # Manual reference implementation (harness recipe).
    mean = embs.mean(axis=0)
    x = embs - mean
    _, _, vt = np.linalg.svd(x, full_matrices=False)
    top = vt[:1]
    ref = x - (x @ top.T) @ top
    n = np.linalg.norm(ref, axis=1, keepdims=True)
    n[n == 0] = 1.0
    ref = (ref / n).astype(np.float32)

    got = rss._whiten_input(embs, 1)
    np.testing.assert_allclose(got, ref, atol=1e-5)
    # And it is exactly the shared emergent_poc helper the harness imported.
    np.testing.assert_allclose(got, whiten_all_but_top(embs, 1), atol=1e-6)


# --------------------------------------------- _country_clusters space wiring

class _FakeConn:
    """Models the keyset-paginated pull: one short (full-corpus) page — the
    `_fetch_country_embeddings` loop terminates after a single statement."""

    def __init__(self, recs):
        self._recs = recs

    async def fetch(self, *_args):
        return self._recs


def _fake_records(n: int = 12, dim: int = 16):
    embs = _unit_rows(n, dim)
    recs = []
    for i in range(n):
        recs.append({
            "id": i + 1,
            "headline": f"Distinct scoped-cluster fixture headline number {i} for testing",
            "country_code": "US",
            "source_name": f"src-{i}",
            "timestamp": None,
            # binary-decoded float4[] (the paginated pull's se.vec::real[])
            "emb": [float(v) for v in embs[i]],
        })
    return recs, embs


def _run_country_clusters(monkeypatch, whiten_k: int):
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
        whiten_k=whiten_k))
    assert res is not None
    clusters, embs_out, rows = res
    return seen, embs_out, raw


def test_country_clusters_k0_feeds_hdbscan_raw(monkeypatch):
    seen, embs_out, _raw = _run_country_clusters(monkeypatch, whiten_k=0)
    # HDBSCAN, stats and gate ALL see the same raw matrix object.
    assert seen["cluster_input"] is embs_out
    assert seen["stats_embs"] is embs_out
    assert seen["gate_embs"] is embs_out


def test_country_clusters_k1_whitens_hdbscan_input_only(monkeypatch):
    seen, embs_out, _raw = _run_country_clusters(monkeypatch, whiten_k=1)
    # HDBSCAN input is the whitened matrix — a different array...
    assert seen["cluster_input"] is not embs_out
    np.testing.assert_allclose(
        seen["cluster_input"], whiten_all_but_top(embs_out, 1), atol=1e-5)
    # ...while stats (centroids) and the precision gate stay on RAW embeddings.
    assert seen["stats_embs"] is embs_out
    assert seen["gate_embs"] is embs_out


def test_country_clusters_returns_raw_embeddings(monkeypatch):
    """The returned embs (used downstream for _prepare_snapshot_rows →
    persisted centroid_vec) must be the raw parsed vectors, whitened or not."""
    for k in (0, 1):
        seen, embs_out, raw = _run_country_clusters(monkeypatch, whiten_k=k)
        # Same vectors as fetched (order preserved by the fixture: all rows
        # survive _clean_and_dedupe and keep their pull order).
        np.testing.assert_allclose(embs_out, raw, atol=1e-5)
