"""EXECUTE-1 (2026-07-19) — hard-killable clustering subprocess.

HDBSCAN's brute-MST Cython loop cannot be interrupted from Python (no signal
checks, GIL-independent C loop) — the 07-19 run sat INSIDE one country for 7+
hours with no way to stop it short of killing the whole run and losing the
night. The only true per-country wall-time guarantee is process isolation:
run the clustering call in a spawn child, join with a deadline, SIGTERM→SIGKILL
on overrun, raise ClusterTimeout so the caller can retry capped or record an
honest time-gap.

Data travels via .npy files in a private temp dir (never the pipe: a >64KB
queue put from a killed child is the classic multiprocessing deadlock).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.scripts.cluster_subproc import (  # noqa: E402
    ClusterTimeout,
    _error_child,
    _sleep_child,
    run_cluster_in_subprocess,
)


def _blob_embs(n_per: int = 30, dim: int = 8, seed: int = 7) -> np.ndarray:
    """Two well-separated unit-norm gaussian blobs — trivially clusterable."""
    rng = np.random.default_rng(seed)
    a = rng.normal(0, 0.02, (n_per, dim)) + np.eye(dim)[0]
    b = rng.normal(0, 0.02, (n_per, dim)) + np.eye(dim)[1]
    x = np.vstack([a, b]).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def test_subprocess_labels_match_inline_cluster():
    pytest.importorskip("hdbscan")  # parity needs the real clusterer
    from backend.scripts.emergent_poc import _cluster

    embs = _blob_embs()
    inline = np.asarray(_cluster(embs, 5, 2, "leaf"))
    sub = run_cluster_in_subprocess(embs, 5, 2, "leaf", timeout_s=120.0)
    assert sub.shape == inline.shape
    # HDBSCAN is deterministic on identical input/params → exact label parity
    assert (np.asarray(sub) == inline).all()


def test_timeout_kills_the_child_and_raises():
    embs = _blob_embs(n_per=3)
    t0 = time.monotonic()
    with pytest.raises(ClusterTimeout):
        run_cluster_in_subprocess(embs, 5, 2, "leaf", timeout_s=1.5,
                                  _target=_sleep_child)
    # the kill is prompt: nowhere near the child's 30s sleep
    assert time.monotonic() - t0 < 15.0


def test_child_error_surfaces_as_runtime_error():
    embs = _blob_embs(n_per=3)
    with pytest.raises(RuntimeError, match="boom-for-tests"):
        run_cluster_in_subprocess(embs, 5, 2, "leaf", timeout_s=30.0,
                                  _target=_error_child)


def test_zero_timeout_means_no_deadline():
    # timeout_s=0 → legacy unbounded behavior (still isolated, never killed).
    pytest.importorskip("hdbscan")
    embs = _blob_embs(n_per=10)
    labels = run_cluster_in_subprocess(embs, 5, 2, "leaf", timeout_s=0)
    assert labels.shape == (20,)
