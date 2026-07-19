"""#229 — PCA harness compare step: pure functions + pre-registered bars.

pca_recall_harness.py is a JSON-only compare (no hdbscan/asyncpg import), so
these run in any venv. Fixtures model the run_scoped_snapshot --dump-json
shape (meta + countries[].clusters[].members[] + cluster_seconds).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.scripts.pca_recall_harness import (  # noqa: E402
    arm_stats, count_lost, evaluate_bars, find_marginals, timing_stats,
    _all_clusters,
)


def _cluster(ids, cohesion=0.96, label="story"):
    return {"cluster_id": ids[0], "label": label, "kept_size": len(ids),
            "cohesion": cohesion,
            "members": [{"signal_id": i, "headline": f"h{i}"} for i in ids]}


def _dump(countries, pca_dim=0, as_of="2026-07-19T12:00:00Z"):
    return {"meta": {"pca_dim": pca_dim, "as_of": as_of},
            "countries": countries}


def _pair(same=True):
    """Control and a treated arm; treated optionally has one marginal cluster."""
    control = _dump([
        {"country": "US", "cluster_seconds": 100.0, "clusters": [
            _cluster(list(range(1, 14))),          # ge12
            _cluster(list(range(20, 29))),         # ge8
        ]},
        {"country": "FR", "cluster_seconds": 20.0, "clusters": [
            _cluster(list(range(40, 49))),
        ]},
    ])
    t_us = [
        _cluster(list(range(1, 14))),              # identical
        _cluster(list(range(20, 29))),             # identical
    ]
    if not same:
        t_us.append(_cluster(list(range(100, 109)), cohesion=0.90,
                             label="marginal"))
    treated = _dump([
        {"country": "US", "cluster_seconds": 20.0, "clusters": t_us},
        {"country": "FR", "cluster_seconds": 4.0, "clusters": [
            _cluster(list(range(40, 49))),
        ]},
    ], pca_dim=128)
    return control, treated


# ------------------------------------------------------------------ arm stats

def test_arm_stats_counts_and_blob():
    control, _ = _pair()
    s = arm_stats(_all_clusters(control))
    assert s["kept_clusters"] == 3
    assert s["ge12_promotable"] == 1
    assert s["kept_signal_mass"] == 13 + 9 + 9
    assert s["kept_max"] == 13 and s["kept_max_country"] == "US"


def test_arm_stats_empty():
    s = arm_stats([])
    assert s["kept_clusters"] == 0 and s["mean_cohesion"] is None


# ------------------------------------------------------------------ marginals

def test_no_marginals_when_arms_identical():
    control, treated = _pair(same=True)
    assert find_marginals(control, treated) == []
    assert count_lost(control, treated) == 0


def test_marginal_detected_and_shared_window_tagged():
    control, treated = _pair(same=False)
    m = find_marginals(control, treated)
    assert len(m) == 1 and m[0]["country"] == "US"
    # members 100-108 > control max id 48 → window-new, not shared-window
    assert m[0]["old_member_frac"] == 0.0


# --------------------------------------------------------------------- timing

def test_timing_overall_speedup():
    control, treated = _pair()
    t = timing_stats(control, treated)
    assert t["countries_timed_both"] == 2
    assert t["overall_speedup"] == 5.0            # (100+20)/(20+4)
    assert t["slowest_control_top10"][0]["country"] == "US"


def test_timing_skips_untimed_countries():
    control, treated = _pair()
    control["countries"][1]["cluster_seconds"] = None
    t = timing_stats(control, treated)
    assert t["countries_timed_both"] == 1
    assert t["overall_speedup"] == 5.0            # 100/20


# ------------------------------------------------------------------ the bars

def test_bars_all_pass_on_identical_fast_pair():
    control, treated = _pair(same=True)
    c, p = arm_stats(_all_clusters(control)), arm_stats(_all_clusters(treated))
    res = evaluate_bars(c, p, [], timing_stats(control, treated))
    assert res["verdict"] == "PASS"
    assert all(b["pass"] for b in res["bars"].values())


def test_speed_bar_fails_below_4x():
    control, treated = _pair(same=True)
    for cc in treated["countries"]:
        cc["cluster_seconds"] = cc["cluster_seconds"] * 2  # speedup 2.5x
    c, p = arm_stats(_all_clusters(control)), arm_stats(_all_clusters(treated))
    res = evaluate_bars(c, p, [], timing_stats(control, treated))
    assert res["bars"]["speed"]["pass"] is False
    assert res["verdict"] == "FAIL"


def test_speed_bar_unmeasured_fails_loudly():
    control, treated = _pair(same=True)
    for d in (control, treated):
        for cc in d["countries"]:
            cc.pop("cluster_seconds")
    c, p = arm_stats(_all_clusters(control)), arm_stats(_all_clusters(treated))
    res = evaluate_bars(c, p, [], timing_stats(control, treated))
    assert res["bars"]["speed"]["measured_speedup"] is None
    assert res["bars"]["speed"]["pass"] is False


def test_yield_bar_fails_on_gt10pct_drop():
    control, treated = _pair(same=True)
    treated["countries"][0]["clusters"] = treated["countries"][0]["clusters"][:1]
    c, p = arm_stats(_all_clusters(control)), arm_stats(_all_clusters(treated))
    res = evaluate_bars(c, p, [], timing_stats(control, treated))
    assert res["bars"]["yield_kept_ge8"]["pass"] is False  # 3 → 2 = −33%
    assert res["verdict"] == "FAIL"


def test_blob_bar_fails_on_mega_blob():
    control, treated = _pair(same=True)
    treated["countries"][0]["clusters"].append(
        _cluster(list(range(200, 230)), label="blob"))  # 30 > 1.5×13
    c, p = arm_stats(_all_clusters(control)), arm_stats(_all_clusters(treated))
    marg = find_marginals(control, treated)
    res = evaluate_bars(c, p, marg, timing_stats(control, treated))
    assert res["bars"]["no_mega_blob"]["pass"] is False
    assert res["verdict"] == "FAIL"


def test_marginal_fraction_caps_verdict_at_judge_required():
    control, treated = _pair(same=False)  # 1 marginal of 4 pca clusters = 25%
    c, p = arm_stats(_all_clusters(control)), arm_stats(_all_clusters(treated))
    marg = find_marginals(control, treated)
    res = evaluate_bars(c, p, marg, timing_stats(control, treated))
    # cohesion 0.90 is within 10pp of control mean (~0.96) → structural pass,
    # but 25% marginal fraction > 15% ⇒ verdict capped.
    assert res["bars"]["marginal_quality"]["pass"] is True
    assert res["bars"]["marginal_quality"]["judge_required"] is True
    assert res["verdict"] == "JUDGE_REQUIRED"


def test_marginal_cohesion_gt10pp_below_control_fails():
    control, treated = _pair(same=False)
    treated["countries"][0]["clusters"][2]["cohesion"] = 0.80  # 0.96−0.80 > 0.10
    c, p = arm_stats(_all_clusters(control)), arm_stats(_all_clusters(treated))
    marg = find_marginals(control, treated)
    res = evaluate_bars(c, p, marg, timing_stats(control, treated))
    assert res["bars"]["marginal_quality"]["pass"] is False
    assert res["verdict"] == "FAIL"
