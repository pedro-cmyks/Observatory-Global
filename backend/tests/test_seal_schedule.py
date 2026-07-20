"""Honest next-seal-attempt truth (council N10).

The staleness banner used to promise "next seal attempt 02:30"
unconditionally. The schedule service computes the REAL next attempt from
the launchd schedule constant (02:30 America/Bogota) and a labeled
schedule-window heuristic for whether an attempt is plausibly in flight.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.services.seal_schedule import (
    SEAL_RUN_WINDOW_H,
    SEAL_TZ,
    build_seal_schedule,
)

BOGOTA = ZoneInfo(SEAL_TZ)


def _utc(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def test_before_todays_attempt_points_at_today():
    # 01:00 Bogota = 06:00 UTC — the next attempt is TODAY 02:30 local.
    out = build_seal_schedule(now=_utc(2026, 7, 20, 6, 0))
    nxt = datetime.fromisoformat(out["next_attempt_at"])
    assert nxt.astimezone(BOGOTA).strftime("%Y-%m-%d %H:%M") == "2026-07-20 02:30"
    assert out["next_attempt_local"] == "02:30"


def test_after_todays_attempt_points_at_tomorrow():
    # 10:00 Bogota — today's 02:30 already passed.
    out = build_seal_schedule(now=_utc(2026, 7, 20, 15, 0))
    nxt = datetime.fromisoformat(out["next_attempt_at"])
    assert nxt.astimezone(BOGOTA).strftime("%Y-%m-%d %H:%M") == "2026-07-21 02:30"


def test_window_open_when_no_seal_landed_yet():
    # 04:00 Bogota, latest seal is from YESTERDAY -> attempt plausibly running.
    out = build_seal_schedule(
        now=_utc(2026, 7, 20, 9, 0),
        last_sealed_at=_utc(2026, 7, 19, 8, 0),
    )
    assert out["attempt_window_open"] is True


def test_window_closed_once_seal_landed():
    # 04:00 Bogota but TODAY's seal already landed after 02:30 local.
    out = build_seal_schedule(
        now=_utc(2026, 7, 20, 9, 0),
        last_sealed_at=_utc(2026, 7, 20, 8, 30),
    )
    assert out["attempt_window_open"] is False


def test_window_closed_outside_run_window():
    # Long after 02:30 + window, even with a stale seal — honest false:
    # the run is no longer plausibly in flight, it FAILED.
    late_utc_hour = 2 + 5 + SEAL_RUN_WINDOW_H + 1  # Bogota 02:30+window+1h
    out = build_seal_schedule(
        now=_utc(2026, 7, 20, late_utc_hour, 0),
        last_sealed_at=_utc(2026, 7, 18, 8, 0),
    )
    assert out["attempt_window_open"] is False


def test_window_open_when_never_sealed():
    out = build_seal_schedule(now=_utc(2026, 7, 20, 9, 0), last_sealed_at=None)
    assert out["attempt_window_open"] is True


def test_naive_last_sealed_treated_as_utc():
    out = build_seal_schedule(
        now=_utc(2026, 7, 20, 9, 0),
        last_sealed_at=datetime(2026, 7, 20, 8, 30),  # naive
    )
    assert out["attempt_window_open"] is False


def test_basis_labels_the_inference():
    out = build_seal_schedule(now=_utc(2026, 7, 20, 6, 0))
    assert "schedule" in out["basis"]
