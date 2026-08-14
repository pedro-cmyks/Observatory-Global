"""The thread row's `source_count` saturates, and a merge leaves it stale.

Measured on prod 2026-08-14 (`/api/v2/threads?hours=168&limit=40`):

    dynamic-topic-13070   source_count 24   evidence_samples 88   distinct 84
    dynamic-topic-12674   source_count 24   evidence_samples 43   distinct 42

Two separate defects produce that 24.

(1) SATURATION. `assemble_dynamic_thread` counts distinct `source_name` over
    `sample_signals`, and those come from `_DYNAMIC_TOPICS_SELECT`'s
    `sample_signal_ids`, which is `... ORDER BY sid DESC LIMIT 24`. So the
    count cannot exceed 24 no matter how many outlets carry the story: it is a
    count over a display-sized receipt slice, served as if it were the story's
    outlet count. 58 of 3,263 active topics exceed that cap (measured).

(2) STALENESS AFTER MERGE. `dedupe_same_event_threads` folds cross-language
    duplicates and UNIONS their `evidence_samples` — but combines the counts
    with `max(keep, drop)`. Two rows with DISJOINT outlet sets of 24 and 17
    therefore serve 24 when the union they actually render carries up to 41.
    `max` is provably wrong for a distinct-count over a union, and the unioned
    evidence is sitting right there to be counted.

A true window-scoped distinct-source count was measured and REJECTED as
unaffordable for the list: over the 40 rows of one request, the correlated
`signals_v2` join ran 2,143ms and the set-based rewrite 1,185ms, against a list
query that already costs ~700-800ms; the `sample_receipts` jsonb lane (durable,
join-free) still cost 278ms and, being itself a per-cluster sample, would not
have produced a true total either. Every affordable number here is a count over
a RECEIPT SAMPLE, so the fix is to make that basis explicit and to stop the
number saturating below the receipts we actually serve.

Contract under test:
  * ``source_count``        distinct outlets among the receipts SERVED — after
                            a merge, recounted over the unioned evidence.
  * ``source_count_basis``  'receipt_sample' — never presentable as the total.
  * ``source_sample_size``  the receipt count it was measured over.
"""
from __future__ import annotations

from app.services.thread_intelligence import (
    _merge_event_pair,
    assemble_dynamic_thread,
)


def _topic_row(topic_id: int = 13070, recent: int = 91) -> dict:
    return {
        "id": topic_id,
        "label": "Colombia Earthquake Response",
        "category": "natural-disaster",
        "identity_key": f"u2-topic-{topic_id}",
        "agg_n_signals": 323,
        "recent_n_signals": recent,
        "count_window_hours": 168,
        "mean_cohesion": 0.95,
        "noise_rate": 0.05,
        "top_country_codes": ["CO"],
        "changed_10h": 4,
        "first_seen": None,
        "last_seen": None,
    }


def _signal(source_name: str, idx: int) -> dict:
    return {
        "id": 500 + idx,
        "headline": f"headline {idx}",
        "source_name": source_name,
        "source_url": f"https://{source_name}/a{idx}",
        "country_code": "CO",
        "timestamp": None,
        "nlp_sentiment": -0.4,
        "persons": [],
    }


def _thread(sources: list[str], topic_id: int = 13070) -> dict:
    signals = [_signal(s, i) for i, s in enumerate(sources)]
    return assemble_dynamic_thread(_topic_row(topic_id), signals)


class TestBasisIsStated:
    def test_basis_names_the_receipt_sample(self):
        """The number is a sample count; the row must say so."""
        assert _thread(["a.com", "b.com"])["source_count_basis"] == "receipt_sample"

    def test_sample_size_is_the_receipts_counted_over(self):
        thread = _thread(["a.com", "a.com", "b.com"])
        assert thread["source_sample_size"] == 3
        assert thread["source_count"] == 2

    def test_no_receipts_keeps_the_measured_flag_false(self):
        """Pre-existing contract: an unanswered lane is not a measured 0."""
        thread = _thread([])
        assert thread["source_count_measured"] is False
        assert thread["source_sample_size"] == 0


class TestMergeRecountsInsteadOfTakingMax:
    def test_disjoint_sources_sum_not_max(self):
        """The provable case: 3 + 2 disjoint outlets is 5, never max(3,2)."""
        keep = _thread(["a.com", "b.com", "c.com"], topic_id=1)
        drop = _thread(["d.com", "e.com"], topic_id=2)
        merged = _merge_event_pair(keep, drop)
        assert merged["source_count"] == 5

    def test_overlapping_sources_are_deduped_not_added(self):
        """Union semantics: shared outlets must not be counted twice."""
        keep = _thread(["a.com", "b.com"], topic_id=1)
        drop = _thread(["b.com", "c.com"], topic_id=2)
        merged = _merge_event_pair(keep, drop)
        assert merged["source_count"] == 3

    def test_count_matches_the_unioned_evidence_it_renders(self):
        """The dt-13070 class: the count must agree with the receipts shown."""
        keep = _thread([f"k{i}.com" for i in range(5)], topic_id=1)
        drop = _thread([f"d{i}.com" for i in range(4)], topic_id=2)
        merged = _merge_event_pair(keep, drop)
        rendered = {e["source"] for e in merged["evidence_samples"] if e.get("source")}
        assert merged["source_count"] == len(rendered)

    def test_sample_size_follows_the_union(self):
        keep = _thread(["a.com", "b.com"], topic_id=1)
        drop = _thread(["c.com"], topic_id=2)
        merged = _merge_event_pair(keep, drop)
        assert merged["source_sample_size"] == len(merged["evidence_samples"])

    def test_merge_without_evidence_falls_back_to_max_not_zero(self):
        """No receipts to recount over must not destroy the existing number."""
        keep = _thread([], topic_id=1)
        drop = _thread([], topic_id=2)
        keep["source_count"], drop["source_count"] = 7, 3
        merged = _merge_event_pair(keep, drop)
        assert merged["source_count"] == 7
