import asyncio
from datetime import datetime, timezone

from app.services.daily_edition import (
    DailyCandidate,
    apply_sample_coverage,
    fetch_daily_candidates,
    global_breadth_signal,
    order_spine_by_publishability,
    select_daily_edition,
)


def candidate(ref: str, **overrides) -> DailyCandidate:
    data = {
        "thread_id": ref,
        "label": ref,
        "category": "General",
        "current_signals": 40,
        "prior_signals": 20,
        "source_breadth": 6,
        "source_origins": 3,
        "coherence": 0.82,
        "noise_rate": 0.08,
        "kalman_velocity": 0.12,
        "kalman_surprise": 1.4,
        "kalman_uncertainty": 0.35,
        "kalman_observations": 12,
        "first_seen": "2026-07-08T10:00:00Z",
        "last_seen": "2026-07-12T10:00:00Z",
    }
    data.update(overrides)
    return DailyCandidate(**data)


def test_category_and_harm_lens_have_zero_ranking_weight():
    sport = candidate("sport", category="World Cup", crisis_relevant=False)
    conflict = candidate("conflict", category="Armed conflict", crisis_relevant=True)

    edition = select_daily_edition([sport, conflict], display_slots=2)

    scores = {row.thread_id: row.score for row in edition.ledger}
    assert scores["sport"] == scores["conflict"]
    assert all("category" not in code for row in edition.ledger for code in row.reason_codes)


def test_raw_volume_does_not_raise_salience_after_evidence_floor():
    small = candidate("small", current_signals=40)
    huge = candidate("huge", current_signals=40_000)

    edition = select_daily_edition([small, huge], display_slots=2)
    scores = {row.thread_id: row.score for row in edition.ledger}

    assert scores["small"] == scores["huge"]


def test_pareto_order_prefers_a_candidate_that_dominates_on_measured_state():
    fast = candidate("fast", kalman_velocity=0.30, kalman_surprise=2.2, kalman_uncertainty=0.2)
    uncertain = candidate("uncertain", kalman_velocity=0.25, kalman_surprise=2.2, kalman_uncertainty=1.8)
    slow = candidate("slow", kalman_velocity=0.02, kalman_surprise=0.3, kalman_uncertainty=0.2)

    edition = select_daily_edition([slow, uncertain, fast], display_slots=3)

    assert [row.thread_id for row in edition.ledger] == ["fast", "uncertain", "slow"]
    assert "kalman_velocity" in edition.ledger[0].reason_codes
    assert "uncertainty_penalty" in {c for row in edition.ledger for c in row.reason_codes}
    assert edition.method["prediction_claim"] is False
    assert edition.method["selection_method"] == "pareto_frontier_equal_rank_aggregation_v1"


def test_pareto_front_keeps_complementary_measured_strengths_without_semantic_judgment():
    fast_thin = candidate(
        "fast-thin", kalman_velocity=0.6, kalman_surprise=2.5,
        current_signals=20, source_breadth=2, source_origins=1, coherence=0.65,
    )
    broad_stable = candidate(
        "broad-stable", kalman_velocity=0.04, kalman_surprise=0.2,
        current_signals=80, source_breadth=12, source_origins=8, coherence=0.95,
    )

    edition = select_daily_edition([fast_thin, broad_stable], display_slots=2)
    by_id = {row.thread_id: row for row in edition.ledger}

    assert by_id["fast-thin"].components["pareto_front"] == 0
    assert by_id["broad-stable"].components["pareto_front"] == 0
    assert by_id["fast-thin"].components["category_weight"] == 0.0
    assert by_id["broad-stable"].components["raw_volume_importance_weight"] == 0.0


def test_complete_ledger_reconciles_every_candidate_and_names_layout_selection():
    rows = [candidate(f"t-{i}", kalman_velocity=0.3 - i * 0.01) for i in range(25)]

    edition = select_daily_edition(rows, display_slots=8)

    assert edition.completion == {
        "candidate_count": 25,
        "scored_count": 25,
        "selected_count": 8,
        "downranked_count": 17,
        "unresolved_count": 0,
        "truncated": False,
    }
    assert len(edition.ledger) == 25
    assert sum(row.status == "selected" for row in edition.ledger) == 8
    assert all("layout_disclosure" in row.reason_codes for row in edition.ledger[8:])


def test_exact_duplicate_story_labels_share_one_visual_slot_but_stay_in_ledger():
    first = candidate("first", label="Ukraine War Updates", kalman_velocity=0.5)
    duplicate = candidate("duplicate", label="  ukraine   war updates ", kalman_velocity=0.4)
    distinct = candidate("distinct", label="Iran negotiations", kalman_velocity=0.3)

    edition = select_daily_edition([first, duplicate, distinct], display_slots=2)

    assert edition.selected_ids == ["first", "distinct"]
    by_id = {row.thread_id: row for row in edition.ledger}
    assert by_id["duplicate"].status == "downranked"
    assert "duplicate_label_sibling" in by_id["duplicate"].reason_codes
    assert len(edition.ledger) == 3


def test_receipt_eligibility_can_fill_layout_without_claiming_absence_for_unchecked_rows():
    stale = candidate("stale", kalman_velocity=0.8)
    current = candidate("current", kalman_velocity=0.4)
    unchecked = candidate("unchecked", kalman_velocity=0.2)

    edition = select_daily_edition(
        [stale, current, unchecked],
        display_slots=2,
        receipt_eligible_ids={"current"},
        receipt_checked_ids={"stale", "current"},
    )
    by_id = {row.thread_id: row for row in edition.ledger}

    assert edition.selected_ids == ["current"]
    assert "no_current_receipt_sample" in by_id["stale"].reason_codes
    assert "no_current_receipt_sample" not in by_id["unchecked"].reason_codes
    assert edition.completion["receipt_checked_count"] == 2
    assert edition.completion["receipt_eligible_count"] == 1


def test_publication_quality_downranking_is_disclosed_in_complete_ledger():
    mixed = candidate("mixed", kalman_velocity=0.8)
    coherent = candidate("coherent", kalman_velocity=0.4)
    quality = {
        "mixed": {
            "status": "downranked",
            "pair_median": 0.12,
            "label_median": 0.09,
            "reason_codes": ["publication_evidence_fit_bivariate_low_tail"],
        },
        "coherent": {
            "status": "eligible",
            "pair_median": 0.72,
            "label_median": 0.61,
            "reason_codes": [],
        },
    }

    edition = select_daily_edition(
        [mixed, coherent],
        display_slots=1,
        receipt_eligible_ids={"coherent"},
        receipt_checked_ids={"mixed", "coherent"},
        quality_ledger_by_id=quality,
    )
    by_id = {row.thread_id: row for row in edition.ledger}

    assert edition.selected_ids == ["coherent"]
    assert "publication_evidence_fit_bivariate_low_tail" in by_id["mixed"].reason_codes
    assert by_id["mixed"].components["publication_evidence_fit"] == quality["mixed"]


def test_fallback_movement_is_labeled_when_kalman_is_unavailable():
    row = candidate(
        "fallback", kalman_velocity=None, kalman_surprise=None,
        kalman_uncertainty=None, kalman_observations=0,
        current_signals=30, prior_signals=10,
    )
    edition = select_daily_edition([row], display_slots=1)

    assert "relative_changed_10h_fallback" in edition.ledger[0].reason_codes
    assert edition.ledger[0].components["movement_source"] == "relative_changed_10h"


def test_candidate_fetch_cursor_exhausts_all_batches_without_semantic_cap():
    class Conn:
        def __init__(self):
            self.cursors = []
            self.edition_ends = []

        async def fetch(self, query, hours, cursor, batch_size, edition_end):
            self.cursors.append(cursor)
            self.edition_ends.append(edition_end)
            if cursor == 0:
                return [
                    {**candidate("dynamic-topic-1", current_signals=0).model_dump(), "id": 1},
                    {**candidate("dynamic-topic-2").model_dump(), "id": 2},
                ]
            if cursor == 2:
                return [{**candidate("dynamic-topic-7").model_dump(), "id": 7}]
            return []

    conn = Conn()
    edition_end = datetime(2026, 7, 12, 7, 30, tzinfo=timezone.utc)
    rows, completion = asyncio.run(fetch_daily_candidates(
        conn, hours=24, batch_size=2, edition_end=edition_end,
    ))

    assert [row.thread_id for row in rows] == ["dynamic-topic-2", "dynamic-topic-7"]
    assert conn.cursors == [0, 2, 7]
    assert conn.edition_ends == [edition_end, edition_end, edition_end]
    assert completion == {
        "batches": 3,
        "rows_scanned": 3,
        "candidate_count": 2,
        "edition_end": "2026-07-12T07:30:00+00:00",
        "cursor_exhausted": True,
        "truncated": False,
    }


def test_sample_coverage_enriches_candidates_without_mutating_input():
    candidates = [
        candidate("dynamic-topic-1", source_breadth=0, source_origins=0),
        candidate("dynamic-topic-2", source_breadth=0, source_origins=0),
    ]

    enriched = apply_sample_coverage(
        candidates,
        sources_by_topic={"dynamic-topic-1": {"Reuters", "AP"}},
        origins_by_topic={"dynamic-topic-1": {"US", "GB"}},
    )

    assert enriched[0].source_breadth == 2
    assert enriched[0].source_origins == 2
    assert enriched[1].source_breadth == 0
    assert candidates[0].source_breadth == 0


def test_spine_leads_with_verified_subject_and_demotes_grab_bags():
    # Editorial order puts the grab-bag first (say, highest movement). The spine
    # must lead with the subject-geography-verified story and demote the
    # incoherent umbrella to the end — without dropping any selected story.
    selected_ids = ["grab", "verified", "partial"]
    publishability = {
        "grab": {"grab_bag": True, "subject_verified": False},
        "verified": {"grab_bag": False, "subject_verified": True},
        "partial": {"grab_bag": False, "subject_verified": False},
    }
    ordered = order_spine_by_publishability(selected_ids, publishability)
    assert [tid for tid, _ in ordered] == ["verified", "partial", "grab"]
    assert ordered[0][1] == "spine_lead_subject_geography_verified"
    assert ordered[-1][1] == "spine_demoted_grab_bag_umbrella"


def test_spine_preserves_editorial_order_within_a_tier():
    selected_ids = ["a", "b", "c"]
    publishability = {
        tid: {"grab_bag": False, "subject_verified": True} for tid in selected_ids
    }
    ordered = order_spine_by_publishability(selected_ids, publishability)
    assert [tid for tid, _ in ordered] == ["a", "b", "c"]


def test_global_breadth_rewards_multilingual_multicountry_over_local():
    war = global_breadth_signal(3, 23)      # Hormuz-like global event
    national = global_breadth_signal(1, 1)  # single-country story
    local = global_breadth_signal(0, 0)     # stale/local noise, no current breadth
    assert war > national > local
    assert local == 0.0
    assert war >= 0.7


def test_global_breadth_is_breadth_not_volume():
    # identical breadth scores regardless of any volume — it is diversity, not size
    assert global_breadth_signal(4, 5) == global_breadth_signal(4, 5)
    # a single-language firehose cannot outscore a genuinely multilingual story
    assert global_breadth_signal(1, 2) < global_breadth_signal(5, 2)
