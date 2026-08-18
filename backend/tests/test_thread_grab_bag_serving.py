"""Live /threads rows carry the grab-bag coherence mark (#257 serving half).

`measure_subject_geography_coherence` (contract atlas-subject-coherence-v1)
ran only at seal time (investigation_graph / daily_publication), so the live
Brief and console could not mark a mixed-geography story until the nightly
seal — the frontend join (lib/cardWarnings.ts) documents the payload hole.

MEASURED 2026-08-18 before choosing the lane: running the measurement inline
in `assemble_dynamic_thread` costs ~3.4 ms/row (24 receipts; the full
_COUNTRY_PATTERNS + _NATIVE_COUNTRY_PATTERNS regex tables per headline, no
cache) = ~137 ms median on a 40-row /threads list — ~2.7x the 50 ms serving
budget. So the measurement runs OFF-REQUEST
(scripts/compute_subject_coherence.py -> dynamic_topic_subject_coherence,
mig 102) and serving is a pure guarded read. These tests freeze the contract:

  * a stored grab_bag measurement marks the row  -> subject_geography_grab_bag=True
  * a stored coherent / single-dominant one      -> False (measured, not flagged)
  * NO stored measurement                        -> None — never false-by-default
  * stored status no_subject_geography_signal    -> None (nothing was measurable)
  * a missing table (mig 102 unapplied)          -> {} from the fetch = all-None
    rows, never a 500 (the mig-087 crash class, avoided by construction)
"""

from __future__ import annotations

import inspect
import json

import pytest

from app.services.subject_geography import measure_subject_geography_coherence
from app.services import thread_intelligence
from app.services.thread_intelligence import (
    _fetch_subject_coherence_map,
    _grab_bag_flag,
    assemble_dynamic_thread,
)


def _topic_row(topic_id: int = 7, label: str = "Wildfires in France and Spain") -> dict:
    return {
        "id": topic_id,
        "identity_key": f"dyn-{topic_id}",
        "label": label,
        "agg_n_signals": 6,
        "changed_10h": 2,
        "noise_rate": None,
        "mean_cohesion": 0.55,
        "first_seen": None,
        "top_country_codes": ["FR", "ES"],
    }


def _receipt(i: int, headline: str) -> dict:
    return {
        "id": i,
        "headline": headline,
        "source_name": f"Outlet {i}",
        "source_url": f"https://o{i}.example/a",
        "country_code": "FR",
        "nlp_places": None,
    }


# Known-good fixtures (same patterns test_geo_tagging_native freezes): the
# disjoint set bundles a Belgium heatwave with a France budget story — the
# #257 grab-bag failure mode; the coherent set is one story whose countries
# co-occur in every receipt.
DISJOINT_HEADLINES = [
    "Heatwave grips Belgium as Brussels issues alert",
    "Belgium swelters as Brussels breaks records",
    "Belgique en canicule cette semaine",
    "France debates budget in Paris",
    "Paris braces as France reviews spending",
    "France budget vote looms in Paris",
]

COHERENT_HEADLINES = [
    "Israel warns US of Iranian plot to assassinate Trump",
    "US and Israel brief allies on Iran assassination plot",
    "Iran denies Israel-US claims of a Trump plot",
]


# ── The end-to-end chain: measurement -> stored result -> served row ──────────

def test_disjoint_multi_geography_receipts_mark_the_row():
    receipts = [{"headline": h} for h in DISJOINT_HEADLINES]
    stored = measure_subject_geography_coherence(receipts)
    assert stored["grab_bag"] is True  # precondition, frozen elsewhere too

    thread = assemble_dynamic_thread(
        _topic_row(),
        [_receipt(i, h) for i, h in enumerate(DISJOINT_HEADLINES)],
        subject_coherence=stored,
    )
    assert thread["subject_geography_grab_bag"] is True


def test_coherent_multi_country_receipts_do_not_mark_the_row():
    receipts = [{"headline": h} for h in COHERENT_HEADLINES]
    stored = measure_subject_geography_coherence(receipts)
    assert stored["grab_bag"] is False

    thread = assemble_dynamic_thread(
        _topic_row(label="Iran Assassination Plot Claims"),
        [_receipt(i, h) for i, h in enumerate(COHERENT_HEADLINES)],
        subject_coherence=stored,
    )
    assert thread["subject_geography_grab_bag"] is False


def test_single_dominant_subject_is_measured_not_flagged():
    receipts = [
        {"headline": "Iran expands drought response as Tehran rations water"},
        {"headline": "Iran reservoirs fall to record lows"},
    ]
    stored = measure_subject_geography_coherence(receipts)
    assert stored["status"] == "single_dominant_subject"

    thread = assemble_dynamic_thread(
        _topic_row(label="Iran Water Crisis"),
        [_receipt(0, receipts[0]["headline"]), _receipt(1, receipts[1]["headline"])],
        subject_coherence=stored,
    )
    # A measured single-dominant story is definitionally not a grab-bag.
    assert thread["subject_geography_grab_bag"] is False


# ── Honest absence: null, never false-by-default ──────────────────────────────

def test_row_without_stored_measurement_serves_null():
    thread = assemble_dynamic_thread(
        _topic_row(),
        [_receipt(0, "France debates budget in Paris")],
    )
    assert "subject_geography_grab_bag" in thread
    assert thread["subject_geography_grab_bag"] is None


def test_no_signal_status_serves_null_not_false():
    # The measurement ran but found NO country evidence in any receipt: it
    # could not tell grab-bag from coherent, so serving False would be a claim
    # it never made.
    stored = measure_subject_geography_coherence(
        [{"headline": "Local council debates parking rules"}]
    )
    assert stored["status"] == "no_subject_geography_signal"
    assert _grab_bag_flag(stored) is None


def test_malformed_stored_value_serves_null():
    assert _grab_bag_flag(None) is None
    assert _grab_bag_flag("not json {") is None
    assert _grab_bag_flag({"status": "grab_bag"}) is None  # missing the bool
    assert _grab_bag_flag(42) is None


def test_stored_jsonb_arriving_as_string_is_parsed():
    # asyncpg returns JSONB as a JSON string unless a codec is set — the same
    # contract _as_list handles for nlp_places (test_thread_places_plumb).
    stored = json.dumps(
        measure_subject_geography_coherence(
            [{"headline": h} for h in DISJOINT_HEADLINES]
        )
    )
    assert _grab_bag_flag(stored) is True


# ── The guarded fetch: pure read, degraded to honest absence ─────────────────

class _FakeConn:
    def __init__(self, *, has_table: bool, rows: list[dict] | None = None,
                 raise_on_fetch: bool = False):
        self._has_table = has_table
        self._rows = rows or []
        self._raise = raise_on_fetch
        self.fetch_calls: list[tuple] = []

    async def fetchval(self, query, *args, **kwargs):
        assert "to_regclass" in query
        return self._has_table

    async def fetch(self, query, *args, **kwargs):
        if self._raise:
            raise RuntimeError("db down")
        self.fetch_calls.append((query, args))
        return list(self._rows)


@pytest.mark.asyncio
async def test_fetch_map_missing_table_returns_empty():
    # mig 102 not applied -> every row serves null; the thread lane never 500s.
    conn = _FakeConn(has_table=False)
    assert await _fetch_subject_coherence_map(conn, [1, 2]) == {}
    assert conn.fetch_calls == []


@pytest.mark.asyncio
async def test_fetch_map_returns_parsed_results_by_topic_id():
    stored = measure_subject_geography_coherence(
        [{"headline": h} for h in DISJOINT_HEADLINES]
    )
    conn = _FakeConn(
        has_table=True,
        rows=[{"topic_id": 9, "result": json.dumps(stored)}],
    )
    out = await _fetch_subject_coherence_map(conn, [9, 11])
    assert out[9]["grab_bag"] is True
    assert 11 not in out


@pytest.mark.asyncio
async def test_fetch_map_degrades_to_empty_on_db_error():
    conn = _FakeConn(has_table=True, raise_on_fetch=True)
    assert await _fetch_subject_coherence_map(conn, [1]) == {}


@pytest.mark.asyncio
async def test_fetch_map_empty_ids_skip_the_db():
    conn = _FakeConn(has_table=True)
    assert await _fetch_subject_coherence_map(conn, []) == {}
    assert conn.fetch_calls == []


# ── The off-request compute measures the SAME receipts the row renders ───────

def test_compute_script_mirrors_the_serving_sample_subquery():
    # scripts/compute_subject_coherence.py carries a copy of the list SELECT's
    # sample_signal_ids subquery (latest snapshot, DISTINCT, DESC-before-cut,
    # LIMIT 24). If serving changes its receipt population, this fails and the
    # script must follow — the stored mark must describe the rendered receipts.
    from scripts.compute_subject_coherence import _TOPICS_SQL

    def _norm(sql: str) -> str:
        return " ".join(
            line.split("--")[0].strip()
            for line in sql.splitlines()
            if line.split("--")[0].strip()
        )

    core = _norm(
        """
        SELECT DISTINCT sid
        FROM dynamic_topic_members dtm3
        JOIN emergent_clusters ec3 ON ec3.id = dtm3.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec3.sample_signal_ids, ARRAY[]::bigint[])) AS sid
        WHERE dtm3.dynamic_topic_id = dt.id
          AND dtm3.snapshot_at = (
              SELECT MAX(snapshot_at) FROM dynamic_topic_members
              WHERE dynamic_topic_id = dt.id
          )
        ORDER BY sid DESC
        LIMIT 24
        """
    )
    assert core in _norm(thread_intelligence._DYNAMIC_TOPICS_SELECT)
    assert core in _norm(_TOPICS_SQL)


def test_compute_script_build_receipts_skips_retention_holes():
    from scripts.compute_subject_coherence import build_receipts

    receipts = build_receipts(
        [3, 2, 1], {3: "France debates budget in Paris", 1: "Belgium swelters"}
    )
    assert receipts == [
        {"headline": "France debates budget in Paris"},
        {"headline": "Belgium swelters"},
    ]
    assert build_receipts([9], {}) == []


# ── Wiring: both live dynamic paths read the stored measurement ───────────────

def test_list_and_detail_paths_are_wired_to_the_stored_measurement():
    src = inspect.getsource(thread_intelligence)
    list_body = src[src.index("async def _fetch_dynamic_threads_with_conn("):]
    list_body = list_body[: list_body.index("\nasync def _fetch_emergent_threads_with_conn(")]
    assert "_fetch_subject_coherence_map(" in list_body
    assert "subject_coherence=" in list_body

    detail_body = src[src.index("async def _fetch_dynamic_thread_detail("):]
    detail_body = detail_body[: detail_body.index("\nasync def ")]
    assert "_fetch_subject_coherence_map(" in detail_body
    assert "subject_coherence=" in detail_body
