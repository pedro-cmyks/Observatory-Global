"""Unit tests for the global e5 whitening helper (app/services/whitening.py).

Synthetic — no DB, no shipped artifact. Verifies the pure math: centering,
top-k projection removal, L2-normalization, single/batch shape, dim guard, and
npz round-trip via load_whitening.
"""
import numpy as np
import pytest

from app.services import whitening as W


def _mk(dim=8, k=2, seed=0):
    rng = np.random.default_rng(seed)
    mean = rng.standard_normal(dim).astype(np.float32)
    # Orthonormal top-k directions.
    comps, _ = np.linalg.qr(rng.standard_normal((dim, k)))
    comps = comps[:, :k].T.astype(np.float32)
    return W.Whitening(mean=mean, components=comps, k=k, dim=dim, fit_n=100, fit_at="t")


def test_output_is_unit_norm():
    w = _mk()
    x = np.random.default_rng(1).standard_normal((5, w.dim)).astype(np.float32)
    y = W.apply_whitening(x, w)
    assert y.shape == x.shape
    np.testing.assert_allclose(np.linalg.norm(y, axis=1), 1.0, atol=1e-5)


def test_removes_top_components():
    w = _mk()
    x = np.random.default_rng(2).standard_normal((6, w.dim)).astype(np.float32)
    y = W.apply_whitening(x, w)
    # Whitened vectors must have ~zero projection on each removed direction.
    proj = y @ w.components.T
    np.testing.assert_allclose(proj, 0.0, atol=1e-5)


def test_single_vector_shape():
    w = _mk()
    v = np.random.default_rng(3).standard_normal(w.dim).astype(np.float32)
    y = W.apply_whitening(v, w)
    assert y.ndim == 1 and y.shape[0] == w.dim
    np.testing.assert_allclose(np.linalg.norm(y), 1.0, atol=1e-5)


def test_k_zero_is_center_and_normalize_only():
    dim = 8
    w = W.Whitening(mean=np.zeros(dim, np.float32), components=np.zeros((0, dim), np.float32),
                    k=0, dim=dim, fit_n=1, fit_at="t")
    x = np.random.default_rng(4).standard_normal((4, dim)).astype(np.float32)
    y = W.apply_whitening(x, w)
    expected = x / np.linalg.norm(x, axis=1, keepdims=True)
    np.testing.assert_allclose(y, expected, atol=1e-5)


def test_dim_mismatch_raises():
    w = _mk(dim=8)
    with pytest.raises(ValueError):
        W.apply_whitening(np.zeros((3, 7), np.float32), w)


def test_whitened_cosine_via_dot():
    w = _mk()
    rng = np.random.default_rng(5)
    a = rng.standard_normal(w.dim).astype(np.float32)
    b = rng.standard_normal(w.dim).astype(np.float32)
    ya, yb = W.apply_whitening(a, w), W.apply_whitening(b, w)
    dot = float(ya @ yb)
    cos = dot / (np.linalg.norm(ya) * np.linalg.norm(yb))
    assert dot == pytest.approx(cos, abs=1e-5)   # unit-norm → dot == cosine
    assert -1.0 - 1e-5 <= dot <= 1.0 + 1e-5


def test_npz_roundtrip(tmp_path):
    w = _mk(dim=8, k=2)
    p = tmp_path / "wh.npz"
    np.savez(p, mean=w.mean, components=w.components, k=np.int64(w.k),
             dim=np.int64(w.dim), fit_n=np.int64(w.fit_n),
             fit_at=np.array(w.fit_at))
    loaded = W.load_whitening(str(p))
    assert loaded.k == w.k and loaded.dim == w.dim and loaded.fit_n == w.fit_n
    np.testing.assert_allclose(loaded.mean, w.mean)
    np.testing.assert_allclose(loaded.components, w.components)
    # Applying loaded transform matches the in-memory one.
    x = np.random.default_rng(6).standard_normal((3, w.dim)).astype(np.float32)
    np.testing.assert_allclose(W.apply_whitening(x, loaded), W.apply_whitening(x, w), atol=1e-6)
