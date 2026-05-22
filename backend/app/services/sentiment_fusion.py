"""Briefing sentiment fusion (Opción A — pre-agg NLP coverage readers).

Picks transformer-normalized sentiment when bucket NLP coverage clears a
threshold; otherwise falls back to GDELT V2Tone. Rescales NLP values so the
returned magnitude matches GDELT amplitude (frontend uses uniform ±0.1
thresholds after the ÷10 normalization).

Two flavors:

- ``choose_sentiment(gdelt_raw, nlp_raw, nlp_coverage)`` is the original
  flat-AVG path kept for backward compatibility with readers that have not
  migrated to the weighted columns.
- ``choose_sentiment_weighted(gdelt_raw, nlp_weight_sum, nlp_confidence_sum,
  nlp_signal_count, signal_count)`` reads the migration 033 columns
  (``nlp_sentiment_weight_sum`` and ``nlp_confidence_sum``) and computes a
  confidence-weighted NLP sentiment per bucket. Transformer rows (avg
  confidence ~0.64) outweigh lexicon rows (~0.31, capped at 0.5) and
  ``fast_neutral`` rows (~0.01), so the few transformer rows that disagree
  with the lexicon no longer get diluted by raw row count.

Pure module — kept outside `app.routers.briefing` so it stays unit-testable
without triggering the FastAPI app's circular router import.
"""
from __future__ import annotations

import os

# GDELT V2Tone raw stddev ~3.99 vs NLP transformer raw stddev ~1.68 measured
# on the production sample (2026-05-20). Rescale NLP by the ratio so the
# ±0.1 frontend threshold behaves consistently regardless of source.
NLP_SENTIMENT_SCALE = float(os.getenv("BRIEFING_NLP_SENTIMENT_SCALE", "2.37"))
NLP_COVERAGE_THRESHOLD = float(os.getenv("BRIEFING_NLP_COVERAGE_THRESHOLD", "0.30"))
SENTIMENT_DIVISOR = 10.0


def choose_sentiment(
    gdelt_raw: float | None,
    nlp_raw: float | None,
    nlp_coverage: float | None,
) -> tuple[float, str, float]:
    """Return (frontend_sentiment, source_label, coverage_ratio).

    `frontend_sentiment` is already divided by SENTIMENT_DIVISOR and (if NLP)
    rescaled by NLP_SENTIMENT_SCALE.
    `source_label` is "nlp" or "gdelt".
    `coverage_ratio` is clamped to [0, 1].
    """
    coverage = max(0.0, min(1.0, float(nlp_coverage or 0.0)))
    if nlp_raw is not None and coverage >= NLP_COVERAGE_THRESHOLD:
        return float(nlp_raw) * NLP_SENTIMENT_SCALE / SENTIMENT_DIVISOR, "nlp", coverage
    return float(gdelt_raw or 0.0) / SENTIMENT_DIVISOR, "gdelt", coverage


def _weighted_nlp_raw(
    nlp_weight_sum: float | None,
    nlp_confidence_sum: float | None,
) -> float | None:
    """Compute the confidence-weighted NLP sentiment for a bucket.

    Returns ``None`` when ``nlp_confidence_sum`` is missing, zero, or negative
    so callers can fall back to the flat AVG path.
    """
    if nlp_weight_sum is None or nlp_confidence_sum is None:
        return None
    cs = float(nlp_confidence_sum)
    if cs <= 0:
        return None
    return float(nlp_weight_sum) / cs


def choose_sentiment_weighted(
    gdelt_raw: float | None,
    nlp_weight_sum: float | None,
    nlp_confidence_sum: float | None,
    nlp_signal_count: int | None,
    signal_count: int | None,
    *,
    fallback_nlp_avg: float | None = None,
) -> tuple[float, str, float]:
    """Return (frontend_sentiment, source_label, coverage_ratio).

    Behavior:

    1. Coverage is computed from ``nlp_signal_count / signal_count`` and
       clamped to ``[0, 1]``.
    2. When coverage clears ``NLP_COVERAGE_THRESHOLD``:
         a. Prefer the confidence-weighted ratio
            ``nlp_weight_sum / nlp_confidence_sum`` when it is computable.
         b. Otherwise fall back to ``fallback_nlp_avg`` (legacy
            ``avg_nlp_sentiment`` column) so rows that predate migration 033
            still serve NLP-sourced values.
         c. If neither is available, fall back to GDELT V2Tone.
    3. Below coverage threshold the call returns GDELT V2Tone.

    The returned ``source_label`` distinguishes the three NLP paths:
    ``"nlp_weighted"`` for the migration 033 weighted ratio, ``"nlp"`` for the
    legacy flat AVG, and ``"gdelt"`` for the fallback.
    """
    total = max(0, int(signal_count or 0))
    nlp_n = max(0, int(nlp_signal_count or 0))
    coverage = 0.0 if total == 0 else min(1.0, nlp_n / total)

    if coverage >= NLP_COVERAGE_THRESHOLD:
        weighted = _weighted_nlp_raw(nlp_weight_sum, nlp_confidence_sum)
        if weighted is not None:
            return weighted * NLP_SENTIMENT_SCALE / SENTIMENT_DIVISOR, "nlp_weighted", coverage
        if fallback_nlp_avg is not None:
            return (
                float(fallback_nlp_avg) * NLP_SENTIMENT_SCALE / SENTIMENT_DIVISOR,
                "nlp",
                coverage,
            )
    return float(gdelt_raw or 0.0) / SENTIMENT_DIVISOR, "gdelt", coverage


def serialize_country_row(r) -> dict:
    """Adapt a country aggregate row to the briefing response shape.

    Accepts both the legacy shape (``nlp_sentiment`` only) and the migration
    033 shape (``nlp_sentiment_weight_sum`` + ``nlp_confidence_sum``). When
    the weighted columns are present the response carries
    ``sentiment_source = "nlp_weighted"``.
    """
    if "nlp_sentiment_weight_sum" in r and "nlp_confidence_sum" in r:
        sentiment, source, coverage = choose_sentiment_weighted(
            r["gdelt_sentiment"],
            r.get("nlp_sentiment_weight_sum"),
            r.get("nlp_confidence_sum"),
            r.get("nlp_signal_count"),
            r.get("signal_count") or r.get("total"),
            fallback_nlp_avg=r.get("nlp_sentiment"),
        )
    else:
        sentiment, source, coverage = choose_sentiment(
            r["gdelt_sentiment"],
            r["nlp_sentiment"],
            r["nlp_coverage"],
        )
    return {
        "code": r["country_code"],
        "name": r["name"],
        "signals": r.get("total") or r.get("signal_count"),
        "sentiment": sentiment,
        "sentiment_source": source,
        "nlp_coverage": round(coverage, 3),
    }
