"""Search performance guardrails for production query shape.

These tests intentionally inspect source text because the expensive behavior only
appears against the production-sized Supabase dataset.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROUTER = ROOT / "app" / "routers" / "search.py"
MIGRATION_022 = ROOT / "migrations" / "022_search_trigram_indexes.sql"


def _search_source() -> str:
    return SEARCH_ROUTER.read_text(encoding="utf-8")


def _migration_source() -> str:
    return MIGRATION_022.read_text(encoding="utf-8")


def test_migration_022_adds_trigram_indexes_for_search_and_topic_backfill():
    sql = _migration_source()

    assert "CREATE EXTENSION IF NOT EXISTS pg_trgm" in sql
    assert "idx_signals_v2_headline_trgm" in sql
    assert "lower(headline) gin_trgm_ops" in sql
    assert "idx_signals_v2_source_name_trgm" in sql
    assert "lower(source_name) gin_trgm_ops" in sql
    assert "idx_signals_v2_themes_gin" in sql
    assert "ON signals_v2 USING gin (themes)" in sql
    assert "idx_signals_v2_created_id_headline" in sql
    assert "idx_wiki_pageviews_v2_article_title_lower_trgm" in sql
    assert "lower(article_title) gin_trgm_ops" in sql
    assert "CONCURRENTLY" in sql


def test_unified_search_accepts_explicit_country_param_from_frontend():
    source = _search_source()

    assert "country: str | None = Query(None, min_length=2, max_length=2)" in source
    assert "explicit_country_code = country.upper() if country else None" in source
    assert "country_filter = country_match[\"code\"] if country_match else explicit_country_code" in source
    assert "country=country_filter" in source


def test_search_segments_have_timeouts_and_degraded_response():
    source = _search_source()

    assert "SEARCH_SEGMENT_TIMEOUT_SECONDS = 8.0" in source
    assert "SEARCH_MATCH_TIMEOUT_SECONDS = 5.0" in source
    assert "timeout=SEARCH_SEGMENT_TIMEOUT_SECONDS" in source
    assert "timeout=SEARCH_MATCH_TIMEOUT_SECONDS" in source
    assert '"degraded": bool(degraded_segments)' in source
    assert '"degraded_segments": sorted(set(degraded_segments))' in source


def test_unified_signal_matches_use_index_compatible_lower_columns():
    source = _search_source()

    assert "LOWER(COALESCE(headline" not in source
    assert "headline IS NOT NULL AND LOWER(headline) LIKE ANY" in source
    assert "source_name IS NOT NULL AND LOWER(source_name) LIKE ANY" in source
