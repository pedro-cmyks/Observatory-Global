"""Precise person→thread relation for #234 (the upgrade over top_entities).

The frontend highlights threads where a focused person sits in `top_entities`
(capped ~6, noisy). `thread_matches_person` is the precise backend predicate:
an atlas thread matches when its topic slug is among the slugs where the person
appears in the FULL signal `persons` array (not the capped top_entities);
dynamic/emergent threads fall back to top_entities (their member persons aren't
in the atlas slug set).
"""
from __future__ import annotations

from app.services.thread_intelligence import thread_matches_person


def _atlas(slug, entities=None):
    return {"thread_id": slug, "anchor_topics": [slug], "top_entities": entities or []}


def _dynamic(entities=None):
    return {"thread_id": "dynamic-topic-42", "anchor_topics": [], "top_entities": entities or []}


def test_empty_person_is_no_filter():
    assert thread_matches_person(_atlas("flood"), set(), "") is True


def test_atlas_matches_precisely_by_slug():
    # slug is in the person's signal set even though top_entities doesn't list them
    assert thread_matches_person(_atlas("flood-disaster", []), {"flood-disaster"}, "trump") is True


def test_atlas_non_matching_slug_and_no_entity_is_false():
    assert thread_matches_person(_atlas("sports-roundup", []), {"flood-disaster"}, "trump") is False


def test_top_entities_fallback_matches_either_kind():
    assert thread_matches_person(_atlas("x", ["donald trump"]), set(), "trump") is True
    assert thread_matches_person(_dynamic(["donald trump", "biden"]), set(), "trump") is True


def test_dynamic_without_entity_is_false_even_if_slugs_present():
    # dynamic threads have no atlas slug → the slug set can't rescue them
    assert thread_matches_person(_dynamic(["biden"]), {"flood-disaster"}, "trump") is False


def test_case_insensitive():
    assert thread_matches_person(_atlas("x", ["Donald TRUMP"]), set(), "trump") is True
