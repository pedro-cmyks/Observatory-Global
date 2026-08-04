"""Durable receipt snapshots (mig 097, 2026-08-04).

The 7-day signals_v2 hot retention deletes rows that
emergent_clusters.sample_signal_ids keeps referencing, so aged stories'
receipt lanes starve (dt-8057: 11 persisted ids -> 1 alive; made HONEST by
e55cb08e). These tests freeze the durability half:

 * the snapshot writer captures ``sample_receipts`` [{id,h,u,src,cc,ts}] in
   the SAME insert, from the in-memory rows already in hand, aligned 1:1
   with ``sample_signal_ids`` and capped identically (idxs == top-K set);
 * the backfill builds receipts for the LIVE subset only (dead ids are
   honest loss), order-preserving, deduped, and is idempotent by predicate
   (``sample_receipts IS NULL`` — processed rows, including all-dead ``[]``
   markers, never re-enter the queue).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("hdbscan")
pytest.importorskip("asyncpg")

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.scripts.backfill_sample_receipts import (  # noqa: E402
    build_receipts_for_cluster,
)
from backend.scripts.snapshot_emergent_topics import (  # noqa: E402
    _INSERT_SNAPSHOT_SQL,
    _prepare_snapshot_rows,
    build_sample_receipts,
)


def _row(i: int, **over) -> dict:
    base = {
        "id": 1000 + i,
        "headline": f"Receipt fixture headline number {i} long enough to keep",
        "country_code": "PE",
        "source_name": f"outlet-{i}.example",
        "source_url": f"https://outlet-{i}.example/story-{i}",
        "timestamp": datetime(2026, 8, 3, 12, i % 60, tzinfo=timezone.utc),
    }
    base.update(over)
    return base


class TestBuildSampleReceipts:
    def test_shape_and_alignment(self):
        rows = [_row(i) for i in range(6)]
        out = json.loads(build_sample_receipts(rows, [4, 1]))
        assert [r["id"] for r in out] == [1004, 1001]
        r = out[0]
        assert set(r) == {"id", "h", "u", "src", "cc", "ts"}
        assert r["h"].startswith("Receipt fixture headline number 4")
        assert r["u"] == "https://outlet-4.example/story-4"
        assert r["src"] == "outlet-4.example"
        assert r["cc"] == "PE"
        # ts round-trips through fromisoformat (the serving parse).
        assert datetime.fromisoformat(r["ts"]) == rows[4]["timestamp"]

    def test_tolerates_missing_source_url_and_null_ts(self):
        rows = [{"id": 7, "headline": "H", "country_code": None,
                 "source_name": None, "timestamp": None}]
        out = json.loads(build_sample_receipts(rows, [0]))
        assert out == [{"id": 7, "h": "H", "u": None, "src": None,
                        "cc": None, "ts": None}]

    def test_empty_idxs_is_empty_array(self):
        assert json.loads(build_sample_receipts([], [])) == []


class TestPreparedRowsCarryReceipts:
    def test_receipts_ride_the_same_insert_aligned_with_sample_ids(self):
        rows = [_row(i) for i in range(8)]
        embs = np.eye(8, 16, dtype=np.float32)
        clusters = [{
            "cluster_id": 3,
            "raw_size": 8,
            "kept_size": 5,
            "cohesion": 0.95,
            "all_idxs": list(range(8)),
            "top_signal_idxs": [0, 3, 5],
        }]
        prepared = _prepare_snapshot_rows(
            snapshot_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
            window_hours=24,
            clusters=clusters,
            ds_labels=[{"label": "Fixture Story", "description": ""}],
            embs=embs,
            rows=rows,
            prior=[],
            gate_threshold=0.5,
        )
        assert len(prepared) == 1
        tup = prepared[0]
        # 17 columns: sample_receipts is the last, next to vendor_labels.
        assert len(tup) == 17
        assert _INSERT_SNAPSHOT_SQL.count("$17::jsonb") == 1
        assert "sample_receipts" in _INSERT_SNAPSHOT_SQL
        sample_ids = tup[11]
        receipts = json.loads(tup[16])
        assert [r["id"] for r in receipts] == sample_ids == [1000, 1003, 1005]
        for r in receipts:
            assert r["h"] and r["u"] and r["ts"]


class TestBackfillReceiptBuilder:
    def test_live_only_order_preserving_and_deduped(self):
        live = {1001: _row(1), 1004: _row(4)}
        out = build_receipts_for_cluster(
            [1004, 1002, 1001, 1004, 1003], live)
        # dead ids (1002, 1003) skipped — honest loss; dup 1004 served once;
        # persisted sample order preserved.
        assert [r["id"] for r in out] == [1004, 1001]
        assert out[0]["h"].startswith("Receipt fixture headline number 4")

    def test_all_dead_is_empty_list_not_none(self):
        # [] is the processed-nothing-recoverable marker (vs NULL = never
        # processed) — the resume predicate depends on the distinction.
        assert build_receipts_for_cluster([1, 2, 3], {}) == []

    def test_null_headline_rows_are_skipped(self):
        live = {5: {"id": 5, "headline": None, "source_url": "u",
                    "source_name": "s", "country_code": "CO",
                    "timestamp": None}}
        assert build_receipts_for_cluster([5], live) == []
