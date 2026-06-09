from __future__ import annotations

from datetime import datetime, timezone

from scripts.dynamic_topic_state_report import (
    Observation,
    build_topic_report,
    estimate_state,
)


def _ts(hour: int) -> datetime:
    return datetime(2026, 6, 1, hour, tzinfo=timezone.utc)


def test_estimate_state_marks_accelerating_topic():
    observations = [
        Observation(snapshot_at=_ts(0), n_signals=20, cohesion=0.8, noise_rate=0.1),
        Observation(snapshot_at=_ts(6), n_signals=40, cohesion=0.8, noise_rate=0.1),
        Observation(snapshot_at=_ts(12), n_signals=90, cohesion=0.8, noise_rate=0.1),
    ]

    estimate = estimate_state(observations)

    assert estimate.smoothed_intensity > 0
    assert estimate.velocity > 0
    assert estimate.trend == "accelerating"
    assert estimate.uncertainty < 2.0


def test_estimate_state_marks_jump_as_surprise():
    observations = [
        Observation(snapshot_at=_ts(0), n_signals=30, cohesion=0.8, noise_rate=0.1),
        Observation(snapshot_at=_ts(6), n_signals=32, cohesion=0.8, noise_rate=0.1),
        Observation(snapshot_at=_ts(12), n_signals=180, cohesion=0.8, noise_rate=0.1),
    ]

    estimate = estimate_state(observations)

    assert estimate.surprise > 1.0
    assert estimate.trend in {"accelerating", "surging"}


def test_single_observation_is_uncertain_and_stationary():
    estimate = estimate_state([
        Observation(snapshot_at=_ts(0), n_signals=50, cohesion=None, noise_rate=None)
    ])

    assert estimate.velocity == 0
    assert estimate.trend == "insufficient_history"
    assert estimate.uncertainty >= 1.0


def test_build_topic_report_keeps_lifecycle_state_separate_from_kalman_reading():
    report = build_topic_report(
        topic_id=17,
        label="Colombia Security Pressure",
        lifecycle_state="active",
        current_noise_rate=0.12,
        current_agg_n_signals=300,
        observations=[
            Observation(snapshot_at=_ts(0), n_signals=40, cohesion=0.9, noise_rate=0.1),
            Observation(snapshot_at=_ts(6), n_signals=45, cohesion=0.9, noise_rate=0.1),
            Observation(snapshot_at=_ts(12), n_signals=140, cohesion=0.9, noise_rate=0.1),
        ],
    )

    assert report["dynamic_topic_id"] == 17
    assert report["lifecycle_state"] == "active"
    assert report["state_estimate"]["trend"] in {"accelerating", "surging"}
    assert report["recommendation"] == "watch_acceleration"


def test_build_topic_report_marks_explicit_roundup_as_do_not_promote():
    report = build_topic_report(
        topic_id=22,
        label="Brazil News Roundup",
        lifecycle_state="candidate",
        current_noise_rate=0.12,
        current_agg_n_signals=400,
        observations=[
            Observation(snapshot_at=_ts(0), n_signals=30, cohesion=0.8, noise_rate=0.1),
            Observation(snapshot_at=_ts(6), n_signals=140, cohesion=0.8, noise_rate=0.1),
        ],
    )

    assert report["is_roundup"] is True
    assert report["recommendation"] == "do_not_promote_roundup"
