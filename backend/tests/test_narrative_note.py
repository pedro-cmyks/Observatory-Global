from app.services.narrative_note import build_thread_narrative_note


def _thread(**overrides):
    base = {
        "label": "Infrastructure and Public Services",
        "signal_count": 120,
        "changed_10h": 25,
        "source_count": 4,
        "country_count": 3,
        "top_country_names": ["Indonesia", "Brazil", "Canada"],
        "top_countries": ["ID", "BR", "CA"],
        "top_sources": ["rri.co.id", "bisnis.com", "antaranews.com"],
        "quality": {
            "source_flags": {},
            "geo_flags": {},
            "entity_flags": {},
            "noise_rate": 0.08,
        },
        "evidence_samples": [
            {
                "headline": "Currency pressure builds",
                "snippet": "Bank officials warned about public-service pressure.",
                "source": "rri.co.id",
            },
            {
                "headline": "Immigration document investigation widens",
                "snippet": None,
                "source": "bisnis.com",
            },
            {
                "headline": "Public-sector operations expand",
                "snippet": "Officials described a new regional service program.",
                "source": "antaranews.com",
            },
        ],
    }
    base.update(overrides)
    return base


def test_builds_strong_thread_note():
    note = build_thread_narrative_note(_thread())
    assert note is not None
    assert note["quality"] == "strong"
    assert note["source"] == "extractive-v1"
    assert "Infrastructure and Public Services" in note["lede"]
    assert "25-signal rise" in note["movement"]
    assert "rri.co.id" in note["evidence"]
    assert note["caveat"] is None


def test_prefers_snippet_rich_evidence_and_diversifies_sources():
    note = build_thread_narrative_note(
        _thread(
            evidence_samples=[
                {
                    "headline": "Currency pressure builds",
                    "snippet": "Bank officials warned about public-service pressure.",
                    "source": "rri.co.id",
                },
                {
                    "headline": "Second local item",
                    "snippet": "A second note from the same outlet should not crowd out other sources.",
                    "source": "rri.co.id",
                },
                {
                    "headline": "Public-sector operations expand",
                    "snippet": "Officials described a new regional service program.",
                    "source": "antaranews.com",
                },
            ]
        )
    )
    assert note is not None
    assert "Bank officials warned" in note["evidence"]
    assert "Officials described" in note["evidence"]
    assert "A second note from the same outlet" not in note["evidence"]


def test_headline_only_thread_is_provisional_with_caveat():
    note = build_thread_narrative_note(
        _thread(
            evidence_samples=[
                {"headline": "Headline one", "snippet": None, "source": "gdelt-a.com"},
                {"headline": "Headline two", "snippet": None, "source": "gdelt-b.com"},
            ]
        )
    )
    assert note is not None
    assert note["quality"] == "provisional"
    assert note["caveat"] is not None
    assert "headline-heavy" in note["caveat"]


def test_thin_thread_returns_thin_quality():
    note = build_thread_narrative_note(
        _thread(signal_count=8, source_count=1, country_count=1, top_sources=["local.test"])
    )
    assert note is not None
    assert note["quality"] == "thin"
    assert note["caveat"] is not None


def test_empty_thread_returns_none():
    assert build_thread_narrative_note({"label": "", "signal_count": 0, "evidence_samples": []}) is None
