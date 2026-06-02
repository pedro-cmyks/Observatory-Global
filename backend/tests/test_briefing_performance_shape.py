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


def test_briefing_long_window_top_sources_uses_historical_source_daily():
    """Long-window top_sources must use compact processed history instead of
    grouping raw signals_v2 over a week."""
    source = _get_briefing_source()
    top_sources_section = source[source.index('"top_sources_historical"'):source.index('"stats"')]

    assert "FROM signals_source_hourly" not in top_sources_section
    assert "to_regclass('historical_source_daily')" in source
    assert '"top_sources_historical"' in top_sources_section
    assert "FROM historical_source_daily" in top_sources_section
    assert "FROM signals_v2" in top_sources_section
    assert "AND source_name IS NOT NULL" in top_sources_section
    assert '"top_sources_source": top_sources_source' in source


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


def test_briefing_top_atlas_topics_reads_signal_topic_assignments():
    """top_atlas_topics surfaces the curated atlas_topics taxonomy via
    signal_topic_assignments (v2 classifier, PR #197). Hot-path SQL must
    use COUNT(*) not COUNT(DISTINCT) — the PK guarantees uniqueness within
    each (topic, model_version) group, and COUNT(DISTINCT) was measured at
    225 ms vs 40 ms for COUNT(*) on 33k assignments. The fetch must run
    through _fetch_section so an empty / missing table degrades to []."""
    source = _get_briefing_source()

    atlas_section = source[source.index('"top_atlas_topics"'):source.index('"top_atlas_topics_source"')]
    assert "FROM signal_topic_assignments a" in source
    assert "JOIN atlas_topics t ON t.id = a.topic_id" in source
    assert "a.model_version = 'theme-hint-lex-v2'" in source
    assert "COUNT(*)::bigint" in source
    # Performance trap: DISTINCT forces an external sort. PK uniqueness
    # means COUNT(*) and COUNT(DISTINCT signal_id) return the same value
    # within (topic, model_version) groups.
    assert "COUNT(DISTINCT a.signal_id)" not in source
    # to_regclass guard so the fetch degrades to [] when table missing.
    assert "to_regclass('signal_topic_assignments')" in source
    # Response shape exposes the product fields, not GDELT raw codes.
    assert '"slug": r["slug"]' in atlas_section
    assert '"label": r["label"]' in atlas_section
    assert '"signal_count": int(r["signal_count"])' in atlas_section
    assert '"parent_domain"' in atlas_section


def test_briefing_prefers_dynamic_topics_before_emergent_clusters():
    source = _get_briefing_source()

    dynamic_pos = source.index("FROM dynamic_topics")
    emergent_pos = source.index("FROM emergent_clusters")
    assert dynamic_pos < emergent_pos
    assert "'dynamic_topics'" in source
    assert "dt.state = 'active'" in source
    assert "noise_rate" in source


def test_briefing_topics_by_domain_groups_by_parent_domain():
    """topics_by_domain exposes the atlas_topics taxonomy hierarchy
    (parent_domain -> [topics]). Reuses the same window as top_atlas_topics
    and groups via jsonb_agg into domain rows. Must only touch
    signal_topic_assignments (no signals_v2 join) — assigned_at is the
    right time filter."""
    source = _get_briefing_source()

    assert '"topics_by_domain"' in source
    assert "GROUP BY parent_domain" in source
    assert "jsonb_agg" in source
    # SQL must filter by assigned_at, not by joining signals_v2
    assert "AND a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')" in source
    # Response shape: each row carries parent_domain + topics array
    assert '"parent_domain": r["parent_domain"]' in source
    assert '"topics_in_domain": int(r["topics_in_domain"])' in source
    assert '"domain_signal_count": int(r["domain_signal_count"])' in source


def test_briefing_related_topics_uses_cooccurrence_no_signals_v2_join():
    """related_topics maps topic_slug -> top-3 co-occurring topics, ranked
    by a Jaccard-proxy co / sqrt(|A|*|B|) so volume doesn't dominate.
    The self-join over signal_topic_assignments MUST stay inside the
    table (no signals_v2 join) — the timestamp lookup was measured at
    605 ms vs 47 ms when filtering by assigned_at directly."""
    source = _get_briefing_source()

    assert '"related_topics"' in source
    assert "WITH pairs AS" in source
    assert "SQRT(tl.sigs * th.sigs)" in source
    assert "WHERE rnk <= 3" in source
    # The co-occurrence CTE block must not join signals_v2.
    co_block_start = source.index("WITH pairs AS")
    co_block_end = source.index("WHERE rnk <= 3", co_block_start)
    co_block = source[co_block_start:co_block_end]
    assert "signals_v2" not in co_block
    # Response shape: dict keyed by topic_slug
    assert 'r["topic_slug"]:' in source


def test_briefing_exposes_top_threads_via_thread_intelligence():
    """Milestone 2: Brief consumes the same living-narrative-threads contract
    that /api/v2/threads serves so the leading product surface speaks in
    threads (label, why_now, changed_10h, confidence band) instead of raw
    atlas-topic counts. The section must reuse the briefing connection (no
    second pool acquire per request) and degrade to [] on failure."""
    source = _briefing_source()

    assert "from app.services.thread_intelligence import fetch_threads" in source
    assert 'TOP_THREADS_CONTRACT = "living-narrative-threads-v0"' in source

    briefing_body = _get_briefing_source()
    assert 'await fetch_threads(' in briefing_body
    assert "conn=conn" in briefing_body
    assert 'degraded_segments.append("top_threads")' in briefing_body
    assert '"top_threads": top_threads' in briefing_body
    assert '"top_threads_contract": TOP_THREADS_CONTRACT' in briefing_body
