"""#238 C-clean slice 2: plumb NER places through SERVING into subject inference.

The inference lane (`infer_receipt_subject_geography` places path, method
"ner_place") shipped first as a no-op — receipts never carried `places`. These
tests freeze the serving plumb: the member-signal SQL selects `nlp_places`,
and `assemble_dynamic_thread` forwards them into the receipt dicts, so an
oblique-headline local story (headline names only a company/venue, NER pulled
the city from the body) can verify its subject country.
"""

from __future__ import annotations

from app.services.thread_intelligence import (
    _EMERGENT_SAMPLE_SIGNALS_SQL,
    assemble_dynamic_thread,
)


def _topic_row() -> dict:
    return {
        "id": 41,
        "identity_key": "dyn-41",
        "label": "Fairgrounds Fire Response",
        "agg_n_signals": 6,
        "changed_10h": 3,
        "noise_rate": None,
        "mean_cohesion": 0.51,
        "first_seen": None,
        "top_country_codes": ["US"],
    }


def test_member_signal_sql_selects_nlp_places():
    # Both the dynamic and emergent detail paths hydrate members through this
    # shared SELECT; without nlp_places the inference places path stays a no-op.
    assert "nlp_places" in _EMERGENT_SAMPLE_SIGNALS_SQL


def test_assemble_dynamic_thread_verifies_subject_from_ner_places():
    # Domestic-story class: no headline names a country, but NER extracted the
    # city from the body of 3 receipts across 3 outlets -> verified US.
    samples = [
        {
            "id": 1,
            "headline": "Fire crews contain blaze near the fairgrounds",
            "source_name": "Outlet A",
            "source_url": "https://a.example/1",
            "country_code": "US",
            "nlp_places": ["roseburg"],
        },
        {
            "id": 2,
            "headline": "Evacuation order lifted after fairgrounds blaze",
            "source_name": "Outlet B",
            "source_url": "https://b.example/2",
            "country_code": "US",
            "nlp_places": ["roseburg"],
        },
        {
            "id": 3,
            "headline": "School closures extend into next week",
            "source_name": "Outlet C",
            "source_url": "https://c.example/3",
            "country_code": "US",
            "nlp_places": ["roseburg"],
        },
    ]

    thread = assemble_dynamic_thread(_topic_row(), samples)

    assert thread["subject_geography_status"] == "verified"
    assert thread["subject_countries"] == ["US"]
    assert thread["subject_country_names"] == ["United States"]


def test_assemble_dynamic_thread_places_survive_asyncpg_jsonb_strings():
    # asyncpg returns JSONB columns as JSON strings unless a codec is set;
    # the plumb must parse them (same _as_list contract as persons/themes).
    samples = [
        {
            "id": 1,
            "headline": "Council approves the stadium redevelopment",
            "source_name": "Outlet A",
            "source_url": "https://a.example/1",
            "country_code": "AU",
            "nlp_places": '["sydney"]',
        },
        {
            "id": 2,
            "headline": "Stadium plan clears final vote",
            "source_name": "Outlet B",
            "source_url": "https://b.example/2",
            "country_code": "AU",
            "nlp_places": '["melbourne"]',
        },
    ]

    thread = assemble_dynamic_thread(_topic_row(), samples)

    assert thread["subject_geography_status"] == "verified"
    assert thread["subject_countries"] == ["AU"]


def test_assemble_dynamic_thread_null_places_change_nothing():
    # Pre-accrual rows (nlp_places NULL) must behave exactly as before the plumb.
    samples = [
        {
            "id": 1,
            "headline": "Constitutional reform divides Senegal parliament",
            "source_name": "Outlet A",
            "source_url": "https://a.example/1",
            "country_code": "SN",
            "nlp_places": None,
        },
        {
            "id": 2,
            "headline": "Senegal lawmakers debate reform",
            "source_name": "Outlet B",
            "source_url": "https://b.example/2",
            "country_code": "SN",
            "nlp_places": None,
        },
    ]

    thread = assemble_dynamic_thread(_topic_row(), samples)

    assert thread["subject_geography_status"] == "verified"
    assert thread["subject_countries"] == ["SN"]
