from __future__ import annotations

import numpy as np

from scripts.project_dynamic_topics import (
    LifecycleConfig,
    Topic,
    is_roundup_label,
    merge_duplicates,
    next_state,
    running_mean,
    process_snapshot,
)

CFG = LifecycleConfig()


def test_is_roundup_label():
    assert is_roundup_label("Daily News Roundup")
    assert is_roundup_label("Mixed News Headlines")
    assert not is_roundup_label("Iran Nuclear Talks Stance")
    assert not is_roundup_label(None)


def test_running_mean():
    old = np.array([1.0, 1.0])
    out = running_mean(old, 1, np.array([3.0, 3.0]))
    assert list(out) == [2.0, 2.0]


def test_next_state_promotes_qualifying_candidate():
    s = next_state("candidate", seen_now=True, n_snapshots=2, mean_cohesion=0.8,
                   agg_n_signals=100, is_roundup=False, since_seen=0, cfg=CFG)
    assert s == "active"


def test_next_state_does_not_promote_roundup():
    s = next_state("candidate", seen_now=True, n_snapshots=5, mean_cohesion=0.9,
                   agg_n_signals=500, is_roundup=True, since_seen=0, cfg=CFG)
    assert s == "candidate"


def test_next_state_does_not_promote_low_volume_or_cohesion():
    assert next_state("candidate", seen_now=True, n_snapshots=3, mean_cohesion=0.2,
                      agg_n_signals=500, is_roundup=False, since_seen=0, cfg=CFG) == "candidate"
    assert next_state("candidate", seen_now=True, n_snapshots=3, mean_cohesion=0.9,
                      agg_n_signals=5, is_roundup=False, since_seen=0, cfg=CFG) == "candidate"


def test_next_state_deprecate_and_retire_on_staleness():
    assert next_state("active", seen_now=False, n_snapshots=3, mean_cohesion=0.8,
                      agg_n_signals=100, is_roundup=False, since_seen=2, cfg=CFG) == "deprecated"
    assert next_state("deprecated", seen_now=False, n_snapshots=3, mean_cohesion=0.8,
                      agg_n_signals=100, is_roundup=False, since_seen=4, cfg=CFG) == "retired"


def test_next_state_reactivates_on_reappearance():
    s = next_state("deprecated", seen_now=True, n_snapshots=4, mean_cohesion=0.8,
                   agg_n_signals=100, is_roundup=False, since_seen=0, cfg=CFG)
    assert s == "active"


def _cluster(snap, cid, vec, label, n=100, coh=0.9):
    return {"id": cid, "snapshot_at": snap, "cluster_id": cid, "label": label,
            "n_signals": n, "cohesion": coh, "centroid": np.array(vec, dtype=np.float64)}


def test_process_snapshot_promotes_persistent_real_topic():
    topics = []
    process_snapshot(topics, [_cluster("s1", 1, [1.0, 0.0], "Iran Talks")], "s1", CFG)
    assert topics[0].state == "candidate"  # only 1 snapshot
    process_snapshot(topics, [_cluster("s2", 2, [0.99, 0.01], "Iran Talks")], "s2", CFG)
    assert len(topics) == 1               # matched, not duplicated
    assert topics[0].state == "active"    # persisted 2 snapshots, cohesive, volume


def test_process_snapshot_keeps_roundup_as_candidate():
    topics = []
    process_snapshot(topics, [_cluster("s1", 1, [1.0, 0.0], "Daily News Roundup")], "s1", CFG)
    process_snapshot(topics, [_cluster("s2", 2, [1.0, 0.0], "Daily News Roundup")], "s2", CFG)
    assert len(topics) == 1
    assert topics[0].is_roundup
    assert topics[0].state == "candidate"  # never promoted despite persistence


def test_merge_duplicates_absorbs_near_duplicate_into_older_identity():
    older = Topic("dyn-s1-1", "Russia Warns", [1.0, 0.0], "s1", 100, 0.9, noise=0.1)
    older.members.append({"cluster_id": 1, "snapshot_at": "s1", "match_score": 1.0})
    older.state = "active"
    older.id = 10

    newer = Topic("dyn-s2-2", "Russia Warnings", [0.99, 0.01], "s2", 80, 0.8, noise=0.2)
    newer.members.append({"cluster_id": 2, "snapshot_at": "s2", "match_score": 1.0})
    newer.state = "candidate"
    newer.id = 11

    merged = merge_duplicates([newer, older], threshold=0.9)

    assert len(merged) == 1
    topic = merged[0]
    assert topic.identity_key == "dyn-s1-1"
    assert topic.id == 10
    assert topic.state == "active"
    assert topic.agg_n_signals == 180
    assert topic.n_member_clusters == 2
    assert topic.noise_rate == 0.15
    assert [m["cluster_id"] for m in topic.members] == [1, 2]


def test_merge_duplicates_does_not_merge_distinct_topics():
    first = Topic("dyn-s1-1", "Russia Warns", [1.0, 0.0], "s1", 100, 0.9)
    second = Topic("dyn-s1-2", "Local Politics", [0.0, 1.0], "s1", 100, 0.9)

    merged = merge_duplicates([first, second], threshold=0.9)

    assert len(merged) == 2


def test_merge_duplicates_requires_compatible_labels_even_with_close_centroids():
    first = Topic("dyn-s1-1", "Orchard Portfolio Sale", [1.0, 0.0], "s1", 100, 0.9)
    second = Topic("dyn-s1-2", "Virginia Bus Crash", [0.99, 0.01], "s1", 100, 0.9)

    merged = merge_duplicates([first, second], threshold=0.9)

    assert len(merged) == 2


def test_merge_duplicates_does_not_let_roundups_absorb_real_topics():
    roundup = Topic("dyn-s1-1", "Daily News Roundup", [1.0, 0.0], "s1", 100, 0.9)
    real = Topic("dyn-s1-2", "Agostina Vega Found Dead", [0.99, 0.01], "s1", 100, 0.9)

    merged = merge_duplicates([roundup, real], threshold=0.9)

    assert len(merged) == 2
