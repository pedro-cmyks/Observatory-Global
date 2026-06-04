from scripts.gdelt_weak_support_audit import (
    build_thread_audit,
    infer_expected_domains,
    normalized_entropy,
    theme_domains,
)


def test_theme_domains_maps_common_gdelt_themes_to_coarse_domains():
    assert "conflict" in theme_domains("WB_2432_FRAGILITY_CONFLICT_AND_VIOLENCE")
    assert "policy" in theme_domains("USPEC_POLICY")
    assert "media_social" in theme_domains("MEDIA_SOCIAL")


def test_theme_domains_ignores_language_metadata_themes():
    assert theme_domains("TAX_WORLDLANGUAGES_RUSSIA") == set()
    assert theme_domains("WORLDLANGUAGES_UKRAINIAN") == set()


def test_infer_expected_domains_from_thread_label():
    assert infer_expected_domains("Russia-Ukraine War Updates") == {"conflict", "policy"}
    assert infer_expected_domains("Social Media") == {"media_social"}


def test_normalized_entropy_is_low_for_concentrated_and_high_for_mixed():
    assert normalized_entropy({"conflict": 10}) == 0
    assert normalized_entropy({"conflict": 1, "policy": 1, "health": 1}) > 0.9


def test_build_thread_audit_reports_support_contradiction_and_bias_slices():
    report = build_thread_audit(
        {
            "thread_id": "dynamic-topic-10",
            "label": "Russia-Ukraine War Updates",
            "signal_count": 100,
            "country_count": 3,
            "source_count": 4,
            "noise_rate": 0.1,
        },
        [
            {
                "signal_id": 1,
                "headline": "Ukraine talks continue after strikes",
                "themes": ["WB_2432_FRAGILITY_CONFLICT_AND_VIOLENCE", "USPEC_POLICY"],
                "country_code": "UA",
                "source_lang": "en",
                "source_family": "api",
                "source_name": "example.com",
            },
            {
                "signal_id": 2,
                "headline": "Celebrity post trends online",
                "themes": ["MEDIA_SOCIAL"],
                "country_code": "US",
                "source_lang": "en",
                "source_family": "social",
                "source_name": "reddit/r/worldnews",
            },
        ],
    )

    assert report["expected_domains"] == ["conflict", "policy"]
    assert report["metrics"]["weak_support_pct"] == 0.5
    assert report["metrics"]["weak_contradiction_pct"] == 0.5
    assert report["bias"]["by_source_lang"]["en"]["rows"] == 2
    assert report["examples"]["supported"][0]["signal_id"] == 1
    assert report["examples"]["contradicted"][0]["signal_id"] == 2
