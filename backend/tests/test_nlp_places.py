"""NER places lane — project place-typed entities into nlp_places.

Places (GPE/LOC) are already extracted by the same NER pass that fills
nlp_persons; this lane projects them into their own JSONB column so the
serving layer (subject_geography.infer_receipt_subject_geography, method
"ner_place") can consume them without unpacking the mixed entity list.

Pure-helper tests only — no model loads (mirrors test_nlp_entity_types.py:
fake ents, never spaCy/transformers).
"""
from __future__ import annotations

from enrichment.nlp_pipeline import places_from_entities


def test_projects_only_place_types():
    entities = [
        {"name": "Lula", "type": "PERSON"},
        {"name": "Petrobras", "type": "ORG"},
        {"name": "Brazil", "type": "GPE"},
        {"name": "Amazon Basin", "type": "LOC"},
        {"name": "El Niño", "type": "EVENT"},
    ]
    assert places_from_entities(entities) == ["brazil", "amazon basin"]


def test_lowercases_and_strips():
    entities = [{"name": "  Bogotá ", "type": "GPE"}]
    assert places_from_entities(entities) == ["bogotá"]


def test_dedupes_case_insensitively_preserving_order():
    entities = [
        {"name": "Gaza", "type": "GPE"},
        {"name": "GAZA", "type": "LOC"},
        {"name": "Rafah", "type": "GPE"},
    ]
    assert places_from_entities(entities) == ["gaza", "rafah"]


def test_drops_one_and_two_char_tokens():
    entities = [
        {"name": "UK", "type": "GPE"},   # 2 chars — dropped by hygiene rule
        {"name": "X", "type": "LOC"},
        {"name": "Iran", "type": "GPE"},
    ]
    assert places_from_entities(entities) == ["iran"]


def test_caps_at_ten_places():
    entities = [{"name": f"City{i:02d}", "type": "GPE"} for i in range(15)]
    out = places_from_entities(entities)
    assert len(out) == 10
    assert out[0] == "city00"
    assert out[-1] == "city09"


def test_empty_and_malformed_are_safe():
    assert places_from_entities([]) == []
    assert places_from_entities([{"type": "GPE"}, {"name": "", "type": "LOC"}]) == []
    assert places_from_entities(None) == []
