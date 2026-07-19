"""EXECUTE-1 (2026-07-19) — budget wiring inside run_scoped_snapshot.

Freezes the per-country wall-time budget contract against a fake conn:

- a too-expensive country is CAPPED to its newest-first fitting slice (the
  pull is (timestamp DESC, id DESC) and _clean_and_dedupe preserves order, so
  rows[:n_use] is exactly "the newest n_use deduped signals");
- stats/gate still receive the RAW e5 slice (whiten/budget never leak into
  scoring space — same invariant test_scoped_whiten.py freezes);
- a hard clustering timeout retries ONCE at half size, then raises
  CountryTimeGap (an honest time-gap, never an infinite night);
- an unaffordable country raises CountryDeferred (first-fit deferral) without
  burning the generic 3-attempt retry loop.

NOTE: run_scoped_snapshot imports emergent_poc which imports hdbscan at module
level — these tests run in the M1 mlvenv (which has hdbscan) and skip cleanly
in the API .venv.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("hdbscan")
pytest.importorskip("asyncpg")

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import backend.scripts.run_scoped_snapshot as rss  # noqa: E402
from backend.scripts.cluster_subproc import ClusterTimeout  # noqa: E402
from backend.scripts.snapshot_budget import (  # noqa: E402
    BudgetContext,
    CountryDeferred,
    CountryTimeGap,
    RateEstimator,
)


class _FakeConn:
    """One short (full-corpus) page — the keyset loop stops after one fetch."""

    def __init__(self, recs):
        self._recs = recs

    async def fetch(self, *_args):
        return self._recs


def _fake_records(n: int = 12, dim: int = 16):
    rng = np.random.default_rng(19)
    embs = rng.standard_normal((n, dim)).astype(np.float32)
    embs /= np.linalg.norm(embs, axis=1, keepdims=True)
    recs = []
    for i in range(n):
        recs.append({
            "id": i + 1,  # pull order == newest-first (id 1 is the newest row)
            "headline": f"Distinct budget-wiring fixture headline number {i} here",
            "country_code": "US",
            "source_name": f"src-{i}",
            "timestamp": None,
            "emb": [float(v) for v in embs[i]],
        })
    return recs, embs


def _ctx(*, country_budget_s=0.00128, remaining_run_s=1000.0,
         min_cluster_n=2, subproc_min_n=0) -> BudgetContext:
    # RateEstimator clamps to MIN_RATE (30k n²/s) — pick a budget whose
    # fit_cap at the clamped rate is 6: int(sqrt(0.00128 × 30000)) == 6.
    return BudgetContext(
        country_budget_s=country_budget_s,
        remaining_run_s=remaining_run_s,
        rate=RateEstimator(initial=30_000.0),
        min_cluster_n=min_cluster_n,
        subproc_min_n=subproc_min_n,
    )


def _patch_pipeline(monkeypatch, seen):
    def fake_cluster(embs, mcs, ms, sel):
        seen["cluster_input"] = embs
        return np.zeros(len(embs), dtype=int)

    def fake_stats(labels, embs, rows, top_k):
        seen["stats_embs"] = embs
        seen["stats_rows"] = rows
        return [{"cluster_id": 0, "top_signal_idxs": [0]}]

    def fake_gate(clusters, embs, gate, min_kept, top_k):
        seen["gate_embs"] = embs
        return clusters

    monkeypatch.setattr(rss, "_cluster", fake_cluster)
    monkeypatch.setattr(rss, "_cluster_stats", fake_stats)
    monkeypatch.setattr(rss, "_apply_gate", fake_gate)


def _run(conn, budget, report=None):
    return asyncio.run(rss._country_clusters(
        conn, "US", 168, 0, 3, 2, gate={}, min_kept=1, top_n=0,
        whiten_k=0, budget=budget, report=report))


def test_expensive_country_capped_to_newest_fitting_slice(monkeypatch):
    recs, _ = _fake_records(n=12)
    seen: dict = {}
    _patch_pipeline(monkeypatch, seen)
    report: dict = {}
    # fit_cap(0.00128s × 30k n²/s) = 6 → newest 6 of 12
    res = _run(_FakeConn(recs), _ctx(), report=report)
    assert res is not None
    _clusters, embs_out, rows = res
    assert [r["id"] for r in rows] == [1, 2, 3, 4, 5, 6]  # newest-first slice
    assert len(seen["cluster_input"]) == 6
    assert seen["stats_embs"] is embs_out  # raw slice feeds stats/gate
    assert seen["gate_embs"] is embs_out
    assert len(embs_out) == 6
    assert report["capped"] is True and report["n_eff"] == 12 and report["n_use"] == 6


def test_no_budget_is_legacy_uncapped(monkeypatch):
    recs, _ = _fake_records(n=12)
    seen: dict = {}
    _patch_pipeline(monkeypatch, seen)
    res = _run(_FakeConn(recs), budget=None)
    assert res is not None
    _clusters, embs_out, rows = res
    assert len(rows) == 12 and len(embs_out) == 12
    assert len(seen["cluster_input"]) == 12


def test_unaffordable_country_raises_deferred(monkeypatch):
    recs, _ = _fake_records(n=12)
    _patch_pipeline(monkeypatch, {})
    with pytest.raises(CountryDeferred):
        _run(_FakeConn(recs), _ctx(remaining_run_s=0.0))


def test_cluster_timeout_halves_once_then_time_gap(monkeypatch):
    recs, _ = _fake_records(n=12)
    seen: dict = {}
    _patch_pipeline(monkeypatch, seen)
    calls: list[int] = []

    def always_timeout(embs, mcs, ms, sel, timeout_s):
        calls.append(len(embs))
        raise ClusterTimeout("too slow")

    monkeypatch.setattr(rss, "run_cluster_in_subprocess", always_timeout)
    with pytest.raises(CountryTimeGap):
        _run(_FakeConn(recs), _ctx(subproc_min_n=1))
    assert calls == [6, 3]  # capped attempt, then ONE halved retry, then gap


def test_cluster_timeout_then_halved_success(monkeypatch):
    recs, _ = _fake_records(n=12)
    seen: dict = {}
    _patch_pipeline(monkeypatch, seen)
    calls: list[int] = []

    def timeout_once(embs, mcs, ms, sel, timeout_s):
        calls.append(len(embs))
        if len(calls) == 1:
            raise ClusterTimeout("too slow")
        return np.zeros(len(embs), dtype=int)

    monkeypatch.setattr(rss, "run_cluster_in_subprocess", timeout_once)
    report: dict = {}
    res = _run(_FakeConn(recs), _ctx(subproc_min_n=1), report=report)
    assert res is not None
    _clusters, embs_out, rows = res
    assert calls == [6, 3]
    assert [r["id"] for r in rows] == [1, 2, 3]  # halved slice, still newest
    assert len(embs_out) == 3
    assert seen["stats_rows"] is rows
    assert report["halved"] is True


def test_env_knob_parsers_are_garbage_tolerant(monkeypatch):
    monkeypatch.setenv("ATLAS_SNAPSHOT_COUNTRY_BUDGET_S", "banana")
    assert rss._env_float("ATLAS_SNAPSHOT_COUNTRY_BUDGET_S", 1800.0) == 1800.0
    monkeypatch.setenv("ATLAS_SNAPSHOT_COUNTRY_BUDGET_S", "0")
    assert rss._env_float("ATLAS_SNAPSHOT_COUNTRY_BUDGET_S", 1800.0) == 0.0
    monkeypatch.delenv("ATLAS_SNAPSHOT_COUNTRY_BUDGET_S", raising=False)
    assert rss._env_float("ATLAS_SNAPSHOT_COUNTRY_BUDGET_S", 1800.0) == 1800.0
