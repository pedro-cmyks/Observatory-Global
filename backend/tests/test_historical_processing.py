from pathlib import Path

from scripts.historical_process_partition import (
    build_daily_topic_country_rows,
    infer_topic_slug,
)
from scripts.historical_sync import build_upsert_payload


MIGRATION = Path("migrations/029_historical_processed_tables.sql")


def test_migration_029_defines_processed_historical_tables():
    sql = MIGRATION.read_text()

    assert "historical_processing_runs" in sql
    assert "historical_topic_country_daily" in sql
    assert "historical_evidence_samples" in sql
    assert "historical_archive_coverage" in sql
    assert (
        "PRIMARY KEY (day, topic_slug, country_code, source_family, "
        "signal_class, model_version)"
    ) in sql
    assert "archive_relative_path" in sql


def test_migration_029_does_not_create_raw_history_table():
    sql = MIGRATION.read_text().lower()

    assert "historical_signals_v2" not in sql
    assert "raw_payload" not in sql
    assert "create table if not exists signals_v2" not in sql


def test_migration_029_tracks_processing_method_and_coverage():
    sql = MIGRATION.read_text().lower()

    assert "model_version" in sql
    assert "processor_version" in sql
    assert "sentiment_coverage" in sql
    assert "topic_coverage" in sql
    assert "entity_coverage" in sql
    assert "check (sentiment_coverage >= 0 and sentiment_coverage <= 1)" in sql


def test_infer_topic_slug_uses_atlas_topic_hints():
    row = {
        "headline": "Colombia energy grid outage prompts rationing",
        "themes": ["ENERGY", "INFRASTRUCTURE"],
    }

    assert infer_topic_slug(row) == "energy-grid-instability"


def test_build_daily_topic_country_rows_groups_processed_archive_rows():
    rows = [
        {
            "id": 1,
            "timestamp": "2026-05-19T03:00:00Z",
            "country_code": "CO",
            "source_family": "gdelt",
            "signal_class": "reporting",
            "headline": "Colombia energy grid outage",
            "themes": ["ENERGY"],
            "nlp_sentiment": -0.4,
            "nlp_confidence": 0.8,
            "nlp_persons": ["Example Person"],
        },
        {
            "id": 2,
            "timestamp": "2026-05-19T04:00:00Z",
            "country_code": "CO",
            "source_family": "gdelt",
            "signal_class": "reporting",
            "headline": "Colombia energy rationing",
            "themes": ["ENERGY"],
            "nlp_sentiment": -0.2,
            "nlp_confidence": 0.7,
            "nlp_persons": [],
        },
    ]

    output = build_daily_topic_country_rows(rows, model_version="atlas-hist-v1")

    assert len(output) == 1
    row = output[0]
    assert row["day"] == "2026-05-19"
    assert row["topic_slug"] == "energy-grid-instability"
    assert row["country_code"] == "CO"
    assert row["signal_count"] == 2
    assert row["sentiment_coverage"] == 1.0
    assert row["topic_coverage"] == 1.0
    assert row["entity_coverage"] == 0.5
    assert row["avg_sentiment"] == -0.3


def test_build_daily_topic_country_rows_falls_back_to_gdelt_sentiment_with_method_gap():
    rows = [
        {
            "timestamp": "2026-05-19T03:00:00Z",
            "country_code": "NG",
            "source_family": "gdelt",
            "signal_class": "reporting",
            "headline": "Food prices rise sharply",
            "themes": ["ECON_INFLATION", "FOOD_SECURITY"],
            "sentiment": -6.0,
            "nlp_sentiment": None,
            "persons": ["Example Minister"],
        }
    ]

    output = build_daily_topic_country_rows(rows, model_version="atlas-hist-v1")

    assert output[0]["topic_slug"] == "food-price-stress"
    assert output[0]["avg_sentiment"] == -0.6
    assert output[0]["sentiment_coverage"] == 0.0
    assert output[0]["entity_coverage"] == 1.0


def test_build_upsert_payload_preserves_primary_key_fields():
    rows = [
        {
            "day": "2026-05-19",
            "topic_slug": "energy-grid-instability",
            "country_code": "CO",
            "source_family": "gdelt",
            "signal_class": "reporting",
            "signal_count": 2,
            "avg_sentiment": -0.3,
            "sentiment_coverage": 1.0,
            "topic_coverage": 1.0,
            "entity_coverage": 0.5,
            "local_voice_ratio": None,
            "source_diversity": None,
            "evidence_sample_count": 0,
            "model_version": "atlas-hist-v1",
        }
    ]

    payload = build_upsert_payload(rows)

    assert payload[0]["day"] == "2026-05-19"
    assert payload[0]["topic_slug"] == "energy-grid-instability"
    assert payload[0]["country_code"] == "CO"
    assert payload[0]["model_version"] == "atlas-hist-v1"


def test_build_upsert_payload_rejects_rows_without_primary_key_fields():
    rows = [{"day": "2026-05-19", "topic_slug": "energy-grid-instability"}]

    try:
        build_upsert_payload(rows)
    except ValueError as exc:
        assert "country_code" in str(exc)
        assert "model_version" in str(exc)
    else:
        raise AssertionError("expected missing primary key fields to fail")
