"""M2 black-hole audit — pure floor math + prune bookkeeping (no DB).

Freezes: the 07-03 adaptive-floor formula (mean+2.5σ), the robust variant's
contamination resistance (the reason the prune uses it), knee derivation from
the junk-fraction distribution (never a guessed cutoff), lane eligibility,
and the quarantine reason format the reversal one-liner matches on.
"""
from __future__ import annotations

import datetime as dt
import random
import statistics

from scripts.audit_topic_blackholes import (
    MAD_TO_SIGMA,
    MAX_PRUNE_FRAC,
    MIN_BG,
    MIN_MEMBERS_PRUNE,
    REASON_PREFIX,
    FloorStats,
    classify_lane,
    floor_stats,
    junk_split,
    knee_threshold,
    lane_eligible,
    quarantine_reason,
    run_id_for,
)


# ---------------------------------------------------------------- floor_stats
def test_floor_stats_matches_precedent_formula():
    """naive floor = mean + 2.5σ, exactly the 07-03 adaptive_noise_cut."""
    rng = random.Random(7)
    bg = [rng.gauss(0.85, 0.01) for _ in range(400)]
    fs = floor_stats(bg)
    assert fs.n == 400
    assert abs(fs.naive_floor - (statistics.fmean(bg) + 2.5 * statistics.stdev(bg))) < 1e-12


def test_floor_stats_robust_equals_naive_on_clean_normal():
    """On uncontaminated ~normal background the two floors agree closely
    (MAD*1.4826 is the normal-consistent σ estimate)."""
    rng = random.Random(3)
    bg = [rng.gauss(0.85, 0.012) for _ in range(4000)]
    fs = floor_stats(bg)
    assert abs(fs.robust_floor - fs.naive_floor) < 0.006


def test_floor_stats_robust_resists_contamination():
    """A mega-story's own coverage inside the random background (the Ukraine
    pilot case) inflates the naive floor; the robust floor must hold."""
    rng = random.Random(11)
    clean = [rng.gauss(0.85, 0.01) for _ in range(360)]
    contaminated = clean + [rng.gauss(0.94, 0.01) for _ in range(40)]  # 10% same-story
    fs_clean = floor_stats(clean)
    fs_cont = floor_stats(contaminated)
    naive_inflation = fs_cont.naive_floor - fs_clean.naive_floor
    robust_drift = abs(fs_cont.robust_floor - fs_clean.robust_floor)
    assert naive_inflation > 0.02      # naive floor blows up
    assert robust_drift < 0.01         # robust floor holds
    assert fs_cont.robust_floor < fs_cont.naive_floor


def test_floor_stats_small_sample_is_honest_none():
    fs = floor_stats([0.85] * (MIN_BG - 1))
    assert fs == FloorStats(MIN_BG - 1, None, None, None, None, None, None)


# ---------------------------------------------------------------- junk_split
def test_junk_split_counts_strictly_below_floor():
    below, total = junk_split([0.80, 0.85, 0.90, 0.95], 0.90)
    assert (below, total) == (2, 4)


def test_junk_split_no_floor_flags_nothing():
    assert junk_split([0.1, 0.2], None) == (0, 2)


# ---------------------------------------------------------------- knee
def test_knee_lands_at_tail_onset_of_flat_then_rising_curve():
    """Typical audit shape: most lanes ~0 junk, a tail of black holes.
    The threshold is the FIRST TAIL VALUE (strictly above the elbow), so
    `frac >= knee` selects exactly the anomalous tail, never the bulk."""
    fracs = [0.0] * 60 + [0.01] * 20 + [0.02] * 10 + [0.3, 0.4, 0.55, 0.7, 0.85]
    knee = knee_threshold(fracs)
    assert knee == 0.3
    assert sum(1 for f in fracs if f >= knee) == 5  # exactly the tail


def test_knee_gapless_ramp_is_weakly_defined_but_from_the_distribution():
    """On a smooth ramp there is no elbow gap; the knee lands wherever float
    noise peaks. The contract that holds: it is a VALUE FROM the distribution
    (never fabricated), and the caller sees the qualifying-lane count to judge
    whether the run is pruneable at all."""
    fracs = [i / 100 for i in range(100)]
    knee = knee_threshold(fracs)
    assert knee in fracs


def test_knee_flat_distribution_returns_none():
    assert knee_threshold([0.1] * 50) is None


def test_knee_too_few_points_returns_none():
    assert knee_threshold([0.0, 0.5, 1.0]) is None


def test_knee_is_a_value_from_the_distribution():
    fracs = [0.0, 0.0, 0.0, 0.05, 0.05, 0.1, 0.6, 0.9]
    knee = knee_threshold(fracs)
    assert knee in fracs


# ---------------------------------------------------------------- eligibility
def test_lane_eligibility_requires_floor_and_min_members():
    assert lane_eligible(MIN_MEMBERS_PRUNE, 0.9)
    assert not lane_eligible(MIN_MEMBERS_PRUNE - 1, 0.9)
    assert not lane_eligible(100, None)


# ---------------------------------------------------------------- classify
def test_classify_prune_band_is_knee_to_half():
    """Prune only lanes with a resolvable core: knee <= frac < 0.5. A median
    member above its own floor ⟺ frac < 0.5 — the guard that spared dt-10
    (mush-centroid Ukraine, all members 'below floor') from false eviction."""
    knee = 0.026
    assert classify_lane(0.0, knee) == "healthy"
    assert classify_lane(0.02, knee) == "healthy"
    assert classify_lane(0.026, knee) == "prune"          # at the knee
    assert classify_lane(0.49, knee) == "prune"
    assert classify_lane(MAX_PRUNE_FRAC, knee) == "centroid_divorced"
    assert classify_lane(1.0, knee) == "centroid_divorced"


def test_classify_no_knee_never_prunes():
    """A degenerate distribution (no derivable knee) must never prune."""
    assert classify_lane(0.9, None) == "healthy"


# ---------------------------------------------------------------- bookkeeping
def test_quarantine_reason_carries_run_and_matches_reversal_prefix():
    run = run_id_for(42, dt.date(2026, 7, 20))
    assert run == "m2-20260720-s42"
    reason = quarantine_reason(0.8612, 0.8934, run)
    assert reason == "blackhole-floor-v1 run=m2-20260720-s42 sim=0.8612 floor=0.8934"
    # the documented reversal one-liner matches on this prefix
    assert reason.startswith(f"{REASON_PREFIX} run={run}")
    assert reason.startswith(REASON_PREFIX)
