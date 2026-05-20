"""Unit tests for briefing sentiment fusion (Opción A reader logic).

The helper picks NLP transformer sentiment when bucket coverage clears
NLP_COVERAGE_THRESHOLD (default 0.30) and rescales by NLP_SENTIMENT_SCALE so
the value lands on the same ±0.1 frontend threshold scale as GDELT V2Tone.
"""

from app.services.sentiment_fusion import (
    NLP_COVERAGE_THRESHOLD,
    NLP_SENTIMENT_SCALE,
    SENTIMENT_DIVISOR,
    choose_sentiment as _choose_sentiment,
)


def test_picks_gdelt_when_nlp_coverage_below_threshold():
    sentiment, source, coverage = _choose_sentiment(
        gdelt_raw=-3.5, nlp_raw=-0.8, nlp_coverage=0.10
    )
    assert source == "gdelt"
    assert sentiment == -0.35  # -3.5 / 10
    assert coverage == 0.10


def test_picks_nlp_when_coverage_meets_threshold():
    sentiment, source, coverage = _choose_sentiment(
        gdelt_raw=-3.5, nlp_raw=-0.8, nlp_coverage=0.45
    )
    assert source == "nlp"
    expected = -0.8 * NLP_SENTIMENT_SCALE / SENTIMENT_DIVISOR
    assert abs(sentiment - expected) < 1e-9
    assert coverage == 0.45


def test_picks_gdelt_when_nlp_value_is_none_even_if_coverage_high():
    sentiment, source, coverage = _choose_sentiment(
        gdelt_raw=-2.1, nlp_raw=None, nlp_coverage=0.99
    )
    assert source == "gdelt"
    assert abs(sentiment - (-0.21)) < 1e-9


def test_picks_gdelt_when_all_none():
    sentiment, source, coverage = _choose_sentiment(
        gdelt_raw=None, nlp_raw=None, nlp_coverage=None
    )
    assert source == "gdelt"
    assert sentiment == 0.0
    assert coverage == 0.0


def test_coverage_clamped_to_unit_interval():
    _, _, coverage_low = _choose_sentiment(0, 0, -0.5)
    _, _, coverage_high = _choose_sentiment(0, 0, 1.7)
    assert coverage_low == 0.0
    assert coverage_high == 1.0


def test_threshold_boundary_uses_nlp():
    sentiment, source, _ = _choose_sentiment(
        gdelt_raw=1.0, nlp_raw=0.5, nlp_coverage=NLP_COVERAGE_THRESHOLD
    )
    assert source == "nlp"


def test_nlp_rescale_matches_gdelt_stddev_within_an_order_of_magnitude():
    """NLP value 1.68 (1 stddev) should rescale to roughly GDELT 1 stddev (3.99)."""
    sentiment, _, _ = _choose_sentiment(
        gdelt_raw=0, nlp_raw=1.68, nlp_coverage=1.0
    )
    # Expect ≈ 1.68 * 2.37 / 10 = 0.398, close to GDELT 1σ ÷ 10 (≈ 0.399).
    assert 0.35 < sentiment < 0.45
