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
