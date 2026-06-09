from datetime import datetime, timezone

from app.services.query_thread import build_query_thread


def _row(**kw):
    base = {"timestamp": datetime(2026, 6, 4, 10, tzinfo=timezone.utc),
            "country_code": "CO", "source_name": "reuters.com",
            "source_url": "http://reuters.com/x", "sentiment": -1.0,
            "headline": "Ivan Cepeda statement", "themes": ["PROTEST"],
            "persons": ["Ivan Cepeda"]}
    base.update(kw)
    return base


def test_empty_rows_thin_coverage_with_zero_sample():
    t = build_query_thread([], "ivan cepeda", hours=168)
    assert t["signalSample"] == 0
    assert t["total"] == 0
    assert t["coverageTier"] == "thin"
    assert t["signals"] == []
    assert t["countryBreakdown"] == []


def test_theme_id_is_query_thread_slug():
    t = build_query_thread([_row()], "Ivan Cepeda", hours=24)
    assert t["theme"] == "query-thread-ivan-cepeda"
    assert t["label"] == "Ivan Cepeda"
    assert t["source"] == "query_thread"
    assert t["query"] == "Ivan Cepeda"


def test_thin_coverage_under_ten_signals():
    rows = [_row() for _ in range(5)]
    t = build_query_thread(rows, "petro", hours=24)
    assert t["signalSample"] == 5
    assert t["coverageTier"] == "thin"
    assert "query_thread_thin_coverage" in t["warnings"]


def test_limited_coverage_between_ten_and_fifty():
    rows = [_row() for _ in range(20)]
    t = build_query_thread(rows, "petro", hours=24)
    assert t["coverageTier"] == "limited"
    assert t["warnings"] == []


def test_ok_coverage_at_fifty_or_more():
    rows = [_row() for _ in range(50)]
    t = build_query_thread(rows, "petro", hours=24)
    assert t["coverageTier"] == "ok"


def test_packet_fields_spread_into_detail_contract():
    rows = [_row(country_code="CO"), _row(country_code="VE")]
    t = build_query_thread(rows, "petro", hours=24)
    # Mirrors the theme-detail contract the reading panel renders.
    for key in ("graphSignals", "countryBreakdown", "topSources",
                "topPersons", "timeline", "signals", "avgSentiment"):
        assert key in t
    assert t["graphSignals"] == t["signals"]
    codes = {c["code"] for c in t["countryBreakdown"]}
    assert codes == {"CO", "VE"}


def test_avg_sentiment_computed():
    rows = [_row(sentiment=-2.0), _row(sentiment=0.0)]
    t = build_query_thread(rows, "petro", hours=24)
    assert t["avgSentiment"] == -1.0


def test_country_passed_through():
    t = build_query_thread([_row()], "petro", hours=24, country="CO")
    assert t["country"] == "CO"


def test_slug_handles_accents_and_symbols():
    t = build_query_thread([_row()], "  Niño & Crisis!! ", hours=24)
    assert t["theme"] == "query-thread-nino-crisis"
    assert t["label"] == "Niño & Crisis!!"
