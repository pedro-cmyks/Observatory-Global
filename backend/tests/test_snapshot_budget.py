"""EXECUTE-1 (2026-07-19) — wall-time budget math for the scoped snapshot.

Forensics (ASSESS-A): HDBSCAN's brute O(n²·d) MST on the biggest country ran
7+h single-threaded on efficiency cores and held the heavy-job mutex all
morning — US alone was 51% of the night's Σn². The structural cure is the
failure-budget philosophy extended to TIME:

  - predict per-country clustering cost from a self-calibrating n²/s rate;
  - cap a too-expensive country's INPUT (newest-first) so it fits its budget;
  - defer (first-fit) what cannot fit the remaining run budget — loudly,
    with next-night rotation priority, never silently;
  - checkpoint after every country so a killed run has banked its work.

This module tests the PURE parts (no numpy/hdbscan/DB): plan_country,
fit_cap, RateEstimator, country ordering, checkpoint/rotation round-trips.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.snapshot_budget import (
    Checkpoint,
    RateEstimator,
    fit_cap,
    load_checkpoint,
    load_rotation,
    order_countries,
    plan_country,
    predict_seconds,
    save_checkpoint,
    save_rotation,
    should_resume,
)

NOW = datetime(2026, 7, 19, 2, 45, tzinfo=timezone.utc)


# ------------------------------------------------------------------ rate math

def test_predict_seconds_is_quadratic_in_n():
    assert predict_seconds(10_000, rate_n2_per_s=300_000) == 10_000**2 / 300_000
    assert predict_seconds(20_000, 300_000) == 4 * predict_seconds(10_000, 300_000)


def test_fit_cap_inverts_predict():
    cap = fit_cap(1800.0, 300_000)
    assert cap == int(math.sqrt(1800.0 * 300_000))
    # the capped size must actually fit the budget
    assert predict_seconds(cap, 300_000) <= 1800.0
    assert predict_seconds(cap + 2, 300_000) > 1800.0


def test_fit_cap_degenerate_inputs():
    assert fit_cap(0, 300_000) == 0
    assert fit_cap(-5, 300_000) == 0
    assert fit_cap(1800, 0) == 0


def test_rate_estimator_moves_toward_measurement_and_clamps():
    est = RateEstimator(initial=300_000)
    assert est.rate == 300_000
    # measured: 20k rows in 800s → 500k n²/s (faster than assumed)
    est.update(n=20_000, seconds=800.0)
    assert 300_000 < est.rate <= 500_000
    # micro countries are overhead-dominated → ignored
    r = est.rate
    est.update(n=500, seconds=60.0)
    assert est.rate == r
    # garbage measurements clamp to sane bounds, never explode the planner
    est.update(n=50_000, seconds=0.001)
    assert est.rate <= est.MAX_RATE
    for _ in range(10):
        est.update(n=50_000, seconds=10_000_000.0)
    assert est.rate >= est.MIN_RATE


# ---------------------------------------------------------------- plan_country

def test_no_budgets_means_uncapped_no_timeout():
    p = plan_country(80_000, remaining_run_s=None, country_budget_s=0,
                     rate=300_000, min_cluster_n=4000)
    assert p.action == "cluster"
    assert p.n_use == 80_000
    assert p.capped is False
    assert p.hard_timeout_s == 0  # 0 = no hard kill (legacy behavior)


def test_small_country_uncapped_with_headroom_timeout():
    p = plan_country(6_000, remaining_run_s=9_000.0, country_budget_s=1800,
                     rate=300_000, min_cluster_n=4000)
    assert p.action == "cluster" and p.capped is False and p.n_use == 6_000
    # timeout = clamp(3×predicted, ≥300s, ≤1.5×country budget)
    assert p.hard_timeout_s >= 300
    assert p.hard_timeout_s <= 1.5 * 1800
    assert p.hard_timeout_s >= 3 * p.predicted_s or p.hard_timeout_s == 300


def test_giant_country_capped_newest_first_size():
    p = plan_country(80_000, remaining_run_s=9_000.0, country_budget_s=1800,
                     rate=300_000, min_cluster_n=4000)
    assert p.action == "cluster" and p.capped is True
    assert p.n_use == fit_cap(1800, 300_000)  # ≈23k of 80k
    assert p.predicted_s <= 1800.0
    # backstop kill is bounded: never more than 1.5× the country budget
    assert p.hard_timeout_s <= 1.5 * 1800


def test_run_budget_first_fit_defers_what_cannot_fit():
    # capped giant predicts ~1800s but only 900s of run budget remain →
    # deferred; a smaller country later can still fit (first-fit-decreasing).
    p = plan_country(80_000, remaining_run_s=900.0, country_budget_s=1800,
                     rate=300_000, min_cluster_n=4000)
    assert p.action == "defer"
    assert p.reason == "run_budget_first_fit"
    small = plan_country(3_000, remaining_run_s=900.0, country_budget_s=1800,
                         rate=300_000, min_cluster_n=4000)
    assert small.action == "cluster"


def test_run_budget_exhausted_defers_everything():
    p = plan_country(3_000, remaining_run_s=0.0, country_budget_s=1800,
                     rate=300_000, min_cluster_n=4000)
    assert p.action == "defer" and p.reason == "run_budget_exhausted"


def test_budget_below_floor_defers_instead_of_garbage_slice():
    # budget only buys a 2k slice of a 50k country but the floor is 4k —
    # a uselessly thin slice of a huge country is a gap, not a topic pass.
    p = plan_country(50_000, remaining_run_s=9_000.0, country_budget_s=15,
                     rate=300_000, min_cluster_n=4000)
    assert p.action == "defer" and p.reason == "budget_below_floor"


def test_run_budget_only_defers_uncappable_giant():
    # country budget OFF, run budget ON: an 80k country predicts ~6h — it can
    # never fit a 2.5h run and is deferred honestly (not silently attempted).
    p = plan_country(80_000, remaining_run_s=9_000.0, country_budget_s=0,
                     rate=300_000, min_cluster_n=4000)
    assert p.action == "defer" and p.reason == "run_budget_first_fit"


# ------------------------------------------------------------------- ordering

def test_order_countries_prepends_rotation_priority_in_list_order():
    ccs = ["US", "IN", "GB", "RU", "IT", "UY"]
    out = order_countries(ccs, priority=["IT", "UY", "ZZ"])  # ZZ not eligible
    assert out == ["IT", "UY", "US", "IN", "GB", "RU"]
    assert order_countries(ccs, priority=[]) == ccs


# ---------------------------------------------------------- checkpoint/resume

def test_checkpoint_roundtrip(tmp_path: Path):
    ck = Checkpoint(snapshot_at="2026-07-19T02:45:37+00:00", hours=168,
                    started_at=NOW.isoformat(), next_base=300000,
                    done={"US": "ok", "GB": "no_clusters"}, complete=False)
    path = tmp_path / "ck.json"
    save_checkpoint(path, ck)
    back = load_checkpoint(path)
    assert back == ck


def test_checkpoint_load_missing_or_corrupt_is_none(tmp_path: Path):
    assert load_checkpoint(tmp_path / "absent.json") is None
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_checkpoint(bad) is None
    # schema-version mismatch is treated as no checkpoint (never crash a run)
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"version": 999}), encoding="utf-8")
    assert load_checkpoint(wrong) is None


def test_should_resume_gates_on_age_window_and_completeness():
    ck = Checkpoint(snapshot_at=(NOW - timedelta(hours=3)).isoformat(),
                    hours=168, started_at=(NOW - timedelta(hours=3)).isoformat(),
                    next_base=200000, done={"US": "ok"}, complete=False)
    assert should_resume(ck, now=NOW, hours=168, max_age_h=12)
    # a COMPLETED run never resumes (budget-stop is completion, not a crash)
    done = Checkpoint(**{**ck.__dict__, "complete": True})
    assert not should_resume(done, now=NOW, hours=168, max_age_h=12)
    # stale checkpoints (yesterday's crash) start fresh
    old = Checkpoint(**{**ck.__dict__,
                        "started_at": (NOW - timedelta(hours=26)).isoformat()})
    assert not should_resume(old, now=NOW, hours=168, max_age_h=12)
    # a different window is a different corpus — never mix
    assert not should_resume(ck, now=NOW, hours=24, max_age_h=12)
    # empty checkpoints (crashed before any country) restart cleanly
    empty = Checkpoint(**{**ck.__dict__, "done": {}})
    assert not should_resume(empty, now=NOW, hours=168, max_age_h=12)


def test_rotation_roundtrip_and_missing(tmp_path: Path):
    path = tmp_path / "rot.json"
    assert load_rotation(path) == []
    save_rotation(path, ["DE", "IR", "ES"])
    assert load_rotation(path) == ["DE", "IR", "ES"]
    save_rotation(path, [])
    assert load_rotation(path) == []
