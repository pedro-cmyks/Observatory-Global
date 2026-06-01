from __future__ import annotations

from datetime import datetime, timezone

from scripts.evidence_role_sampler import (
    SAMPLE_SQL,
    build_cluster_id,
    build_teacher_packet_row,
)


def test_build_cluster_id_is_stable_from_snapshot_and_cluster_pk():
    assert build_cluster_id("2026-06-01T12:41:32Z", 48) == "2026-06-01T12:41:32Z/48"
    snapshot_at = datetime(2026, 6, 1, 12, 41, 32, tzinfo=timezone.utc)
    assert build_cluster_id(snapshot_at, 48) == "2026-06-01T12:41:32+00:00/48"


def test_build_teacher_packet_row_maps_cluster_signal_and_candidate_fields():
    row = build_teacher_packet_row(
        {
            "signal_id": 10,
            "headline": "Iran threatens retaliation after sanctions &amp; tariffs",
            "source_name": "example.org",
            "source_lang": "en",
            "country_code": "IR",
            "cluster_pk": 48,
            "snapshot_at": "2026-06-01T12:41:32Z",
            "cluster_label": "Iran Threats &amp; US",
            "cluster_description": "Iran-US sanctions and threats.",
            "raw_signal_count": 122,
            "n_signals": 109,
            "cohesion": 0.72,
            "candidate_topic_slug": "sanctions-diplomatic-pressure",
            "candidate_topic_label": "Sanctions and diplomatic pressure",
            "candidate_confidence": 0.77,
            "gate_score": 0.66,
            "gate_kept": False,
            "matched_terms": ["sanction"],
            "sample_reason": "centroid_near",
        }
    )

    assert row["schema_version"] == "atlas-evidence-role-packet-v1"
    assert row["cluster_id"] == "2026-06-01T12:41:32Z/48"
    assert row["headline"] == "Iran threatens retaliation after sanctions & tariffs"
    assert row["cluster_label"] == "Iran Threats & US"
    assert row["candidate_topic_slug"] == "sanctions-diplomatic-pressure"
    assert row["gate_kept"] is False
    assert row["matched_terms"] == ["sanction"]
    assert row["teacher_role"] is None


def test_sampler_sql_reads_emergent_clusters_signals_and_assignments():
    assert "FROM emergent_clusters ec" in SAMPLE_SQL
    assert "JOIN signals_v2 s" in SAMPLE_SQL
    assert "LEFT JOIN signal_topic_assignments sta" in SAMPLE_SQL
    assert "sample_signal_ids" in SAMPLE_SQL
