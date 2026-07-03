#!/usr/bin/env python3
"""Backtest: does Kalman velocity/surprise LEAD volume? (read-only, #219)

The claim behind topic_movement is that the smoothed Kalman velocity/surprise
is a LEADING indicator — it should predict where volume goes NEXT, not just
describe where it is now. If true, wiring topic_movement into the front-page
thread ordering is justified. If not, changed_10h stays the ordering source and
topic_movement stays a display-only chip.

Method — REPLAY over the DURABLE snapshot history (emergent_clusters, ~33d at
the clustering cadence ≈ 8h/snapshot; NOT the recency-windowed topic_members):
  1. Per-topic volume series = each topic's n_signals across its snapshots.
  2. Walk a sliding point t through each series. At t:
       - Kalman velocity(t)/surprise(t) from the PAST snapshots only (obs[:t]).
       - changed(t) = naive contemporaneous delta (the changed_10h analogue):
         this snapshot's n_signals minus the previous snapshot's.
     Target = FUTURE growth: log-volume over the next H snapshots minus the
     prior H (does the topic actually grow AFTER t?).
  3. Forward rank-correlation (Spearman) of each signal with future growth,
     with a bootstrap 95% CI. Verdict:
       - velocity LEADS if CI_low(corr(velocity, future)) > 0.
       - Kalman BEATS naive if corr(velocity,future) − corr(changed,future)
         has a bootstrap CI above 0.
       - UNDERPOWERED if too few (topic, t) points or the CIs straddle 0.

Read-only: reuses the state-pilot loader over emergent_clusters; writes nothing.
Run: python -m scripts.backtest_movement_leading --horizon-snaps 2
"""
from __future__ import annotations

import argparse
import asyncio
import math
import os

import numpy as np

try:  # works as `-m scripts.backtest_movement_leading` and standalone
    from scripts.dynamic_topic_state_report import (
        Observation, estimate_state, load_topic_observations,
    )
except ImportError:
    from dynamic_topic_state_report import (
        Observation, estimate_state, load_topic_observations,
    )

MIN_HISTORY_SNAPS = 5   # ≥5 past snapshots before a point is evaluable


# --------------------------------------------------------------------------- #
# stats (no scipy)
# --------------------------------------------------------------------------- #
def _rankdata(a: np.ndarray) -> np.ndarray:
    """Average-rank (ties shared), like scipy.stats.rankdata."""
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=np.float64)
    ranks[order] = np.arange(1, len(a) + 1, dtype=np.float64)
    # average ties
    sa = a[order]
    i = 0
    n = len(a)
    while i < n:
        j = i + 1
        while j < n and sa[j] == sa[i]:
            j += 1
        if j - i > 1:
            avg = (i + 1 + j) / 2.0  # mean of ranks i+1..j
            ranks[order[i:j]] = avg
        i = j
    return ranks


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return float("nan")
    xc = x - x.mean()
    yc = y - y.mean()
    denom = math.sqrt(float((xc * xc).sum()) * float((yc * yc).sum()))
    if denom == 0:
        return float("nan")
    return float((xc * yc).sum() / denom)


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return float("nan")
    return _pearson(_rankdata(x), _rankdata(y))


def _bootstrap_ci(x: np.ndarray, y: np.ndarray, n_boot: int, seed: int):
    """95% CI of Spearman(x, y) via paired resampling (fixed seed = reproducible)."""
    n = len(x)
    if n < 8:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    corrs = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        corrs[b] = _spearman(x[idx], y[idx])
    corrs = corrs[~np.isnan(corrs)]
    if len(corrs) < 2:
        return (float("nan"), float("nan"))
    return (float(np.percentile(corrs, 2.5)), float(np.percentile(corrs, 97.5)))


def _bootstrap_diff_ci(xa, xb, y, n_boot: int, seed: int):
    """95% CI of [ Spearman(xa,y) − Spearman(xb,y) ] on the SAME resample."""
    n = len(y)
    if n < 8:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        diffs[b] = _spearman(xa[idx], y[idx]) - _spearman(xb[idx], y[idx])
    diffs = diffs[~np.isnan(diffs)]
    if len(diffs) < 2:
        return (float("nan"), float("nan"))
    return (float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)))


# --------------------------------------------------------------------------- #
# backtest
# --------------------------------------------------------------------------- #
def _collect_points(observations: list[Observation], horizon_snaps: int):
    """Yield (velocity, surprise, changed, future_growth) for each evaluable t.

    `observations` = one topic's snapshot series (n_signals per snapshot_at),
    already chronological from the loader."""
    obs = sorted(observations, key=lambda o: o.snapshot_at)
    n = len(obs)
    counts = np.array([o.n_signals for o in obs], dtype=np.float64)
    h = horizon_snaps
    pts = []
    for i in range(MIN_HISTORY_SNAPS, n - h):
        est = estimate_state(obs[: i + 1])          # PAST only → no leakage
        changed = float(counts[i] - counts[i - 1])  # naive contemporaneous delta
        fut = counts[i + 1 : i + 1 + h].sum()       # future H snapshots
        pastw = counts[i + 1 - h : i + 1].sum()     # prior H snapshots
        future_growth = math.log1p(fut) - math.log1p(pastw)
        pts.append((est.velocity, est.surprise, changed, future_growth))
    return pts


async def run(horizon_snaps: int, n_boot: int, min_points: int, limit: int) -> dict:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"], statement_cache_size=0)
    try:
        # ALL real states = maximum history (lifecycle at eval time is irrelevant;
        # candidate/deprecated carry the richest multi-snapshot series)
        topic_inputs = await load_topic_observations(
            conn, ["active", "candidate", "deprecated", "retired"], limit
        )
    finally:
        await conn.close()

    all_pts = []
    n_topics_used = 0
    for topic in topic_inputs:
        obs = topic["observations"]
        if len(obs) < MIN_HISTORY_SNAPS + horizon_snaps + 1:
            continue
        pts = _collect_points(obs, horizon_snaps)
        if pts:
            n_topics_used += 1
            all_pts.extend(pts)

    if len(all_pts) < 3:
        return {"verdict": "no_data", "n_points": len(all_pts), "n_topics": n_topics_used}

    arr = np.array(all_pts, dtype=np.float64)
    vel, surprise, changed10h, growth = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]

    c_vel = _spearman(vel, growth)
    c_sur = _spearman(surprise, growth)
    c_naive = _spearman(changed10h, growth)
    ci_vel = _bootstrap_ci(vel, growth, n_boot, seed=1)
    ci_sur = _bootstrap_ci(surprise, growth, n_boot, seed=2)
    ci_naive = _bootstrap_ci(changed10h, growth, n_boot, seed=3)
    ci_diff = _bootstrap_diff_ci(vel, changed10h, growth, n_boot, seed=4)

    n = len(all_pts)
    velocity_leads = (not math.isnan(ci_vel[0])) and ci_vel[0] > 0
    beats_naive = (not math.isnan(ci_diff[0])) and ci_diff[0] > 0
    underpowered = n < min_points or (math.isnan(ci_vel[0]))

    if underpowered:
        verdict = "underpowered"
    elif velocity_leads and beats_naive:
        verdict = "leads_and_beats_naive"
    elif velocity_leads:
        verdict = "leads_but_not_beyond_naive"
    else:
        verdict = "no_lead"

    return {
        "verdict": verdict,
        "params": {
            "horizon_snaps": horizon_snaps, "n_boot": n_boot,
            "min_points": min_points, "min_history_snaps": MIN_HISTORY_SNAPS,
            "source": "emergent_clusters snapshot series",
        },
        "n_points": n,
        "n_topics": n_topics_used,
        "forward_spearman": {
            "velocity":   {"corr": round(c_vel, 4),   "ci95": [round(ci_vel[0], 4), round(ci_vel[1], 4)]},
            "surprise":   {"corr": round(c_sur, 4),   "ci95": [round(ci_sur[0], 4), round(ci_sur[1], 4)]},
            "changed10h": {"corr": round(c_naive, 4), "ci95": [round(ci_naive[0], 4), round(ci_naive[1], 4)]},
        },
        "velocity_minus_naive_diff_ci95": [round(ci_diff[0], 4), round(ci_diff[1], 4)],
    }


def _print(report: dict) -> None:
    import json
    print(json.dumps(report, indent=2, ensure_ascii=False))
    v = report.get("verdict")
    fs = report.get("forward_spearman")
    if not fs:
        return
    print("\n--- reading ---")
    print(f"points={report['n_points']} topics={report['n_topics']} verdict={v}")
    print(f"  velocity → future growth: {fs['velocity']['corr']:+.3f}  CI{fs['velocity']['ci95']}")
    print(f"  surprise → future growth: {fs['surprise']['corr']:+.3f}  CI{fs['surprise']['ci95']}")
    print(f"  changed  → future growth: {fs['changed10h']['corr']:+.3f}  CI{fs['changed10h']['ci95']}  (naive baseline)")
    print(f"  velocity − naive diff CI:  {report['velocity_minus_naive_diff_ci95']}")
    if v == "leads_and_beats_naive":
        print("  => WIRE topic_movement into thread ordering (behind A/B).")
    elif v == "leads_but_not_beyond_naive":
        print("  => velocity has forward signal but no gain over changed_10h; keep changed_10h.")
    elif v == "no_lead":
        print("  => velocity does NOT lead volume; topic_movement = display-only chip.")
    else:
        print("  => underpowered: too few points / wide CI. Re-run after substrate thickens.")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon-snaps", type=int, default=2,
                        help="future window in snapshots (~8h each)")
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--min-points", type=int, default=200)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    report = await run(args.horizon_snaps, args.n_boot, args.min_points, args.limit)
    _print(report)


if __name__ == "__main__":
    import asyncpg  # noqa: F401  (imported here so --help works without the dep)
    asyncio.run(main())
