"""Briefing query-shape guardrails for production-sized Supabase data."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRIEFING_ROUTER = ROOT / "app" / "routers" / "briefing.py"


def _briefing_source() -> str:
    return BRIEFING_ROUTER.read_text(encoding="utf-8")


def _get_briefing_source() -> str:
    source = _briefing_source()
    start = source.index('async def get_briefing(')
    end = source.index('@router.get("/api/v2/briefing/insight")')
    return source[start:end]


def test_briefing_uses_preaggregates_for_country_sentiment_sections():
    source = _get_briefing_source()

    assert "FROM country_hourly_v2 h" in source
    assert '"negative_sentiment"' in source
    assert '"positive_sentiment"' in source
    assert "AVG(s.sentiment)" not in source
    assert "FROM signals_v2 s JOIN countries_v2" not in source


def test_briefing_uses_parameterized_intervals_and_no_percent_interpolation():
    source = _get_briefing_source()

    assert "$1::int * INTERVAL '1 hour'" in source
    assert "% hours" not in source
    assert " % hours" not in source


def test_briefing_segments_have_timeouts_and_degraded_response():
    source = _briefing_source()

    assert "BRIEFING_DB_TIMEOUT_SECONDS" in source
    assert "timeout=BRIEFING_DB_TIMEOUT_SECONDS" in source
    assert '"degraded": bool(degraded_segments)' in source
    assert '"degraded_segments": degraded_segments' in source
