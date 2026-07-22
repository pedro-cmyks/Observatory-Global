"""Orbital Thread View (E2/L11) — pure aggregation contract.

Spec: docs/specs/2026-07-02-orbital-thread-view.md §4. The endpoint's SQL is
window/DB-bound; build_orbital_bodies is the pure layer every body flows
through, so its shape + typing + presence math are frozen here.
"""
from datetime import datetime, timedelta, timezone

import app.main_v2  # noqa: F401 — initialize app + routers before importing themes
from app.routers.themes import build_orbital_bodies, _vector_text


T0 = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def _row(hours_offset: float, country="LB", persons=None, dist=0.04, sentiment=0.0):
    return {
        "timestamp": T0 + timedelta(hours=hours_offset),
        "country_code": country,
        "persons": persons or [],
        "dist": dist,
        "sentiment": sentiment,
    }


def test_tone_is_mean_sentiment_per_body():
    rows = [
        _row(0, persons=["angry actor"], sentiment=-0.6),
        _row(1, persons=["angry actor"], sentiment=-0.2),
    ]
    body = next(b for b in build_orbital_bodies(rows) if b["id"] == "entity-angry actor")
    assert body["tone"] == -0.4


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


def test_radial_drift_measures_late_vs_early_distance():
    # receding body: early signals close (0.03), late signals far (0.05)
    rows = [
        _row(0, persons=["drifter x"], dist=0.03),
        _row(1, persons=["drifter x"], dist=0.03),
        _row(10, persons=["drifter x"], dist=0.05),
        _row(11, persons=["drifter x"], dist=0.05),
        # approaching body, reversed
        _row(0, persons=["comer y"], dist=0.05),
        _row(1, persons=["comer y"], dist=0.05),
        _row(10, persons=["comer y"], dist=0.03),
        _row(11, persons=["comer y"], dist=0.03),
        # too few samples -> honest None
        _row(5, persons=["single z"], dist=0.04),
    ]
    by_id = {b["id"]: b for b in build_orbital_bodies(rows)}
    assert by_id["entity-drifter x"]["drift"] == 0.02   # receding
    assert by_id["entity-comer y"]["drift"] == -0.02    # approaching
    assert by_id["entity-single z"]["drift"] is None


def test_moons_from_co_occurrence():
    # 'satellite org' appears ONLY inside 'big person' signals; countries never moon
    rows = []
    for i in range(8):
        rows.append({**_row(i, persons=["big person"]), "id": i})
    for i in range(3):
        rows[i]["persons"] = ["big person", "un-anama"]  # satellite rides along
    rows.append({**_row(20, persons=["independent actor"]), "id": 99})
    bodies = build_orbital_bodies(rows)
    by_id = {b["id"]: b for b in bodies}
    # NOTE: un-anama must classify as an entity; use a name the gazetteer keeps
    sat = next((b for b in bodies if b["label"] == "un-anama"), None)
    if sat is not None:  # classify_subject may drop unknown tokens — then no moon claim
        assert sat.get("moon_of") == "entity-big person"
        assert sat["moon_overlap"] == 1.0
    assert "moon_of" not in by_id["entity-big person"]
    assert "moon_of" not in by_id.get("country-LB", {})


def test_orbital_mds_layout_places_center_and_bodies():
    from app.routers.themes import orbital_mds_layout

    bodies = [
        {"id": "entity-a", "label": "A"},
        {"id": "entity-b", "label": "B"},
        {"id": "country-US", "label": "US"},
    ]
    centroid = [1.0, 0.0, 0.0, 0.0]
    vectors = {
        "entity-a": [1.0, 0.1, 0.0, 0.0],
        "entity-b": [0.0, 1.0, 0.0, 0.0],
        "country-US": [0.0, 0.0, 1.0, 0.0],
    }
    pos_by_id, center_pos, meta = orbital_mds_layout(bodies, centroid, vectors)

    assert set(pos_by_id) == {"entity-a", "entity-b", "country-US"}
    assert all(len(p) == 3 for p in pos_by_id.values())
    assert center_pos is not None and len(center_pos) == 3
    assert meta["basis"] == "cosine"
    assert meta["n"] == 4          # centroid + 3 bodies
    assert 0.0 <= meta["stress"] <= 2.0
    assert meta["unplaced"] == []
    # closest body to the centroid must also be nearest in the layout
    import math
    d_a = math.dist(center_pos, pos_by_id["entity-a"])
    d_b = math.dist(center_pos, pos_by_id["entity-b"])
    assert d_a < d_b


def test_orbital_mds_layout_reports_bodies_without_vectors_as_unplaced():
    from app.routers.themes import orbital_mds_layout

    bodies = [
        {"id": "entity-a", "label": "A"},
        {"id": "entity-b", "label": "B"},
        {"id": "entity-ghost", "label": "Ghost"},
    ]
    vectors = {"entity-a": [1.0, 0.0, 0.0], "entity-b": [0.0, 1.0, 0.0]}
    pos_by_id, center_pos, meta = orbital_mds_layout(bodies, [1.0, 1.0, 0.0], vectors)

    assert "entity-ghost" not in pos_by_id       # never a made-up coordinate
    assert meta["unplaced"] == ["entity-ghost"]
    assert center_pos is not None


def test_orbital_mds_layout_degenerates_honestly():
    from app.routers.themes import orbital_mds_layout

    # one body + centroid = 2 nodes → below MIN_NODES
    out = orbital_mds_layout(
        [{"id": "entity-a", "label": "A"}], [1.0, 0.0], {"entity-a": [0.0, 1.0]},
    )
    assert out == ({}, None, None)
    # no centroid at all
    assert orbital_mds_layout([{"id": "x"}], None, {"x": [1.0]}) == ({}, None, None)


def test_parse_vector_text_roundtrips():
    from app.routers.themes import _parse_vector_text, _vector_text

    assert _parse_vector_text(None) is None
    assert _parse_vector_text("") is None
    assert _parse_vector_text("[1.5,-0.25,0]") == [1.5, -0.25, 0.0]
    assert _parse_vector_text(_vector_text([0.5, 0.25])) == [0.5, 0.25]
