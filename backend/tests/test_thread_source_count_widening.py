"""The saturated outlet count stops being pinned at the receipt slice.

FOLLOW-UP to the count-basis fix (d0b5a678). That fix made the number
correct-by-construction against the receipts each row renders and declared the
basis. It left the number SMALL: `sample_signal_ids` is `ORDER BY sid DESC LIMIT
24`, so `source_count` saturates at 24 for every busy story. Measured on the
live front page 2026-08-14 (`/api/v2/threads?hours=24&limit=40`): the top rows
served 23, 22, 18, 21, 23, 23 — clustered against the cap, which makes the
number useless for COMPARING stories: every big story looks the same size.

WHAT WAS MEASURED BEFORE CHANGING SQL (prod, 2026-08-14, read-only):

  * A true window-scoped distinct-source count over `signals_v2` stays rejected:
    2,143ms correlated / 1,185ms set-based on the 40-row list request.
  * `emergent_clusters.sample_receipts` (mig 097, jsonb, frozen at snapshot
    write, join-free) counts distinct `src` for **+5-6ms warm** on the list
    query (19-21ms → 24-25ms, 4 interleaved EXPLAIN ANALYZE runs). The earlier
    278ms reading was a cold-cache measurement of the same lane.
  * Coverage on the serving population: 2,747 latest-snapshot clusters, 0 NULL
    `sample_receipts`, 27,977 receipts, `src` present on 27,977/27,977.
  * Impact: corpus-wide only 52/3,263 active topics carry more than 24 sample
    ids — but they are umbrellas, and ranking puts them on top: **12 of today's
    40 front-page rows** widen past 24 (avg 20 → 28.2, max 132).

SO THE POPULATION MOVES, THE HONESTY RAIL MOVES WITH IT. `sample_receipts` is
the SAME per-cluster top-K population as `sample_signal_ids`, unioned across an
umbrella's member clusters — still a sample, never "every outlet that
published", and it is frozen, so unlike the live-hydrated count it does not
decay as the 7-day retention deletes rows. It shares the latest-snapshot
lineage with `signal_count`, which the hydrated count never did.

Contract under test:
  * ``source_count``        the widest MEASURED count available for the row, and
                            never below the distinct outlets its own rendered
                            receipts show (a reader can count those).
  * ``source_count_basis``  'snapshot_receipts' when counted over the frozen
                            snapshot sample, 'receipt_sample' when counted over
                            the receipts served — the row always says which.
  * ``source_sample_size``  the receipt population THAT basis was measured over.
"""
from __future__ import annotations

from app.services.thread_intelligence import (
    _DYNAMIC_TOPICS_COUNTRY_SQL,
    _DYNAMIC_TOPICS_SELECT,
    _DYNAMIC_TOPIC_DETAIL_SQL,
    _merge_event_pair,
    assemble_dynamic_thread,
    assemble_emergent_thread,
    resolve_thread_source_count,
)


def _topic_row(*, stats=None, topic_id: int = 3433) -> dict:
    row = {
        "id": topic_id,
        "identity_key": f"u2-topic-{topic_id}",
        "label": "Russian Strikes on Ukraine",
        "recent_n_signals": 1200,
        "agg_n_signals": 4200,
        "count_window_hours": 168,
        "changed_10h": 9,
        "noise_rate": 0.1,
        "mean_cohesion": 0.9,
        "first_seen": None,
        "top_country_codes": ["UA", "RU"],
    }
    if stats is not None:
        row["snapshot_receipt_stats"] = stats
    return row


def _signal(source_name: str | None, idx: int) -> dict:
    return {
        "id": 900 + idx,
        "headline": f"strike report {idx}",
        "source_name": source_name,
        "source_url": f"https://{source_name or 'unknown'}/{idx}",
        "country_code": "UA",
        "timestamp": None,
        "nlp_sentiment": -0.3,
        "persons": [],
    }


def _thread(sources: list[str | None], *, stats=None, topic_id: int = 3433) -> dict:
    return assemble_dynamic_thread(
        _topic_row(stats=stats, topic_id=topic_id),
        [_signal(s, i) for i, s in enumerate(sources)],
    )


class TestTheNumberWidensPastTheSlice:
    def test_snapshot_receipts_lift_the_count_past_the_24_cap(self):
        """dt-3433 on prod: 23 outlets in the served slice, 143 in the snapshot."""
        thread = _thread([f"o{i}.com" for i in range(23)], stats=[143, 246])
        assert thread["source_count"] == 143

    def test_the_row_says_which_population_it_counted(self):
        thread = _thread([f"o{i}.com" for i in range(23)], stats=[143, 246])
        assert thread["source_count_basis"] == "snapshot_receipts"
        assert thread["source_sample_size"] == 246

    def test_a_row_that_does_not_saturate_keeps_the_served_basis(self):
        """Most topics sit at avg 11.8 ids — nothing to widen, nothing to
        relabel. Only the rows the cap actually binds change basis."""
        thread = _thread(["a.com", "b.com"], stats=[2, 2])
        assert thread["source_count"] == 2
        assert thread["source_count_basis"] == "receipt_sample"
        assert thread["source_sample_size"] == 2

    def test_the_number_never_drops_below_the_outlets_it_renders(self):
        """A reader can count the domains under the row. Serving fewer than
        that is visibly false — so a short/partial frozen sample never wins."""
        thread = _thread(["a.com", "b.com", "c.com"], stats=[1, 1])
        assert thread["source_count"] == 3
        assert thread["source_count_basis"] == "receipt_sample"
        assert thread["source_sample_size"] == 3

    def test_missing_stats_leave_the_prior_contract_untouched(self):
        """Pre-097 rows, the emergent lane and every fixture without the column
        must serve exactly what they served before."""
        thread = _thread(["a.com", "b.com"])
        assert thread["source_count"] == 2
        assert thread["source_count_basis"] == "receipt_sample"
        assert thread["source_sample_size"] == 2


class TestStarvedRowsRecoverAMeasuredCount:
    def test_frozen_receipts_answer_when_retention_ate_the_live_rows(self):
        """The dt-12138 starvation class: 0 live receipts resolved, but the
        snapshot froze its own. That IS a measurement — of the snapshot."""
        thread = _thread([], stats=[31, 44])
        assert thread["source_count"] == 31
        assert thread["source_count_basis"] == "snapshot_receipts"
        assert thread["source_count_measured"] is True

    def test_starvation_with_no_frozen_receipts_stays_unmeasured(self):
        thread = _thread([], stats=[0, 0])
        assert thread["source_count"] == 0
        assert thread["source_count_measured"] is False
        assert thread["source_count_basis"] == "receipt_sample"


class TestMalformedStatsCannotBreakARow:
    def test_none_is_tolerated(self):
        assert _thread(["a.com"], stats=None)["source_count"] == 1

    def test_empty_and_short_arrays_are_tolerated(self):
        assert _thread(["a.com"], stats=[])["source_count"] == 1
        assert _thread(["a.com"], stats=[5])["source_count"] == 5

    def test_null_elements_are_tolerated(self):
        assert _thread(["a.com"], stats=[None, None])["source_count"] == 1

    def test_non_numeric_elements_are_tolerated(self):
        assert _thread(["a.com"], stats=["x", "y"])["source_count"] == 1


class TestResolverIsPure:
    def test_snapshot_wins_only_when_strictly_wider(self):
        assert resolve_thread_source_count(
            receipt_source_count=5, receipt_sample_size=6, snapshot_receipt_stats=[5, 40]
        ) == (5, "receipt_sample", 6)
        assert resolve_thread_source_count(
            receipt_source_count=5, receipt_sample_size=6, snapshot_receipt_stats=[9, 40]
        ) == (9, "snapshot_receipts", 40)

    def test_population_falls_back_to_the_count_when_absent(self):
        """A stats array that carries outlets but no population size still has
        to name a sample size — the count itself is its floor."""
        assert resolve_thread_source_count(
            receipt_source_count=1, receipt_sample_size=1, snapshot_receipt_stats=[9]
        ) == (9, "snapshot_receipts", 9)


class TestMergeKeepsTheWidestMeasuredNumber:
    def test_a_widened_side_survives_the_fold(self):
        """Merging must not throw away a snapshot count by recounting only the
        24+24 receipts the folded row happens to render."""
        keep = _thread([f"k{i}.com" for i in range(20)], stats=[132, 210], topic_id=1)
        drop = _thread([f"d{i}.com" for i in range(10)], topic_id=2)
        merged = _merge_event_pair(keep, drop)
        assert merged["source_count"] == 132
        assert merged["source_count_basis"] == "snapshot_receipts"
        assert merged["source_sample_size"] == 210

    def test_the_union_wins_when_it_is_wider_than_either_side(self):
        keep = _thread([f"k{i}.com" for i in range(5)], stats=[5, 5], topic_id=1)
        drop = _thread([f"d{i}.com" for i in range(4)], stats=[4, 4], topic_id=2)
        merged = _merge_event_pair(keep, drop)
        rendered = {e["source"] for e in merged["evidence_samples"] if e.get("source")}
        assert merged["source_count"] == len(rendered) == 9
        assert merged["source_count_basis"] == "receipt_sample"
        assert merged["source_sample_size"] == len(merged["evidence_samples"])

    def test_basis_can_never_be_left_describing_a_different_number(self):
        """The regression this class exists to prevent: a fold that recounts
        over evidence while the row still carries the snapshot label."""
        keep = _thread([f"k{i}.com" for i in range(3)], stats=[3, 3], topic_id=1)
        drop = _thread([f"d{i}.com" for i in range(3)], stats=[3, 3], topic_id=2)
        merged = _merge_event_pair(keep, drop)
        assert merged["source_count"] == 6
        assert merged["source_count_basis"] == "receipt_sample"
        assert merged["source_sample_size"] == len(merged["evidence_samples"])


class TestBothListSqlCopiesCarryTheColumn:
    """The list SELECT is shared with the country view, and the single-thread
    detail keeps its own copy — a column added to one only would make the same
    story count differently on two doors (the N19 defect class)."""

    def test_global_and_country_list_select_the_stats(self):
        assert "AS snapshot_receipt_stats" in _DYNAMIC_TOPICS_SELECT
        assert "AS snapshot_receipt_stats" in _DYNAMIC_TOPICS_COUNTRY_SQL

    def test_detail_sql_selects_the_stats(self):
        assert "AS snapshot_receipt_stats" in _DYNAMIC_TOPIC_DETAIL_SQL

    def test_the_lane_is_the_join_free_jsonb_one(self):
        """The affordable lane (+5-6ms warm) is `sample_receipts`; a rewrite
        that reaches into signals_v2 here costs 1.2-2.1s and must not land."""
        block = _DYNAMIC_TOPICS_SELECT[
            _DYNAMIC_TOPICS_SELECT.index("snapshot_receipt_stats") - 700:
            _DYNAMIC_TOPICS_SELECT.index("AS snapshot_receipt_stats")
        ]
        assert "sample_receipts" in block
        assert "signals_v2" not in block


class TestEmergentLaneIsUnchanged:
    def test_emergent_rows_still_count_over_the_receipts_they_serve(self):
        """One emergent cluster IS one top-K sample, so there is no wider
        frozen population to reach for — the basis stays as it was."""
        cluster = {
            "id": 77,
            "label": "Drone Strikes",
            "description": None,
            "n_signals": 40,
            "velocity": 2,
            "cohesion": 0.6,
            "snapshot_at": None,
            "top_country_codes": ["RU"],
        }
        thread = assemble_emergent_thread(cluster, [_signal("ria.ru", 1)])
        assert thread["source_count_basis"] == "receipt_sample"
        assert thread["source_count"] == 1
