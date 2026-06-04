from scripts.gdelt_weak_recall_pilot import (
    build_candidate_item,
    label_anchor_terms,
    select_expansion_themes,
    summarize_expansion,
)


def test_select_expansion_themes_keeps_only_expected_domain_matches():
    audit = {
        "expected_domains": ["conflict", "policy"],
        "top_gdelt_themes": [
            {"theme": "WB_2432_FRAGILITY_CONFLICT_AND_VIOLENCE", "count": 17, "domains": ["conflict"]},
            {"theme": "USPEC_POLICY", "count": 12, "domains": ["policy"]},
            {"theme": "MEDIA_SOCIAL", "count": 20, "domains": ["media_social"]},
            {"theme": "TAX_WORLDLANGUAGES_UKRAINIAN", "count": 38, "domains": []},
            {"theme": "WB_2471_PEACEKEEPING", "count": 1, "domains": ["conflict", "policy"]},
        ],
    }

    assert select_expansion_themes(audit, min_count=3, max_themes=5) == [
        "WB_2432_FRAGILITY_CONFLICT_AND_VIOLENCE",
        "USPEC_POLICY",
    ]


def test_select_expansion_themes_rejects_generic_metadata_and_overbroad_codes():
    audit = {
        "expected_domains": ["conflict", "policy"],
        "top_gdelt_themes": [
            {"theme": "GENERAL_GOVERNMENT", "count": 40, "domains": ["policy"]},
            {"theme": "TAX_FNCACT_PRESIDENT", "count": 29, "domains": ["policy"]},
            {"theme": "CRISISLEX_C07_SAFETY", "count": 20, "domains": ["conflict"]},
            {"theme": "UNGP_FORESTS_RIVERS_OCEANS", "count": 10, "domains": ["policy"]},
            {"theme": "WB_2471_PEACEKEEPING", "count": 9, "domains": ["conflict", "policy"]},
        ],
    }

    assert select_expansion_themes(audit, min_count=3, max_themes=5) == [
        "WB_2471_PEACEKEEPING",
    ]


def test_build_candidate_item_marks_supported_rows():
    item = build_candidate_item(
        {
            "signal_id": 99,
            "headline": "Ukraine ceasefire talks continue",
            "themes": ["WB_2471_PEACEKEEPING"],
            "country_code": "UA",
            "source_name": "example.com",
            "source_lang": "en",
            "source_family": "api",
        },
        expected_domains={"conflict", "policy"},
    )

    assert item["signal_id"] == 99
    assert item["weak_status"] == "supported"
    assert item["domains"] == ["conflict", "policy"]


def test_label_anchor_terms_ignores_generic_words():
    assert label_anchor_terms("Russia-Ukraine War Updates") == {"russia", "ukraine"}
    assert label_anchor_terms("Local News and Politics") == set()


def test_summarize_expansion_excludes_current_sample_ids_and_counts_added_candidates():
    audit = {
        "thread_id": "dynamic-topic-10",
        "label": "Russia-Ukraine War Updates",
        "metrics": {"sample_rows": 2},
        "signal_count": 100,
        "expected_domains": ["conflict", "policy"],
    }
    candidates = [
        {"signal_id": 1, "headline": "already sampled Ukraine item", "themes": ["USPEC_POLICY"], "country_code": "UA", "source_name": "a.com"},
        {"signal_id": 2, "headline": "new Ukraine policy item", "themes": ["USPEC_POLICY"], "country_code": "UA", "source_name": "b.com"},
        {"signal_id": 3, "headline": "new Russia peacekeeping item", "themes": ["WB_2471_PEACEKEEPING"], "country_code": "RU", "source_name": "b.com"},
        {"signal_id": 4, "headline": "legacy proposals unrelated", "themes": ["WB_2471_PEACEKEEPING"], "country_code": "GB", "source_name": "c.com"},
    ]

    report = summarize_expansion(
        audit=audit,
        expansion_themes=["USPEC_POLICY", "WB_2471_PEACEKEEPING"],
        current_sample_ids={1},
        candidates=candidates,
        review_limit=10,
    )

    assert report["added_candidate_count"] == 2
    assert report["added_country_count"] == 2
    assert report["added_source_count"] == 1
    assert report["weak_status_counts"] == {"supported": 2}
    assert [row["signal_id"] for row in report["review_sample"]] == [2, 3]


def test_summarize_expansion_skips_generic_labels_without_anchor_terms():
    audit = {
        "thread_id": "dynamic-topic-18",
        "label": "Local News and Politics",
        "metrics": {"sample_rows": 2},
        "signal_count": 100,
        "expected_domains": ["policy"],
    }

    report = summarize_expansion(
        audit=audit,
        expansion_themes=["USPEC_POLICY"],
        current_sample_ids=set(),
        candidates=[{"signal_id": 2, "headline": "new policy item", "themes": ["USPEC_POLICY"]}],
        review_limit=10,
    )

    assert report["added_candidate_count"] == 0
    assert report["recommendation"] == "label_review_before_expansion"
