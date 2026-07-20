"""Umbrella child ENTAILMENT guard — pure floor/band math + bookkeeping (M1).

Council evidence 2026-07-19: the llm-event judge over-merges — a Belgian
Molenbeek shooting and Chinese landslide children sat INSIDE the Venezuela
earthquake umbrella. The guard decides per child whether it belongs to the
family it was grouped into:

  (a) hard floor — child↔family-centroid cosine must clear a MEASURED
      per-family floor (adaptive over the family's own children sims,
      never a fixed cutoff),
  (b) gray band — borderline children are confirmed by a cheap judge call
      (one per umbrella); below-floor children are out regardless (a AND b).

Rejected children stay TOP-LEVEL active — never dropped, every rejection
bookkept (no silent filtering).
"""
import math

import pytest

from app.services.umbrella_child_guard import (
    ACCEPT,
    BORDERLINE,
    REJECT,
    CHILD_CONFIRM_SYSTEM,
    FamilyGuardReport,
    GuardParams,
    child_confirm_user,
    classify_children,
    compute_family_floor,
    finalize_family,
    parse_child_confirm_response,
)

P = GuardParams()  # defaults: k=2.5, band=1.0, min_measure=4, sigma_min=0.01


# --- (a) the measured per-family floor ------------------------------------

def test_floor_is_measured_per_family_not_fixed():
    # Two families with different internal spreads yield DIFFERENT floors —
    # the adaptive claim (2026-07-03 precedent: thresholds VARY per centroid,
    # fixed cutoffs always serve junk).
    tight = compute_family_floor([0.98, 0.985, 0.98, 0.975, 0.98], P)
    spread = compute_family_floor([0.93, 0.94, 0.95, 0.96, 0.96, 0.97, 0.98, 0.98], P)
    assert tight is not None and spread is not None
    assert abs(tight.floor - spread.floor) > 0.01
    assert spread.floor < tight.floor  # looser family → lower floor


def test_tight_family_rejects_clear_outlier_hard():
    sims = [0.99, 0.98, 0.985, 0.975, 0.97, 0.98, 0.99, 0.97, 0.90]
    floor = compute_family_floor(sims, P)
    zones = classify_children(sims, floor)
    assert zones[-1] == REJECT          # the 0.90 Belgium-class outlier
    assert all(z == ACCEPT for z in zones[:-1])


def test_outlier_contamination_does_not_hide_the_outlier():
    # The very child we hunt contaminates mean/σ (drags the mean, inflates σ,
    # weakening its own rejection): mean−2.5σ here is 0.892 → 0.90 would PASS.
    # The robust center/spread (median + scaled MAD) must still reject it.
    sims = [0.98, 0.98, 0.98, 0.98, 0.98, 0.90]
    floor = compute_family_floor(sims, P)
    assert floor is not None
    mean = sum(sims) / len(sims)
    sigma = math.sqrt(sum((s - mean) ** 2 for s in sims) / len(sims))
    assert mean - 2.5 * sigma < 0.90    # the naive floor would keep the outlier
    assert classify_children(sims, floor)[-1] == REJECT


def test_small_family_floor_unmeasurable_all_borderline():
    # n < min_measure → no stable measured floor. Measurement impossible is
    # NOT permission to hard-reject: every child is borderline (judge decides).
    sims = [0.99, 0.91, 0.90]
    assert compute_family_floor(sims, P) is None
    assert classify_children(sims, None) == [BORDERLINE] * 3


def test_legit_spread_family_keeps_everyone():
    # A real cross-country event family with honest spread — nobody rejected.
    sims = [0.93, 0.94, 0.95, 0.96, 0.96, 0.97, 0.98, 0.98]
    zones = classify_children(sims, compute_family_floor(sims, P))
    assert all(z == ACCEPT for z in zones)


def test_gray_band_sits_between_floor_and_band_top():
    sims = [0.98, 0.98, 0.98, 0.98, 0.98, 0.96]
    floor = compute_family_floor(sims, P)
    assert floor is not None
    assert floor.floor <= 0.96 < floor.band_top
    assert classify_children(sims, floor)[-1] == BORDERLINE


def test_sigma_min_prevents_zero_width_band():
    # An all-identical family has MAD 0 — σ_eff floors at sigma_min so the
    # floor/band stay non-degenerate and the members themselves accept.
    sims = [0.98] * 5
    floor = compute_family_floor(sims, P)
    assert floor is not None
    assert floor.sigma_eff == pytest.approx(P.sigma_min)
    assert floor.band_top > floor.floor
    assert classify_children(sims, floor) == [ACCEPT] * 5


def test_degenerate_inputs_yield_no_floor():
    assert compute_family_floor([], P) is None
    assert compute_family_floor([0.97], P) is None


# --- (b) finalize: judge bookkeeping, a AND b semantics -------------------

def _fam(sims_by_id):
    return [(tid, f"topic-{tid}", s) for tid, s in sims_by_id]


def test_below_floor_rejected_even_if_judge_says_yes():
    # (a) AND (b): the judge is consulted only inside the gray band — a
    # below-floor child cannot be saved by a stray judge verdict.
    children = _fam([(1, 0.98), (2, 0.98), (3, 0.98), (4, 0.98), (5, 0.98), (9, 0.90)])
    floor = compute_family_floor([s for _, _, s in children], P)
    verdicts = finalize_family(children, floor, {9: True}, anchor_id=1)
    v9 = next(v for v in verdicts if v.topic_id == 9)
    assert v9.final == "rejected_floor" and not v9.kept


def test_borderline_confirmed_kept_rejected_dropped():
    children = _fam([(1, 0.98), (2, 0.98), (3, 0.98), (4, 0.98),
                     (5, 0.96), (6, 0.96)])
    floor = compute_family_floor([s for _, _, s in children], P)
    verdicts = finalize_family(children, floor, {5: True, 6: False}, anchor_id=1)
    by_id = {v.topic_id: v for v in verdicts}
    assert by_id[5].final == "accepted_judge" and by_id[5].kept
    assert by_id[6].final == "rejected_judge" and not by_id[6].kept
    assert by_id[2].final == "accepted" and by_id[2].kept


def test_judge_unavailable_fails_open_loudly():
    # Judge outage must degrade to the status quo ante (child kept, loudly
    # labeled) — never a silent rejection driven by infrastructure state.
    children = _fam([(1, 0.98), (2, 0.98), (3, 0.98), (4, 0.98), (5, 0.96)])
    floor = compute_family_floor([s for _, _, s in children], P)
    verdicts = finalize_family(children, floor, None, anchor_id=1)
    v5 = next(v for v in verdicts if v.topic_id == 5)
    assert v5.final == "kept_judge_unavailable" and v5.kept


def test_judge_missing_id_fails_open_for_that_child():
    children = _fam([(1, 0.98), (2, 0.98), (3, 0.98), (4, 0.98),
                     (5, 0.96), (6, 0.96)])
    floor = compute_family_floor([s for _, _, s in children], P)
    verdicts = finalize_family(children, floor, {5: False}, anchor_id=1)
    by_id = {v.topic_id: v for v in verdicts}
    assert by_id[5].final == "rejected_judge" and not by_id[5].kept
    assert by_id[6].final == "kept_judge_unavailable" and by_id[6].kept


def test_anchor_is_never_rejected():
    # The head child IS the umbrella's identity — it anchors the entailment
    # question and is exempt (a family of one dissolves anyway).
    children = _fam([(1, 0.90), (2, 0.98), (3, 0.98), (4, 0.98), (5, 0.98)])
    floor = compute_family_floor([s for _, _, s in children], P)
    verdicts = finalize_family(children, floor, {}, anchor_id=1)
    v1 = next(v for v in verdicts if v.topic_id == 1)
    assert v1.final == "anchor" and v1.kept


def test_unmeasured_family_all_borderline_judge_decides():
    children = _fam([(1, 0.99), (2, 0.91)])
    verdicts = finalize_family(children, None, {2: False}, anchor_id=1)
    by_id = {v.topic_id: v for v in verdicts}
    assert by_id[1].final == "anchor" and by_id[1].kept
    assert by_id[2].final == "rejected_judge" and not by_id[2].kept


def test_family_report_dissolves_below_two_kept():
    children = _fam([(1, 0.99), (2, 0.91)])
    verdicts = finalize_family(children, None, {2: False}, anchor_id=1)
    report = FamilyGuardReport(head_label="Quake", floor=None, verdicts=verdicts)
    assert report.kept_ids == [1]
    assert report.dissolved  # < 2 kept → no umbrella, everyone top-level
    assert [v.topic_id for v in report.rejected] == [2]


def test_every_child_gets_exactly_one_verdict():
    children = _fam([(1, 0.98), (2, 0.98), (3, 0.98), (4, 0.98),
                     (5, 0.96), (9, 0.80)])
    floor = compute_family_floor([s for _, _, s in children], P)
    verdicts = finalize_family(children, floor, {5: True}, anchor_id=1)
    assert sorted(v.topic_id for v in verdicts) == [1, 2, 3, 4, 5, 9]


# --- judge prompt + tolerant parse ----------------------------------------

def test_child_confirm_user_lists_anchor_core_and_candidates():
    user = child_confirm_user(
        "Venezuela Earthquake Death Toll",
        ["Venezuela Earthquake Rescue", "Caracas Aftershocks"],
        [{"id": 7, "label": "Molenbeek Shooting"},
         {"id": 8, "label": "Chinese Landslide Children"}],
    )
    assert "Venezuela Earthquake Death Toll" in user
    assert "Caracas Aftershocks" in user
    assert "7\tMolenbeek Shooting" in user
    assert "8\tChinese Landslide Children" in user


def test_child_confirm_user_handles_empty_core():
    user = child_confirm_user("Quake", [], [{"id": 7, "label": "X"}])
    assert "none" in user.lower()


def test_parse_child_confirm_verdicts_and_coercion():
    raw = ('{"verdicts":[{"topic_id":7,"same_event":false},'
           '{"topic_id":"8","same_event":"true"},'
           '{"topic_id":999,"same_event":true},'
           '{"topic_id":9,"same_event":"maybe"}]}')
    out = parse_child_confirm_response(raw, [7, 8, 9])
    assert out == {7: False, 8: True}   # 999 hallucinated → dropped;
    #                                     9's non-boolean verdict → unresolved


def test_parse_child_confirm_fenced_json():
    raw = 'Sure:\n```json\n{"verdicts":[{"topic_id":7,"same_event":true}]}\n```'
    assert parse_child_confirm_response(raw, [7]) == {7: True}


def test_parse_child_confirm_unparseable_returns_none():
    assert parse_child_confirm_response("", [7]) is None
    assert parse_child_confirm_response("NOT JSON garbage", [7]) is None
    # parseable-but-empty is {} (per-child fail-open), NOT a parse failure
    assert parse_child_confirm_response('{"verdicts":[]}', [7]) == {}


def test_confirm_system_prompt_is_precision_first_strict_json():
    assert "STRICT JSON" in CHILD_CONFIRM_SYSTEM
    assert "same_event" in CHILD_CONFIRM_SYSTEM
