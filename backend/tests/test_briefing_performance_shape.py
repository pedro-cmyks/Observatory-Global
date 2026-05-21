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


def test_briefing_top_themes_uses_theme_hourly_v2_not_dead_table():
    """Hot-window top_themes must read from theme_hourly_v2, not dead tables."""
    source = _get_briefing_source()
    top_themes_section = source[source.index('"top_themes"'):source.index('"top_sources"')]

    assert "FROM theme_hourly_v2" in top_themes_section
    assert "FROM signals_theme_hourly" not in top_themes_section
    assert "WHERE hour >" in top_themes_section


def test_briefing_long_windows_use_historical_processed_tables():
    """Long-window top_themes must use compact processed history instead of
    rehydrating/scanning historical raw signals."""
    source = _get_briefing_source()
    top_themes_section = source[source.index('"top_themes_historical"'):source.index('"top_sources"')]

    assert "def _use_historical_processed(hours: int)" in _briefing_source()
    assert "_use_historical_processed(hours)" in source
    assert "to_regclass('historical_topic_country_daily')" in source
    assert "FROM historical_topic_country_daily" in top_themes_section
    assert "topic_slug AS theme" in top_themes_section
    assert "CEIL($1::numeric / 24)::int" in top_themes_section
    assert "AND model_version = $2::text" in top_themes_section
    assert "HISTORICAL_PROCESSED_MODEL_VERSION" in source
    assert '"top_themes_source": top_themes_source' in source
    assert '"historical_coverage"' in source
    assert '"historical_processed"' in source
    assert "FROM signals_v2" not in top_themes_section


def test_briefing_top_sources_does_not_read_dead_table():
    """top_sources must not read from signals_source_hourly (dead). Direct
    signals_v2 scan is acceptable because the section is Redis-cached."""
    source = _get_briefing_source()
    top_sources_section = source[source.index('"top_sources"'):source.index('"stats"')]

    assert "FROM signals_source_hourly" not in top_sources_section
    assert "FROM signals_v2" in top_sources_section
    assert "AND source_name IS NOT NULL" in top_sources_section


def test_briefing_exposes_heat_countries_section():
    """heat_countries reads country_heat_v2 (mig 017) and exposes atlas_heat
    components so the briefing offers both volume and heat rankings."""
    source = _get_briefing_source()

    assert '"heat_countries"' in source
    assert "FROM country_heat_v2" in source
    assert "ORDER BY h.atlas_heat DESC" in source
    assert "to_regclass('country_heat_v2')" in source
    # Component breakdown exposed for transparency
    for component in ("velocity", "surprise", "diversity", "voice",
                      "polyphony", "geo_confidence", "duplication"):
        assert f'"{component}"' in source, f"heat_countries missing component {component}"


def test_briefing_exposes_heat_voluminous_countries_section():
    """heat_voluminous_countries (#187) filters country_heat_v2 by a volume
    percentile floor before re-ranking by atlas_heat — surfaces stories that
    are both heating up and large enough to matter."""
    source = _get_briefing_source()

    assert '"heat_voluminous_countries"' in source
    assert "HEAT_VOLUMINOUS_PERCENTILE" in source
    assert "percentile_disc" in source
    # percentile_disc with WITHIN GROUP works as an aggregate in PG, not a
    # window function — so the volume_floor lives in a CTE that the main
    # SELECT references via a scalar subquery (validated live on Supabase).
    assert "AND h.volume_now >= (SELECT v FROM volume_floor)" in source
    assert '"heat_voluminous_percentile"' in source


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


def _get_briefing_insight_source() -> str:
    source = _briefing_source()
    start = source.index('async def get_briefing_insight(')
    end = source.index('# TRUST INDICATORS API (v3)')
    return source[start:end]


def test_briefing_insight_uses_preaggregates_not_raw_signals_v2():
    source = _get_briefing_insight_source()

    assert "FROM country_hourly_v2" in source
    assert "FROM theme_hourly_v2" in source
    # Raw signals_v2 scans removed from the insight hot path
    assert "FROM signals_v2 WHERE timestamp" not in source
    assert "FROM signals_v2 s LEFT JOIN countries_v2" not in source


def test_briefing_insight_uses_parameterized_intervals():
    source = _get_briefing_insight_source()

    assert "$1::int * INTERVAL '1 hour'" in source
    # No f-string interval interpolation
    assert "INTERVAL '{hours}" not in source


def test_briefing_insight_uses_fetch_section_degraded_pattern():
    source = _get_briefing_insight_source()

    assert "_fetch_section(conn, degraded_segments" in source
    assert 'logger.warning("briefing/insight db failed' in source
