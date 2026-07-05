"""X5 (L2 review 2026-07-05): freeze the two-tier gate contract.

The verified/extended/candidate grading + the below-gate fallback are
load-bearing serving honesty (07-04 cutover) and had NO test coverage — a
threshold retune could silently flip what the detail surfaces serve.
"""
import app.main_v2  # noqa: F401 — resolve the app↔router import cycle first
from app.routers.themes import _gate_tier


class TestGateTier:
    def test_gate_kept_is_verified_regardless_of_score(self):
        assert _gate_tier(True, 0.10, 0.95) == "verified"
        assert _gate_tier(True, None, 0.95) == "verified"

    def test_score_at_or_above_extended_threshold_is_extended(self):
        assert _gate_tier(False, 0.95, 0.95) == "extended"
        assert _gate_tier(False, 0.99, 0.95) == "extended"
        assert _gate_tier(None, 0.96, 0.95) == "extended"

    def test_below_threshold_or_unscored_is_candidate(self):
        assert _gate_tier(False, 0.80, 0.95) == "candidate"
        assert _gate_tier(False, None, 0.95) == "candidate"
        assert _gate_tier(None, None, 0.95) == "candidate"

    def test_disabled_tier_file_means_nothing_extends(self):
        # missing thresholds file → ext_thr 1.0 → only gate_kept serves
        assert _gate_tier(False, 0.999, 1.0) == "candidate"
        assert _gate_tier(True, None, 1.0) == "verified"


class TestBelowGateFallbackCondition:
    """The serve-raw decision from themes detail (mirrors the inline logic):
    raw material serves ONLY when the gate is pending or graded coverage is
    effectively empty against substantial raw volume."""

    @staticmethod
    def _fallback(gate_pending: bool, served_n: int, raw_n: int) -> bool:
        return (not gate_pending) and raw_n > 0 and (
            served_n == 0 or (served_n < 5 and raw_n >= 20)
        )

    def test_zero_served_with_raw_falls_back(self):
        assert self._fallback(False, 0, 44) is True

    def test_thin_served_with_big_raw_falls_back(self):
        assert self._fallback(False, 3, 25) is True

    def test_thin_served_with_thin_raw_does_not(self):
        assert self._fallback(False, 3, 10) is False

    def test_healthy_served_never_falls_back(self):
        assert self._fallback(False, 12, 500) is False

    def test_gate_pending_is_its_own_branch_not_fallback(self):
        assert self._fallback(True, 0, 100) is False

    def test_no_raw_no_fallback(self):
        assert self._fallback(False, 0, 0) is False
