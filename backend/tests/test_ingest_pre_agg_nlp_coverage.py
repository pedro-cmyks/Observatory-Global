"""Ingest pre-agg shape guardrail — verifies NLP coverage columns are populated.

Covers migrations 025 (`nlp_signal_count` + `avg_nlp_sentiment`) and
033 (`nlp_sentiment_weight_sum` + `nlp_confidence_sum`) without pinning the
exact whitespace alignment, so adding columns to the UPSERT does not break
the test on every realignment.
"""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INGEST_FILE = ROOT / "app" / "services" / "ingest_v2.py"


def _ingest_source() -> str:
    return INGEST_FILE.read_text(encoding="utf-8")


def _assigns(column: str, block: str) -> bool:
    """Return True when `column = EXCLUDED.column` appears in the UPSERT block,
    tolerating any inter-token whitespace introduced by alignment."""
    pattern = rf"\b{re.escape(column)}\s*=\s*EXCLUDED\.{re.escape(column)}\b"
    return re.search(pattern, block) is not None


def test_theme_hourly_v2_insert_includes_nlp_coverage():
    source = _ingest_source()
    start = source.index("INSERT INTO theme_hourly_v2")
    end = source.index("Updated theme_hourly_v2")
    block = source[start:end]

    assert "nlp_signal_count" in block
    assert "avg_nlp_sentiment" in block
    assert "FILTER (WHERE nlp_sentiment IS NOT NULL)" in block
    assert _assigns("nlp_signal_count", block)
    assert _assigns("avg_nlp_sentiment", block)


def test_theme_country_hourly_v2_insert_includes_nlp_coverage():
    source = _ingest_source()
    start = source.index("INSERT INTO theme_country_hourly_v2")
    end = source.index("Updated theme_country_hourly_v2")
    block = source[start:end]

    assert "nlp_signal_count" in block
    assert "avg_nlp_sentiment" in block
    assert "FILTER (WHERE nlp_sentiment IS NOT NULL)" in block
    assert _assigns("nlp_signal_count", block)
    assert _assigns("avg_nlp_sentiment", block)


def test_theme_hourly_v2_insert_includes_confidence_weighted_sums():
    """Migration 033: ingest must populate nlp_sentiment_weight_sum and
    nlp_confidence_sum so downstream readers can compute
    SUM(s*c) / SUM(c) instead of the flat AVG that diluted high-confidence
    transformer rows with low-confidence lexicon/fast_neutral rows."""
    source = _ingest_source()
    start = source.index("INSERT INTO theme_hourly_v2")
    end = source.index("Updated theme_hourly_v2")
    block = source[start:end]

    assert "nlp_sentiment_weight_sum" in block
    assert "nlp_confidence_sum" in block
    assert "SUM(nlp_sentiment * nlp_confidence)" in block
    assert _assigns("nlp_sentiment_weight_sum", block)
    assert _assigns("nlp_confidence_sum", block)


def test_theme_country_hourly_v2_insert_includes_confidence_weighted_sums():
    source = _ingest_source()
    start = source.index("INSERT INTO theme_country_hourly_v2")
    end = source.index("Updated theme_country_hourly_v2")
    block = source[start:end]

    assert "nlp_sentiment_weight_sum" in block
    assert "nlp_confidence_sum" in block
    assert "SUM(nlp_sentiment * nlp_confidence)" in block
    assert _assigns("nlp_sentiment_weight_sum", block)
    assert _assigns("nlp_confidence_sum", block)
