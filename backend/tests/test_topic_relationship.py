"""Unified Engine F0.4 — relationship classifier tests (spec §9.2)."""
from __future__ import annotations

from app.services.topic_relationship import (
    PUBLIC_LED_RATIO,
    RELATIONSHIP_TYPES,
    classify_relationship,
)


def _type(**kw) -> str:
    return classify_relationship(**kw)["relationship"]


def test_media_led_press_only():
    assert _type(evidence=40, discussion=0, mood=0) == "media-led"


def test_media_led_press_outweighs_discussion():
    # discussion present but below evidence → still media-led
    assert _type(evidence=40, discussion=10, mood=0) == "media-led"


def test_public_led_discussion_outweighs_press():
    assert _type(evidence=10, discussion=30, mood=0) == "public-led"


def test_public_led_boundary_is_inclusive():
    # discussion == evidence → ratio 1.0 == PUBLIC_LED_RATIO → public-led
    assert PUBLIC_LED_RATIO == 1.0
    assert _type(evidence=20, discussion=20, mood=0) == "public-led"


def test_social_led_discussion_no_press_no_mood():
    assert _type(evidence=0, discussion=25, mood=0) == "social-led"


def test_silent_risk_mood_present_press_absent():
    assert _type(evidence=0, discussion=8, mood=12) == "silent-risk"


def test_silent_risk_is_relative_not_absolute_zero():
    # a couple of stray press rows below the 5% floor still reads as silent-risk
    # (the #172 ratio reframe), not media-led.
    assert _type(evidence=1, discussion=20, mood=15) == "silent-risk"


def test_negligible_press_without_mood_is_social_led():
    assert _type(evidence=1, discussion=40, mood=0) == "social-led"


def test_meaningful_press_above_floor_is_not_silent():
    # evidence_frac >= 5% → press is meaningfully present, classify on ratio
    r = classify_relationship(evidence=5, discussion=50, mood=20)
    assert r["relationship"] == "public-led"
    assert r["evidence_fraction"] >= 0.05


def test_uncoupled_attention_no_members():
    assert _type(evidence=0, discussion=0, mood=0) == "uncoupled-attention"


def test_uncoupled_attention_movement_only():
    r = classify_relationship(evidence=0, discussion=0, mood=0, movement=7)
    assert r["relationship"] == "uncoupled-attention"
    assert r["movement_count"] == 7


def test_all_outputs_are_known_types():
    cases = [
        dict(evidence=40, discussion=0, mood=0),
        dict(evidence=10, discussion=30, mood=0),
        dict(evidence=0, discussion=25, mood=0),
        dict(evidence=0, discussion=8, mood=12),
        dict(evidence=0, discussion=0, mood=0),
    ]
    for kw in cases:
        assert classify_relationship(**kw)["relationship"] in RELATIONSHIP_TYPES


def test_counts_and_ratio_echoed():
    r = classify_relationship(evidence=10, discussion=30, mood=5, movement=2)
    assert r["evidence_count"] == 10
    assert r["discussion_count"] == 30
    assert r["mood_count"] == 5
    assert r["movement_count"] == 2
    assert r["public_ratio"] == 3.0
    assert r["verified_evidence_only"] is True
    assert r["rationale"]


def test_negative_inputs_clamped():
    r = classify_relationship(evidence=-5, discussion=-1, mood=0)
    assert r["evidence_count"] == 0
    assert r["relationship"] == "uncoupled-attention"
