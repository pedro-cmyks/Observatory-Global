"""Unified Engine F1.2 — Lemmy ingest parse tests (spec §7)."""
from __future__ import annotations

from datetime import timezone

from app.services.ingest_lemmy import (
    LEMMY_INSTANCES,
    _parse_published,
)


def test_parse_published_z_suffix_with_micros():
    dt = _parse_published("2026-06-29T18:00:00.123456Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert (dt.year, dt.month, dt.day, dt.hour) == (2026, 6, 29, 18)


def test_parse_published_offset_form():
    dt = _parse_published("2026-06-29T18:00:00+00:00")
    assert dt is not None and dt.utcoffset().total_seconds() == 0


def test_parse_published_naive_is_assumed_utc():
    dt = _parse_published("2026-06-29T18:00:00")
    assert dt is not None and dt.tzinfo == timezone.utc


def test_parse_published_second_precision_fallback():
    # a form fromisoformat may choke on → strptime fallback to second precision
    dt = _parse_published("2026-06-29T18:00:00.000Z")
    assert dt is not None and dt.hour == 18


def test_parse_published_garbage_returns_none():
    assert _parse_published("not-a-date") is None
    assert _parse_published("") is None
    assert _parse_published(None) is None


def test_instances_wellformed_and_country_codes_valid():
    assert LEMMY_INSTANCES, "must have at least one instance"
    for host, origin, lang in LEMMY_INSTANCES:
        assert host and "." in host
        assert origin is None or (isinstance(origin, str) and len(origin) == 2 and origin.isupper())
        assert lang and lang.islower()


def test_country_instances_present():
    # the value of Lemmy is instance=country; at least some must carry an origin
    origins = {o for _, o, _ in LEMMY_INSTANCES if o}
    assert {"IT", "FR", "GB", "CA"} <= origins
