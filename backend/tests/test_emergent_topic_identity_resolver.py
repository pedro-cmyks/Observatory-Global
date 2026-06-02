from __future__ import annotations

import numpy as np

from scripts.emergent_topic_identity_resolver import (
    cosine,
    jaccard,
    sequential_link,
    global_agglomerative,
    identity_stats,
    intra_identity_variance,
)


def _c(snap, cid, vec, label="x", n=10, sids=None):
    return {
        "id": cid,
        "snapshot_at": snap,
        "cluster_id": cid,
        "label": label,
        "n_signals": n,
        "sample_signal_ids": sids or [],
        "centroid": np.array(vec, dtype=np.float64),
    }


def test_cosine_and_jaccard():
    assert cosine(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == 1.0
    assert abs(cosine(np.array([1.0, 0.0]), np.array([0.0, 1.0]))) < 1e-9
    assert jaccard([1, 2, 3], [2, 3, 4]) == 0.5
    assert jaccard([], []) == 0.0
    assert jaccard([1], [2]) == 0.0


def test_sequential_link_persists_same_topic_across_snapshots():
    # one persistent topic (vec ~ [1,0]) across 3 snapshots + a one-off
    clusters = [
        _c("s1", 1, [1.0, 0.0]),
        _c("s2", 2, [0.99, 0.01]),
        _c("s2", 3, [0.0, 1.0]),  # different topic, appears once
        _c("s3", 4, [0.98, 0.02]),
    ]
    idents = sequential_link(clusters, threshold=0.9)
    persistent = [i for i in idents if len(i["snapshots"]) >= 2]
    assert len(persistent) == 1
    assert len(persistent[0]["members"]) == 3
    assert persistent[0]["first_seen"] == "s1"
    assert persistent[0]["last_seen"] == "s3"


def test_sequential_link_high_threshold_splits():
    clusters = [_c("s1", 1, [1.0, 0.0]), _c("s2", 2, [0.6, 0.8])]
    idents = sequential_link(clusters, threshold=0.95)
    assert len(idents) == 2  # too dissimilar to link


def test_sequential_link_one_to_one_per_snapshot():
    # two clusters in same snapshot both near the same identity -> only one links
    clusters = [
        _c("s1", 1, [1.0, 0.0]),
        _c("s2", 2, [1.0, 0.0]),
        _c("s2", 3, [0.99, 0.01]),
    ]
    idents = sequential_link(clusters, threshold=0.9)
    # identity from s1 absorbs one s2 cluster; the other opens a new identity
    assert len(idents) == 2


def test_global_agglomerative_groups_by_threshold():
    clusters = [
        _c("s1", 1, [1.0, 0.0]),
        _c("s2", 2, [0.99, 0.01]),
        _c("s3", 3, [0.0, 1.0]),
    ]
    groups = global_agglomerative(clusters, threshold=0.9)
    sizes = sorted(len(g) for g in groups)
    assert sizes == [1, 2]


def test_identity_stats_and_variance():
    clusters = [_c("s1", 1, [1.0, 0.0]), _c("s2", 2, [1.0, 0.0]), _c("s2", 3, [0.0, 1.0])]
    idents = sequential_link(clusters, threshold=0.9)
    st = identity_stats(idents)
    assert st["n_identities"] == 2
    assert st["n_persistent"] == 1
    assert st["max_lifespan"] == 2
    # identical-centroid members -> ~0 spread
    var = intra_identity_variance(idents)
    assert var is not None and var < 1e-6
