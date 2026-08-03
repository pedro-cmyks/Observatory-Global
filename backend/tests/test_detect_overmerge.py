"""detect_overmerge script — pure helpers + import smoke (no DB, no LLM).

Guarantees the script module imports with only numpy present (asyncpg/httpx are
imported lazily inside the DB/judge paths) and freezes its small pure surface:
vector parsing, the sub-cluster actor set, representative selection, the run-id
format, and the relabel-ledger vague-blob cross-ref loader.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pytest

from scripts import detect_overmerge as dom


# ---------------------------------------------------------------- _parse_vec
def test_parse_vec_handles_bracket_and_brace_forms():
    assert np.allclose(dom._parse_vec("[0.1,0.2,0.3]"), [0.1, 0.2, 0.3])
    assert np.allclose(dom._parse_vec("{0.1,0.2,0.3}"), [0.1, 0.2, 0.3])


# ---------------------------------------------------------------- _member_actors
def test_member_actors_prefixes_country_and_persons():
    actors = dom._member_actors("ua", ["Zelensky", "Putin"])
    assert actors == {"c:UA", "p:zelensky", "p:putin"}


def test_member_actors_tolerates_missing():
    assert dom._member_actors(None, None) == set()
    assert dom._member_actors("PE", []) == {"c:PE"}
    assert dom._member_actors(None, ["  "]) == set()  # blank person dropped


def test_member_actors_country_and_person_never_collide():
    # prefixing means a country code can't be mistaken for a person token
    a = dom._member_actors("US", ["us"])
    assert a == {"c:US", "p:us"}


# ------------------------------------------------------------- _rep_indices
def test_rep_indices_returns_members_central_to_the_side():
    # side 0 = a tight blob at axis0; side 1 = a tight blob at axis1
    d = 16
    e0 = np.zeros(d); e0[0] = 1.0
    e1 = np.zeros(d); e1[1] = 1.0
    rng = np.random.default_rng(0)
    a = e0 + rng.normal(0, 0.01, size=(5, d))
    b = e1 + rng.normal(0, 0.01, size=(5, d))
    matn = dom.normalize_rows(np.vstack([a, b]))
    labels = np.array([0] * 5 + [1] * 5)
    reps0 = dom._rep_indices(matn, labels, 0, k=3)
    reps1 = dom._rep_indices(matn, labels, 1, k=3)
    assert len(reps0) == 3 and all(i < 5 for i in reps0)
    assert len(reps1) == 3 and all(i >= 5 for i in reps1)


def test_rep_indices_empty_side_is_empty():
    matn = dom.normalize_rows(np.eye(4))
    labels = np.array([0, 0, 0, 0])  # side 1 empty
    assert dom._rep_indices(matn, labels, 1) == []


# ---------------------------------------------------------------- run_id_for
def test_run_id_for_format():
    assert dom.run_id_for(42, dt.date(2026, 7, 20)) == "m4-20260720-s42"


# ---------------------------------------------------- vague-blob ledger loader
def test_load_vague_blob_ids_matches_fusion_labels(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join([
        '{"topic_id": 1, "old": "x", "new": "Mixed Local News: Floods, Drones"}',
        '{"topic_id": 2, "old": "x", "new": "Multiple Deadly Incidents Across Peru and Ukraine"}',
        '{"topic_id": 3, "old": "x", "new": "Spain tops Argentina in dominant display"}',
        'not json',
        '{"topic_id": 4, "old": "x", "new": "Diverse Local Incidents Across Regions"}',
    ]))
    monkeypatch.setattr(dom, "RELABEL_LEDGER", ledger)
    ids = dom._load_vague_blob_ids()
    assert ids == {1, 2, 4}  # 3 (a specific headline) is correctly excluded


def test_load_vague_blob_ids_missing_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(dom, "RELABEL_LEDGER", tmp_path / "nope.jsonl")
    assert dom._load_vague_blob_ids() == set()


# ── blob-veto stamping (2026-08-03 gate-(c) census) ──────────────────────────
def test_topics_sql_population_gated_by_blob_stamp_flag(monkeypatch):
    monkeypatch.setattr(dom, "BLOB_STAMP_ENABLED", True)
    sql = dom._topics_sql()
    assert "dt.state = 'active'" in sql
    assert "dt.revived_at IS NOT NULL" in sql  # revived stock joins the scan
    monkeypatch.setattr(dom, "BLOB_STAMP_ENABLED", False)
    sql = dom._topics_sql()
    assert "revived_at" not in sql  # legacy active-only scan


def test_evaluated_clean_requires_a_measured_verdict():
    keep_measured = {"verdict": dom.KEEP, "gap_ratio": 0.41,
                     "lane": dom.LANE_EMBEDDING, "reason": "no fusion signal"}
    keep_unmeasured = {"verdict": dom.KEEP, "gap_ratio": None,
                       "lane": dom.LANE_EMBEDDING,
                       "reason": "too few embedded members to split"}
    keep_country = {"verdict": dom.KEEP, "gap_ratio": None,
                    "lane": dom.LANE_COUNTRY,
                    "reason": "country-lane KEEP: not multimodal "
                              "(distinct 1, dominant 1.00)"}
    keep_country_thin = {"verdict": dom.KEEP, "gap_ratio": None,
                         "lane": dom.LANE_COUNTRY,
                         "reason": "country-lane KEEP: too few located members "
                                   "(2 < 5)"}
    assert dom._evaluated_clean(keep_measured) is True
    assert dom._evaluated_clean(keep_country) is True
    assert dom._evaluated_clean(keep_unmeasured) is False  # 2-means never ran
    assert dom._evaluated_clean(keep_country_thin) is False
    assert dom._evaluated_clean({"verdict": dom.DEMOTE, "gap_ratio": 0.9}) is False
    assert dom._evaluated_clean({"verdict": dom.BORDERLINE, "gap_ratio": 0.7}) is False


class _FakeConn:
    def __init__(self):
        self.calls: list[tuple[str, list[int]]] = []

    async def execute(self, sql, ids):
        self.calls.append((sql, list(ids)))
        return f"UPDATE {len(ids)}"


def test_write_blob_stamps_stamps_confirmed_and_clears_clean():
    import asyncio
    artifact = {"topics": [
        {"topic_id": 1, "verdict": dom.DEMOTE, "gap_ratio": 0.9,
         "lane": dom.LANE_EMBEDDING, "reason": "fusion"},
        {"topic_id": 2, "verdict": dom.KEEP, "gap_ratio": 0.4,
         "lane": dom.LANE_EMBEDDING, "reason": "clean"},
        {"topic_id": 3, "verdict": dom.KEEP, "gap_ratio": None,
         "lane": dom.LANE_EMBEDDING,
         "reason": "too few embedded members to split"},
        {"topic_id": 4, "verdict": dom.BORDERLINE, "gap_ratio": 0.7,
         "lane": dom.LANE_EMBEDDING, "reason": "judge not run"},
    ]}
    demote = [artifact["topics"][0]]
    conn = _FakeConn()
    asyncio.run(dom._write_blob_stamps(conn, artifact, demote))
    assert len(conn.calls) == 2
    stamp_sql, stamp_ids = conn.calls[0]
    clear_sql, clear_ids = conn.calls[1]
    assert "blob_confirmed_at=NOW()" in stamp_sql and stamp_ids == [1]
    # 3 was unevaluable and 4 unresolved: neither may clear a prior stamp
    assert "blob_confirmed_at=NULL" in clear_sql and clear_ids == [2]


def test_write_blob_stamps_no_ops_on_empty_sets():
    import asyncio
    artifact = {"topics": [
        {"topic_id": 3, "verdict": dom.KEEP, "gap_ratio": None,
         "lane": dom.LANE_EMBEDDING,
         "reason": "too few embedded members to split"},
    ]}
    conn = _FakeConn()
    asyncio.run(dom._write_blob_stamps(conn, artifact, []))
    assert conn.calls == []  # no empty ANY() statements
