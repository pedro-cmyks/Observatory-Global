from datetime import datetime, timezone

from scripts.subject_geography_report import (
    SignalSubjectInput,
    extract_headline_country_evidence,
    score_subject_candidates,
)


def _signal(
    signal_id: int,
    headline: str,
    language: str = "en",
    *,
    coverage_country: str | None = None,
    source_family: str = "press",
    day: int = 1,
    ner_places: tuple[str, ...] = (),
    embedding_similarity: float | None = 0.9,
) -> SignalSubjectInput:
    return SignalSubjectInput(
        signal_id=signal_id,
        headline=headline,
        language=language,
        coverage_country=coverage_country,
        source_family=source_family,
        published_at=datetime(2026, 7, day, tzinfo=timezone.utc),
        ner_places=ner_places,
        embedding_similarity=embedding_similarity,
    )


def test_extractor_returns_every_country_in_multi_country_headline():
    evidence = extract_headline_country_evidence(
        "Iran and Israel resume negotiations in Qatar"
    )

    assert {row["country"] for row in evidence} >= {"IR", "IL", "QA"}


def test_multilingual_headlines_build_a_country_distribution():
    signals = [
        _signal(1, "Venezuela earthquake death toll rises", "en", day=1),
        _signal(2, "Sube el balance del terremoto en Venezuela", "es", day=2),
        _signal(3, "Землетрясение в Венесуэле", "ru", day=3),
    ]

    result = score_subject_candidates(signals)

    assert result["primary_country"] == "VE"
    assert result["candidate_distribution"]["VE"] == 1.0
    assert "headline_geo_consensus" in result["reason_codes"]


def test_coverage_country_never_creates_subject_candidate():
    result = score_subject_candidates([
        _signal(
            1,
            "Central bank changes interest rate",
            coverage_country="US",
        )
    ])

    assert result["primary_country"] is None
    assert result["candidate_distribution"] == {}
    assert "insufficient_subject_evidence" in result["reason_codes"]


def test_ambiguous_multi_country_headlines_abstain():
    result = score_subject_candidates([
        _signal(1, "Iran and Israel resume negotiations", day=1),
        _signal(2, "Israel and Iran trade accusations", day=2),
    ])

    assert result["primary_country"] is None
    assert result["entropy"] > 0
    assert "ambiguous_subject_geo" in result["reason_codes"]


def test_native_script_evidence_is_exposed_separately():
    evidence = extract_headline_country_evidence("ایران اور پاکستان مذاکرات")

    by_country = {row["country"]: row["methods"] for row in evidence}
    assert "native_pattern" in by_country["IR"]
    assert "native_pattern" in by_country["PK"]


def test_candidate_exposes_components_provenance_and_uncertainty():
    result = score_subject_candidates([
        _signal(1, "Flooding in Colombia displaces families", ner_places=("Colombia",)),
        _signal(2, "Colombia flood response expands", day=2),
    ])

    candidate = result["candidates"][0]
    assert candidate["country"] == "CO"
    assert set(candidate["components"]) == {
        "headline_geo_support",
        "native_pattern_support",
        "ner_gazetteer_support",
        "member_consensus",
        "embedding_neighborhood_consistency",
        "temporal_stability",
    }
    assert candidate["supporting_signal_ids"] == [1, 2]
    assert result["top_two_margin"] == 1.0
    assert result["entropy"] == 0.0
