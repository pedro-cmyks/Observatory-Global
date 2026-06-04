from datetime import datetime, timezone
from app.services.thread_packet import build_thread_packet


def _row(**kw):
    base = {"timestamp": datetime(2026, 6, 4, 10, tzinfo=timezone.utc),
            "country_code": "CO", "source_name": "reuters.com",
            "source_url": "http://reuters.com/x", "sentiment": -1.0,
            "headline": "h", "themes": ["PROTEST"], "persons": ["Petro"]}
    base.update(kw)
    return base


def test_empty_input_returns_empty_packet():
    p = build_thread_packet([])
    assert p["countryBreakdown"] == [] and p["topSources"] == []
    assert p["timeline"] == [] and p["graphSignals"] == []
    assert p["lanes"] == {"media": 0, "social": 0, "state": 0, "other": 0}


def test_country_breakdown_groups_and_sorts():
    rows = [_row(country_code="CO"), _row(country_code="CO"), _row(country_code="VE")]
    p = build_thread_packet(rows)
    assert p["countryBreakdown"][0]["code"] == "CO"
    assert p["countryBreakdown"][0]["count"] == 2


def test_top_sources_carry_family():
    p = build_thread_packet([_row(source_name="reddit.com/r/x")])
    assert "family" in p["topSources"][0]


def test_lanes_split_social():
    p = build_thread_packet([_row(source_name="reddit.com/r/x")])
    assert p["lanes"]["social"] >= 1


def test_related_themes_excludes_own_topic():
    rows = [_row(themes=["PROTEST", "ECON"]), _row(themes=["PROTEST"])]
    p = build_thread_packet(rows, own_topic="PROTEST")
    themes = {t["theme"] for t in p["relatedThemes"]}
    assert "PROTEST" not in themes and "ECON" in themes


def test_timeline_buckets_by_hour():
    p = build_thread_packet([_row(), _row()])
    assert len(p["timeline"]) == 1 and p["timeline"][0]["count"] == 2
