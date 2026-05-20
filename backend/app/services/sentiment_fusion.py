"""Briefing sentiment fusion (Opción A — pre-agg NLP coverage readers).

Picks transformer-normalized sentiment when bucket NLP coverage clears a
threshold; otherwise falls back to GDELT V2Tone. Rescales NLP values so the
returned magnitude matches GDELT amplitude (frontend uses uniform ±0.1
thresholds after the ÷10 normalization).

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


def serialize_country_row(r) -> dict:
    """Adapt a country aggregate row to the briefing response shape."""
    sentiment, source, coverage = choose_sentiment(
        r["gdelt_sentiment"],
        r["nlp_sentiment"],
        r["nlp_coverage"],
    )
    return {
        "code": r["country_code"],
        "name": r["name"],
        "signals": r["total"],
        "sentiment": sentiment,
        "sentiment_source": source,
        "nlp_coverage": round(coverage, 3),
    }
