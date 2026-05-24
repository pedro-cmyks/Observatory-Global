from __future__ import annotations

from app.services.thread_intelligence import (
    THREADS_SQL,
    assemble_thread,
    build_thread_id,
    build_thread_label,
    confidence_band,
    parse_thread_id,
)


def test_confidence_band_high():
    assert (
        confidence_band(
            evidence_count=80,
            source_count=12,
            geo_count=5,
            assignment_confidence=0.82,
        )
        == "high"
    )


def test_confidence_band_thin():
    assert (
        confidence_band(
            evidence_count=6,
            source_count=2,
            geo_count=1,
            assignment_confidence=0.7,
        )
        == "thin"
    )


def test_confidence_band_degraded():
    assert (
        confidence_band(
            evidence_count=100,
            source_count=1,
            geo_count=1,
            assignment_confidence=0.4,
        )
        == "degraded"
    )


def test_build_thread_id_is_stable():
    assert (
        build_thread_id("fuel-subsidy-unrest", ["NG", "PE"])
        == "fuel-subsidy-unrest--ng-pe"
    )


def test_parse_thread_id_returns_anchor_and_country_codes():
    assert parse_thread_id("fuel-subsidy-unrest--ng-pe") == (
        "fuel-subsidy-unrest",
        ["NG", "PE"],
    )


def test_build_thread_label_uses_topic_and_geography():
    label = build_thread_label(
        anchor_label="Fuel subsidy unrest",
        top_countries=["Nigeria", "Peru"],
        changed_10h=42,
    )
    assert label == "Fuel subsidy unrest intensifies in Nigeria and Peru"


def test_assemble_thread_contract():
    row = {
        "topic_slug": "fuel-subsidy-unrest",
        "topic_label": "Fuel subsidy unrest",
        "signal_count": 120,
        "source_count": 18,
        "country_count": 3,
        "avg_confidence": 0.81,
        "changed_10h": 47,
        "sentiment_swing_10h": -0.24,
        "top_countries": ["NG", "PE"],
        "top_country_names": ["Nigeria", "Peru"],
        "top_sources": ["reuters.com", "elcomercio.pe"],
        "related_topics": [{"topic": "labor-strike-disruption", "score": 0.21}],
    }
    thread = assemble_thread(row)
    assert thread["thread_id"] == "fuel-subsidy-unrest--ng-pe"
    assert thread["anchor_topics"] == ["fuel-subsidy-unrest"]
    assert thread["confidence"] == "high"
    assert (
        thread["why_now"]
        == "47 more signals in the last 10h, concentrated in Nigeria and Peru."
    )
    assert thread["related_threads"][0]["topic"] == "labor-strike-disruption"


def test_threads_sql_uses_assignments_and_atlas_topics():
    assert "signal_topic_assignments" in THREADS_SQL
    assert "atlas_topics" in THREADS_SQL
    assert "model_version = 'theme-hint-lex-v2'" in THREADS_SQL
    assert "assigned_at >= NOW() - ($1::int * INTERVAL '1 hour')" in THREADS_SQL
    assert "LIMIT $2" in THREADS_SQL
