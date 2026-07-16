from scripts.voice_asymmetry_report import (
    TopicVoiceInput,
    build_report,
    render_markdown,
    score_topic_voice_asymmetry,
)


def _topic(**overrides) -> TopicVoiceInput:
    values = {
        "topic_id": 7,
        "label": "Iran water and energy pressure",
        "signal_count": 100,
        "distinct_sources": 8,
        "subject_country": "IR",
        "subject_country_method": "cluster_primary_coverage_proxy",
        "language_counts": {"en": 90, "fa": 0, "xx": 10},
        "origin_counts": {"US": 80, "GB": 10, "(null)": 10},
        "public_count": 0,
    }
    values.update(overrides)
    return TopicVoiceInput(**values)


def test_concentrated_outside_voice_is_a_ranked_hit_with_reasons():
    result = score_topic_voice_asymmetry(_topic())

    assert result["eligible"] is True
    assert result["is_hit"] is True
    assert result["voice_asymmetry_score"] >= 80
    assert result["dominant_origin"] == "US"
    assert result["subject_voice_share"] == 0
    assert "dominant_outside_origin" in result["reason_codes"]
    assert "subject_voice_absent" in result["reason_codes"]
    assert "primary_language_absent" in result["reason_codes"]
    assert "thin_public_lane" in result["reason_codes"]


def test_balanced_self_voice_is_not_a_hit():
    result = score_topic_voice_asymmetry(_topic(
        subject_country="CO",
        language_counts={"es": 80, "en": 20},
        origin_counts={"CO": 60, "MX": 20, "US": 20},
        public_count=8,
    ))

    assert result["eligible"] is True
    assert result["is_hit"] is False
    assert result["voice_asymmetry_score"] < 60
    assert "subject_voice_absent" not in result["reason_codes"]


def test_missing_subject_geography_is_not_scored():
    result = score_topic_voice_asymmetry(_topic(subject_country=None))

    assert result["eligible"] is False
    assert result["voice_asymmetry_score"] is None
    assert result["reason_codes"] == ["insufficient_subject_geo"]


def test_low_attribution_is_not_scored():
    result = score_topic_voice_asymmetry(_topic(
        language_counts={"en": 10, "xx": 90},
        origin_counts={"US": 10, "(null)": 90},
    ))

    assert result["eligible"] is False
    assert "insufficient_attribution" in result["reason_codes"]
    assert "high_unattributed_share" in result["reason_codes"]


def test_sql_null_origin_sentinels_are_not_treated_as_countries():
    result = score_topic_voice_asymmetry(_topic(
        language_counts={"xx": 100},
        origin_counts={"(NULL)": 100},
    ))

    assert result["eligible"] is False
    assert result["attribution_share"] == 0
    assert "insufficient_attribution" in result["reason_codes"]


def test_volume_and_source_floors_are_explicit():
    low_volume = score_topic_voice_asymmetry(_topic(signal_count=19))
    low_sources = score_topic_voice_asymmetry(_topic(distinct_sources=2))

    assert low_volume["eligible"] is False
    assert "insufficient_volume" in low_volume["reason_codes"]
    assert low_sources["eligible"] is False
    assert "insufficient_source_diversity" in low_sources["reason_codes"]


def test_report_is_read_only_ranked_and_renders_guardrails():
    report = build_report([_topic(), _topic(
        topic_id=8,
        label="Colombia domestic coverage",
        subject_country="CO",
        language_counts={"es": 80, "en": 20},
        origin_counts={"CO": 70, "US": 30},
        public_count=4,
    )], hours=168)

    assert report["read_only"] is True
    assert report["model_version"] == "voice-asymmetry-v0"
    assert report["eligible_count"] == 2
    assert report["topics"][0]["dynamic_topic_id"] == 7
    markdown = render_markdown(report)
    assert "coverage proxy" in markdown.lower()
    assert "not real-world truth" in markdown.lower()


# ── C7 geo-source swap (2026-07-16 reconsideration): subject country comes from
# the SERVING receipt-subject inference when it verifies; the cluster coverage
# proxy survives only as a labeled fallback (the scorer already discounts it).
from scripts.voice_asymmetry_report import resolve_topic_subject


def _receipts(pairs):
    return [{"headline": h, "source_name": s} for h, s in pairs]


def test_verified_inference_wins_over_proxy():
    receipts = _receipts([(f"Ukraine reports new strikes, wire {i}", f"o{i}") for i in range(4)])
    code, method = resolve_topic_subject(receipts, proxy_code="RU")
    assert code == "UA"
    assert method == "receipt_subject_inference_verified"


def test_unverified_falls_back_to_labeled_proxy():
    receipts = _receipts([("Local council meets on budget", "o1"), ("Mayor speaks at fair", "o2")])
    code, method = resolve_topic_subject(receipts, proxy_code="FR")
    assert code == "FR"
    assert method == "cluster_primary_coverage_proxy"


def test_no_receipts_no_proxy_is_honest_none():
    assert resolve_topic_subject([], proxy_code=None) == (None, None)


def test_verified_subject_scores_without_proxy_reason_code():
    receipts = _receipts([(f"Ukraine reports new strikes, wire {i}", f"o{i}") for i in range(4)])
    code, method = resolve_topic_subject(receipts, proxy_code="RU")
    row = score_topic_voice_asymmetry(_topic(subject_country=code, subject_country_method=method))
    assert "subject_geo_is_coverage_proxy" not in row["reason_codes"]
