"""The 'Sources' stat rendered the LENGTH OF A DISPLAY LIST, not a count.

Measured on prod 2026-08-14 (dt-242 "7.4-Magnitude Earthquake Kills Dozens in
Colombia", the screen Pedro was reading):

  * the payload served `topSources` with exactly 20 entries, and the detail
    panel printed "20" under the label `Sources`
  * the SAME payload's 37 evidence receipts carry 36 DISTINCT source domains

20 was never a measurement — `build_thread_packet` caps the source preview at
`[:20]` (a display slice), and the surface read `topSources.length` as if the
slice were the count. The page disproved its own number: a reader could count
36 outlets in the receipts printed directly beneath the "20".

Contract under test — the preview stays a preview, and the COUNT is counted:
  * ``topSources``        unchanged: a ranked preview, still capped at 20.
  * ``sourceCount``       distinct non-empty source names across ALL rows the
                          packet was given — uncapped, so it can never saturate
                          at the display slice.
  * ``sourceSampleSize``  how many receipts that count ran over, so the number
                          is interpretable as what it is (a count over the
                          receipt sample) and never reads as the story's total.

Absence stays honest: no rows means no receipts were resolved, which is a
DEGRADED state, not a measured "zero outlets" — `sourceCount` serves None.
"""
from __future__ import annotations

from app.services.thread_packet import build_thread_packet


def _row(source_name: str, *, idx: int = 0) -> dict:
    return {
        "id": 1000 + idx,
        "headline": f"headline {idx}",
        "source_name": source_name,
        "source_url": f"https://{source_name}/story-{idx}",
        "country_code": "CO",
        "nlp_sentiment": -0.5,
        "timestamp": None,
        "persons": [],
    }


def _rows(names: list[str]) -> list[dict]:
    return [_row(n, idx=i) for i, n in enumerate(names)]


class TestSourceCountIsCountedNotSliced:
    def test_count_exceeds_the_twenty_item_preview_cap(self):
        """The dt-242 witness: 36 distinct sources must not report as 20."""
        packet = build_thread_packet(_rows([f"outlet{i}.com" for i in range(36)]))
        assert len(packet["topSources"]) == 20, "preview stays a 20-item preview"
        assert packet["sourceCount"] == 36, "the COUNT must not inherit the cap"

    def test_preview_length_and_count_are_independent_numbers(self):
        """Reading one as the other is the defect; they must diverge here."""
        packet = build_thread_packet(_rows([f"outlet{i}.com" for i in range(25)]))
        assert len(packet["topSources"]) != packet["sourceCount"]

    def test_distinct_not_row_count(self):
        """Five receipts from two outlets is two sources, not five."""
        packet = build_thread_packet(
            _rows(["a.com", "a.com", "b.com", "a.com", "b.com"])
        )
        assert packet["sourceCount"] == 2

    def test_below_the_cap_count_and_preview_agree(self):
        """No regression for the ordinary case that was already correct."""
        packet = build_thread_packet(_rows(["a.com", "b.com", "c.com"]))
        assert packet["sourceCount"] == 3
        assert len(packet["topSources"]) == 3


class TestSampleSizeMakesTheBasisReadable:
    def test_sample_size_is_the_receipts_counted_over(self):
        """'36 sources' is only honest beside 'across 37 receipts'."""
        packet = build_thread_packet(_rows([f"o{i}.com" for i in range(37)]))
        assert packet["sourceSampleSize"] == 37

    def test_sample_size_counts_rows_not_distinct_sources(self):
        packet = build_thread_packet(_rows(["a.com", "a.com", "b.com"]))
        assert packet["sourceSampleSize"] == 3
        assert packet["sourceCount"] == 2


class TestAbsenceIsHonest:
    def test_no_receipts_serves_none_not_zero(self):
        """A 0 claims 'no outlets cover this'; we measured nothing at all."""
        packet = build_thread_packet([])
        assert packet["sourceCount"] is None
        assert packet["sourceSampleSize"] == 0

    def test_receipts_with_no_source_name_serve_zero_not_none(self):
        """Here we DID look at receipts and none were attributable — a real 0."""
        packet = build_thread_packet(_rows(["", "", ""]))
        assert packet["sourceSampleSize"] == 3
        assert packet["sourceCount"] == 0
