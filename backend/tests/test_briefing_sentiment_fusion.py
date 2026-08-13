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
    choose_sentiment_weighted as _choose_sentiment_weighted,
    _weighted_nlp_raw,
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


# ── Confidence-weighted helper (migration 033) ───────────────────────────────


def test_weighted_nlp_raw_computes_ratio():
    # 1 transformer row (s=-2.0, c=0.9) + 4 lexicon rows (s=+0.5, c=0.3 each).
    # Flat AVG = (-2.0 + 4*0.5) / 5 = 0.0
    # Weighted = (-2.0*0.9 + 4*0.5*0.3) / (0.9 + 4*0.3)
    #          = (-1.8 + 0.6) / 2.1 = -0.571
    w_sum = -2.0 * 0.9 + 4 * 0.5 * 0.3
    c_sum = 0.9 + 4 * 0.3
    assert _weighted_nlp_raw(w_sum, c_sum) == w_sum / c_sum
    assert _weighted_nlp_raw(w_sum, c_sum) < 0  # transformer dominates


def test_weighted_nlp_raw_returns_none_when_no_confidence():
    assert _weighted_nlp_raw(0.0, 0.0) is None
    assert _weighted_nlp_raw(None, 1.0) is None
    assert _weighted_nlp_raw(1.0, None) is None
    assert _weighted_nlp_raw(1.0, -0.1) is None


def test_choose_weighted_prefers_weighted_when_available():
    # weighted_avg = -0.571, rescaled = -0.571 * 2.37 / 10 = -0.1353
    sentiment, source, coverage = _choose_sentiment_weighted(
        gdelt_raw=0.5,
        nlp_weight_sum=-1.2,
        nlp_confidence_sum=2.1,
        nlp_signal_count=5,
        signal_count=10,
    )
    assert source == "nlp_weighted"
    expected = (-1.2 / 2.1) * NLP_SENTIMENT_SCALE / SENTIMENT_DIVISOR
    assert abs(sentiment - expected) < 1e-9
    assert coverage == 0.5


def test_choose_weighted_falls_back_to_flat_nlp_when_no_weight_columns():
    # Legacy row: no weight_sum/conf_sum, but coverage clears threshold.
    sentiment, source, _ = _choose_sentiment_weighted(
        gdelt_raw=1.0,
        nlp_weight_sum=None,
        nlp_confidence_sum=None,
        nlp_signal_count=5,
        signal_count=10,
        fallback_nlp_avg=-0.8,
    )
    assert source == "nlp"
    expected = -0.8 * NLP_SENTIMENT_SCALE / SENTIMENT_DIVISOR
    assert abs(sentiment - expected) < 1e-9


def test_choose_weighted_falls_back_to_gdelt_when_coverage_low():
    sentiment, source, _ = _choose_sentiment_weighted(
        gdelt_raw=-2.0,
        nlp_weight_sum=-5.0,
        nlp_confidence_sum=5.0,  # would compute ratio -1.0
        nlp_signal_count=2,
        signal_count=100,        # coverage 0.02 < threshold
        fallback_nlp_avg=-1.0,
    )
    assert source == "gdelt"
    assert abs(sentiment - (-0.20)) < 1e-9


def test_choose_weighted_returns_zero_when_all_missing():
    sentiment, source, coverage = _choose_sentiment_weighted(
        gdelt_raw=None,
        nlp_weight_sum=None,
        nlp_confidence_sum=None,
        nlp_signal_count=0,
        signal_count=0,
    )
    assert source == "gdelt"
    assert sentiment == 0.0
    assert coverage == 0.0


def test_choose_weighted_zero_confidence_falls_back_to_legacy_flat():
    # Coverage clears, but every row had nlp_confidence=0 (impossible in
    # practice, but the helper should still pick a sensible path).
    sentiment, source, _ = _choose_sentiment_weighted(
        gdelt_raw=0.0,
        nlp_weight_sum=0.0,
        nlp_confidence_sum=0.0,
        nlp_signal_count=10,
        signal_count=20,
        fallback_nlp_avg=-1.5,
    )
    assert source == "nlp"
    expected = -1.5 * NLP_SENTIMENT_SCALE / SENTIMENT_DIVISOR
    assert abs(sentiment - expected) < 1e-9


def test_choose_weighted_threshold_boundary_uses_weighted():
    # Coverage exactly at threshold should still pick NLP weighted.
    sentiment, source, _ = _choose_sentiment_weighted(
        gdelt_raw=1.0,
        nlp_weight_sum=-1.0,
        nlp_confidence_sum=1.0,
        nlp_signal_count=int(round(100 * NLP_COVERAGE_THRESHOLD)),
        signal_count=100,
    )
    assert source == "nlp_weighted"
    expected = -1.0 * NLP_SENTIMENT_SCALE / SENTIMENT_DIVISOR
    assert abs(sentiment - expected) < 1e-9


def test_choose_weighted_transformer_dominates_lexicon_volume():
    """Empirical motivation: 1 transformer row should swing the bucket more
    than 10 lexicon rows of opposite sign, mirroring the production miss."""
    # 1 transformer row, sentiment=-3.0, confidence=0.85.
    # 10 lexicon rows,  sentiment=+0.5, confidence=0.30 each.
    # Flat AVG  = (-3.0 + 10*0.5) / 11 = +0.18 (positive)
    # Weighted  = (-3.0*0.85 + 10*0.5*0.30) / (0.85 + 10*0.30)
    #           = (-2.55 + 1.5) / 3.85 = -0.273 (negative)
    sentiment_flat, _, _ = _choose_sentiment(
        gdelt_raw=0.0, nlp_raw=(-3.0 + 10 * 0.5) / 11, nlp_coverage=1.0
    )
    sentiment_weighted, source, _ = _choose_sentiment_weighted(
        gdelt_raw=0.0,
        nlp_weight_sum=-3.0 * 0.85 + 10 * 0.5 * 0.30,
        nlp_confidence_sum=0.85 + 10 * 0.30,
        nlp_signal_count=11,
        signal_count=11,
    )
    assert source == "nlp_weighted"
    assert sentiment_flat > 0       # flat AVG misclassifies as positive
    assert sentiment_weighted < 0   # weighted recovers the transformer signal


# ── Scale descriptor (C2: three scales on one screen, no bridge) ─────────────
#
# The Brief prints the SAME fused number on two scales — the instrument strip
# on ±1 and the tone panels on ×10 — and the panel legend (−10…+10) is NARROWER
# than what the fusion can serve (NLP maps to [-5, 5], rescaled by 2.37 → ±1.185
# on the ±1 unit = ±11.85 on the panel scale). Measured 2026-08-13: 1.29% of
# eligible country-days exceed the legend, and because clipping happens exactly
# at the extreme the columns rank for, 6 of 9 days rendered a clamped "−10.0".
# The payload must therefore SAY so instead of leaving the frontend to guess.


def test_scale_descriptor_names_the_unit_and_the_panel_conversion():
    from app.services.sentiment_fusion import sentiment_scale_descriptor

    d = sentiment_scale_descriptor()
    assert d["unit"] == "pm1"
    assert d["panel_multiplier"] == 10.0
    assert d["panel_bounds"] == [-10.0, 10.0]
    # the bridge is exact: a strip value times the multiplier IS the panel value
    assert -0.49 * d["panel_multiplier"] == -4.9


def test_scale_descriptor_declares_the_served_range_wider_than_the_legend():
    """The honest disclosure: values can exceed the printed legend."""
    from app.services.sentiment_fusion import sentiment_scale_descriptor

    d = sentiment_scale_descriptor()
    served_on_panel = d["served_abs_max"] * d["panel_multiplier"]
    assert served_on_panel > d["panel_bounds"][1]
    assert abs(served_on_panel - 11.85) < 0.01  # 5.0 * 2.37


def test_scale_descriptor_names_the_blend_not_one_source():
    """The panels' footer said 'GDELT tone' while every row was NLP-weighted."""
    from app.services.sentiment_fusion import sentiment_scale_descriptor

    d = sentiment_scale_descriptor()
    assert d["basis"] == "fused"
    assert d["nlp_coverage_threshold"] == NLP_COVERAGE_THRESHOLD
    assert d["nlp_scale"] == NLP_SENTIMENT_SCALE


def test_served_abs_max_tracks_the_configured_nlp_scale():
    """Descriptor is derived, never a hardcoded number that can drift."""
    from app.services.sentiment_fusion import (
        NLP_MODEL_ABS_MAX,
        sentiment_scale_descriptor,
    )

    d = sentiment_scale_descriptor()
    expected = NLP_MODEL_ABS_MAX * NLP_SENTIMENT_SCALE / SENTIMENT_DIVISOR
    assert abs(d["served_abs_max"] - expected) < 1e-3
