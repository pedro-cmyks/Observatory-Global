# Constellation 3D — distance-preserving MDS layout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One distance-preserving 3D constellation — the spatial distance between two nodes IS their measured distance (classical metric MDS), rotatable with the universe's trackball — applied to the per-story view and the Workbench/Dossier pin cloud through one shared module.

**Architecture:** MDS runs on the BACKEND (`app/services/mds.py`, numpy only). Two endpoints gain an additive `pos3` per node + an `mds` block carrying the measured Kruskal stress-1. The frontend gets two shared pure/hook pieces — `lib/mds3d.ts` (projection, reusing `universeLayout`'s `Rot3`/`applyRot`/`depthScale`/`depthAlpha` verbatim) and `hooks/useTrackball.ts` (the universe's gesture layer, extracted and de-duplicated) — consumed by `ConstellationThreadView` (per-story, replaces the retired `OrbitalThreadView`) and `InvestigativeUniverse` (dossier report + compact Workbench).

**Tech Stack:** Python 3 / FastAPI / asyncpg / numpy / pgvector (backend); React 19 / TypeScript / vanilla CSS / vitest (frontend). No scikit-learn. No new data, no engine writes.

**Spec:** `docs/superpowers/specs/2026-07-22-constellation-3d-mds-design.md`

---

## Context an implementer needs (read this before Task 1)

Atlas is a narrative-intelligence system. Its product rule is **honesty over decoration**: every visual quantity must map to a measured engine number, and where a measurement is absent the UI says so instead of inventing something. This change makes *position itself* a measured claim, so the distortion of squeezing high-dimensional distance into 3D (`stress`) must be served and shown, never rounded away.

### Findings from the codebase survey (these resolve the spec's four open items)

1. **Per-story bodies carry NO vector.** `GET /api/v2/theme/{id}/orbital` (`backend/app/routers/themes.py:2277`) aggregates member *signals* into entity/country **bodies** (`build_orbital_bodies`, line 2174). Each body carries `dist` = the MEAN of its member signals' cosine distance to the topic centroid — a scalar, no vector. Pairwise cosine therefore needs a **new SQL aggregate** producing one mean embedding per body (Task 2). It is computed server-side by GROUP BY (≤36 vectors over the wire) — never by shipping every member vector (thousands × 768 floats).
2. **The dossier already emits ONE scalar per edge.** `POST /api/v2/dossier/connections` (`backend/app/routers/dossier.py:222`) builds `edges[].weight` as `max()` over the per-basis weights (semantic / shared_country / shared_person / text_mention / body_mention), clamped to 1.0 — `dossier.py:610-696`. So `d = clamp(1 − weight, 0, 1)` works directly on a scalar that already exists. The collapse (`max`) is stated explicitly in the payload's `mds.collapse` field, because the choice is itself a measurement decision.
3. **There is NO Orbits/Constellation toggle.** `ConstellationThreadView` (built 2026-07-17, commit `96e659d0`) is **never mounted** — grep shows zero importers. The live per-story surface is `OrbitalThreadView`, mounted inside `UniverseView` at `frontend-v2/src/components/UniverseView.tsx:461` (the "travel to the orbit inside the panel" path; `ThemeDetail`'s STORY SYSTEM was removed on 2026-07-02). Retiring Orbits therefore means: mount `ConstellationThreadView` in that slot and delete `OrbitalThreadView.tsx` + `.css`. `lib/orbitalLayout.ts` STAYS (it holds the shared `OrbitalBody`/`OrbitalWindow` types and the comet/drift/interaction helpers both views use).
4. **Stress threshold + scrubber** — Task 8 (measured against real stories and a real pin set after the backend deploy).

### Honesty rails (non-negotiable — do not "improve" these away)

- The stress number is ALWAYS served and ALWAYS shown. Above the threshold the label says "high distortion — rotate to see the real geometry".
- Unmeasured pairs sit at **maximum distance (1.0)**. Never fabricate proximity.
- A body with no vector is an "unplaced" chip — never a made-up coordinate.
- The dossier's per-edge basis chips, receipts and tier colours are **untouched**: position says *how related overall*, the edge says *why*.
- Normalization to the unit cube must be a **single uniform scale across all three axes**. Per-axis min-max would stretch the cloud anisotropically and silently destroy the distance claim.
- `UniverseView` stays PCA. `WalkConstellation` stays radial. Do not touch either layout.
- Tone stays OFF the star rims (it lives in the tone-of-coverage strip). That was a deliberate 2026-07-17 eval decision ("one variable per channel"); the 3D move does not reopen it.

### Environment

- Repo root: `/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal`, branch `v3-intel-layer` (canonical production branch).
- Backend tests: `cd backend && .venv/bin/python -m pytest tests/... -q`. **pytest startup can take ~2 minutes on this machine — use a 300000 ms timeout and do not assume a hang.**
- Frontend: `cd frontend-v2 && npx vitest run` and `npm run build` (Vite runs `tsc -b`, which is stricter than `tsc --noEmit` — a passing `--noEmit` is NOT sufficient). Node 24.
- Dev server proxies `/api` to the PRODUCTION backend (`https://atlas-api-pedro.fly.dev`) — see `frontend-v2/vite.config.ts:76`. So browser verification needs the backend deployed first.
- The repo working tree has unrelated modified/untracked files under `docs/research/label-court/` and `docs/research/atlas-paper/` (engine output churn). **Never `git add -A`.** Add only the exact files a task touches.

---

## File Structure

**Created**
- `backend/app/services/mds.py` — classical metric MDS + the two distance-matrix builders + unit-cube normalization. Pure, numpy-only.
- `backend/tests/test_mds.py` — MDS unit tests.
- `frontend-v2/src/lib/mds3d.ts` — pure projection of `pos3` → screen + stress wording.
- `frontend-v2/src/lib/mds3d.test.ts` — projection tests.
- `frontend-v2/src/hooks/useTrackball.ts` — the extracted gesture layer (rotate / roll / pan / zoom / pinch / tap / ambient spin).

**Modified**
- `backend/app/routers/themes.py` — per-body mean-vector query + `pos3` + `mds` on the orbital payload.
- `backend/tests/test_theme_orbital.py` — tests for the new pure layout helper.
- `backend/app/routers/dossier.py` — `pos3` + `mds` on the connections payload.
- `backend/tests/test_dossier_connections.py` — tests for the edge→distance collapse wiring.
- `frontend-v2/src/lib/orbitalLayout.ts` — `pos3` on `OrbitalBody`.
- `frontend-v2/src/lib/constellationLayout.ts` — extract `starStates()` (the non-positional star attributes) so 2D and 3D share them.
- `frontend-v2/src/lib/constellationLayout.test.ts` — tests for `starStates`.
- `frontend-v2/src/lib/dossierConnections.ts` — `pos3` on `ConnectionNode`, `mds` on `ConnectionsData`.
- `frontend-v2/src/components/ConstellationThreadView.tsx` + `.css` — 3D render, trackball, honesty label, unplaced chips.
- `frontend-v2/src/components/UniverseView.tsx` — use `useTrackball`; mount `ConstellationThreadView` in the story slot.
- `frontend-v2/src/components/DossierConnections.tsx` + `.css` — 3D positions from `pos3` with 2D fallback, trackball, honesty label.

**Deleted**
- `frontend-v2/src/components/OrbitalThreadView.tsx`
- `frontend-v2/src/components/OrbitalThreadView.css`

---

### Task 1: Backend — the shared MDS module

**Files:**
- Create: `backend/app/services/mds.py`
- Test: `backend/tests/test_mds.py`

Pure module, numpy only. `mds_3d` is classical (Torgerson) metric MDS: double-centre the squared-distance matrix, eigendecompose, take the top-3 eigenvectors scaled by √eigenvalue. Cosine distance is not perfectly Euclidean, so negative eigenvalues are **clipped to 0** and the resulting error surfaces in `stress` (Kruskal stress-1) rather than being hidden.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_mds.py`:

```python
"""Classical metric MDS — the distance-preserving 3D layout (spec
docs/superpowers/specs/2026-07-22-constellation-3d-mds-design.md §2).

Positions become a MEASURED claim here, so these tests pin the three
properties that claim rests on: exact geometry embeds at ~zero stress,
non-Euclidean input surfaces its error in `stress` instead of hiding it,
and normalization is a UNIFORM scale (distance ratios preserved).
"""
import math

from app.services.mds import (
    cosine_distance_matrix,
    edge_weight_distance_matrix,
    mds_3d,
    to_unit_cube,
)


def _pairwise(coords):
    out = []
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            out.append(math.dist(coords[i], coords[j]))
    return out


def test_regular_tetrahedron_embeds_exactly():
    # 4 mutually equidistant points ARE a 3D object — stress must be ~0.
    d = [[0.0 if i == j else 1.0 for j in range(4)] for i in range(4)]
    res = mds_3d(d)
    assert res is not None
    assert res.n == 4
    assert len(res.coords) == 4 and all(len(c) == 3 for c in res.coords)
    assert res.stress < 1e-6
    for got in _pairwise(res.coords):
        assert abs(got - 1.0) < 1e-6


def test_four_simplex_does_not_fit_and_says_so():
    # 5 mutually equidistant points need 4 dimensions. Squeezed into 3 they
    # MUST report real distortion — the honest number, not a hidden one.
    d = [[0.0 if i == j else 1.0 for j in range(5)] for i in range(5)]
    res = mds_3d(d)
    assert res is not None
    assert res.stress > 0.01
    assert all(math.isfinite(v) for c in res.coords for v in c)


def test_non_euclidean_input_clips_negative_eigenvalues():
    # Violates the triangle inequality (0-2 = 3 > 1 + 1) → the double-centred
    # matrix has a negative eigenvalue. Clipped to 0: finite coords, real stress.
    d = [
        [0.0, 1.0, 3.0, 1.0],
        [1.0, 0.0, 1.0, 1.0],
        [3.0, 1.0, 0.0, 1.0],
        [1.0, 1.0, 1.0, 0.0],
    ]
    res = mds_3d(d)
    assert res is not None
    assert all(math.isfinite(v) for c in res.coords for v in c)
    assert res.stress > 0.0


def test_degenerate_below_three_nodes_returns_none():
    assert mds_3d([]) is None
    assert mds_3d([[0.0]]) is None
    assert mds_3d([[0.0, 1.0], [1.0, 0.0]]) is None


def test_deterministic_same_input_same_output():
    d = [
        [0.0, 0.3, 0.7, 0.9],
        [0.3, 0.0, 0.5, 0.8],
        [0.7, 0.5, 0.0, 0.4],
        [0.9, 0.8, 0.4, 0.0],
    ]
    a = mds_3d(d)
    b = mds_3d(d)
    assert a is not None and b is not None
    assert a.coords == b.coords
    assert a.stress == b.stress


def test_cosine_distance_matrix_bounds_and_zero_guard():
    m = cosine_distance_matrix([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])
    assert m[0][0] == 0.0
    assert abs(m[0][1]) < 1e-9          # identical direction → distance 0
    assert abs(m[0][2] - 1.0) < 1e-9    # orthogonal → distance 1
    assert abs(m[0][3] - 1.0) < 1e-9    # zero vector guarded, never NaN
    for i in range(4):
        for j in range(4):
            assert m[i][j] == m[j][i]
            assert 0.0 <= m[i][j] <= 2.0


def test_edge_weight_matrix_unmeasured_pairs_sit_at_max_distance():
    ids = ["a", "b", "c"]
    edges = [{"a": "a", "b": "b", "weight": 0.75}]
    m = edge_weight_distance_matrix(ids, edges)
    assert m[0][0] == 0.0
    assert abs(m[0][1] - 0.25) < 1e-9
    assert m[0][2] == 1.0   # honest absence — never fabricated closeness
    assert m[1][2] == 1.0
    assert m[0][1] == m[1][0]


def test_edge_weight_matrix_ignores_unknown_ids_and_keeps_strongest():
    ids = ["a", "b"]
    edges = [
        {"a": "a", "b": "ghost", "weight": 0.9},   # not in the node set
        {"a": "a", "b": "b", "weight": 0.4},
        {"a": "b", "b": "a", "weight": 0.8},       # strongest wins → nearest
        {"a": "a", "b": "a", "weight": 1.0},       # self-pair ignored
    ]
    m = edge_weight_distance_matrix(ids, edges)
    assert abs(m[0][1] - 0.2) < 1e-9
    assert m[0][0] == 0.0


def test_edge_weight_matrix_clamps_out_of_range_weights():
    m = edge_weight_distance_matrix(["a", "b"], [{"a": "a", "b": "b", "weight": 1.4}])
    assert m[0][1] == 0.0
    m2 = edge_weight_distance_matrix(["a", "b"], [{"a": "a", "b": "b", "weight": -0.3}])
    assert m2[0][1] == 1.0


def test_to_unit_cube_is_a_uniform_scale_preserving_distance_ratios():
    coords = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 2.0]]
    u = to_unit_cube(coords)
    assert len(u) == 4 and all(len(c) == 3 for c in u)
    for c in u:
        for v in c:
            assert 0.0 <= v <= 1.0
    before = _pairwise(coords)
    after = _pairwise(u)
    ratio = after[0] / before[0]
    for b, a in zip(before, after):
        assert abs(a / b - ratio) < 1e-6   # ONE scale for all three axes


def test_to_unit_cube_handles_a_collapsed_cloud():
    u = to_unit_cube([[2.0, 2.0, 2.0]] * 3)
    assert all(c == [0.5, 0.5, 0.5] for c in u)
    assert to_unit_cube([]) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend && .venv/bin/python -m pytest tests/test_mds.py -q
```
Expected: collection error — `ModuleNotFoundError: No module named 'app.services.mds'`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/mds.py`:

```python
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
    return [[round(float(v), 5) for v in row] for row in U]


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
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd backend && .venv/bin/python -m pytest tests/test_mds.py -q
```
Expected: `12 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add backend/app/services/mds.py backend/tests/test_mds.py
git commit -m "feat(mds): classical metric MDS in numpy — distance-preserving 3D layout + Kruskal stress"
```

---

### Task 2: Backend — per-story `pos3` + `mds` on the orbital endpoint

**Files:**
- Modify: `backend/app/routers/themes.py` (after `build_orbital_bodies`, line ~2274, and inside `get_theme_orbital`, line ~2277-2433)
- Test: `backend/tests/test_theme_orbital.py`

The endpoint's bodies are *aggregations* of member signals, so each body needs a mean embedding. One extra grouped SQL query returns `body_id → mean vector`, keyed EXACTLY the way `build_orbital_bodies` builds ids (`country-<UPPER cc>`, `entity-<lower name>`), so the join is exact. The story centroid enters as node 0, which preserves "distance to the core" for free.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_theme_orbital.py`:

```python
def test_orbital_mds_layout_places_center_and_bodies():
    from app.routers.themes import orbital_mds_layout

    bodies = [
        {"id": "entity-a", "label": "A"},
        {"id": "entity-b", "label": "B"},
        {"id": "country-US", "label": "US"},
    ]
    centroid = [1.0, 0.0, 0.0, 0.0]
    vectors = {
        "entity-a": [1.0, 0.1, 0.0, 0.0],
        "entity-b": [0.0, 1.0, 0.0, 0.0],
        "country-US": [0.0, 0.0, 1.0, 0.0],
    }
    pos_by_id, center_pos, meta = orbital_mds_layout(bodies, centroid, vectors)

    assert set(pos_by_id) == {"entity-a", "entity-b", "country-US"}
    assert all(len(p) == 3 for p in pos_by_id.values())
    assert center_pos is not None and len(center_pos) == 3
    assert meta["basis"] == "cosine"
    assert meta["n"] == 4          # centroid + 3 bodies
    assert 0.0 <= meta["stress"] <= 2.0
    assert meta["unplaced"] == []
    # closest body to the centroid must also be nearest in the layout
    import math
    d_a = math.dist(center_pos, pos_by_id["entity-a"])
    d_b = math.dist(center_pos, pos_by_id["entity-b"])
    assert d_a < d_b


def test_orbital_mds_layout_reports_bodies_without_vectors_as_unplaced():
    from app.routers.themes import orbital_mds_layout

    bodies = [
        {"id": "entity-a", "label": "A"},
        {"id": "entity-b", "label": "B"},
        {"id": "entity-ghost", "label": "Ghost"},
    ]
    vectors = {"entity-a": [1.0, 0.0, 0.0], "entity-b": [0.0, 1.0, 0.0]}
    pos_by_id, center_pos, meta = orbital_mds_layout(bodies, [1.0, 1.0, 0.0], vectors)

    assert "entity-ghost" not in pos_by_id       # never a made-up coordinate
    assert meta["unplaced"] == ["entity-ghost"]
    assert center_pos is not None


def test_orbital_mds_layout_degenerates_honestly():
    from app.routers.themes import orbital_mds_layout

    # one body + centroid = 2 nodes → below MIN_NODES
    out = orbital_mds_layout(
        [{"id": "entity-a", "label": "A"}], [1.0, 0.0], {"entity-a": [0.0, 1.0]},
    )
    assert out == ({}, None, None)
    # no centroid at all
    assert orbital_mds_layout([{"id": "x"}], None, {"x": [1.0]}) == ({}, None, None)


def test_parse_vector_text_roundtrips():
    from app.routers.themes import _parse_vector_text, _vector_text

    assert _parse_vector_text(None) is None
    assert _parse_vector_text("") is None
    assert _parse_vector_text("[1.5,-0.25,0]") == [1.5, -0.25, 0.0]
    assert _parse_vector_text(_vector_text([0.5, 0.25])) == [0.5, 0.25]
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend && .venv/bin/python -m pytest tests/test_theme_orbital.py -q
```
Expected: FAIL — `ImportError: cannot import name 'orbital_mds_layout'`.

- [ ] **Step 3: Add the pure helpers**

In `backend/app/routers/themes.py`, immediately after `_vector_text` (line ~2157) add:

```python
def _parse_vector_text(text: str | None) -> list[float] | None:
    """pgvector text output ('[0.1,0.2,...]') → python floats."""
    if not text:
        return None
    body = text.strip().strip("[]")
    if not body:
        return None
    return [float(part) for part in body.split(",")]
```

Then, immediately after `build_orbital_bodies` (after line ~2274) add:

```python
# Per-body mean embedding, keyed EXACTLY as build_orbital_bodies builds body
# ids, so the join needs no second keying convention. Aggregating in SQL keeps
# the wire small (≤36 vectors) — shipping every member vector would be
# thousands × 768 floats across the WAN.
_BODY_VECTOR_SQL = """
WITH m AS (
    SELECT s.country_code, s.persons, se.vec::vector(768) AS v
    FROM signals_v2 s
    JOIN signal_embeddings se ON se.signal_id = s.id
    WHERE s.id = ANY($1::bigint[])
)
SELECT 'country-' || upper(btrim(country_code)) AS body_id, avg(v)::text AS vec
FROM m
WHERE btrim(COALESCE(country_code, '')) <> ''
GROUP BY 1
UNION ALL
SELECT 'entity-' || lower(btrim(p)) AS body_id, avg(v)::text AS vec
FROM m, LATERAL unnest(m.persons) AS p
WHERE btrim(COALESCE(p, '')) <> ''
GROUP BY 1
"""


def orbital_mds_layout(bodies, centroid_vec, body_vectors):
    """Distance-preserving 3D placement for one story (pure).

    Builds the pairwise COSINE matrix over [story centroid, *bodies with a
    vector], solves classical metric MDS, and normalizes with ONE uniform
    scale. Returns (pos3_by_body_id, center_pos3, mds_meta); (({}, None, None))
    when the layout is degenerate, so the caller falls back to the 2D radial
    view with an honest note. Bodies with no vector are NEVER given a made-up
    coordinate — they come back in meta['unplaced'].
    """
    from app.services.mds import (
        MIN_NODES, cosine_distance_matrix, mds_3d, to_unit_cube,
    )

    if not centroid_vec:
        return {}, None, None
    placed_ids = [b["id"] for b in bodies if body_vectors.get(b["id"])]
    unplaced = [b["id"] for b in bodies if not body_vectors.get(b["id"])]
    if len(placed_ids) + 1 < MIN_NODES:
        return {}, None, None

    matrix = cosine_distance_matrix(
        [list(centroid_vec)] + [body_vectors[i] for i in placed_ids])
    result = mds_3d(matrix)
    if result is None:
        return {}, None, None

    coords = to_unit_cube(result.coords)
    meta = {
        "stress": result.stress,
        "basis": "cosine",
        "n": result.n,
        "unplaced": unplaced,
        "note": (
            "3D positions are classical metric MDS over pairwise cosine "
            "distance between the story centroid and each body's MEAN member "
            "embedding. The per-body `dist` field stays the mean of its "
            "signals' individual distances to the centroid."
        ),
    }
    return dict(zip(placed_ids, coords[1:])), coords[0], meta
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd backend && .venv/bin/python -m pytest tests/test_theme_orbital.py -q
```
Expected: all pass (the 4 new tests plus the pre-existing ones).

- [ ] **Step 5: Wire the helpers into the endpoint**

In `get_theme_orbital`, replace the final block (currently lines ~2414-2430, from `bodies = build_orbital_bodies(...)` to the closing `}` of the success return) with:

```python
            bodies = build_orbital_bodies([dict(r) for r in rows])
            stamps = sorted(r["timestamp"] for r in rows)

            # Distance-preserving 3D layout. Best effort: any failure serves the
            # payload exactly as before (the frontend keeps its 2D radial view).
            pos_by_id: dict = {}
            center_pos3 = None
            mds_meta = None
            try:
                vec_rows = await conn.fetch(_BODY_VECTOR_SQL, member_ids)
                body_vectors = {
                    r["body_id"]: v
                    for r in vec_rows
                    if (v := _parse_vector_text(r["vec"])) is not None
                }
                pos_by_id, center_pos3, mds_meta = orbital_mds_layout(
                    bodies, _parse_vector_text(centroid_text), body_vectors)
            except Exception as exc:
                logger.warning("orbital mds layout failed for %s: %s", theme_code, exc)

            for b in bodies:
                pos = pos_by_id.get(b["id"])
                if pos is not None:
                    b["pos3"] = pos

            return {
                "contract": "orbital-thread-v0",
                "theme": theme_code,
                "hours": hours,
                "centroid_basis": centroid_basis,
                "center": {
                    **(center or {}),
                    "member_count": len(rows),
                    "pos3": center_pos3,
                    "window": {
                        "start": stamps[0].isoformat(),
                        "end": stamps[-1].isoformat(),
                    },
                },
                "bodies": bodies,
                "mds": mds_meta,
            }
```

- [ ] **Step 6: Run the touched neighbours**

```bash
cd backend && .venv/bin/python -m pytest tests/test_theme_orbital.py tests/test_mds.py -q
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add backend/app/routers/themes.py backend/tests/test_theme_orbital.py
git commit -m "feat(orbital): serve pos3 + measured MDS stress per story (cosine over body mean embeddings)"
```

---

### Task 3: Backend — dossier `pos3` + `mds` on the connections endpoint

**Files:**
- Modify: `backend/app/routers/dossier.py` (helper near `_project_positions` line ~197; wiring right after `edges.sort(...)` line ~704; payload line ~849-880)
- Test: `backend/tests/test_dossier_connections.py`

The endpoint already produces ONE combined scalar per edge (`weight` = `max` over the per-basis weights, `dossier.py:610-696`), so the collapse needs no new measurement — only an explicit statement of what it is. Per-edge basis chips, receipts and the existing PCA `pos` field are untouched.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_dossier_connections.py`:

```python
def test_connection_mds_positions_places_every_node():
    nodes = [
        {"id": "dynamic-topic-1", "pos": None},
        {"id": "dynamic-topic-2", "pos": None},
        {"id": "dynamic-topic-3", "pos": None},
    ]
    edges = [
        {"a": "dynamic-topic-1", "b": "dynamic-topic-2", "weight": 0.9},
        {"a": "dynamic-topic-2", "b": "dynamic-topic-3", "weight": 0.2},
    ]
    pos_by_id, meta = dossier._connection_mds_positions(nodes, edges)

    assert set(pos_by_id) == {f"dynamic-topic-{i}" for i in (1, 2, 3)}
    assert all(len(p) == 3 for p in pos_by_id.values())
    assert meta["basis"] == "edge-weight-6basis"
    assert meta["n"] == 3
    assert "max" in meta["collapse"]
    assert 0.0 <= meta["stress"] <= 2.0

    # the STRONGEST edge must be the SHORTEST distance in the layout
    import math
    strong = math.dist(pos_by_id["dynamic-topic-1"], pos_by_id["dynamic-topic-2"])
    weak = math.dist(pos_by_id["dynamic-topic-2"], pos_by_id["dynamic-topic-3"])
    assert strong < weak


def test_connection_mds_positions_degenerates_below_three_pins():
    nodes = [{"id": "a"}, {"id": "b"}]
    assert dossier._connection_mds_positions(nodes, []) == ({}, None)
    assert dossier._connection_mds_positions([], []) == ({}, None)


def test_connection_mds_unconnected_pin_sits_furthest_out():
    # An isolated pin has NO measured relation → maximum distance to everyone.
    nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "lonely"}]
    edges = [
        {"a": "a", "b": "b", "weight": 0.95},
        {"a": "b", "b": "c", "weight": 0.95},
        {"a": "a", "b": "c", "weight": 0.95},
    ]
    pos_by_id, meta = dossier._connection_mds_positions(nodes, edges)
    import math
    tight = math.dist(pos_by_id["a"], pos_by_id["b"])
    apart = math.dist(pos_by_id["a"], pos_by_id["lonely"])
    assert apart > tight
    assert meta is not None
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend && .venv/bin/python -m pytest tests/test_dossier_connections.py -q
```
Expected: FAIL — `AttributeError: module 'app.routers.dossier' has no attribute '_connection_mds_positions'`.

- [ ] **Step 3: Add the pure helper**

In `backend/app/routers/dossier.py`, immediately after `_project_positions` (after line ~219) add:

```python
def _connection_mds_positions(nodes: list[dict], edges: list[dict]) -> tuple[dict, dict | None]:
    """Distance-preserving 3D placement of the pinned stories (pure).

    The endpoint already collapses the six measured bases into ONE scalar per
    pair (`edge.weight` = max over the basis weights), so the distance is
    d = clamp(1 - weight, 0, 1) and a pair with NO measured relation keeps the
    maximum distance — honest absence, never fabricated closeness. Position
    encodes HOW related overall; the per-edge basis chips still carry WHY.
    """
    from app.services.mds import edge_weight_distance_matrix, mds_3d, to_unit_cube

    ids = [n["id"] for n in nodes]
    result = mds_3d(edge_weight_distance_matrix(ids, edges))
    if result is None:
        return {}, None
    coords = to_unit_cube(result.coords)
    meta = {
        "stress": result.stress,
        "basis": "edge-weight-6basis",
        "n": result.n,
        "collapse": (
            "d = 1 - max(per-basis edge weights); a pair with no measured "
            "relation keeps the maximum distance 1.0"
        ),
    }
    return dict(zip(ids, coords)), meta
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd backend && .venv/bin/python -m pytest tests/test_dossier_connections.py -q
```
Expected: all pass.

- [ ] **Step 5: Wire it into the endpoint**

In `dossier_connections`, directly after `edges.sort(key=lambda e: -e["weight"])` (line ~704) insert:

```python
    # Distance-preserving 3D layout over the measured edges. Best effort: a
    # failure leaves the payload exactly as before (the frontend keeps its 2D
    # field), never a 500.
    mds_meta = None
    try:
        pos3_by_id, mds_meta = _connection_mds_positions(nodes, edges)
        for n in nodes:
            pos3 = pos3_by_id.get(n["id"])
            if pos3 is not None:
                n["pos3"] = pos3
    except Exception as exc:
        logger.warning("dossier connections mds layout failed: %s", exc)
```

Then in the `payload` dict (line ~849) add `"mds": mds_meta,` immediately after `"neighbors": neighbors,`, and inside `payload["meta"]` add, right after the existing `"position_basis"` entry:

```python
            "position_basis_3d": "classical metric MDS over d = 1 - combined edge weight; spatial distance IS the measured relation, `mds.stress` is the distortion",
```

- [ ] **Step 6: Run the touched neighbours**

```bash
cd backend && .venv/bin/python -m pytest tests/test_dossier_connections.py tests/test_connections_body_mention.py tests/test_mds.py -q
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add backend/app/routers/dossier.py backend/tests/test_dossier_connections.py
git commit -m "feat(dossier): serve pos3 + measured MDS stress over the combined edge weight"
```

---

### Task 4: Frontend — `lib/mds3d.ts` (pure projection + stress wording)

**Files:**
- Create: `frontend-v2/src/lib/mds3d.ts`
- Create: `frontend-v2/src/lib/mds3d.test.ts`
- Modify: `frontend-v2/src/lib/orbitalLayout.ts` (add `pos3` to `OrbitalBody`)
- Modify: `frontend-v2/src/lib/dossierConnections.ts` (add `pos3` to `ConnectionNode`, `mds` to `ConnectionsData`)

The projection math is the universe's, reused verbatim: `applyRot` / `depthScale` / `depthAlpha` from `universeLayout.ts` (already pure and unit-tested). This module adds only the perspective divide, the screen mapping and the honest stress wording.

Note on `STRESS_HIGH`: 0.20 is the spec's starting proposal. Task 8 replaces it with a value measured on real stories and a real pin set. Leave the constant in ONE place so that swap is a one-line change.

- [ ] **Step 1: Write the failing tests**

Create `frontend-v2/src/lib/mds3d.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { IDENTITY_ROT, rotY } from './universeLayout'
import {
  STRESS_HIGH,
  centerOfMass,
  perspectiveSpread,
  projectPos3,
  screenXY,
  stressPct,
  stressTier,
  type Pos3,
} from './mds3d'

const CENTER = { cx: 0.5, cy: 0.5, cz: 0.5 }

describe('centerOfMass', () => {
  it('averages the cloud', () => {
    const c = centerOfMass([[0, 0, 0], [1, 1, 1]] as Pos3[])
    expect(c).toEqual({ cx: 0.5, cy: 0.5, cz: 0.5 })
  })
  it('falls back to the cube center when empty', () => {
    expect(centerOfMass([])).toEqual({ cx: 0.5, cy: 0.5, cz: 0.5 })
  })
})

describe('projectPos3', () => {
  it('is the identity at rest with no perspective', () => {
    const p = projectPos3([0.25, 0.75, 0.5], IDENTITY_ROT, CENTER, 0)
    expect(p.px).toBeCloseTo(0.25, 9)
    expect(p.py).toBeCloseTo(0.75, 9)
    expect(p.scale).toBeCloseTo(1, 9)
  })

  it('preserves distance under rotation (the whole point of MDS)', () => {
    const a: Pos3 = [0.2, 0.3, 0.4]
    const b: Pos3 = [0.8, 0.6, 0.4]
    const dist = (r: typeof IDENTITY_ROT) => {
      const pa = projectPos3(a, r, CENTER, 0)
      const pb = projectPos3(b, r, CENTER, 0)
      return Math.hypot(pa.px - pb.px, pa.py - pb.py, pa.depth - pb.depth)
    }
    expect(dist(rotY(0.9))).toBeCloseTo(dist(IDENTITY_ROT), 9)
  })

  it('turns the cloud: a half turn about Y mirrors x', () => {
    const p = projectPos3([0.9, 0.5, 0.5], rotY(Math.PI), CENTER, 0)
    expect(p.px).toBeCloseTo(0.1, 6)
  })

  it('perspective brings near bodies forward and pushes far ones back', () => {
    const near = projectPos3([0.9, 0.5, 0.1], IDENTITY_ROT, CENTER, 1)
    const far = projectPos3([0.9, 0.5, 0.9], IDENTITY_ROT, CENTER, 1)
    expect(near.scale).toBeGreaterThan(1)
    expect(far.scale).toBeLessThan(1)
    expect(Math.abs(near.px - 0.5)).toBeGreaterThan(Math.abs(far.px - 0.5))
  })
})

describe('perspectiveSpread', () => {
  it('is orthographic at rest and grows with zoom, capped', () => {
    expect(perspectiveSpread(1)).toBe(0)
    expect(perspectiveSpread(0.5)).toBe(0)
    expect(perspectiveSpread(2)).toBeCloseTo(0.8, 9)
    expect(perspectiveSpread(99)).toBeCloseTo(1.6, 9)
  })
})

describe('screenXY', () => {
  it('maps normalized coords into the padded canvas and honours pan/zoom', () => {
    const box = { w: 500, h: 300, margin: 50, view: { k: 1, tx: 0, ty: 0 } }
    expect(screenXY({ px: 0, py: 0 }, box)).toEqual({ sx: 50, sy: 50 })
    expect(screenXY({ px: 1, py: 1 }, box)).toEqual({ sx: 450, sy: 250 })
    const zoomed = screenXY({ px: 0, py: 0 }, { ...box, view: { k: 2, tx: 10, ty: -5 } })
    expect(zoomed).toEqual({ sx: 110, sy: 95 })
  })
})

describe('stress wording', () => {
  it('tiers the measured distortion', () => {
    expect(stressTier(0)).toBe('exact')
    expect(stressTier(0.02)).toBe('exact')
    expect(stressTier(0.1)).toBe('good')
    expect(stressTier(STRESS_HIGH)).toBe('high')
    expect(stressTier(0.9)).toBe('high')
  })
  it('reports whole percent, never rounding the number away', () => {
    expect(stressPct(0.1449)).toBe(14)
    expect(stressPct(0)).toBe(0)
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend-v2 && npx vitest run src/lib/mds3d.test.ts
```
Expected: FAIL — cannot resolve `./mds3d`.

- [ ] **Step 3: Write the implementation**

Create `frontend-v2/src/lib/mds3d.ts`:

```ts
/**
 * Shared 3D constellation projection (pure).
 * Spec: docs/superpowers/specs/2026-07-22-constellation-3d-mds-design.md §3
 *
 * The backend solves classical metric MDS and serves `pos3` per node, so the
 * SPATIAL distance between two nodes IS their measured distance. This module
 * only turns those coordinates into screen space: the rotation math is the
 * universe's (`applyRot` / `depthScale` / `depthAlpha` — already pure and
 * unit-tested, reused verbatim), plus a perspective divide and the honest
 * wording for the served distortion.
 *
 * Because positions are now a measured claim, `stress` is never optional and
 * never rounded away: above STRESS_HIGH the surface says so in words.
 */
import { applyRot, depthAlpha, depthScale, type Rot3 } from './universeLayout'

export type Pos3 = [number, number, number]

/** The `mds` block served alongside the nodes. */
export interface Mds3dMeta {
  /** Kruskal stress-1 — the measured distortion of the 3D squeeze. */
  stress: number
  /** What the distance MEANS on this surface ('cosine' | 'edge-weight-6basis'). */
  basis: string
  n: number
  /** Story path: bodies with no vector — rendered as chips, never placed. */
  unplaced?: string[]
  /** Dossier path: how the six bases collapse into the one scalar. */
  collapse?: string
  note?: string
}

export interface Projected {
  /** Normalized screen-frame coords (0..1 before pan/zoom). */
  px: number
  py: number
  /** 0 = nearest … 1 = furthest. Painter order + depth cues. */
  depth: number
  /** Perspective size factor (>1 near, <1 far). */
  scale: number
}

export interface CloudCenter3 { cx: number; cy: number; cz: number }

/** Rotation axis = the cloud's center of mass, so it never orbits an
 *  external point (the universe's "rota como por fuera" lesson). */
export function centerOfMass(points: Pos3[]): CloudCenter3 {
  if (points.length === 0) return { cx: 0.5, cy: 0.5, cz: 0.5 }
  let sx = 0, sy = 0, sz = 0
  for (const p of points) { sx += p[0]; sy += p[1]; sz += p[2] }
  const n = points.length
  return { cx: sx / n, cy: sy / n, cz: sz / n }
}

/** Perspective strengthens with zoom; at k ≤ 1 the view is orthographic —
 *  the honest map, where screen distance is exactly measured distance. */
export function perspectiveSpread(k: number): number {
  return Math.min(1.6, Math.max(0, (k - 1) * 0.8))
}

export function projectPos3(
  pos: Pos3, rot: Rot3, center: CloudCenter3, spread: number,
): Projected {
  const p = applyRot(rot, pos[0], pos[1], pos[2], center.cx, center.cy, center.cz)
  const scale = 1 / (1 + (p.depth - 0.5) * 2.4 * spread)
  return {
    px: 0.5 + (p.px - 0.5) * scale,
    py: 0.5 + (p.py - 0.5) * scale,
    depth: p.depth,
    scale,
  }
}

export interface ScreenBox {
  w: number
  h: number
  margin: number
  view: { k: number; tx: number; ty: number }
}

/** Normalized projection → canvas pixels, with the surface's pan/zoom. */
export function screenXY(p: { px: number; py: number }, box: ScreenBox): { sx: number; sy: number } {
  const { w, h, margin, view } = box
  return {
    sx: (margin + p.px * (w - 2 * margin)) * view.k + view.tx,
    sy: (margin + p.py * (h - 2 * margin)) * view.k + view.ty,
  }
}

/**
 * Distortion bands. STRESS_HIGH is MEASURED, not guessed: calibrated against
 * real stories and real pin sets (see the plan's Task 8 and the spec addendum).
 */
export const STRESS_EXACT = 0.05
export const STRESS_HIGH = 0.20

export type StressTier = 'exact' | 'good' | 'high'

export function stressTier(stress: number): StressTier {
  if (stress >= STRESS_HIGH) return 'high'
  if (stress <= STRESS_EXACT) return 'exact'
  return 'good'
}

export function stressPct(stress: number): number {
  return Math.floor(stress * 100)
}

/** The honest sentence for a served stress value. */
export function stressNote(stress: number): string {
  const tier = stressTier(stress)
  if (tier === 'high') return 'high distortion — rotate to see the real geometry'
  if (tier === 'exact') return 'near-exact — this geometry is trustworthy'
  return 'low distortion'
}

export { depthAlpha, depthScale }
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd frontend-v2 && npx vitest run src/lib/mds3d.test.ts
```
Expected: all pass.

- [ ] **Step 5: Extend the payload types**

In `frontend-v2/src/lib/orbitalLayout.ts`, inside `interface OrbitalBody` (after the `moon_overlap?: number` line) add:

```ts
  /** Distance-preserving 3D position (classical MDS over pairwise cosine,
      served by the backend). Absent when the body has no member embedding —
      it is then listed in the payload's `mds.unplaced`, never placed. */
  pos3?: [number, number, number]
```

In `frontend-v2/src/lib/dossierConnections.ts`, inside `interface ConnectionNode` (after `pos: { x: number; y: number } | null`) add:

```ts
  /** Distance-preserving 3D position (classical MDS over d = 1 − combined
      edge weight). Spatial distance IS the measured relation; `mds.stress`
      carries the distortion. */
  pos3?: [number, number, number]
```

and inside `interface ConnectionsData` (after `neighbors?: ConnectionNeighbor[]`) add:

```ts
  /** Measured 3D-layout distortion + what the distance means (null when the
      layout is degenerate — the field then falls back to the 2D placement). */
  mds?: Mds3dMeta | null
```

with the import at the top of the file:

```ts
import type { Mds3dMeta } from './mds3d'
```

- [ ] **Step 6: Verify types and the whole suite**

```bash
cd frontend-v2 && npx vitest run && npm run build
```
Expected: all tests pass, build succeeds.

- [ ] **Step 7: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add frontend-v2/src/lib/mds3d.ts frontend-v2/src/lib/mds3d.test.ts frontend-v2/src/lib/orbitalLayout.ts frontend-v2/src/lib/dossierConnections.ts
git commit -m "feat(mds3d): shared pure 3D projection + payload types for pos3/mds"
```

---

### Task 5: Frontend — extract `hooks/useTrackball.ts` from `UniverseView`

**Files:**
- Create: `frontend-v2/src/hooks/useTrackball.ts`
- Modify: `frontend-v2/src/components/UniverseView.tsx` (state/refs at lines ~73-162, handlers at lines ~530-643, RESET button ~520-527)

This is a **behaviour-preserving extraction**, not a redesign. The universe is the flagship surface; the hook must reproduce its gesture layer exactly so both constellations get the one working implementation. Everything below already exists inline in `UniverseView` — move it, do not re-invent it:

- drag = trackball orbit (`mul3(mul3(rotX(-dy*0.006), rotY(dx*0.006)), r)`), premultiplied so roll emerges from combined drags and there is no gimbal lock
- alt/ctrl/meta drag or `navMode === 'roll'` = roll (`rotZ(dx * 0.01)`)
- shift / right / middle button drag or `navMode === 'pan'` = pan
- two fingers = pan + pinch-zoom + twist→roll about the midpoint
- wheel = zoom about the cursor
- a pointer-up that never moved >5px = a TAP (pointer capture eats SVG `onClick`, so the tap is hit-tested by the consumer via `onTap`)
- ambient spin at ~10fps that stops while dragging, while hovering, while `document.hidden`, while the panel is CSS-hidden (`offsetParent === null`), and after 90s without interaction — the thermal discipline from the 2026-07-03 kernel-panic post-mortem
- `reset()` returns rotation to identity and the view to `{k:1,tx:0,ty:0}`

- [ ] **Step 1: Write the hook**

Create `frontend-v2/src/hooks/useTrackball.ts`:

```ts
/**
 * The shared trackball: free 3D rotation + zoom/pan gestures for a normalized
 * point cloud. Extracted verbatim from UniverseView (2026-07-03 "roll
 * disponible 3D... para donde sea") so the universe, the story constellation
 * and the investigation cloud all share ONE working implementation.
 *
 * Orientation is an accumulated 3×3 matrix (arcball), never Euler angles: no
 * gimbal lock, no clamp, any orientation.
 *
 * Thermal discipline (2026-07-03 kernel-panic post-mortem — a 60fps re-render
 * of a large SVG is exactly the compositor load that tripped the WindowServer
 * watchdog): ambient spin ticks at ~10fps, stops while dragging or hovering,
 * while the tab is hidden, while the PANEL is CSS-hidden (display:none does not
 * set document.hidden), and rests after 90s of no interaction.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent, type RefObject, type WheelEvent } from 'react'
import { IDENTITY_ROT, mul3, rotX, rotY, rotZ, type Rot3 } from '../lib/universeLayout'

export interface TrackballView { k: number; tx: number; ty: number }

export interface UseTrackballOptions {
  /** The canvas element — used for cursor-relative zoom, tap coordinates and
      the CSS-hidden check. */
  containerRef: RefObject<HTMLDivElement | null>
  /** Drag intent when no modifier is held. */
  navMode?: 'rotate' | 'pan' | 'roll'
  minZoom?: number
  maxZoom?: number
  /** Multiplier per wheel notch. */
  wheelStep?: number
  /** Ambient yaw when idle. Off by default: only the universe spins by itself. */
  ambient?: boolean
  /** External pause (a hover card is open, another view covers this one). */
  paused?: boolean
  /** A press that never moved: canvas-local coordinates of the tap. */
  onTap?: (lx: number, ly: number) => void
}

export interface Trackball {
  rot: Rot3
  setRot: React.Dispatch<React.SetStateAction<Rot3>>
  view: TrackballView
  setView: React.Dispatch<React.SetStateAction<TrackballView>>
  reset: () => void
  /** True while a drag/pinch is in flight (callers pause their own animation). */
  isDragging: () => boolean
  handlers: {
    onWheel: (e: WheelEvent<HTMLDivElement>) => void
    onPointerDown: (e: PointerEvent<HTMLDivElement>) => void
    onPointerMove: (e: PointerEvent<HTMLDivElement>) => void
    onPointerUp: (e: PointerEvent<HTMLDivElement>) => void
    onPointerLeave: (e: PointerEvent<HTMLDivElement>) => void
    onContextMenu: (e: { preventDefault: () => void }) => void
    onDragStart: (e: { preventDefault: () => void }) => void
  }
}

const DEFAULT_VIEW: TrackballView = { k: 1, tx: 0, ty: 0 }
/** Ambient yaw ≈ one turn per 105s. */
const AMBIENT_RATE = 0.06
const AMBIENT_TICK_MS = 100
const REST_AFTER_MS = 90_000
const TAP_SLOP_PX = 5

export function useTrackball({
  containerRef,
  navMode = 'rotate',
  minZoom = 0.6,
  maxZoom = 8,
  wheelStep = 1.12,
  ambient = false,
  paused = false,
  onTap,
}: UseTrackballOptions): Trackball {
  const [rot, setRot] = useState<Rot3>(IDENTITY_ROT)
  const [view, setView] = useState<TrackballView>(DEFAULT_VIEW)

  const draggingRef = useRef(false)
  const lastInteractionRef = useRef(performance.now())
  const dragRef = useRef<{
    lastX: number; lastY: number; downX: number; downY: number
    moved: boolean; mode: 'orbit' | 'roll' | 'pan'
  } | null>(null)
  const pointersRef = useRef<Map<number, { x: number; y: number }>>(new Map())
  const pinchRef = useRef<{ dist: number; cx: number; cy: number; tx: number; ty: number; k: number; angle: number } | null>(null)
  const viewRef = useRef(view)
  viewRef.current = view
  const pausedRef = useRef(paused)
  pausedRef.current = paused
  const onTapRef = useRef(onTap)
  onTapRef.current = onTap

  const clampZoom = useCallback(
    (k: number) => Math.min(maxZoom, Math.max(minZoom, k)),
    [maxZoom, minZoom],
  )

  const localPoint = useCallback((clientX: number, clientY: number) => {
    const rect = containerRef.current?.getBoundingClientRect()
    return { lx: clientX - (rect?.left ?? 0), ly: clientY - (rect?.top ?? 0) }
  }, [containerRef])

  const reset = useCallback(() => {
    setRot(IDENTITY_ROT)
    setView(DEFAULT_VIEW)
    lastInteractionRef.current = performance.now()
  }, [])

  useEffect(() => {
    if (!ambient) return
    let raf = 0
    let last = performance.now()
    let acc = 0
    const tick = (now: number) => {
      acc += now - last
      last = now
      if (acc >= AMBIENT_TICK_MS) {
        const resting = now - lastInteractionRef.current > REST_AFTER_MS
        // display:none does NOT set document.hidden — without this check the
        // SVG kept re-rendering behind a hidden mobile panel (battery burn).
        const panelHidden = containerRef.current !== null
          && containerRef.current.offsetParent === null
        if (!pausedRef.current && !draggingRef.current && !document.hidden && !resting && !panelHidden) {
          setRot(r => mul3(rotY((acc / 1000) * AMBIENT_RATE), r))
        }
        acc = 0
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [ambient, containerRef])

  const handlers = useMemo(() => ({
    onWheel: (e: WheelEvent<HTMLDivElement>) => {
      e.preventDefault()
      lastInteractionRef.current = performance.now()
      const factor = e.deltaY < 0 ? wheelStep : 1 / wheelStep
      const { lx, ly } = localPoint(e.clientX, e.clientY)
      setView(v => {
        const k = clampZoom(v.k * factor)
        return { k, tx: lx - (lx - v.tx) * (k / v.k), ty: ly - (ly - v.ty) * (k / v.k) }
      })
    },

    onPointerDown: (e: PointerEvent<HTMLDivElement>) => {
      e.preventDefault()
      try { (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId) } catch { /* synthetic/inactive pointer */ }
      draggingRef.current = true
      lastInteractionRef.current = performance.now()
      pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
      if (pointersRef.current.size === 2) {
        const pts = [...pointersRef.current.values()]
        pinchRef.current = {
          dist: Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y),
          cx: (pts[0].x + pts[1].x) / 2,
          cy: (pts[0].y + pts[1].y) / 2,
          angle: Math.atan2(pts[1].y - pts[0].y, pts[1].x - pts[0].x),
          tx: viewRef.current.tx, ty: viewRef.current.ty, k: viewRef.current.k,
        }
        dragRef.current = null
      } else {
        const mode: 'orbit' | 'roll' | 'pan' =
          (navMode === 'pan' || e.shiftKey || e.button === 2 || e.button === 1) ? 'pan'
          : (navMode === 'roll' || e.altKey || e.ctrlKey || e.metaKey) ? 'roll'
          : 'orbit'
        dragRef.current = {
          lastX: e.clientX, lastY: e.clientY,
          downX: e.clientX, downY: e.clientY, moved: false, mode,
        }
      }
    },

    onPointerMove: (e: PointerEvent<HTMLDivElement>) => {
      if (pointersRef.current.has(e.pointerId)) {
        pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
      }
      if (pinchRef.current && pointersRef.current.size === 2) {
        const pts = [...pointersRef.current.values()]
        const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y)
        const cx = (pts[0].x + pts[1].x) / 2
        const cy = (pts[0].y + pts[1].y) / 2
        const angle = Math.atan2(pts[1].y - pts[0].y, pts[1].x - pts[0].x)
        const p = pinchRef.current
        setView({
          k: clampZoom(p.k * (dist / Math.max(1, p.dist))),
          tx: p.tx + (cx - p.cx),
          ty: p.ty + (cy - p.cy),
        })
        const dRoll = angle - p.angle
        if (Math.abs(dRoll) > 1e-4) setRot(r => mul3(rotZ(dRoll), r))
        pinchRef.current = { ...p, angle }
        lastInteractionRef.current = performance.now()
        return
      }
      const d = dragRef.current
      if (!d) return
      lastInteractionRef.current = performance.now()
      const dx = e.clientX - d.lastX
      const dy = e.clientY - d.lastY
      d.lastX = e.clientX; d.lastY = e.clientY
      if (Math.hypot(e.clientX - d.downX, e.clientY - d.downY) > TAP_SLOP_PX) d.moved = true
      if (d.mode === 'pan') {
        setView(v => ({ ...v, tx: v.tx + dx, ty: v.ty + dy }))
      } else if (d.mode === 'roll') {
        setRot(r => mul3(rotZ(dx * 0.01), r))
      } else {
        // free trackball orbit: screen-space incremental rotation, premultiplied
        // → no fixed up-vector, roll emerges from combined drags
        setRot(r => mul3(mul3(rotX(-dy * 0.006), rotY(dx * 0.006)), r))
      }
    },

    onPointerUp: (e: PointerEvent<HTMLDivElement>) => {
      const d = dragRef.current
      if (d && !d.moved && pointersRef.current.size === 1) {
        const { lx, ly } = localPoint(e.clientX, e.clientY)
        onTapRef.current?.(lx, ly)
      }
      pointersRef.current.delete(e.pointerId)
      if (pointersRef.current.size < 2) pinchRef.current = null
      if (pointersRef.current.size === 0) { dragRef.current = null; draggingRef.current = false }
    },

    onPointerLeave: (e: PointerEvent<HTMLDivElement>) => {
      pointersRef.current.delete(e.pointerId)
      if (pointersRef.current.size === 0) {
        pinchRef.current = null; dragRef.current = null; draggingRef.current = false
      }
    },

    onContextMenu: (e: { preventDefault: () => void }) => e.preventDefault(),
    onDragStart: (e: { preventDefault: () => void }) => e.preventDefault(),
  }), [clampZoom, localPoint, navMode, wheelStep])

  return {
    rot, setRot, view, setView, reset,
    isDragging: () => draggingRef.current,
    handlers,
  }
}
```

- [ ] **Step 2: Migrate `UniverseView` onto the hook**

In `frontend-v2/src/components/UniverseView.tsx`:

(a) Add the import next to the existing ones:

```ts
import { useTrackball } from '../hooks/useTrackball'
```

(b) DELETE these now-owned-by-the-hook declarations (lines ~73, ~90, ~94-101): `const [view, setView] = useState(...)`, `const [rot, setRot] = useState<Rot3>(IDENTITY_ROT)`, `spinPausedRef`, `draggingRef`, `dragRef`, `pointersRef`, `pinchRef`, and the whole ambient-spin `useEffect` (lines ~132-162 including `lastInteractionRef`) and the `useEffect` that syncs `spinPausedRef` from `hoveredId` (lines ~164-166).

(c) After `hitTestBody` is defined (it must exist before the hook call — move the `useTrackball` call to just after `hitTestBody`, i.e. after line ~307), insert:

```ts
    // The ONE gesture layer (shared with the story + investigation clouds).
    // Ambient spin stops while a story system covers the field.
    const trackball = useTrackball({
        containerRef,
        navMode,
        minZoom: 0.6,
        maxZoom: 8,
        wheelStep: 1.12,
        ambient: !orbitalVisible,
        paused: hoveredId !== null,
        onTap: (lx, ly) => {
            const hit = hitTestBody(lx, ly)
            // Clicking the ALREADY-open thread re-enters its system
            // (onThemeSelect no-ops when the theme is unchanged).
            if (hit && hit === activeTheme) setOrbitalVisible(true)
            // Item 8: pass the node's REAL label with the id — the opener knows
            // it; downstream must never re-derive a generic from the raw id.
            else if (hit) onThemeSelect(hit, allNodes.find(n => n.id === hit)?.label)
        },
    })
    const { rot, setRot, view, setView } = trackball
```

Because `rot`/`view` are now declared after the code that used them at lines ~250-307 (`px`, `py`, `project3`, `projected`, `hitTestBody`), move the `useTrackball` call to just BEFORE the `const margin = 46` line (~250) and keep `hitTestBody` where it is — instead pass the tap handler through a ref so the hook does not need `hitTestBody` at construction time:

```ts
    // hitTestBody is defined below (it needs `projected`); route the tap through
    // a ref so the hook can be constructed before it.
    const tapRef = useRef<(lx: number, ly: number) => void>(() => {})
    const trackball = useTrackball({
        containerRef, navMode,
        minZoom: 0.6, maxZoom: 8, wheelStep: 1.12,
        ambient: !orbitalVisible,
        paused: hoveredId !== null,
        onTap: (lx, ly) => tapRef.current(lx, ly),
    })
    const { rot, setRot, view, setView } = trackball
```

and immediately after `hitTestBody`'s definition add:

```ts
    tapRef.current = (lx: number, ly: number) => {
        const hit = hitTestBody(lx, ly)
        if (hit && hit === activeTheme) setOrbitalVisible(true)
        else if (hit) onThemeSelect(hit, allNodes.find(n => n.id === hit)?.label)
    }
```

(d) Replace the canvas handler props (lines ~533-643) with:

```tsx
                {...trackball.handlers}
```

keeping `className`, `ref={attachCanvas}` as they are.

(e) The RESET button (line ~520) calls the hook's reset:

```tsx
                    onClick={() => trackball.reset()}
```

(replacing whatever inline `setRot(IDENTITY_ROT)` / `setView(...)` pair it currently uses — keep the existing label, tip and class).

(f) `setRot` is still imported-and-used by nothing else; make sure the now-unused imports (`IDENTITY_ROT`, `rotX`, `rotY`, `rotZ`, `mul3`) are removed from the `universeLayout` import list **only if** no other line in the file uses them. `applyRot` IS still used (travel + focus framing) — keep it.

- [ ] **Step 3: Verify the build and the suite**

```bash
cd frontend-v2 && npx vitest run && npm run build
```
Expected: all tests pass, build succeeds with no unused-import errors.

- [ ] **Step 4: Browser-verify the universe did not regress**

```bash
cd frontend-v2 && npm run dev
```
Open `http://localhost:3000/app`, switch the map panel to the UNIVERSE tab, and confirm: drag rotates the cloud; alt-drag rolls; shift-drag pans; wheel zooms about the cursor; ⌖ RESET restores; clicking a body opens its story; the console is clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add frontend-v2/src/hooks/useTrackball.ts frontend-v2/src/components/UniverseView.tsx
git commit -m "refactor(universe): extract useTrackball — one shared gesture layer for every 3D cloud"
```

---

### Task 6: Frontend — 3D story constellation; retire Orbits

**Files:**
- Modify: `frontend-v2/src/lib/constellationLayout.ts` (+ `constellationLayout.test.ts`)
- Modify: `frontend-v2/src/components/ConstellationThreadView.tsx` + `.css`
- Modify: `frontend-v2/src/components/UniverseView.tsx` (the story slot at line ~461 and the `◉ TO ORBIT` button at ~500)
- Delete: `frontend-v2/src/components/OrbitalThreadView.tsx`, `frontend-v2/src/components/OrbitalThreadView.css`

`ConstellationThreadView` currently places stars on a radial (`placeConstellation`). The 3D path replaces the POSITION source only; every other measured channel is conserved: co-occurrence edges, entity-type colours, moons, ignition core, comet dashes, drift streaks, the time scrubber, hover receipts, and the tone-of-coverage strip. **Tone stays off the star rims** — that was a deliberate eval decision, not an oversight.

The scrubber STAYS (decision, spec open item 4): rotation is a *camera* gesture on the canvas, the scrubber is a *time* control below it — they occupy different controls and different axes, exactly as the universe already carries both.

- [ ] **Step 1: Write the failing test for the extracted star state**

Append to `frontend-v2/src/lib/constellationLayout.test.ts`:

```ts
describe('starStates', () => {
  const window_ = { start: '2026-07-01T00:00:00Z', end: '2026-07-08T00:00:00Z' }
  const body = {
    id: 'entity-a', label: 'A', type: 'person' as const, n: 4, dist: 0.1,
    first_seen: '2026-07-02T00:00:00Z', last_seen: '2026-07-03T00:00:00Z',
    timestamps: ['2026-07-02T00:00:00Z', '2026-07-03T00:00:00Z'],
    moon_of: 'entity-b',
  }

  it('carries the same measured attributes the 2D placement uses', () => {
    const t = Date.parse('2026-07-03T00:00:00Z')
    const [s] = starStates([body], t, window_)
    const [p] = placeConstellation([body], t, { cx: 0, cy: 0, rMin: 1, rMax: 2, ex: 1, ey: 1 }, window_)
    expect(s.alpha).toBeCloseTo(p.alpha, 12)
    expect(s.ignition).toBeCloseTo(p.ignition, 12)
    expect(s.comet).toBe(p.comet)
    expect(s.moonParentId).toBe('entity-b')
  })

  it('hides a star before it is first seen', () => {
    const [s] = starStates([body], Date.parse('2026-07-01T00:00:00Z'), window_)
    expect(s.alpha).toBe(0)
  })
})
```

Add `starStates` to the file's existing import from `./constellationLayout`.

- [ ] **Step 2: Run it to verify it fails**

```bash
cd frontend-v2 && npx vitest run src/lib/constellationLayout.test.ts
```
Expected: FAIL — `starStates` is not exported.

- [ ] **Step 3: Extract `starStates` and reuse it in `placeConstellation`**

In `frontend-v2/src/lib/constellationLayout.ts`, add before `placeConstellation`:

```ts
/** The non-positional, measured attributes of a star at a scrubbed moment.
 *  Shared by the 2D radial fallback and the 3D MDS render so both read the
 *  same numbers from the same place. */
export interface StarState {
    body: OrbitalBody
    /** Presence opacity (birth + decay, floor 0.14 — the field's PRESENCE_FLOOR). */
    alpha: number
    /** Cumulative-activity luminosity [0,1] at the scrubbed moment. */
    ignition: number
    comet: boolean
    moon: boolean
    /** Parent star id when this is a co-occurrence satellite. */
    moonParentId: string | null
}

export function starStates(
    bodies: OrbitalBody[], scrubT: number, window_: OrbitalWindow,
): StarState[] {
    return bodies.map(body => ({
        body,
        alpha: presenceAlphaField(body, scrubT),
        ignition: ignitionGlow(body, scrubT),
        comet: isComet(body, window_),
        moon: !!body.moon_of,
        moonParentId: body.moon_of ?? null,
    }))
}
```

and rewrite `placeConstellation`'s body to build on it (behaviour unchanged):

```ts
export function placeConstellation(
    bodies: OrbitalBody[],
    scrubT: number,
    geom: ConstellationGeom,
    window_: OrbitalWindow,
): PlacedStar[] {
    const { cx, cy, rMin, rMax, ex, ey } = geom
    return starStates(bodies, scrubT, window_).map(state => {
        const frac = radiusFraction(state.body.dist)
        const r = orbitRadius(frac, rMin, rMax)
        const a = seedAngle(state.body.id)
        return {
            ...state,
            x: cx + r * ex * Math.cos(a),
            y: cy + r * ey * Math.sin(a),
            distFraction: frac,
        }
    })
}
```

and change `interface PlacedStar` to `export interface PlacedStar extends StarState { x: number; y: number; distFraction: number }`.

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd frontend-v2 && npx vitest run src/lib/constellationLayout.test.ts
```
Expected: all pass.

- [ ] **Step 5: Render the 3D constellation**

In `frontend-v2/src/components/ConstellationThreadView.tsx`:

(a) Extend the payload interface:

```ts
interface ConstellationPayload {
    contract: string
    theme: string
    centroid_basis?: 'stored' | 'computed'
    center: {
        label: string
        category: string | null
        crisis_relevant: boolean | null
        member_count: number
        window: OrbitalWindow
        pos3?: [number, number, number] | null
    } | null
    bodies: OrbitalBody[]
    mds?: Mds3dMeta | null
    reason?: string
}
```

(b) Imports to add:

```ts
import { starStates, type StarState } from '../lib/constellationLayout'
import {
    centerOfMass, depthAlpha, depthScale, perspectiveSpread, projectPos3,
    screenXY, stressNote, stressPct, type Mds3dMeta, type Pos3,
} from '../lib/mds3d'
import { useTrackball } from '../hooks/useTrackball'
```

(c) Replace the bespoke zoom/pan state (`const [view, setView] = useState({k:1,tx:0,ty:0})`, `panRef`, and the inline `onWheel`/`onPointer*` props on `.constellation-canvas`) with the shared trackball:

```ts
    const trackball = useTrackball({
        containerRef,
        minZoom: 0.6, maxZoom: 10, wheelStep: 1.2,
        // No ambient spin here: the universe already spins, and a second
        // always-animating SVG is exactly the compositor load the 2026-07-03
        // post-mortem told us to avoid. Drag to rotate.
        ambient: false,
        paused: hovered !== null,
    })
    const view = trackball.view
```

and on the canvas div: `{...trackball.handlers}` plus `style={{ cursor: 'grab' }}`; the reset button becomes `onClick={() => trackball.reset()}` and renders when `view.k !== 1 || trackball.rot !== IDENTITY_ROT` — simplest honest condition: always render it (a rotation is as resettable as a zoom), tip `"Reset rotation and zoom"`.

(d) Compute the 3D placement (keeping the 2D radial as the fallback):

```ts
    const mds = payload?.mds ?? null
    const placedIn3d = useMemo(() => bodies.filter(b => b.pos3), [bodies])
    const use3d = !!mds && placedIn3d.length >= 2 && !!payload?.center?.pos3

    // Rotation axis = the cloud's center of mass (core included), so the story
    // never orbits an external point.
    const cloudCenter = useMemo(
        () => centerOfMass([
            ...(payload?.center?.pos3 ? [payload.center.pos3 as Pos3] : []),
            ...placedIn3d.map(b => b.pos3 as Pos3),
        ]),
        [payload, placedIn3d],
    )
    const spread = perspectiveSpread(view.k)
    const box = { w: width, h: height, margin: 54, view }

    const states: StarState[] = useMemo(
        () => (window_ ? starStates(bodies, scrubT, window_) : []),
        [bodies, scrubT, window_],
    )

    /** Star with its projected screen position + depth cues (3D path). */
    const stars3d = useMemo(() => {
        if (!use3d) return []
        return states
            .filter(s => s.body.pos3)
            .map(s => {
                const p = projectPos3(s.body.pos3 as Pos3, trackball.rot, cloudCenter, spread)
                const { sx, sy } = screenXY(p, box)
                return { ...s, x: sx, y: sy, depth: p.depth, scale: p.scale }
            })
            // painter order: draw far bodies first so near ones sit on top
            .sort((a, b) => b.depth - a.depth)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [use3d, states, trackball.rot, cloudCenter, spread, width, height, view])

    const core3d = useMemo(() => {
        if (!use3d || !payload?.center?.pos3) return null
        const p = projectPos3(payload.center.pos3 as Pos3, trackball.rot, cloudCenter, spread)
        return { ...screenXY(p, box), depth: p.depth, scale: p.scale }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [use3d, payload, trackball.rot, cloudCenter, spread, width, height, view])
```

(e) In the SVG, when `use3d` is true render from `stars3d` and `core3d` instead of `placed`/`cx,cy`:
- the outer `<g transform={...}>` zoom wrapper is DROPPED on the 3D path (pan/zoom already ride in `screenXY`); keep it for the 2D fallback,
- hub spokes go from `core3d.sx/sy` to each star,
- co-occurrence edges look their parent up in a `Map` built from `stars3d`,
- drift streaks use the radial direction from `core3d` (unchanged semantics: outward = receding),
- star radius is `universeRadius(n) * depthScale(depth) * scale`, opacity `alpha * depthAlpha(depth)`,
- the anchor star renders at `core3d.sx/sy`.

Keep the 2D branch intact so a payload without `mds` renders exactly as today.

(f) Honesty label — replace the `constellation-legend-note` span with:

```tsx
                {mds ? (
                    <span
                        className={`constellation-legend-note constellation-stress--${stressTier(mds.stress)}`}
                        data-tip="Positions are classical metric MDS over the measured cosine distances between the story core and each body's mean embedding. Distortion is Kruskal stress-1 — the honest error of squeezing high-dimensional distance into three axes. Drag to rotate."
                    >
                        distance ≈ semantic similarity · 3D distortion {stressPct(mds.stress)}% — {stressNote(mds.stress)}
                    </span>
                ) : (
                    <span className="constellation-legend-note" data-tip="No 3D layout for this story (too few placed bodies or no embeddings) — showing the fixed radial view: radius = measured cosine distance to the core.">
                        fixed scale · comparable across stories{payload.centroid_basis === 'computed' ? ' · computed centroid' : ''}
                    </span>
                )}
```

(g) Unplaced chips — after the legend, when `mds?.unplaced?.length`:

```tsx
            {mds && mds.unplaced && mds.unplaced.length > 0 && (
                <div className="constellation-unplaced" aria-label="Bodies without a measured position">
                    <span
                        className="constellation-unplaced-label"
                        data-tip="These bodies have no member embedding, so there is no measured distance to place them by. They are listed, never drawn at an invented coordinate."
                    >
                        unplaced ({mds.unplaced.length})
                    </span>
                    {mds.unplaced.slice(0, 8).map(id => {
                        const b = bodies.find(x => x.id === id)
                        return <span key={id} className="constellation-unplaced-chip">{b ? bodyLabel(b) : id}</span>
                    })}
                </div>
            )}
```

(h) Add to `ConstellationThreadView.css` (following the file's existing dark-canvas conventions):

```css
/* Unplaced bodies: measured absence, listed not drawn. */
.constellation-unplaced {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    font-size: 10px;
    color: #94a3b8;
}
.constellation-unplaced-label {
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748b;
    border-bottom: 1px dotted #475569;
    cursor: help;
}
.constellation-unplaced-chip {
    padding: 1px 6px;
    border: 1px dashed rgba(148, 163, 184, 0.45);
    border-radius: 8px;
}
/* The measured distortion drives the wording AND the colour. */
.constellation-stress--exact { color: #34d399; }
.constellation-stress--good { color: #94a3b8; }
.constellation-stress--high { color: #fbbf24; }
```

- [ ] **Step 6: Mount it and retire Orbits**

In `frontend-v2/src/components/UniverseView.tsx`:
- change the import at line 32 to `import { ConstellationThreadView } from './ConstellationThreadView'`
- at line ~461 replace `<OrbitalThreadView ... />` with `<ConstellationThreadView theme={activeTheme} themeLabel={orbitLabel} hours={hours} onCountrySelect={onCountrySelect} onPersonSelect={onPersonSelect} />`
- rename the return-to-story button (line ~500) label `◉ TO ORBIT` → `◉ TO STORY` and its tip to `"Return to the open story's constellation"`
- rename the local state `orbitalVisible`/`setOrbitalVisible` is fine to keep (internal), but update the `universe-orbit-back` tip if it says "orbit": keep `← UNIVERSE` and its existing tip.

Then delete the retired files:

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git rm frontend-v2/src/components/OrbitalThreadView.tsx frontend-v2/src/components/OrbitalThreadView.css
grep -rn "OrbitalThreadView" frontend-v2/src || echo "no importers left"
```
Expected: only CSS comments referencing the old filename remain (update those comment lines to name `ConstellationThreadView.css` instead).

- [ ] **Step 7: Verify**

```bash
cd frontend-v2 && npx vitest run && npm run build
```
Expected: all pass, build clean.

- [ ] **Step 8: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add -u frontend-v2/src
git add frontend-v2/src/components/ConstellationThreadView.tsx frontend-v2/src/components/ConstellationThreadView.css frontend-v2/src/lib/constellationLayout.ts frontend-v2/src/lib/constellationLayout.test.ts frontend-v2/src/components/UniverseView.tsx
git commit -m "feat(story): 3D distance-preserving constellation replaces the orbital view"
```

---

### Task 7: Frontend — 3D investigation cloud (Dossier + Workbench)

**Files:**
- Modify: `frontend-v2/src/components/DossierConnections.tsx` (`InvestigativeUniverse`, lines ~395-671) + `DossierConnections.css`

`InvestigativeUniverse` is ALREADY the shared renderer — the dossier report mounts it directly and `WorkbenchConstellation` mounts it with `compact`. So the change is one component: source positions from `pos3` when the payload carries them, keep `layoutInvestigativeUniverse` as the fallback, and add the trackball + honesty label. Neighbours keep their existing placement math (barycenter for bridges, outward fan for singles) — it already reads pin positions, so it follows the rotation for free.

**Do not touch** the edge tier colours, edge tags, receipts, hover card, cluster rings, or the "Nearby unpinned stories" list.

- [ ] **Step 1: Add the 3D placement**

In `InvestigativeUniverse`, replace the `placed` memo (line ~405) with:

```tsx
  const containerRef = useRef<HTMLDivElement | null>(null)
  const trackball = useTrackball({
    containerRef,
    minZoom: 0.6, maxZoom: 8, wheelStep: 1.15,
    ambient: false,          // an investigation cloud must hold still to be read
    paused: hover !== null,
  })
  const mds = data.mds ?? null
  const use3d = !!mds && data.nodes.every(n => n.pos3)

  const cloud3 = useMemo(
    () => centerOfMass(data.nodes.map(n => (n.pos3 ?? [0.5, 0.5, 0.5]) as Pos3)),
    [data.nodes],
  )

  const placed = useMemo(() => {
    if (!use3d) return layoutInvestigativeUniverse(data.nodes, data.edges, UNIVERSE_W, UNIVERSE_H)
    const spread = perspectiveSpread(trackball.view.k)
    const box = { w: UNIVERSE_W, h: UNIVERSE_H, margin: 40, view: trackball.view }
    return data.nodes.map(n => {
      const p = projectPos3(n.pos3 as Pos3, trackball.rot, cloud3, spread)
      const { sx, sy } = screenXY(p, box)
      return { ...n, px: sx, py: sy, depth: p.depth, scale: p.scale }
    })
  }, [use3d, data, trackball.rot, trackball.view, cloud3])
```

Type: widen the local placement type to `Array<PlacedNode & { depth?: number; scale?: number }>`.

Wrap the `<svg>` in the gesture div (keeping the existing classes on the svg itself):

```tsx
      <div
        className={`dcx-universe-stage${compact ? ' dcx-universe-stage--compact' : ''}`}
        ref={containerRef}
        {...(use3d ? trackball.handlers : {})}
        style={use3d ? { cursor: 'grab', touchAction: 'none', userSelect: 'none' } : undefined}
      >
        <svg viewBox={...} ...> ... </svg>
      </div>
```

Apply depth cues to the pin circles only (edges and labels stay legible):

```tsx
              <circle r={r * (n.scale ?? 1) * (n.depth !== undefined ? depthScale(n.depth) : 1)}
                      style={{ fill: n.category ? categoryColor(n.category) : '#7dd3fc' }}
                      fillOpacity={n.depth !== undefined ? depthAlpha(n.depth) : 1}
                      stroke={isolated ? '#64748b' : clusterColor(ci)}
                      strokeWidth={active ? 2.5 : 1.5} />
```

Draw pins far-to-near so near ones sit on top: iterate `[...placed].sort((a, b) => (b.depth ?? 0) - (a.depth ?? 0))` in the pins block only (the `labelY` memo keeps using `placed` — label lanes are independent of paint order).

- [ ] **Step 2: Swap the position claim in the legend**

In the `!compact` header block replace the line `<span>position ≈ semantic field · closer = more alike</span>` with:

```tsx
            {use3d && mds ? (
              <span
                className={`dcx-stress dcx-stress--${stressTier(mds.stress)}`}
                data-tip="Positions are classical metric MDS over the combined measured edge weight (d = 1 − weight; a pair with no measured relation sits at maximum distance). Distortion is Kruskal stress-1. The WHY of any link stays on the edge itself — drag to rotate."
              >
                distance ≈ measured relation (6 bases) · the why is on each edge · distortion {stressPct(mds.stress)}% — {stressNote(mds.stress)}
              </span>
            ) : (
              <span data-tip="Fewer than 3 pins, or no measured layout — positions here are an approximate field; the edges carry the exact relation.">position ≈ semantic field · closer = more alike</span>
            )}
```

For the compact Workbench variant add a single line under the svg:

```tsx
      {compact && use3d && mds && (
        <div
          className={`dcx-stress dcx-stress--compact dcx-stress--${stressTier(mds.stress)}`}
          data-tip="Distance between pins IS their measured relation (classical MDS over the combined edge weight). This is the distortion of showing it in 3D. Drag to rotate."
        >
          distance = measured relation · distortion {stressPct(mds.stress)}%
        </div>
      )}
```

Add the imports at the top of `DossierConnections.tsx`:

```ts
import { useTrackball } from '../hooks/useTrackball'
import {
  centerOfMass, depthAlpha, depthScale, perspectiveSpread, projectPos3,
  screenXY, stressNote, stressPct, stressTier, type Pos3,
} from '../lib/mds3d'
```

- [ ] **Step 3: CSS**

Append to `frontend-v2/src/components/DossierConnections.css`:

```css
/* 3D stage: the gesture surface wrapping the constellation svg. */
.dcx-universe-stage { position: relative; touch-action: none; }
.dcx-universe-stage--compact { max-height: 300px; }
/* Measured distortion — the honest companion to a positional claim. */
.dcx-stress { cursor: help; }
.dcx-stress--exact { color: #34d399; }
.dcx-stress--good { color: #94a3b8; }
.dcx-stress--high { color: #fbbf24; }
.dcx-stress--compact {
    padding: 2px 8px 6px;
    font-size: 9.5px;
    letter-spacing: 0.04em;
}
```

- [ ] **Step 4: Verify**

```bash
cd frontend-v2 && npx vitest run && npm run build
```
Expected: all pass, build clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add frontend-v2/src/components/DossierConnections.tsx frontend-v2/src/components/DossierConnections.css
git commit -m "feat(dossier): investigation cloud placed by measured relation (3D MDS) + distortion label"
```

---

### Task 8: Deploy, calibrate the stress threshold, browser-verify

**Files:**
- Modify: `frontend-v2/src/lib/mds3d.ts` (the `STRESS_HIGH` constant, if the measurement moves it)
- Modify: `docs/superpowers/specs/2026-07-22-constellation-3d-mds-design.md` (measured addendum)

- [ ] **Step 1: Deploy the backend**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal && ./scripts/deploy-fly-api.sh
```

- [ ] **Step 2: Smoke both endpoints**

```bash
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/threads?hours=24&limit=5' | jq -r '.threads[].thread_id'
```
then for one of those ids:
```bash
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/theme/<ID>/orbital?hours=168' \
  | jq '{mds, center_pos3: .center.pos3, placed: [.bodies[] | select(.pos3)] | length, bodies: (.bodies|length)}'
```
Expected: `mds.stress` a real number, `mds.basis == "cosine"`, `center.pos3` a 3-array, most bodies carrying `pos3`.

```bash
curl -s -X POST 'https://atlas-api-pedro.fly.dev/api/v2/dossier/connections' \
  -H 'Content-Type: application/json' \
  -d '{"topic_ids":["<ID1>","<ID2>","<ID3>"]}' \
  | jq '{mds, pos3: [.nodes[].pos3]}'
```
(Use three real thread ids from the threads call; check the request field name against `ConnectionsRequest` in `backend/app/routers/dossier.py` before sending.)
Expected: `mds.basis == "edge-weight-6basis"`, `mds.collapse` present, every node carrying `pos3`.

- [ ] **Step 3: Calibrate the threshold**

Measure `mds.stress` across **at least 8 real stories** (mix of small and large member counts) and **at least 2 real pin sets** (3-pin and 5+-pin). Record every number. Then set `STRESS_HIGH` so that the "high distortion" wording fires only where the geometry genuinely misleads — i.e. above the bulk of real stories, not on the typical case. If the measured distribution says 0.20 is wrong, change the constant; a threshold nothing ever crosses is a dead label, and one everything crosses is noise.

Write the measured table into the spec as a `## Measured (2026-07-22)` addendum, including the chosen threshold and why.

- [ ] **Step 4: Browser-verify both surfaces with real data**

```bash
cd frontend-v2 && npm run dev
```

Story constellation: `http://localhost:3000/app` → map panel → UNIVERSE tab → click a body → the story system opens. Confirm: stars render in 3D; dragging rotates them; near stars are larger/brighter than far ones; the label shows a real percentage; the scrubber still lights stars; hovering shows the receipt; console clean.

Workbench cloud: open the WORKBENCH overlay, create an investigation and pin ≥3 threads (or open an existing investigation that has them). Confirm: the compact constellation renders, rotates, shows the distortion line; edges keep their basis chips/tags; then open the dossier report and confirm the full `InvestigativeUniverse` rotates and labels too.

- [ ] **Step 5: Commit and push**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add frontend-v2/src/lib/mds3d.ts docs/superpowers/specs/2026-07-22-constellation-3d-mds-design.md
git commit -m "chore(mds): calibrate the stress threshold against real stories and pin sets"
git push origin v3-intel-layer
```

---

## Self-review

**Spec coverage**

| Spec section | Task |
|---|---|
| §1 backend MDS, additive payload | 1, 2, 3 |
| §2 `mds_3d`, Kruskal stress, clipping, determinism, n<3 | 1 |
| §2 Consumer A (cosine + centroid as node 0) | 2 |
| §2 Consumer B (`d = 1 − weight`, absence = 1.0, basis chips untouched) | 3 |
| §3 `lib/mds3d.ts` reusing the universe rotation math | 4 |
| §3 `hooks/useTrackball.ts` extraction + de-duplication | 5 |
| §3 `ConstellationThreadView` 3D, Orbits retired | 6 |
| §3 `WorkbenchConstellation` + `InvestigativeUniverse` on the same renderer | 7 |
| §3 honesty labels per surface, `stress >` threshold wording | 6, 7, 8 |
| §4 unplaced bodies, absence stays absence, degenerate fallback | 2, 6 |
| §4 testing (pytest, vitest, browser both surfaces) | 1, 4, 6, 7, 8 |
| Non-goals: universe PCA, WalkConstellation radial, no new data | untouched by every task |
| Open item 1 (vectors) | resolved in Context; built in 2 |
| Open item 1b (one scalar weight) | resolved in Context; stated in 3 |
| Open item 2 (toggle wiring) | resolved in Context; executed in 6 |
| Open item 3 (threshold) | 8 |
| Open item 4 (scrubber) | 6 — kept, reasoning stated |

**Deliberate deviation from the spec text:** §3 lists "tone rim" among the things to keep. The current `ConstellationThreadView` deliberately moved tone OFF the rims into the tone-of-coverage strip (2026-07-17 eval, "one variable per channel"). This plan keeps the strip and does NOT restore rim tone — re-adding it would regress a prior honesty decision.

**Type consistency:** `Pos3 = [number, number, number]` and `Mds3dMeta` are defined in Task 4 and used unchanged in 6 and 7. Backend `MdsResult(coords, stress, n)` is defined in Task 1 and consumed in 2 and 3. `starStates`/`StarState` are defined in Task 6 Step 3 and used in Task 6 Step 5. `useTrackball`'s returned shape (`rot`, `setRot`, `view`, `setView`, `reset`, `isDragging`, `handlers`) is defined in Task 5 and used in 5, 6, 7.
