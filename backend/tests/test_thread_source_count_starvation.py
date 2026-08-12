"""The "116 SIGNALS · 0 sources" class (cold-user probe 2026-08-12).

The Brief served `Russian Air Defense Shoots Down Ukrainian Drones — 116
SIGNALS · 0 sources` with no receipts at all. Traced in prod
(`dynamic-topic-12138`): the two numbers ride DIFFERENT lineages in
``assemble_dynamic_thread`` —

  * ``signal_count`` = ``recent_n_signals``, a persisted per-snapshot count;
  * ``source_count`` = ``len(sources)``, derived from the receipt sample that
    ``sample_signal_ids`` resolves to in live ``signals_v2``.

The list SQL sliced that sample with ``ARRAY(SELECT DISTINCT sid ... LIMIT 24)``
and **no ORDER BY**, so the 24 ids were an arbitrary slice of the topic's ~111.
Measured on prod 2026-08-12: 80 of 12138's 111 sample ids were still live, but
all 24 the unordered slice picked had been deleted by the 7-day hot retention →
zero receipts resolved → ``source_count`` 0 while the count survived.

DECISION — the SEALED edition is NOT the lane at fault, and needs no change.
``fetch_daily_publication`` computes ``receipt_eligible_ids = set(by_topic) &
fit_accepted_ids`` and passes it to ``select_daily_edition``, which SKIPS any
candidate outside that set (daily_edition.py: ``if receipt_eligible_ids is not
None and candidate.thread_id not in receipt_eligible_ids: continue``). A
receipt-less thread therefore cannot be sealed, and
``test_daily_edition.test_receipt_eligibility_can_fill_layout_without_claiming_absence_for_unchecked_rows``
already freezes that. Verified on the live 2026-08-11 artifact: all 12 sealed
story nodes carried ≥4 receipts. The probe's Brief was on the LIVE fallback
(that edition sealed ``status: degraded``), which is the path fixed here.

Two guards here:
  1. the slice is ordered newest-first (``signals_v2.id`` is monotonic, and
     retention deletes the oldest), so a live id is preferred by construction;
  2. even so, a starved sample never gets to *assert* a source count — the row
     carries ``source_count_measured: False`` so no surface can print "0
     sources" as a measurement.
"""

from __future__ import annotations

from app.services.thread_intelligence import (
    _DYNAMIC_TOPICS_SELECT,
    _DYNAMIC_TOPICS_COUNTRY_SQL,
    assemble_dynamic_thread,
    assemble_emergent_thread,
)


def _sample_slice(sql: str) -> str:
    """The ARRAY(...) sample_signal_ids subquery, isolated from the full SELECT.

    `--` comment lines are stripped: the fix documents itself in SQL comments
    that quote the clauses, and an assertion must read the executed statement,
    not the prose about it.
    """
    marker = "unnest(COALESCE(ec3.sample_signal_ids"
    start = sql.index(marker)
    end = sql.index("AS sample_signal_ids", start)
    block = sql[start:end]
    return "\n".join(
        line for line in block.splitlines() if not line.strip().startswith("--")
    )


def test_dynamic_list_sql_orders_the_sample_slice_before_limiting():
    # Without ORDER BY, `DISTINCT sid ... LIMIT 24` returns an arbitrary 24 of
    # the topic's ids — and it landed on 24 retention-dead ones in prod.
    block = _sample_slice(_DYNAMIC_TOPICS_SELECT)
    assert "ORDER BY sid DESC" in block
    assert block.index("ORDER BY sid DESC") < block.index("LIMIT")


def test_country_list_sql_orders_the_sample_slice_too():
    # The country view hydrates receipts through its own copy of the block;
    # fixing only the global SQL would leave every country edition exposed.
    block = _sample_slice(_DYNAMIC_TOPICS_COUNTRY_SQL)
    assert "ORDER BY sid DESC" in block
    assert block.index("ORDER BY sid DESC") < block.index("LIMIT")


def _topic_row(**over) -> dict:
    row = {
        "id": 12138,
        "identity_key": "dyn-12138",
        "label": "Russian Air Defense Shoots Down Ukrainian Drones",
        "recent_n_signals": 116,
        "agg_n_signals": 2846,
        "changed_10h": 4,
        "noise_rate": 0.2,
        "mean_cohesion": 0.5,
        "first_seen": None,
        "top_country_codes": ["RU", "UA"],
    }
    row.update(over)
    return row


def _sample(idx: int, source: str | None = "ria.ru") -> dict:
    return {
        "id": idx,
        "headline": f"Air defence downed {idx} drones overnight",
        "source_name": source,
        "source_url": f"https://ria.ru/{idx}",
        "country_code": "RU",
    }


def test_starved_sample_never_asserts_a_measured_source_count():
    thread = assemble_dynamic_thread(_topic_row(), [])
    # The count lineage survives, honestly.
    assert thread["signal_count"] == 116
    assert thread["evidence_samples"] == []
    # ...but the source lane could not answer, and says so.
    assert thread["source_count_measured"] is False
    assert thread["source_count"] == 0


def test_resolved_sample_reports_a_measured_source_count():
    thread = assemble_dynamic_thread(
        _topic_row(), [_sample(1, "ria.ru"), _sample(2, "tass.ru"), _sample(3, "ria.ru")],
    )
    assert thread["source_count"] == 2
    assert thread["source_count_measured"] is True


def test_receipts_without_an_outlet_name_are_measured_but_zero():
    # A distinct failure from starvation: receipts DID resolve, they simply
    # carry no outlet to count. The surface must be able to tell them apart.
    thread = assemble_dynamic_thread(_topic_row(), [_sample(1, None), _sample(2, "")])
    assert thread["source_count"] == 0
    assert thread["source_count_measured"] is True


def test_emergent_path_carries_the_same_flag():
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
    starved = assemble_emergent_thread(cluster, [])
    assert starved["source_count_measured"] is False
    served = assemble_emergent_thread(cluster, [_sample(1, "ria.ru")])
    assert served["source_count_measured"] is True
