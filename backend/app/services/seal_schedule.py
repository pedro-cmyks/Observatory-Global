"""Honest next-seal-attempt truth for the staleness banner (council N10).

The sealed edition is built by the M1 nightly (launchd
``com.atlas.scoped-snapshot``, StartCalendarInterval 02:30, which fires in
the machine's LOCAL timezone — America/Bogota, no DST). The banner used to
promise "next seal attempt 02:30" unconditionally, even when the attempt
was hours away or plausibly running right now.

This module computes, from the schedule CONSTANT (kept in sync with
``infra/launchd/com.atlas.scoped-snapshot.plist``):

- ``next_attempt_at``: the actual next 02:30 Bogota as an ISO timestamp.
- ``attempt_window_open``: whether an attempt is plausibly in flight NOW —
  a schedule-window inference (the serving box cannot observe the M1), true
  only inside [02:30, 02:30 + SEAL_RUN_WINDOW_H) local when no seal has
  landed for that run yet. Labeled via ``basis``; never presented as a live
  observation.

Pure: the clock is injected, so it is deterministic under test.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

# Keep in sync with infra/launchd/com.atlas.scoped-snapshot.plist.
SEAL_HOUR = 2
SEAL_MINUTE = 30
SEAL_TZ = "America/Bogota"
# The nightly regularly runs long (post-steps: court, umbrellas, lineage,
# events, publication) — observed 4-7h wall time. Inside this window after
# 02:30 an unlanded seal is plausibly still in flight; past it, it failed.
SEAL_RUN_WINDOW_H = 7


def _aware_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def build_seal_schedule(
    now: Optional[datetime] = None,
    last_sealed_at: Optional[datetime] = None,
) -> dict:
    """Next-attempt truth from the launchd schedule constant (pure)."""
    tz = ZoneInfo(SEAL_TZ)
    now_utc = _aware_utc(now) if now is not None else datetime.now(timezone.utc)
    local_now = now_utc.astimezone(tz)

    todays_attempt = local_now.replace(
        hour=SEAL_HOUR, minute=SEAL_MINUTE, second=0, microsecond=0,
    )
    next_attempt = (
        todays_attempt
        if local_now < todays_attempt
        else todays_attempt + timedelta(days=1)
    )

    window_open = False
    if todays_attempt <= local_now < todays_attempt + timedelta(hours=SEAL_RUN_WINDOW_H):
        sealed_this_run = (
            last_sealed_at is not None
            and _aware_utc(last_sealed_at) >= todays_attempt
        )
        window_open = not sealed_this_run

    return {
        "next_attempt_at": next_attempt.isoformat(),
        "next_attempt_local": f"{SEAL_HOUR:02d}:{SEAL_MINUTE:02d}",
        "attempt_window_open": window_open,
        "basis": "launchd com.atlas.scoped-snapshot schedule constant "
                 f"({SEAL_HOUR:02d}:{SEAL_MINUTE:02d} {SEAL_TZ}); window is a "
                 "schedule inference, not a live observation",
    }
