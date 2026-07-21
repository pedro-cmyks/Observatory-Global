"""The walked constellation — pure walk math (no DB).

Spec: docs/superpowers/specs/2026-07-21-multi-hop-transitive-chains.md. Freezes the
LOCKED brake (REL_FLOOR 0.35 + HOP_CAP 3), the blob-connector penalty, the same-
event dedup (0.85), the typed-destination word-boundary match, and the #234 actor-
rarity formula (0.30 + 0.68·norm_rarity). Graphs are hand-built so the geometry —
and thus every threshold — is exact and deterministic.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.services.constellation_walk import (
    KnnGraph,
    WalkParams,
    actor_edge_weight,
    blob_connector_flags,
    build_knn_graph,
    category_entropy,
    dedup_reached,
    match_destination,
    max_product_walk,
    norm_rarity,
    walk_constellation,
)


def _unit(rows):
    m = np.asarray(rows, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def _chain_graph(weights, bfh_override=None):
    """A linear chain 0→1→2→…: nbrs[i] = [(i+1, w_i)]; last node has no neighbor.
    bfh[i] = that node's outgoing weight (its only/best neighbor). indeg computed."""
    n = len(weights) + 1
    nbrs = {i: [(i + 1, float(weights[i]))] for i in range(len(weights))}
    nbrs[n - 1] = []
    bfh = np.zeros(n, dtype=np.float32)
    for i in range(len(weights)):
        bfh[i] = weights[i]
    if bfh_override is not None:
        for i, v in bfh_override.items():
            bfh[i] = v
    indeg = np.zeros(n, dtype=np.int32)
    for i, lst in nbrs.items():
        for j, _ in lst:
            indeg[j] += 1
    return KnnGraph(nbrs=nbrs, bfh=bfh, indeg=indeg, n=n)


# ---------------------------------------------------------------- build_knn_graph
def test_build_knn_graph_structure():
    # e0, e1 orthonormal; a,b in the e0/e1 plane. cos(a,b)=0.96, cos(e0,a)=0.8.
    W = _unit([[1, 0, 0, 0], [0, 1, 0, 0], [0.8, 0.6, 0, 0], [0.6, 0.8, 0, 0]])
    g = build_knn_graph(W, k=2)
    assert g.n == 4
    # each adjacency list is top-2, sorted descending, self excluded
    for i in range(4):
        assert len(g.nbrs[i]) == 2
        sims = [s for _, s in g.nbrs[i]]
        assert sims == sorted(sims, reverse=True)
        assert all(j != i for j, _ in g.nbrs[i])
    # a's best neighbor is b at 0.96; bfh = max off-diagonal cosine
    assert g.bfh[2] == pytest.approx(0.96, abs=1e-4)
    assert g.bfh[0] == pytest.approx(0.8, abs=1e-4)
    # a (idx 2) is listed by e0, e1 and b → in-degree 3
    assert int(g.indeg[2]) == 3


def test_build_knn_graph_empty():
    g = build_knn_graph(np.zeros((0, 8), dtype=np.float32), k=6)
    assert g.n == 0 and g.nbrs == {}


# ---------------------------------------------------------------- the brake
def test_hop_cap_self_terminates_on_strong_chain():
    # strong chain 0→1→2→3→4 at 0.9. acc: 1º .9, 2º .81, 3º .729, 4º .656.
    # rel-floor 0.35·bfh(0.9)=0.315 keeps all, but HOP_CAP 3 forbids expanding 3º.
    g = _chain_graph([0.9, 0.9, 0.9, 0.9])
    reached = max_product_walk([0], g, WalkParams())
    degrees = {i: r.degree for i, r in reached.items()}
    assert degrees == {1: 1, 2: 2, 3: 3}     # node 4 never reached — 4º blocked
    assert 4 not in reached
    assert reached[3].acc_weight == pytest.approx(0.729, abs=1e-3)


def test_relative_floor_cuts_a_weak_trail_early():
    # weak chain at 0.5, bfh(0)=0.5 → floor 0.175. acc: 1º .5, 2º .25, 3º .125<floor.
    g = _chain_graph([0.5, 0.5, 0.5, 0.5])
    reached = max_product_walk([0], g, WalkParams())
    assert set(reached) == {1, 2}            # 3º .125 < 0.175 → not kept
    assert reached[2].degree == 2


def test_hop_cap_is_load_bearing_even_when_floor_would_allow_4th():
    # a very tight seed (bfh 0.99) at strong hops keeps acc high past 3º, so ONLY
    # the hard cap stops the 4º (spec §2.3: the relative floor alone leaks 4º).
    g = _chain_graph([0.98, 0.98, 0.98, 0.98, 0.98])
    reached = max_product_walk([0], g, WalkParams())
    assert max(r.degree for r in reached.values()) == 3
    assert all(d not in reached for d in (4, 5))


# ---------------------------------------------------------------- multi-source
def test_multi_source_keeps_best_product_and_excludes_seeds():
    # two seeds 0 and 4 converge on middle node 2 via 0→1→2 (.81) and 4→3→2 (.9·.95=.855)
    nbrs = {
        0: [(1, 0.9)], 1: [(2, 0.9)], 2: [],
        3: [(2, 0.95)], 4: [(3, 0.9)],
    }
    bfh = np.array([0.9, 0.9, 0.0, 0.95, 0.9], dtype=np.float32)
    indeg = np.zeros(5, dtype=np.int32)
    g = KnnGraph(nbrs=nbrs, bfh=bfh, indeg=indeg, n=5)
    reached = max_product_walk([0, 4], g, WalkParams())
    assert 0 not in reached and 4 not in reached          # seeds excluded
    # node 2's best product is via seed 4 (0.855 > 0.81) → origin 4
    assert reached[2].origin_seed == 4
    assert reached[2].acc_weight == pytest.approx(0.855, abs=1e-3)


# ---------------------------------------------------------------- kinship
def test_kinship_hermano_is_direct_primo_is_transitive():
    g = _chain_graph([0.9, 0.9, 0.9])   # 0→1→2→3
    reached = max_product_walk([0], g, WalkParams())
    assert reached[1].kinship == "hermano"   # 1º: direct edge to seed
    assert reached[2].kinship == "primo"     # 2º: only transitive
    assert reached[3].kinship == "primo"     # 3º


def test_promotion_direct_edge_makes_a_reached_node_hermano():
    # 0→1→2 (2-hop path), but 2 ALSO has a direct edge back to seed 0 → hermano
    # (spec §2.5 promotion: the proof upgrades the relation).
    nbrs = {0: [(1, 0.9)], 1: [(2, 0.9)], 2: [(0, 0.6)]}
    bfh = np.array([0.9, 0.9, 0.9], dtype=np.float32)
    g = KnnGraph(nbrs=nbrs, bfh=bfh, indeg=np.zeros(3, np.int32), n=3)
    reached = max_product_walk([0], g, WalkParams())
    assert reached[2].kinship == "hermano"   # 0 ∈ nbrs[2] → direct → promoted


# ---------------------------------------------------------------- blob penalty
def test_blob_penalty_cuts_a_glued_cross_domain_hop():
    # seed 0 → blob B(1) at 0.9 → far F(2) at 0.4. Without penalty acc(F)=0.36 ≥
    # floor 0.315; a hop OUT of the flagged blob halves it → 0.9·(0.4·0.5)=0.18 < floor.
    g = _chain_graph([0.9, 0.4])
    kept = max_product_walk([0], g, WalkParams(), blob_flags=set())
    assert 2 in kept                                   # F survives without the flag
    cut = max_product_walk([0], g, WalkParams(), blob_flags={1})
    assert 2 not in cut                                # penalized below floor
    assert cut[1].kinship == "hermano"                 # the blob itself still reached


def test_blob_penalty_never_applies_when_the_blob_is_a_seed():
    # if the analyst pinned the blob (it IS a seed), its onward hops are not penalized
    g = _chain_graph([0.9, 0.4])
    reached = max_product_walk([1], g, WalkParams(), blob_flags={1})
    assert 2 in reached


# ---------------------------------------------------------------- blob detection
def test_category_entropy_hub_low_blob_high():
    # hub: all neighbors share one category → entropy 0. blob: every neighbor a
    # different category → high entropy.
    nbrs = {0: [(1, .9), (2, .9), (3, .9)], 1: [(0, .9)], 2: [(0, .9)], 3: [(0, .9)]}
    hub_cats = ["war", "war", "war", "war"]
    assert category_entropy(nbrs, hub_cats, 0) == pytest.approx(0.0, abs=1e-9)
    blob_cats = ["mix", "econ", "sport", "weather"]
    assert category_entropy(nbrs, blob_cats, 0) > 1.5


def test_blob_connector_flags_gate_on_indegree_and_entropy():
    # node 0 is topically spread (high entropy) AND a connector (in-degree 3) → blob.
    # A genuine hub (high in-degree, ONE category) is NOT flagged.
    nbrs = {0: [(1, .9), (2, .9), (3, .9)], 1: [(0, .9)], 2: [(0, .9)], 3: [(0, .9)]}
    indeg = np.array([3, 1, 1, 1], dtype=np.int32)
    bfh = np.full(4, 0.9, dtype=np.float32)
    g = KnnGraph(nbrs=nbrs, bfh=bfh, indeg=indeg, n=4)
    spread = blob_connector_flags(g, ["mix", "econ", "sport", "weather"], WalkParams())
    assert 0 in spread
    hub = blob_connector_flags(g, ["war", "war", "war", "war"], WalkParams())
    assert 0 not in hub                                 # low entropy → genuine hub
    # entropy high but in-degree below the connector floor → not flagged
    lonely = KnnGraph(nbrs=nbrs, bfh=bfh, indeg=np.array([2, 1, 1, 1], np.int32), n=4)
    assert blob_connector_flags(lonely, ["mix", "econ", "sport", "weather"],
                                WalkParams(blob_indeg_min=3)) == set()


# ---------------------------------------------------------------- dedup
def test_dedup_folds_same_event_fragments_keeps_distinct():
    # 0 and 1 near-duplicate (cos ~0.9), 2 distinct.
    W = _unit([[1, 0, 0], [0.98, 0.2, 0], [0, 1, 0]])
    reps, fold = dedup_reached([0, 1, 2], W, tau=0.85)
    assert reps == [0, 2]            # 1 folds into 0 (its representative)
    assert fold[0] == [1]
    assert fold[2] == []


def test_dedup_high_tau_underfolds():
    W = _unit([[1, 0, 0], [0.98, 0.2, 0], [0, 1, 0]])
    reps, _ = dedup_reached([0, 1, 2], W, tau=0.99)
    assert reps == [0, 1, 2]         # 0.9 < 0.99 → nothing folds


# ---------------------------------------------------------------- typed dest
def test_match_destination_word_boundary_rejects_substring():
    # "Ukraine political turmOIL" must NOT match the term "oil" (the probe FP).
    assert match_destination("Ukraine political turmoil", "Armed conflict", ["oil"]) is None
    assert match_destination("Brent oil prices surge", "Markets", ["oil"]) == "oil"


def test_match_destination_category():
    assert match_destination("Iran threatens exports", "Oil and gas supply risk",
                             [], categories={"Oil and gas supply risk"}) == "Oil and gas supply risk"
    assert match_destination("random story", "Sports", [], categories={"Markets"}) is None


# ---------------------------------------------------------------- #234 rarity
def test_norm_rarity_endpoints():
    assert norm_rarity(1, 29) == pytest.approx(1.0)      # unique actor
    assert norm_rarity(29, 29) == pytest.approx(0.0)     # ubiquitous
    # monotone decreasing in df
    vals = [norm_rarity(df, 29) for df in (1, 2, 3, 5, 10, 29)]
    assert vals == sorted(vals, reverse=True)


def test_actor_edge_weight_locked_numbers():
    # spec §2.4 measured: trump df=29 → 0.300; rare df=2 → 0.628; crossover ≈ df 3.
    assert actor_edge_weight([29], 29) == pytest.approx(0.300, abs=1e-3)
    assert actor_edge_weight([2], 29) == pytest.approx(0.628, abs=2e-3)
    assert actor_edge_weight([1], 29) == pytest.approx(0.98, abs=1e-3)
    assert actor_edge_weight([3], 29) >= 0.50            # df 3 clears the gate
    assert actor_edge_weight([4], 29) < 0.50             # df 4 is thin
    # the rarest shared actor carries the link (max over dfs)
    assert actor_edge_weight([29, 2], 29) == pytest.approx(0.628, abs=2e-3)
    assert actor_edge_weight([], 29) == 0.0


# ---------------------------------------------------------------- acceptance
def test_cross_story_primo_survives_to_third_degree():
    """Spec §8 marquee: dt-31 → Hormuz-fees (1º) → … → [Oil & gas] energy-exports
    (3º). A sparse chain (no direct seed→energy edge) so the energy node is a
    genuine transitive PRIMO, reached at 3º under the LOCKED brake, with a receipt
    + a typed-destination match. Mirrors the probe's acc 0.249 at 3º."""
    nbrs = {
        0: [(1, 0.55)],    # seed → Hormuz-fees hermano (direct)
        1: [(2, 0.70)],    # → Hormuz-closure
        2: [(3, 0.60)],    # → energy-exports (transitive-only)
        3: [],
    }
    bfh = np.array([0.55, 0.70, 0.60, 0.0], dtype=np.float32)
    g = KnnGraph(nbrs=nbrs, bfh=bfh, indeg=np.array([0, 1, 1, 1], np.int32), n=4)
    reached = max_product_walk([0], g, WalkParams())
    energy = reached[3]
    assert energy.degree == 3 and energy.kinship == "primo"     # transitive cousin
    assert energy.acc_weight == pytest.approx(0.55 * 0.70 * 0.60, abs=1e-3)  # ≈0.231
    assert energy.via_parent == 2 and energy.via_weight == pytest.approx(0.60)  # receipt
    cats = ["Armed conflict", "Oil and gas supply risk"]
    assert match_destination("Iran Threatens Energy Exports",
                             "Oil and gas supply risk", ["oil", "energy"],
                             categories={c for c in cats}) == "Oil and gas supply risk"


# ---------------------------------------------------------------- orchestrator
def test_walk_constellation_plumbing():
    # composes build → blob-flag → walk → dedup and returns a coherent WalkResult.
    W = _unit([
        [1.00, 0.02, 0.00, 0.00, 0.0],
        [0.98, 0.15, 0.00, 0.00, 0.0],
        [0.90, 0.40, 0.00, 0.00, 0.0],
        [0.55, 0.83, 0.10, 0.00, 0.0],
        [0.20, 0.90, 0.38, 0.00, 0.0],
        [0.00, 0.00, 0.00, 0.00, 1.0],  # orphan
    ])
    cats = ["Armed conflict", "Armed conflict", "Armed conflict",
            "Diplomacy", "Oil and gas supply risk", "Lifestyle"]
    res = walk_constellation(W, cats, seeds=[0], params=WalkParams())
    assert res.graph.n == 6
    assert isinstance(res.blob_flags, set)
    assert set(res.reps).issubset(set(res.reached))        # reps are reached nodes
    assert 0 not in res.reached                            # seed excluded
    assert 5 not in res.reached                            # orphan never fabricated
    for r in res.reached.values():
        assert r.via_weight > 0                            # every hop carries a receipt


def test_walk_constellation_honest_orphan_state():
    # a seed whose neighbors sit at cosine 0 returns EMPTY reached (spec §8) —
    # the caller renders "no measured kin," never a fabricated primo.
    W = _unit([[1, 0, 0], [0, 1, 0], [0, 0, 1]])   # mutually orthogonal
    res = walk_constellation(W, ["a", "b", "c"], seeds=[0], params=WalkParams())
    assert res.reached == {}
