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
