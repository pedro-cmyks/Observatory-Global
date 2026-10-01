"""Slot planning for the on-demand local refresh (scripts/local_refresh.py)."""
from datetime import datetime, timedelta, timezone

from scripts.local_refresh import floor_slot, plan_slots, slot_from_url

UTC = timezone.utc


def test_floor_slot_snaps_to_the_quarter_hour():
    assert floor_slot(datetime(2026, 10, 1, 14, 16, 59, tzinfo=UTC)) == datetime(2026, 10, 1, 14, 15, tzinfo=UTC)


def test_slot_from_url_reads_both_lanes():
    want = datetime(2026, 10, 1, 16, 0, tzinfo=UTC)
    assert slot_from_url("http://data.gdeltproject.org/gdeltv2/20261001160000.gkg.csv.zip") == want
    assert slot_from_url("http://data.gdeltproject.org/gdeltv2/20261001160000.translation.gkg.csv.zip") == want


def test_replays_every_file_after_the_last_ingested_bucket():
    last = datetime(2026, 10, 1, 14, 15, tzinfo=UTC)
    latest = datetime(2026, 10, 1, 16, 0, tzinfo=UTC)
    slots, hole = plan_slots(last, latest, max_hours=36)
    assert slots[0] == datetime(2026, 10, 1, 14, 30, tzinfo=UTC)
    assert slots[-1] == latest
    assert len(slots) == 7
    assert hole == 0


def test_already_current_plans_nothing():
    latest = datetime(2026, 10, 1, 16, 0, tzinfo=UTC)
    assert plan_slots(latest, latest, max_hours=36) == ([], 0.0)


def test_gap_longer_than_max_hours_is_capped_and_the_hole_is_reported():
    latest = datetime(2026, 10, 5, 0, 0, tzinfo=UTC)
    last = latest - timedelta(hours=100)
    slots, hole = plan_slots(last, latest, max_hours=36)
    assert len(slots) == 36 * 4
    assert slots[0] == latest - timedelta(hours=36) + timedelta(minutes=15)
    assert hole == 100 - 36


def test_step_thins_the_replay_but_always_keeps_the_newest_file():
    last = datetime(2026, 10, 1, 0, 0, tzinfo=UTC)
    latest = datetime(2026, 10, 2, 0, 0, tzinfo=UTC)
    slots, _ = plan_slots(last, latest, max_hours=36, step=4)
    assert len(slots) == 24
    assert slots[-1] == latest
    assert all(b - a == timedelta(hours=1) for a, b in zip(slots, slots[1:]))
    assert slots[0] > last
