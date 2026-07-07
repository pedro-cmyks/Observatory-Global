"""Global e5 whitening ("all-but-the-top" decompression) — shared read-time helper.

e5 embeddings (`signal_embeddings.vec`, `dynamic_topics.centroid_vec`) are
anisotropic: a dominant shared direction + a few rogue dims squash cosine into a
narrow ~0.88-0.97 band, so a fixed similarity threshold can't separate real
neighbors from noise. "All-but-the-top" whitening (Mu & Viswanath, 2017)
decompresses the space: subtract the corpus mean, project out the top-k
principal components, re-normalize.

This module loads the ONE global transform fitted + stored by
`scripts/fit_global_whitening.py` (artifact `app/data/e5_whitening.npz`) and
applies it. Fit once, apply consistently everywhere — vs the per-request refit
the dossier neighbors currently do.

ADOPTION IS PER-CONSUMER. This helper only transforms vectors; it does NOT set
any threshold. Every consumer (semantic-assignment taus, MATCH_THRESHOLD /
resurrection, HDBSCAN params, dossier SEM_EDGE_THRESHOLD, thread-coherence
tiers, semantic thread-members ANN, research semantic-lane taus, SignalDetail
HNSW) must RE-MEASURE its own threshold in whitened space before adopting.
Never a big-bang flip. See docs/research/embedding-whitening/.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass

import numpy as np

ARTIFACT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "e5_whitening.npz")

_lock = threading.Lock()
_cached: "Whitening | None" = None


@dataclass(frozen=True)
class Whitening:
    mean: np.ndarray        # float32[dim]
    components: np.ndarray  # float32[k][dim] — top-k principal directions to remove
    k: int
    dim: int
    fit_n: int
    fit_at: str

    def apply(self, vecs: np.ndarray) -> np.ndarray:
        return apply_whitening(vecs, self)


def load_whitening(path: str | None = None) -> Whitening:
    """Load + cache the global whitening transform. Thread-safe, load-once."""
    global _cached
    if _cached is not None and path is None:
        return _cached
    p = path or ARTIFACT_PATH
    with _lock:
        if _cached is not None and path is None:
            return _cached
        with np.load(p, allow_pickle=True) as z:
            w = Whitening(
                mean=np.asarray(z["mean"], dtype=np.float32),
                components=np.asarray(z["components"], dtype=np.float32),
                k=int(z["k"]),
                dim=int(z["dim"]),
                fit_n=int(z["fit_n"]),
                fit_at=str(z["fit_at"]),
            )
        if path is None:
            _cached = w
        return w


def apply_whitening(vecs: np.ndarray, w: Whitening | None = None) -> np.ndarray:
    """Center by mean, project out the stored top-k components, L2-normalize.

    Accepts a single vector (shape [dim]) or a batch (shape [n, dim]); returns
    the same shape. Output rows are unit-norm, so a plain dot product between two
    whitened vectors is their whitened cosine similarity.
    """
    if w is None:
        w = load_whitening()
    x = np.asarray(vecs, dtype=np.float32)
    single = x.ndim == 1
    if single:
        x = x[None, :]
    if x.shape[1] != w.dim:
        raise ValueError(f"whitening dim mismatch: got {x.shape[1]}, expected {w.dim}")
    y = x - w.mean
    if w.k > 0 and len(w.components):
        top = w.components[: w.k]
        y = y - (y @ top.T) @ top
    n = np.linalg.norm(y, axis=1, keepdims=True)
    n[n == 0] = 1.0
    y = y / n
    return y[0] if single else y
