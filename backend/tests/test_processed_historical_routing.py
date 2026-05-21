from app.services.processed_historical import CoverageRange, days_for_hours, use_processed_history
from pathlib import Path


def test_days_for_hours_rounds_up_to_utc_days():
    assert days_for_hours(1) == 1
    assert days_for_hours(24) == 1
    assert days_for_hours(25) == 2
    assert days_for_hours(168) == 7


def test_use_processed_history_only_for_long_windows():
    assert use_processed_history(24) is False
    assert use_processed_history(25) is True


def test_coverage_range_serializes_from_key_for_api_payload():
    payload = CoverageRange(from_="2026-05-03", to="2026-05-20", row_count=2128070).to_dict()

    assert payload == {
        "from": "2026-05-03",
        "to": "2026-05-20",
        "row_count": 2128070,
    }


def test_heat_countries_routes_long_windows_to_processed_history():
    source = Path("app/routers/heat.py").read_text(encoding="utf-8")

    assert "use_processed_history(hours)" in source
    assert "query_historical_country_attention" in source
    assert "build_historical_coverage" in source
    assert '"source": "historical_topic_country_daily"' in source
    assert "hours_window=24 only in v1" not in source


def test_country_detail_routes_long_windows_to_processed_history():
    source = Path("app/routers/geo.py").read_text(encoding="utf-8")

    assert "use_processed_history(hours)" in source
    assert "query_historical_country_detail" in source
    assert "build_historical_coverage" in source
    assert '"source": "historical_topic_country_daily"' in source
    assert "source_mix_not_source_names" in source


def test_atlas_topic_detail_routes_long_windows_to_processed_history():
    source = Path("app/routers/themes.py").read_text(encoding="utf-8")

    assert "use_processed_history(hours) and \"-\" in theme_code" in source
    assert "query_historical_topic_detail" in source
    assert "atlas_topic_slug" in source
    assert '"source": "historical_topic_country_daily"' in source
