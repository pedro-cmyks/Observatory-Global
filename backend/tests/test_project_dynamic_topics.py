from __future__ import annotations

import numpy as np

from scripts.project_dynamic_topics import (
    LifecycleConfig,
    is_roundup_label,
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
