"""Honesty guards on the volume z-score.

Cold-user probe 2026-08-12 §4/§7: East Timor showed "12x above 7-day baseline"
in the alert row and "z: 71.2" in its own Trust Indicators. Measured that day,
TL had baseline_avg 2.3 signals/day over 6 observed days with a stddev of ~1.
A "z of 71" off six sparse daily counts is not a sigma anyone can act on -- it
is a divide-by-a-rounding-error printed to one decimal place.

Two defects fixed here:
  1. sigma was scaled LINEARLY with the window (stddev * hours/24) alongside the
     mean. For count data the sd of a sum grows ~sqrt(t), not t, so the multiplier
     (where the factor cancels) stayed stable while z drifted with the window --
     the two numbers on the panel diverged further the more the reader changed it.
  2. a degenerate baseline produced a confident-looking precise z with nothing
     marking it as unusable. It is now flagged so the surface can degrade.
"""
from __future__ import annotations

import math

import pytest

from indicators.normalized_volume import (
    MIN_BASELINE_AVG,
    MIN_BASELINE_DAYS,
    calculate_normalized_volume,
    scale_baseline_stddev,
)


class TestSigmaScaling:
    def test_sigma_of_a_sum_grows_with_the_square_root_of_the_window(self):
        # A 6h window is a quarter of a day: the mean scales by 1/4, sigma by 1/2.
        assert scale_baseline_stddev(8.0, hours=6) == pytest.approx(8.0 * math.sqrt(0.25))

    def test_a_24h_window_is_the_identity(self):
        assert scale_baseline_stddev(8.0, hours=24) == pytest.approx(8.0)

    def test_a_longer_window_widens_sigma_sublinearly(self):
        # 96h = 4 days: linear scaling would have said 4x. Sqrt says 2x.
        assert scale_baseline_stddev(3.0, hours=96) == pytest.approx(6.0)

    def test_non_positive_inputs_degrade_to_zero_rather_than_nan(self):
        assert scale_baseline_stddev(0.0, hours=24) == 0.0
        assert scale_baseline_stddev(5.0, hours=0) == 0.0


class TestThinBaselineFlag:
    def _call(self, **kw):
        params = dict(
            current_count=53,
            baseline_avg=2.3,
            baseline_stddev=1.0,
            days_observed=6,
            baseline_days=7,
        )
        params.update(kw)
        return calculate_normalized_volume(**params)

    def test_the_east_timor_case_is_flagged_thin(self):
        # The exact prod measurement that produced "z: 71.2".
        assert self._call()["thin_baseline"] is True

    def test_a_healthy_baseline_is_not_flagged(self):
        out = self._call(
            current_count=900, baseline_avg=300.0, baseline_stddev=40.0, days_observed=7
        )
        assert out["thin_baseline"] is False
        assert out["z_score"] == pytest.approx(15.0)

    def test_too_few_observed_days_is_thin_even_on_healthy_volume(self):
        out = self._call(
            current_count=900,
            baseline_avg=300.0,
            baseline_stddev=40.0,
            days_observed=MIN_BASELINE_DAYS - 1,
        )
        assert out["thin_baseline"] is True

    def test_a_tiny_baseline_average_is_thin_however_many_days_were_seen(self):
        out = self._call(
            current_count=50,
            baseline_avg=MIN_BASELINE_AVG - 0.1,
            baseline_stddev=1.0,
            days_observed=7,
        )
        assert out["thin_baseline"] is True

    def test_zero_variance_is_thin_and_does_not_fabricate_a_precise_z(self):
        out = self._call(baseline_avg=300.0, baseline_stddev=0.0, days_observed=7)
        assert out["thin_baseline"] is True

    def test_unknown_days_observed_does_not_by_itself_flag_thin(self):
        out = self._call(
            current_count=900, baseline_avg=300.0, baseline_stddev=40.0, days_observed=None
        )
        assert out["thin_baseline"] is False


class TestServedBasis:
    def test_the_payload_names_the_window_it_measured(self):
        out = calculate_normalized_volume(
            current_count=53,
            baseline_avg=2.3,
            baseline_stddev=1.0,
            days_observed=6,
            baseline_days=7,
        )
        # The surface must never hardcode a baseline window again.
        assert out["baseline_days"] == 7
        assert out["days_observed"] == 6

    def test_the_tooltip_discloses_a_thin_baseline_instead_of_asserting_precision(self):
        out = calculate_normalized_volume(
            current_count=53, baseline_avg=2.3, baseline_stddev=1.0, days_observed=6
        )
        assert "thin" in out["tooltip"].lower() or "not meaningful" in out["tooltip"].lower()

    def test_multiplier_is_unchanged_by_the_sigma_fix(self):
        # The ratio never depended on sigma; this pins that the fix is scoped.
        out = calculate_normalized_volume(
            current_count=53, baseline_avg=2.3, baseline_stddev=1.0, days_observed=6
        )
        assert out["multiplier"] == pytest.approx(23.04, abs=0.01)

    def test_no_baseline_still_returns_the_honest_unknown(self):
        out = calculate_normalized_volume(
            current_count=10, baseline_avg=0, baseline_stddev=0, days_observed=0
        )
        assert out["multiplier"] is None
        assert out["z_score"] is None
        assert out["level"] == "unknown"
