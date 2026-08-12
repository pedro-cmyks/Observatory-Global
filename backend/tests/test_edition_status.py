"""The seal's status stops being an unreachable binary (T3.2, policy a+b).

`_edition_status` used to demand UNANIMOUS per-story-node attribution across 12
story nodes while per-node coverage runs ~50% — an all-or-nothing conjunction
that turned 0.5^12 into a 0% pass rate, so 25 of 25 sealed editions carried
`degraded` and the correct Pareto selection never reached a reader. The bars
below are MEASURED (see `docs/research/brief-daily/2026-08-12-m0-measurement.md`
addendum §D and the 25-edition fraction histogram), not invented.
"""
from __future__ import annotations

import pytest

from app.services.edition_status import (
    DATA_LAG_BAR_HOURS,
    EDITION_STATUS_CONTRACT,
    READINESS_FULL_BAR,
    READINESS_PARTIAL_BAR,
    SEALED_FULL,
    SEALED_PARTIAL,
    SEALED_THIN,
    STATUS_VALUES,
    grade_edition,
    normalize_stored_status,
)


def _readiness(**fractions: tuple[int, int]) -> dict[str, dict]:
    """Readiness in the STORED (dict) shape: what a sealed artifact carries."""
    out: dict[str, dict] = {}
    for dim, (ready, total) in fractions.items():
        fraction = (ready / total) if total else None
        out[dim] = {
            "status": "missing" if not total else "ready",
            "values": [f"{dim}-value"] if ready else [],
            "reason_codes": [],
            "measured": {
                "ready": ready,
                "total": total,
                "fraction": fraction,
                "basis": "story_nodes",
            },
        }
    return out


def _all(ready: int, total: int = 12) -> dict[str, dict]:
    return _readiness(
        who=(ready, total), what=(total, total), when=(total, total),
        where=(ready, total), how=(total, total),
    )


_CLEAN = {"cursor_exhausted": True, "data_lag_hours": 0.0, "receipt_fetch_error": None}


# --- the bars themselves -----------------------------------------------------

def test_bars_sit_in_the_empty_intervals_of_the_measured_histogram():
    # Pooled who+where over the 21 non-empty sealed editions is quantised to
    # k/12 and every step 4/12..10/12 is occupied — no natural split — so the
    # bars are the pooled TERTILES, placed in the adjacent EMPTY intervals
    # (0.333<0.40<0.417 and 0.500<0.55<0.583) so a one-node wobble cannot flip
    # an edition's grade.
    assert 4 / 12 < READINESS_PARTIAL_BAR < 5 / 12
    assert 6 / 12 < READINESS_FULL_BAR < 7 / 12
    assert STATUS_VALUES == (SEALED_FULL, SEALED_PARTIAL, SEALED_THIN)


def test_graded_status_never_emits_the_old_binary_vocabulary():
    for ready in range(0, 13):
        grade = grade_edition(_all(ready), _CLEAN)
        assert grade.status in STATUS_VALUES
        assert grade.status not in {"ready", "degraded"}
        assert grade.contract == EDITION_STATUS_CONTRACT


# --- grading from the measured fractions -------------------------------------

def test_seven_of_twelve_story_nodes_seals_full_without_unanimity():
    # The whole point: 7/12 = 0.583 clears the full bar. Unanimity is dead.
    grade = grade_edition(_all(7), _CLEAN)
    assert grade.status == SEALED_FULL
    assert grade.reasons == []


def test_half_the_story_nodes_seals_partial_and_names_the_dimensions():
    grade = grade_edition(_all(6), _CLEAN)
    assert grade.status == SEALED_PARTIAL
    assert "who_below_full_bar" in grade.reasons
    assert "where_below_full_bar" in grade.reasons


def test_a_third_of_the_story_nodes_seals_thin_and_names_the_dimensions():
    grade = grade_edition(_all(4), _CLEAN)
    assert grade.status == SEALED_THIN
    assert "who_below_bar" in grade.reasons
    assert "where_below_bar" in grade.reasons


def test_one_thin_dimension_pulls_the_whole_edition_thin():
    # 2026-08-04: who 7/12 clears the full bar, where 4/12 is below the partial
    # bar. The edition is thin, and the reason says WHICH dimension.
    readiness = _readiness(
        who=(7, 12), what=(12, 12), when=(12, 12), where=(4, 12), how=(12, 12),
    )
    grade = grade_edition(readiness, _CLEAN)
    assert grade.status == SEALED_THIN
    assert grade.reasons == ["where_below_bar"]


def test_structurally_empty_edition_is_thin_with_named_missing_dimensions():
    grade = grade_edition(_all(0, total=0), _CLEAN)
    assert grade.status == SEALED_THIN
    assert "who_missing" in grade.reasons
    assert "where_missing" in grade.reasons


def test_why_is_never_required_for_the_seal():
    # `why` is forced partial by construction (causality is never measured), so
    # requiring it would recreate the unreachable binary on another axis.
    readiness = _all(12)
    readiness["why"] = _readiness(why=(0, 12))["why"]
    assert grade_edition(readiness, _CLEAN).status == SEALED_FULL


# --- data lag is a labelled fact, never a voider -----------------------------

def test_data_lag_names_itself_but_never_lowers_the_grade():
    # THE decisive row: 2026-07-13 is the one edition in 25 that reached
    # unanimity on both who and where — and sealed `degraded` anyway because
    # data_lag_hours was 8.455 > 6. Under the graded policy it seals FULL and
    # carries the lag as a named fact.
    completion = {**_CLEAN, "data_lag_hours": 8.455}
    grade = grade_edition(_all(12), completion)
    assert grade.status == SEALED_FULL
    assert grade.reasons == ["data_lag"]
    assert grade.facts["data_lag_hours"] == pytest.approx(8.455)
    assert grade.facts["data_lag_bar_hours"] == DATA_LAG_BAR_HOURS


def test_data_lag_within_the_bar_is_carried_as_a_fact_without_a_reason():
    grade = grade_edition(_all(12), {**_CLEAN, "data_lag_hours": 2.0})
    assert grade.reasons == []
    assert grade.facts["data_lag_hours"] == pytest.approx(2.0)


def test_data_lag_does_not_rescue_or_sink_a_partial_edition():
    lagged = grade_edition(_all(6), {**_CLEAN, "data_lag_hours": 21.5})
    fresh = grade_edition(_all(6), _CLEAN)
    assert lagged.status == fresh.status == SEALED_PARTIAL
    assert "data_lag" in lagged.reasons and "data_lag" not in fresh.reasons


# --- evidence incompleteness -------------------------------------------------

def test_unfinished_receipt_scan_caps_a_full_edition_at_partial():
    grade = grade_edition(_all(12), {**_CLEAN, "cursor_exhausted": False})
    assert grade.status == SEALED_PARTIAL
    assert "receipts_incomplete" in grade.reasons


def test_receipt_fetch_error_caps_at_partial_but_never_voids_the_seal():
    grade = grade_edition(_all(12), {**_CLEAN, "receipt_fetch_error": "timeout"})
    assert grade.status == SEALED_PARTIAL
    assert "receipts_incomplete" in grade.reasons
    assert grade.status in STATUS_VALUES  # still a sealed edition


# --- shape tolerance + legacy rows -------------------------------------------

def test_grading_accepts_model_items_as_well_as_stored_dicts():
    from app.services.investigation_graph import ReadinessFraction, ReadinessItem

    readiness = {
        dim: ReadinessItem(
            status="ready",
            measured=ReadinessFraction(ready=8, total=12, basis="story_nodes"),
        )
        for dim in ("who", "what", "when", "where", "how")
    }
    assert grade_edition(readiness, _CLEAN).status == SEALED_FULL


def test_a_dimension_with_no_measurement_falls_back_to_its_status():
    readiness = {dim: {"status": "ready"} for dim in ("who", "what", "when", "where", "how")}
    assert grade_edition(readiness, _CLEAN).status == SEALED_FULL
    readiness["who"] = {"status": "missing"}
    assert grade_edition(readiness, _CLEAN).status == SEALED_THIN


def test_legacy_stored_status_is_remapped_readably_and_never_claims_a_grade():
    # 25 sealed rows predate the graded vocabulary. Serving must not break on
    # them, and the remap must never be mistaken for a measurement.
    legacy = normalize_stored_status("degraded")
    assert legacy["status"] == SEALED_PARTIAL
    assert legacy["stored_status"] == "degraded"
    assert legacy["reasons"] == ["legacy_status_not_graded"]

    ready = normalize_stored_status("ready")
    assert ready["status"] == SEALED_FULL
    assert ready["reasons"] == ["legacy_status_not_graded"]


def test_graded_stored_status_passes_through_untouched():
    for value in STATUS_VALUES:
        out = normalize_stored_status(value)
        assert out["status"] == value
        assert out["reasons"] == []
        assert out["stored_status"] == value


def test_unknown_or_missing_stored_status_degrades_to_thin_readably():
    assert normalize_stored_status(None)["status"] == SEALED_THIN
    unknown = normalize_stored_status("something-else")
    assert unknown["status"] == SEALED_THIN
    assert unknown["reasons"] == ["unrecognized_stored_status"]
    assert unknown["stored_status"] == "something-else"
