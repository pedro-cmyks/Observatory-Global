"""Classical (Torgerson) metric MDS — the ONE distance-preserving layout.

Spec: docs/superpowers/specs/2026-07-22-constellation-3d-mds-design.md §2.

Two surfaces feed their OWN distance definition into this one solver:
  - per-story  : pairwise COSINE over the story centroid + its member bodies
  - dossier    : d(i,j) = clamp(1 - combined_edge_weight, 0, 1)

Positions produced here are a MEASURED claim (the distance you see IS the
distance measured), so every call also returns Kruskal stress-1 — the honest
distortion of squeezing high-dimensional distance into three axes. Cosine is
not perfectly Euclidean, so negative eigenvalues are clipped to 0 and the
error lands in `stress` instead of being hidden.

Pure + deterministic: numpy only (no scikit-learn), no random init, and an
explicit eigenvector sign convention so the same input always draws the same
picture on any machine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np

# Below three nodes MDS is degenerate (2 points are a line, trivially exact) —
# the caller falls back to its existing 2D layout with an honest note.
MIN_NODES = 3

# Fraction of the unit cube the normalized cloud fills. The margin keeps the
# outermost node off the panel edge without touching the (uniform) scale.
UNIT_FILL = 0.94


@dataclass(frozen=True)
class MdsResult:
    """coords: one [x, y, z] per input row, in the SAME units as the input
    distances. stress: Kruskal stress-1 over those raw coords (0 = exact)."""
    coords: list[list[float]]
    stress: float
    n: int


def cosine_distance_matrix(vectors: Sequence[Sequence[float]]) -> list[list[float]]:
    """Pairwise cosine distance (1 - cosine similarity). Zero vectors are
    guarded to distance 1 (maximally unrelated) rather than producing NaN."""
    M = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(M, axis=1, keepdims=True)
    norms[norms < 1e-12] = 1.0
    U = M / norms
    sim = np.clip(U @ U.T, -1.0, 1.0)
    D = np.maximum(1.0 - sim, 0.0)
    np.fill_diagonal(D, 0.0)
    return D.tolist()


def edge_weight_distance_matrix(
    ids: Sequence[str], edges: Iterable[dict[str, Any]],
) -> list[list[float]]:
    """Collapse measured edges into a distance matrix: d = 1 - weight.

    A pair with NO measured relation keeps the MAXIMUM distance (1.0) — honest
    absence, never a fabricated closeness. Duplicate pairs keep the strongest
    (= nearest) edge. Ids not in `ids` and self-pairs are ignored.
    """
    n = len(ids)
    index = {t: i for i, t in enumerate(ids)}
    D = [[0.0 if i == j else 1.0 for j in range(n)] for i in range(n)]
    for edge in edges:
        i = index.get(edge.get("a"))
        j = index.get(edge.get("b"))
        if i is None or j is None or i == j:
            continue
        weight = float(edge.get("weight") or 0.0)
        d = min(1.0, max(0.0, 1.0 - weight))
        if d < D[i][j]:
            D[i][j] = D[j][i] = d
    return D


def mds_3d(dist_matrix: Sequence[Sequence[float]]) -> MdsResult | None:
    """Classical metric MDS into 3 dimensions. None when degenerate (n < 3)."""
    D = np.asarray(dist_matrix, dtype=np.float64)
    if D.ndim != 2 or D.shape[0] != D.shape[1] or D.shape[0] < MIN_NODES:
        return None
    n = D.shape[0]
    D = np.maximum(0.5 * (D + D.T), 0.0)   # symmetric, non-negative
    np.fill_diagonal(D, 0.0)

    # Double-centre the squared distances: B = -1/2 · J · D² · J
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * (J @ (D ** 2) @ J)
    B = 0.5 * (B + B.T)                     # kill float asymmetry before eigh
    try:
        values, vectors = np.linalg.eigh(B)
    except np.linalg.LinAlgError:
        return None

    top = np.argsort(values)[::-1][:3]
    # Cosine is not perfectly Euclidean → negatives clipped; the error the clip
    # introduces shows up in `stress` below rather than being hidden.
    lam = np.clip(values[top], 0.0, None)
    V = np.array(vectors[:, top], dtype=np.float64)
    # Determinism: eigenvector SIGN is arbitrary per LAPACK build. Pin it so the
    # same story always draws the same constellation everywhere.
    for k in range(V.shape[1]):
        pivot = int(np.argmax(np.abs(V[:, k])))
        if V[pivot, k] < 0:
            V[:, k] = -V[:, k]
    X = V * np.sqrt(lam)

    return MdsResult(
        coords=[[round(float(v), 6) for v in row] for row in X],
        stress=_kruskal_stress_1(X, D),
        n=n,
    )


def to_unit_cube(coords: Sequence[Sequence[float]]) -> list[list[float]]:
    """Center on the cloud's mass and scale into [0,1]^3 with ONE factor for
    all three axes. Per-axis min-max would stretch the cloud anisotropically
    and silently break the distance claim — this keeps every ratio exact."""
    if len(coords) == 0:
        return []
    X = np.asarray(coords, dtype=np.float64)
    C = X - X.mean(axis=0)
    radius = float(np.abs(C).max())
    if radius < 1e-12:
        return [[0.5, 0.5, 0.5] for _ in range(X.shape[0])]
    U = 0.5 + 0.5 * UNIT_FILL * (C / radius)
    return [[round(float(v), 8) for v in row] for row in U]


def _kruskal_stress_1(coords: np.ndarray, D: np.ndarray) -> float:
    """√( Σ(d₃ᴅ − d_target)² / Σ d_target² ) over the upper triangle."""
    diff = coords[:, None, :] - coords[None, :, :]
    fitted = np.sqrt((diff ** 2).sum(-1))
    iu = np.triu_indices(D.shape[0], k=1)
    target = D[iu]
    denom = float((target ** 2).sum())
    if denom <= 1e-18:
        return 0.0
    return round(float(np.sqrt(((fitted[iu] - target) ** 2).sum() / denom)), 4)
