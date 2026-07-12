from datetime import datetime, timezone

import pytest

from scripts.subject_geography_report import (
    SignalSubjectInput,
    TOPIC_PAGE_SQL,
    compare_proxies,
    evaluate_invariants,
    extract_headline_country_evidence,
    run_ablations,
    run_complete_universe,
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


@pytest.fixture
def anyio_backend():
    return "asyncio"


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


class _FakeConnection:
    def __init__(self, pages, members=None):
        self.pages = list(pages)
        self.members = members or {}
        self.topic_calls = []

    async def fetch(self, sql, *args, **_kwargs):
        if "FROM dynamic_topics" in sql and "ORDER BY id" in sql:
            self.topic_calls.append(args)
            page = self.pages.pop(0)
            if isinstance(page, Exception):
                raise page
            return page
        if "subject-geo member loader" in sql:
            topic_ids = args[0]
            return [
                row
                for topic_id in topic_ids
                for row in self.members.get(topic_id, [])
            ]
        if "archive_story_units" in sql:
            return []
        raise AssertionError(sql)


def _topic(topic_id: int, state: str = "active"):
    return {
        "id": topic_id,
        "label": f"Topic {topic_id}",
        "state": state,
        "is_junk": False,
        "last_seen": datetime(2026, 7, 12, tzinfo=timezone.utc),
    }


@pytest.mark.anyio
async def test_cursor_batches_reach_exhaustion_without_topic_ceiling():
    conn = _FakeConnection([[_topic(1), _topic(2)], [_topic(3)], []])

    rows, meta = await run_complete_universe(
        conn,
        batch_size=2,
        states=("active", "candidate"),
        hours=336,
    )

    assert [row["dynamic_topic_id"] for row in rows] == [1, 2, 3]
    assert meta["complete_universe"] is True
    assert meta["rows_discovered"] == meta["rows_processed"] == 3
    assert meta["last_cursor"] == 3
    assert [call[0] for call in conn.topic_calls] == [0, 2, 3]


@pytest.mark.anyio
async def test_failed_batch_is_resumable_and_never_claims_complete():
    conn = _FakeConnection([[_topic(1)], RuntimeError("timeout")])

    rows, meta = await run_complete_universe(
        conn,
        batch_size=1,
        states=("active",),
        hours=336,
        max_retries=0,
    )

    assert [row["dynamic_topic_id"] for row in rows] == [1]
    assert meta["complete_universe"] is False
    assert meta["last_cursor"] == 1
    assert meta["failures"][0]["reason"] == "timeout"


def test_topic_page_sql_has_cursor_batch_but_no_total_topic_ceiling():
    assert "id > $1" in TOPIC_PAGE_SQL
    assert "ORDER BY id" in TOPIC_PAGE_SQL
    assert "LIMIT $3" in TOPIC_PAGE_SQL
    assert "OFFSET" not in TOPIC_PAGE_SQL


def _stable_venezuela_topic():
    return [
        _signal(1, "Venezuela earthquake response expands", "en", source_family="wire", day=1),
        _signal(2, "Venezuela refuerza respuesta al terremoto", "es", source_family="press", day=2),
        _signal(3, "Землетрясение в Венесуэле", "ru", source_family="state", day=3),
        _signal(4, "Venezuela earthquake aid arrives", "en", source_family="wire", day=4),
        _signal(5, "Venezuela recibe ayuda tras el sismo", "es", source_family="press", day=5),
    ]


def test_leave_one_source_family_out_does_not_flip_stable_subject():
    result = evaluate_invariants(_stable_venezuela_topic())

    assert result["leave_one_source_family_out"]["stable"] is True


def test_archive_and_coverage_are_labeled_proxies_not_gold():
    row = compare_proxies(
        subject={"VE": 0.9}, coverage=["US", "BR"], archive=["VE"]
    )

    assert row["coverage_relation"] == "subject_missing_from_coverage"
    assert row["archive_relation"] == "agrees_with_candidate"
    assert row["truth_status"] == "not_gold"


def test_ablation_reports_candidate_and_abstention_delta():
    report = run_ablations([_stable_venezuela_topic()])

    assert "headline_geo_support" in report["components"]
    assert "primary_changed" in report["components"]["headline_geo_support"]
    assert "abstention_delta" in report["components"]["headline_geo_support"]
