"""Receipt-prune policy (2026-08-04) — bounded growth for mig 097.

emergent_clusters never prunes rows (identity history: dynamic_topic_members
references them), and 55fb4639 added ``sample_receipts`` jsonb that grows
every night. These tests freeze the PRUNE POLICY, which is reference-state
based, never age-of-cluster based, because the census measured active topics
referencing member clusters back to 2026-05-31 — age-based NULLing would
destroy reachable receipts of exactly the long-running stories durable
receipts exist for:

 * receipts are NULLed only when NO referencing topic keeps them alive —
   a topic keeps its clusters' receipts while it is non-retired (active or
   candidate: one promotion from serving), while its retirement is younger
   than the horizon (revival wants receipts), or while its retirement time
   is unknown (NULL last_state_change -> conservative keep);
 * clusters referenced by no topic at all have no serving path (binding
   happens only at snapshot time) and prune once older than the horizon;
 * the horizon has a hard floor so a fat-fingered --horizon-days can never
   gut the revival window.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.scripts.prune_sample_receipts import (  # noqa: E402
    HORIZON_FLOOR_DAYS,
    build_select_sql,
    chunked,
    ledger_entry,
    summarize,
    validate_horizon,
)


class TestValidateHorizon:
    def test_default_horizon_passes(self):
        assert validate_horizon(90) == 90

    def test_floor_is_inclusive(self):
        assert validate_horizon(HORIZON_FLOOR_DAYS) == HORIZON_FLOOR_DAYS

    def test_below_floor_raises(self):
        with pytest.raises(ValueError):
            validate_horizon(HORIZON_FLOOR_DAYS - 1)

    def test_zero_and_negative_raise(self):
        with pytest.raises(ValueError):
            validate_horizon(0)
        with pytest.raises(ValueError):
            validate_horizon(-30)


class TestSummarize:
    def test_mixed_rows(self):
        rows = [
            {"bytes": 100, "referenced": True},
            {"bytes": 50, "referenced": False},
            {"bytes": 25, "referenced": True},
        ]
        out = summarize(rows)
        assert out["clusters"] == 3
        assert out["bytes"] == 175
        assert out["by_reason"]["retired_only"] == {"clusters": 2, "bytes": 125}
        assert out["by_reason"]["unreferenced"] == {"clusters": 1, "bytes": 50}

    def test_empty_rows_report_zeros_with_both_reasons(self):
        out = summarize([])
        assert out["clusters"] == 0
        assert out["bytes"] == 0
        assert out["by_reason"]["retired_only"] == {"clusters": 0, "bytes": 0}
        assert out["by_reason"]["unreferenced"] == {"clusters": 0, "bytes": 0}

    def test_null_bytes_count_as_zero(self):
        out = summarize([{"bytes": None, "referenced": False}])
        assert out["clusters"] == 1
        assert out["bytes"] == 0


class TestLedgerEntry:
    def test_entry_preserves_restorable_payload(self):
        at = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
        snap = datetime(2026, 4, 1, 3, 30, tzinfo=timezone.utc)
        receipts = [{"id": 7, "h": "headline", "u": "https://x", "src": "s",
                     "cc": "CO", "ts": "2026-04-01T03:00:00+00:00"}]
        entry = ledger_entry(
            cluster_id=42,
            snapshot_at=snap,
            receipts_text=json.dumps(receipts),
            at=at,
        )
        assert entry["cluster_id"] == 42
        assert entry["snapshot_at"] == snap.isoformat()
        assert entry["at"] == at.isoformat()
        # restore path: UPDATE ... SET sample_receipts = entry["receipts"]::jsonb
        assert entry["receipts"] == receipts
        # a ledger line must be a single JSON document
        assert json.loads(json.dumps(entry)) == entry

    def test_null_receipts_text_becomes_empty_list(self):
        entry = ledger_entry(
            cluster_id=1,
            snapshot_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            receipts_text=None,
            at=datetime(2026, 8, 4, tzinfo=timezone.utc),
        )
        assert entry["receipts"] == []


class TestSelectSql:
    """Freeze the policy predicate — the keep-guards ARE the design."""

    def test_only_stamped_rows_are_candidates(self):
        sql = build_select_sql(include_receipts=False)
        assert "sample_receipts IS NOT NULL" in sql

    def test_cluster_age_guard_present(self):
        sql = build_select_sql(include_receipts=False)
        assert "snapshot_at < now() - ($1 || ' days')::interval" in sql

    def test_keep_guards_survive(self):
        """Non-retired ref, young retirement, or unknown retirement time
        each block the prune (the NOT EXISTS anti-join)."""
        sql = build_select_sql(include_receipts=False)
        assert "NOT EXISTS" in sql
        assert "dt.state <> 'retired'" in sql
        assert "dt.last_state_change IS NULL" in sql
        assert "dt.last_state_change >= now() - ($1 || ' days')::interval" in sql

    def test_receipts_payload_only_fetched_for_execute(self):
        dry = build_select_sql(include_receipts=False)
        wet = build_select_sql(include_receipts=True)
        assert "sample_receipts::text" not in dry  # dry-run never pulls payloads
        assert "ec.sample_receipts::text AS receipts_text" in wet

    def test_reason_flag_selected(self):
        sql = build_select_sql(include_receipts=False)
        assert "AS referenced" in sql


class TestChunked:
    def test_chunks_evenly_with_remainder(self):
        assert list(chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]

    def test_empty(self):
        assert list(chunked([], 3)) == []
