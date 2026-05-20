"""Ingest pre-agg shape guardrail — verifies NLP coverage columns are populated (mig 025)."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INGEST_FILE = ROOT / "app" / "services" / "ingest_v2.py"


def _ingest_source() -> str:
    return INGEST_FILE.read_text(encoding="utf-8")


def test_theme_hourly_v2_insert_includes_nlp_coverage():
    source = _ingest_source()
    start = source.index("INSERT INTO theme_hourly_v2")
    end = source.index("Updated theme_hourly_v2")
    block = source[start:end]

    assert "nlp_signal_count" in block
    assert "avg_nlp_sentiment" in block
    assert "FILTER (WHERE nlp_sentiment IS NOT NULL)" in block
    assert "nlp_signal_count  = EXCLUDED.nlp_signal_count" in block
    assert "avg_nlp_sentiment = EXCLUDED.avg_nlp_sentiment" in block


def test_theme_country_hourly_v2_insert_includes_nlp_coverage():
    source = _ingest_source()
    start = source.index("INSERT INTO theme_country_hourly_v2")
    end = source.index("Updated theme_country_hourly_v2")
    block = source[start:end]

    assert "nlp_signal_count" in block
    assert "avg_nlp_sentiment" in block
    assert "FILTER (WHERE nlp_sentiment IS NOT NULL)" in block
    assert "nlp_signal_count  = EXCLUDED.nlp_signal_count" in block
    assert "avg_nlp_sentiment = EXCLUDED.avg_nlp_sentiment" in block
