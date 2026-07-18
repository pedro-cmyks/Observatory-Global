"""Temporal signature (mig 085) — pure classification tests.

Freezes the Lane C contract: every ACTIVE topic gets a temporal shape from
the narrative_lineage weeks + its own hot span —
  new          no ancestor units AND the census actually attempted the topic
  continuous   one unbroken weekly chain (1-week gaps absorbed — the known
               Stage-B unit hole between archive and hot must not fabricate
               resurrections)
  resurrected  exactly one >=2-week quiet gap, then returned
  recurrent    >=3 eras (quiet-and-returned happened >=2 times)
Below the census member floor -> NO signature (absence over guess).
Umbrellas inherit the majority of their children; ties fall to no-badge.
"""
from __future__ import annotations

from datetime import date

from scripts.temporal_signature import (
    classify_topic,
    hot_weeks,
    monday,
    split_eras,
    umbrella_signature,
)

W = [date(2026, 5, 4) + __import__("datetime").timedelta(weeks=k) for k in range(12)]
# W[0]=May 4, W[1]=May 11, ... all Mondays


def test_monday_normalizes_any_day():
    assert monday(date(2026, 7, 16)) == date(2026, 7, 13)   # Thursday -> Monday
    assert monday(date(2026, 7, 13)) == date(2026, 7, 13)


def test_hot_weeks_spans_first_to_last_seen():
    assert hot_weeks(date(2026, 7, 1), date(2026, 7, 16)) == {
        date(2026, 6, 29), date(2026, 7, 6), date(2026, 7, 13)}
    assert hot_weeks(None, date(2026, 7, 16)) == {date(2026, 7, 13)}
    assert hot_weeks(None, None) == set()


# ── era splitting ───────────────────────────────────────────────────────────

def test_split_eras_contiguous_is_one_era():
    assert split_eras([W[0], W[1], W[2]]) == [[W[0], W[1], W[2]]]


def test_split_eras_one_week_gap_absorbed():
    # quiet of exactly 1 week does NOT split (unit-hole tolerance)
    assert split_eras([W[0], W[2]]) == [[W[0], W[2]]]


def test_split_eras_two_week_gap_splits():
    assert split_eras([W[0], W[3]]) == [[W[0]], [W[3]]]


def test_split_eras_multiple_gaps():
    weeks = [W[0], W[1], W[4], W[8], W[9]]
    assert split_eras(weeks) == [[W[0], W[1]], [W[4]], [W[8], W[9]]]


def test_split_eras_dedupes_and_sorts():
    assert split_eras([W[1], W[0], W[1]]) == [[W[0], W[1]]]


# ── classification ──────────────────────────────────────────────────────────

def test_new_requires_attempted_coverage():
    sig, meta = classify_topic([], date(2026, 7, 10), date(2026, 7, 16),
                               coverage_included=True)
    assert sig == "new"
    assert meta["first_seen_week"] == "2026-07-06"
    assert meta["eras"] == 1


def test_below_floor_is_absence_not_new():
    sig, meta = classify_topic([], date(2026, 7, 10), date(2026, 7, 16),
                               coverage_included=False)
    assert sig is None
    sig2, _ = classify_topic([], date(2026, 7, 10), date(2026, 7, 16),
                             coverage_included=None)
    assert sig2 is None


def test_continuous_chain_archive_into_hot():
    # archive W6..W8, hot starts W9 — unbroken
    sig, meta = classify_topic([W[6], W[7], W[8]], W[9], W[10],
                               coverage_included=True)
    assert sig == "continuous"
    assert meta["eras"] == 1
    assert meta["gap_weeks"] == 0


def test_unit_hole_one_week_gap_stays_continuous():
    # archive ends W7, hot week W9 — the ~1-week archive lag must not read
    # as a resurrection
    sig, _ = classify_topic([W[6], W[7]], W[9], W[9], coverage_included=True)
    assert sig == "continuous"


def test_resurrected_single_two_week_gap():
    sig, meta = classify_topic([W[2], W[3]], W[6], W[7],
                               coverage_included=True)
    assert sig == "resurrected"
    assert meta["eras"] == 2
    assert meta["gap_weeks"] == 2          # W4, W5 quiet
    assert meta["returned_week"] == W[6].isoformat()
    assert meta["first_seen_week"] == W[2].isoformat()


def test_dead_lineage_descendant_folds_into_resurrected():
    # archive lineage died at W1; the live topic appears W8 — a descendant of
    # a dead lineage IS a resurrection (task: fold the edge case)
    sig, meta = classify_topic([W[0], W[1]], W[8], W[9],
                               coverage_included=True)
    assert sig == "resurrected"
    assert meta["gap_weeks"] == 6


def test_recurrent_three_eras():
    sig, meta = classify_topic([W[0], W[3], W[4]], W[8], W[8],
                               coverage_included=True)
    assert sig == "recurrent"
    assert meta["eras"] == 3
    # latest quiet gap: W5..W7 between W4 and W8
    assert meta["gap_weeks"] == 3
    assert meta["returned_week"] == W[8].isoformat()


def test_stitched_topic_classifies_even_without_coverage_row():
    # an existing stitch IS evidence — coverage bookkeeping missing must not
    # erase a measured lineage
    sig, _ = classify_topic([W[5], W[6]], W[7], W[8], coverage_included=None)
    assert sig == "continuous"


def test_hot_span_fills_its_own_weeks():
    # hot first_seen W5..last_seen W8 bridges what would otherwise be a gap
    sig, _ = classify_topic([W[3], W[4]], W[5], W[8], coverage_included=True)
    assert sig == "continuous"


# ── umbrella inheritance ────────────────────────────────────────────────────

def test_umbrella_majority_wins():
    sig, meta = umbrella_signature(["recurrent", "recurrent", "continuous"])
    assert sig == "recurrent"
    assert meta["inherited"] is True
    assert meta["children"] == {"recurrent": 2, "continuous": 1}


def test_umbrella_none_children_do_not_vote():
    sig, _ = umbrella_signature([None, None, "new"])
    assert sig == "new"


def test_umbrella_tie_falls_to_continuous_when_present():
    sig, _ = umbrella_signature(["resurrected", "continuous"])
    assert sig == "continuous"


def test_umbrella_tie_without_continuous_is_absence():
    sig, _ = umbrella_signature(["resurrected", "recurrent"])
    assert sig is None


def test_umbrella_no_votes_is_absence():
    sig, meta = umbrella_signature([None, None])
    assert sig is None
    assert meta == {}
