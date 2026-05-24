from __future__ import annotations

import asyncio
import inspect

from app.services import thread_intelligence
from app.services.thread_intelligence import (
    THREAD_EVIDENCE_SQL,
    THREADS_SQL,
    _serialize_evidence,
    assemble_thread,
    build_thread_id,
    build_thread_label,
    confidence_band,
    evidence_role,
    fetch_threads,
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


def test_evidence_sql_deduplicates_syndicated_headlines():
    assert "DISTINCT ON (LOWER(s.headline))" in THREAD_EVIDENCE_SQL
    assert "COUNT(*) OVER (PARTITION BY LOWER(s.headline))" in THREAD_EVIDENCE_SQL
    assert "syndication_count" in THREAD_EVIDENCE_SQL
    assert "ORDER BY confidence DESC, timestamp DESC" in THREAD_EVIDENCE_SQL


def test_evidence_role_classifies_by_syndication_count():
    assert evidence_role(1) == "representative"
    assert evidence_role(2) == "repeated"
    assert evidence_role(4) == "repeated"
    assert evidence_role(5) == "syndicated"
    assert evidence_role(25) == "syndicated"


def test_fetch_threads_accepts_external_connection():
    """Milestone 2: briefing reuses its open connection by passing conn=...
    Without this, every briefing request would acquire a second pool
    connection just for the threads section."""
    sig = inspect.signature(fetch_threads)
    assert "conn" in sig.parameters
    assert sig.parameters["conn"].default is None


def test_fetch_threads_uses_supplied_connection_without_pool():
    """When conn is supplied, fetch_threads must NOT touch db.pool."""

    class FakeConn:
        def __init__(self) -> None:
            self.fetch_calls: list[tuple] = []

        async def fetch(self, query, *args, **kwargs):
            self.fetch_calls.append((query, args, kwargs))
            return []

    fake = FakeConn()
    original_pool = getattr(thread_intelligence.db, "pool", None)
    thread_intelligence.db.pool = None  # prove no pool access
    try:
        result = asyncio.run(
            fetch_threads(hours=12, limit=5, conn=fake)
        )
    finally:
        thread_intelligence.db.pool = original_pool

    assert result == []
    assert len(fake.fetch_calls) == 1
    args = fake.fetch_calls[0][1]
    assert args[0] == 12  # hours
    assert args[1] == 5  # limit


def test_serialize_evidence_includes_syndication_metadata():
    row = {
        "id": 42,
        "headline": "Russia launches strikes on Kyiv",
        "source_name": "reuters.com",
        "source_url": "https://reuters.com/x",
        "country_code": "UA",
        "country_name": "Ukraine",
        "timestamp": None,
        "nlp_sentiment": -0.6,
        "confidence": 0.95,
        "syndication_count": 25,
    }
    serialized = _serialize_evidence(row)
    assert serialized["syndication_count"] == 25
    assert serialized["evidence_role"] == "syndicated"
    assert serialized["country_code"] == "UA"
