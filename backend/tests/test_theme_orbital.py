"""Orbital Thread View (E2/L11) — pure aggregation contract.

Spec: docs/specs/2026-07-02-orbital-thread-view.md §4. The endpoint's SQL is
window/DB-bound; build_orbital_bodies is the pure layer every body flows
through, so its shape + typing + presence math are frozen here.
"""
from datetime import datetime, timedelta, timezone

import app.main_v2  # noqa: F401 — initialize app + routers before importing themes
from app.routers.themes import build_orbital_bodies, _vector_text


T0 = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def _row(hours_offset: float, country="LB", persons=None, dist=0.04):
    return {
        "timestamp": T0 + timedelta(hours=hours_offset),
        "country_code": country,
        "persons": persons or [],
        "dist": dist,
    }


def test_bodies_carry_type_presence_and_mean_distance():
    rows = [
        _row(0, persons=["benjamin netanyahu"], dist=0.03),
        _row(5, persons=["benjamin netanyahu"], dist=0.05),
        _row(10, persons=["joseph aoun"], dist=0.04),
    ]
    bodies = build_orbital_bodies(rows)
    by_id = {b["id"]: b for b in bodies}

    netanyahu = by_id["entity-benjamin netanyahu"]
    assert netanyahu["type"] == "person"
    assert netanyahu["n"] == 2
    assert netanyahu["dist"] == 0.04  # mean of 0.03/0.05
    assert netanyahu["first_seen"] == T0.isoformat()
    assert netanyahu["last_seen"] == (T0 + timedelta(hours=5)).isoformat()
    assert len(netanyahu["timestamps"]) == 2

    lb = by_id["country-LB"]
    assert lb["type"] == "country"
    assert lb["n"] == 3


def test_non_subjects_are_dropped_not_mistyped():
    # gazetteer non-persons (el niño = event) must not orbit as persons
    rows = [_row(0, persons=["el niño", "dar una patada"])]
    bodies = build_orbital_bodies(rows)
    types = {b["label"]: b["type"] for b in bodies if b["type"] != "country"}
    assert types.get("el niño") == "event"
    assert "dar una patada" not in types  # invalid person → dropped


def test_entity_cap_keeps_highest_volume():
    rows = []
    for i in range(30):
        rows.extend(_row(h, persons=[f"person alpha{i}"]) for h in range(i + 1))
    bodies = build_orbital_bodies(rows, max_entities=5)
    entity_bodies = [b for b in bodies if b["type"] != "country"]
    assert len(entity_bodies) <= 5
    assert all(b["n"] >= 26 for b in entity_bodies)


def test_vector_text_is_pgvector_input():
    assert _vector_text([0.5, -1.0]) == "[0.500000,-1.000000]"
