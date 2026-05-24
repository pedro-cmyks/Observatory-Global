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
        "parent_domain": "economy-livelihoods",
        "signal_count": 120,
        "source_count": 18,
        "country_count": 3,
        "avg_confidence": 0.81,
        "first_seen": None,
        "changed_10h": 47,
        "sentiment_swing_10h": -0.24,
        "top_countries": ["NG", "PE"],
        "top_country_names": ["Nigeria", "Peru"],
        "top_sources": ["reuters.com", "elcomercio.pe"],
        "top_entities": ["Bola Tinubu", "Dina Boluarte"],
        "hourly_timeline": [{"hour": "2026-05-24T10:00:00Z", "count": 12}],
        "related_topics": [{"topic": "labor-strike-disruption", "score": 0.21}],
    }
    thread = assemble_thread(row)
    assert thread["thread_id"] == "fuel-subsidy-unrest--ng-pe"
    assert thread["anchor_topics"] == ["fuel-subsidy-unrest"]
    assert thread["parent_domain"] == "economy-livelihoods"
    assert thread["confidence"] == "high"
    assert thread["avg_confidence"] == 0.81
    # 47 / 120 = 0.392 → surging (>= 5% delta)
    assert thread["trend"] == "surging"
    assert thread["top_entities"] == ["Bola Tinubu", "Dina Boluarte"]
    assert thread["hourly_timeline"][0]["count"] == 12
    assert (
        thread["why_now"]
        == "47 more signals in the last 10h, concentrated in Nigeria and Peru."
    )
    assert thread["related_threads"][0]["topic"] == "labor-strike-disruption"


def test_assemble_thread_exposes_quality_metadata_and_raw_entity_guardrails():
    row = {
        "topic_slug": "transport-corridor-disruption",
        "topic_label": "Transport corridor disruption",
        "parent_domain": "infrastructure",
        "signal_count": 25,
        "source_count": 4,
        "country_count": 2,
        "avg_confidence": 0.67,
        "first_seen": None,
        "changed_10h": 5,
        "sentiment_swing_10h": 0.08,
        "lex_count": 6,
        "theme_count": 19,
        "top_countries": ["US", "RB"],
        "top_country_names": ["United States", "RB"],
        "top_sources": ["zazoom.it", "reuters.com"],
        "top_entities": ["Pacific Ocean", "El Niño"],
        "hourly_timeline": [],
        "related_topics": [],
    }

    thread = assemble_thread(row)

    assert thread["top_people"] == []
    assert thread["top_entities"] == ["Pacific Ocean", "El Niño"]
    assert thread["quality"] == {
        "lex_pct": 0.24,
        "method_mix": {"lex": 6, "theme": 19},
        "source_flags": {"aggregator_dominant": True},
        "geo_flags": {"unresolved_country_code": True},
        "entity_flags": {"raw_entity_field_untyped": True},
    }


def test_assemble_thread_quality_metadata_handles_zero_counts_and_clean_rows():
    row = {
        "topic_slug": "heat-health-risk",
        "topic_label": "Heat and public health risk",
        "signal_count": 0,
        "source_count": 0,
        "country_count": 0,
        "avg_confidence": None,
        "changed_10h": 0,
        "lex_count": None,
        "theme_count": None,
        "top_countries": [],
        "top_country_names": [],
        "top_sources": ["reuters.com"],
        "top_entities": [],
    }

    thread = assemble_thread(row)

    assert thread["quality"]["lex_pct"] == 0
    assert thread["quality"]["method_mix"] == {"lex": 0, "theme": 0}
    assert thread["quality"]["source_flags"] == {"aggregator_dominant": False}
    assert thread["quality"]["geo_flags"] == {"unresolved_country_code": False}
    assert thread["quality"]["entity_flags"] == {"raw_entity_field_untyped": False}


def test_trend_label_classifies_volume_delta():
    from app.services.thread_intelligence import _trend_label
    assert _trend_label(0, 100) == "stable"
    assert _trend_label(10, 100) == "surging"  # 10% jump
    assert _trend_label(-20, 100) == "fading"
    assert _trend_label(2, 1000) == "stable"  # 0.2% noise
    assert _trend_label(100, 0) == "stable"  # divide-by-zero guard


def test_threads_sql_exposes_enriched_fields():
    """M3a additions: parent_domain, first_seen, top_entities, hourly_timeline
    must be SELECTed so the frontend NarrativeThreads card has parity with
    the legacy /api/v2/narratives shape."""
    assert "parent_domain" in THREADS_SQL
    assert "first_seen" in THREADS_SQL
    assert "top_entities" in THREADS_SQL
    assert "hourly_timeline" in THREADS_SQL
    assert "entity_lists" in THREADS_SQL
    assert "timeline_base" in THREADS_SQL
    # Performance: PK guarantees uniqueness within (topic, model_version)
    # group, so COUNT(*) replaces COUNT(DISTINCT signal_id) in topic_agg.
    # related_counts intentionally keeps DISTINCT because it joins back to
    # signal_topic_assignments and may see the same signal twice.
    assert "COUNT(*)::int AS signal_count" in THREADS_SQL


def test_threads_sql_exposes_method_counts_for_quality_metadata():
    assert "sta.evidence" in THREADS_SQL
    assert "evidence->>'lex_count'" in THREADS_SQL
    assert "evidence->>'theme_hits'" in THREADS_SQL
    assert "ta.lex_count" in THREADS_SQL
    assert "ta.theme_count" in THREADS_SQL


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
