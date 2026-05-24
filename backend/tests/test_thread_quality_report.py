from __future__ import annotations

from scripts.thread_quality_report import (
    attach_evidence,
    fetch_thread_detail,
    format_markdown,
    grade_thread_quality,
    thread_quality_row,
)


def test_grade_thread_quality_passes_clean_lex_supported_thread():
    thread = {
        "thread_id": "heat-health-risk--in-gb",
        "signal_count": 327,
        "quality": {
            "lex_pct": 1.0,
            "source_flags": {},
            "geo_flags": {},
            "entity_flags": {},
        },
    }

    assert grade_thread_quality(thread) == "pass"


def test_grade_thread_quality_fails_on_active_quality_flags():
    thread = {
        "thread_id": "transport-corridor-disruption--it-gb",
        "signal_count": 478,
        "quality": {
            "lex_pct": 0.226,
            "source_flags": {"aggregator_dominant": True},
            "geo_flags": {"unresolved_country_code": False},
            "entity_flags": ["raw_entity_field_untyped"],
        },
    }

    assert grade_thread_quality(thread) == "fail"


def test_grade_thread_quality_fails_high_volume_low_lexical_support():
    thread = {
        "thread_id": "armed-conflict-escalation--us-ir-ua",
        "signal_count": 7459,
        "quality": {
            "lex_pct": 0.056,
            "source_flags": {},
            "geo_flags": {},
            "entity_flags": {},
        },
    }

    assert grade_thread_quality(thread) == "fail"


def test_grade_thread_quality_reviews_thin_or_missing_lex_rows():
    assert (
        grade_thread_quality(
            {
                "thread_id": "small-thread",
                "signal_count": 20,
                "quality": {"lex_pct": 0.1},
            }
        )
        == "review"
    )
    assert grade_thread_quality({"thread_id": "no-quality", "signal_count": 200}) == "review"


def test_thread_quality_row_normalizes_legacy_flag_shapes():
    row = thread_quality_row(
        {
            "thread_id": "election-legitimacy-dispute--it-ng-rb",
            "label": "Election legitimacy dispute intensifies",
            "signal_count": "1597",
            "confidence": "medium",
            "quality": {
                "lex_pct": "0.334",
                "source_flags": {"aggregator_dominant": False},
                "geo_flags": {"unresolved_country_code": True},
                "entity_flags": [],
            },
        }
    )

    assert row["topic/thread id"] == "election-legitimacy-dispute--it-ng-rb"
    assert row["signal_count"] == "1597"
    assert row["lex_pct"] == "33.4%"
    assert row["geo_flags"] == "unresolved_country_code"
    assert row["grade"] == "fail"


def test_format_markdown_includes_quality_columns_and_rows():
    markdown = format_markdown(
        [
            {
                "topic_slug": "heat-health-risk",
                "topic_label": "Heat and public health risk",
                "signal_count": 327,
                "confidence": "high",
                "quality": {"lex_pct": 1.0},
                "evidence_samples": [
                    {
                        "headline": "Heatwave warnings expand across northern India",
                        "source": "reuters.com",
                        "country_code": "IN",
                        "evidence_role": "representative",
                    }
                ],
            },
            {
                "thread_id": "gender-violence-rights--us-gb-in",
                "label": "Gender violence and rights",
                "signal_count": 1494,
                "confidence": "medium",
                "quality": {
                    "lex_pct": 0.002,
                    "source_flags": [],
                    "geo_flags": [],
                    "entity_flags": ["raw_entity_field_untyped"],
                },
            },
        ],
        hours=24,
        api_url="http://localhost:8000",
    )

    assert (
        "| topic/thread id | label | signal_count | lex_pct | confidence | "
        "source_flags | geo_flags | entity_flags | grade |"
    ) in markdown
    assert (
        "| heat-health-risk | Heat and public health risk | 327 | 100.0% | "
        "high | - | - | - | pass |"
    ) in markdown
    assert "gender-violence-rights--us-gb-in" in markdown
    assert "raw_entity_field_untyped" in markdown
    assert "## Evidence: `heat-health-risk`" in markdown
    assert "Heatwave warnings expand across northern India" in markdown
    assert "| API: `http://localhost:8000`" not in markdown
    assert "- API: `http://localhost:8000`" in markdown


def test_attach_evidence_merges_detail_samples(monkeypatch):
    threads = [{"thread_id": "heat-health-risk--in-gb", "signal_count": 327}]

    def fake_fetch_detail(api_url, thread, *, hours):
        assert api_url == "http://localhost:8000"
        assert thread["thread_id"] == "heat-health-risk--in-gb"
        assert hours == 24
        return {
            "thread_id": "heat-health-risk--in-gb",
            "evidence_samples": [{"headline": "Heat warnings expand"}],
        }

    monkeypatch.setattr(
        "scripts.thread_quality_report.fetch_thread_detail",
        fake_fetch_detail,
    )

    enriched = attach_evidence("http://localhost:8000", threads, hours=24)

    assert enriched[0]["signal_count"] == 327
    assert enriched[0]["evidence_samples"] == [{"headline": "Heat warnings expand"}]


def test_fetch_thread_detail_unwraps_router_payload(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return (
                b'{"beta":true,"thread":{"thread_id":"abc","evidence_samples":[{"headline":"x"}]}}'
            )

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    detail = fetch_thread_detail(
        "http://localhost:8000",
        {"thread_id": "abc"},
        hours=24,
    )

    assert detail == {"thread_id": "abc", "evidence_samples": [{"headline": "x"}]}
