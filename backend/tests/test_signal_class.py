"""Test signal_class derivation helper.

Migration 021 + ingest service writes. Issue #155.
"""

from pathlib import Path

from app.services._signal_class import (
    ALLOWED_SIGNAL_CLASSES,
    derive_signal_class,
)


MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "021_signal_class.sql"
)


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


# ── Migration shape ───────────────────────────────────────────────────────────

def test_migration_021_exists():
    assert MIGRATION.exists()


def test_migration_021_adds_column_with_default():
    sql = _sql()
    assert "ADD COLUMN IF NOT EXISTS signal_class VARCHAR(30) NOT NULL DEFAULT 'reporting'" in sql


def test_migration_021_enforces_valid_classes():
    sql = _sql()
    for cls in [
        "reporting",
        "wire",
        "state_media",
        "humanitarian",
        "social_commentary",
        "public_attention",
        "unknown",
    ]:
        assert f"'{cls}'" in sql
    assert "signals_v2_signal_class_valid" in sql


def test_migration_021_adds_required_indexes():
    sql = _sql()
    assert "idx_signals_class_time" in sql
    assert "idx_signals_class_country_time" in sql


def test_migration_021_backfills_with_5_rules():
    sql = _sql()
    # Most specific first
    assert "attribution_method = 'reddit_public'" in sql
    assert "attribution_method = 'reliefweb_ocha'" in sql
    assert "is_state_media = TRUE" in sql
    assert "source_family = 'wire'" in sql
    assert "source_family IN ('gdelt','rss','api','independent')" in sql


# ── Helper behavior ───────────────────────────────────────────────────────────

def test_allowed_classes_match_migration_constraint():
    assert ALLOWED_SIGNAL_CLASSES == frozenset({
        "reporting",
        "wire",
        "state_media",
        "humanitarian",
        "social_commentary",
        "public_attention",
        "unknown",
    })


def test_reddit_is_social_commentary():
    assert derive_signal_class("social", "reddit_public", False) == "social_commentary"
    # Even if family flips, attribution wins
    assert derive_signal_class("api", "reddit_public", False) == "social_commentary"


def test_reliefweb_is_humanitarian():
    assert derive_signal_class("ngo", "reliefweb_ocha", False) == "humanitarian"
    assert derive_signal_class("ngo", "reliefweb_rss", False) == "humanitarian"


def test_state_media_wins_over_family():
    # RT/Sputnik/Global Times: source_family='state' AND is_state_media=True
    assert derive_signal_class("state", "rss_feed", True) == "state_media"
    # is_state_media flag wins even when family is independent/rss
    assert derive_signal_class("rss", "rss_feed", True) == "state_media"


def test_wire_family_returns_wire():
    assert derive_signal_class("wire", "rss_feed", False) == "wire"


def test_gdelt_is_reporting():
    assert derive_signal_class("gdelt", "gdelt_gkg", False) == "reporting"
    assert derive_signal_class("gdelt", "gdelt_gkg_translated", False) == "reporting"


def test_api_aggregators_are_reporting():
    assert derive_signal_class("api", "newsdata_api", False) == "reporting"
    assert derive_signal_class("api", "newsapi_org", False) == "reporting"
    assert derive_signal_class("api", "mediastack_api", False) == "reporting"


def test_independent_rss_is_reporting():
    assert derive_signal_class("independent", "rss_feed", False) == "reporting"
    assert derive_signal_class("rss", "rss_feed", False) == "reporting"


def test_unknown_when_provenance_missing():
    assert derive_signal_class(None, None, False) == "unknown"
    assert derive_signal_class("mystery", "mystery_method", False) == "unknown"


# ── Order of precedence (critical: must match migration UPDATE CASE order) ────

def test_reddit_takes_precedence_over_state_flag():
    """Hypothetical contradictory row: Reddit + is_state_media=True.
    social_commentary should win because attribution_method='reddit_public' fires first.
    """
    assert derive_signal_class("social", "reddit_public", True) == "social_commentary"


def test_ngo_takes_precedence_over_state_flag():
    """ReliefWeb cannot be state_media. NGO rule fires before is_state_media."""
    assert derive_signal_class("ngo", "reliefweb_ocha", True) == "humanitarian"


# ── Ingest service smoke checks (string-level so we avoid asyncpg setup) ──────

def _service_path(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "app" / "services" / f"{name}.py"


def test_ingest_v2_writes_signal_class():
    src = _service_path("ingest_v2").read_text()
    assert "'signal_class': 'reporting'" in src
    assert "signal_class" in src and "$22" in src  # 22nd param after origin_country


def test_ingest_reddit_writes_social_commentary():
    src = _service_path("ingest_reddit").read_text()
    assert '"signal_class": "social_commentary"' in src


def test_ingest_reliefweb_writes_humanitarian():
    src = _service_path("ingest_reliefweb").read_text()
    assert '"signal_class": "humanitarian"' in src


def test_ingest_reliefweb_promotes_conflicting_urls_to_humanitarian():
    src = _service_path("ingest_reliefweb").read_text()
    assert "ON CONFLICT (source_url) WHERE source_url IS NOT NULL DO UPDATE SET" in src
    assert "source_family = EXCLUDED.source_family" in src
    assert "attribution_method = EXCLUDED.attribution_method" in src
    assert "signal_class = EXCLUDED.signal_class" in src
    assert 'result in {"INSERT 0 1", "UPDATE 1"}' in src


def test_ingest_rss_uses_derivation_helper():
    src = _service_path("ingest_rss").read_text()
    assert "from app.services._signal_class import derive_signal_class" in src
    assert "derive_signal_class(source_family" in src


def test_ingest_newsdata_writes_reporting():
    src = _service_path("ingest_newsdata").read_text()
    assert '"signal_class": "reporting"' in src


def test_ingest_newsapi_writes_reporting():
    src = _service_path("ingest_newsapi").read_text()
    assert '"signal_class": "reporting"' in src


def test_ingest_mediastack_writes_reporting():
    src = _service_path("ingest_mediastack").read_text()
    assert '"signal_class": "reporting"' in src
