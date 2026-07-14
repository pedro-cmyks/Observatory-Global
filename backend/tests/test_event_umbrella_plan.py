"""Gap 2 — pure planning of event umbrellas from an LLM same-event verdict.

The planner is representation-independent: it turns (active topics + the LLM's
same-event groups) into UmbrellaPlan objects (which children roll up, the event
label, the inherited/LLM type). A separate writer creates the umbrella rows and
sets parent_id. Guardrails live here so they are unit-tested without a DB or LLM:
confidence floor, min group size, hallucinated-id drop, no double-parenting, one
event per topic, category/crisis_relevant resolution.
"""
from __future__ import annotations

from app.services.event_umbrella import (
    SAME_EVENT_SYSTEM,
    UmbrellaPlan,
    parse_same_event_response,
    plan_event_umbrellas,
    plans_to_index_groups,
    same_event_user,
)


def _t(tid, label, *, category=None, crisis=None, parent_id=None, is_umbrella=False):
    return {"id": tid, "label": label, "category": category,
            "crisis_relevant": crisis, "parent_id": parent_id, "is_umbrella": is_umbrella}


def test_merges_us_iran_fragments_into_one_plan():
    topics = [
        _t(121, "US Bombards Iran Over Ormuz Attack", category="Armed conflict escalation", crisis=True),
        _t(583, "US-Iran Military Strikes", category="Armed conflict escalation", crisis=True),
        _t(881, "Bahrain Accuses Iran of Drone Attack", category="Armed conflict escalation", crisis=True),
        _t(452, "Ukraine War Updates", category="Armed conflict escalation", crisis=True),
    ]
    events = [
        {"name": "US-Iran Military Strikes", "topic_ids": [121, 583, 881], "confidence": 0.85},
        # Ukraine is a singleton in the verdict → no plan
    ]
    plans = plan_event_umbrellas(topics, events)
    assert len(plans) == 1
    p = plans[0]
    assert isinstance(p, UmbrellaPlan)
    assert p.event_name == "US-Iran Military Strikes"
    assert set(p.child_ids) == {121, 583, 881}
    assert 452 not in p.child_ids


def test_drops_low_confidence_groups():
    topics = [_t(1, "A strike"), _t(2, "A strike, reaction")]
    events = [{"name": "e", "topic_ids": [1, 2], "confidence": 0.5}]
    assert plan_event_umbrellas(topics, events, min_confidence=0.7) == []


def test_requires_at_least_two_real_children():
    topics = [_t(1, "Only one")]
    events = [{"name": "e", "topic_ids": [1, 999], "confidence": 0.9}]  # 999 not in set
    # after dropping the hallucinated 999, only 1 child remains → no umbrella
    assert plan_event_umbrellas(topics, events) == []


def test_drops_hallucinated_ids_but_keeps_valid_group():
    topics = [_t(1, "x"), _t(2, "y"), _t(3, "z")]
    events = [{"name": "e", "topic_ids": [1, 2, 777], "confidence": 0.9}]
    plans = plan_event_umbrellas(topics, events)
    assert len(plans) == 1
    assert set(plans[0].child_ids) == {1, 2}


def test_never_makes_an_existing_umbrella_a_child():
    topics = [_t(1, "child"), _t(2, "child2"), _t(9, "existing umbrella", is_umbrella=True)]
    events = [{"name": "e", "topic_ids": [1, 2, 9], "confidence": 0.9}]
    plans = plan_event_umbrellas(topics, events)
    assert set(plans[0].child_ids) == {1, 2}


def test_one_event_per_topic_first_group_wins():
    topics = [_t(1, "a"), _t(2, "b"), _t(3, "c")]
    events = [
        {"name": "first", "topic_ids": [1, 2], "confidence": 0.95},
        {"name": "second", "topic_ids": [2, 3], "confidence": 0.9},  # 2 already claimed
    ]
    plans = plan_event_umbrellas(topics, events)
    first = next(p for p in plans if p.event_name == "first")
    assert set(first.child_ids) == {1, 2}
    second = [p for p in plans if p.event_name == "second"]
    # 2 is claimed by 'first'; 'second' keeps only 3 → below min size → dropped
    assert second == []


def test_umbrella_type_uses_llm_fields_when_present():
    topics = [_t(1, "Sam Neill obituary", category=None, crisis=None),
              _t(2, "Sam Neill dies", category=None, crisis=None)]
    events = [{"name": "Sam Neill death", "topic_ids": [1, 2], "confidence": 0.9,
               "category": "Obituary & Tribute", "crisis_relevant": False}]
    p = plan_event_umbrellas(topics, events)[0]
    assert p.category == "Obituary & Tribute"
    assert p.crisis_relevant is False


def test_umbrella_type_inherits_from_children_when_llm_silent():
    # No LLM type → inherit the dominant non-null child category + crisis flag.
    topics = [_t(1, "Graham dies", category="Obituary & Tribute", crisis=False),
              _t(2, "Graham death reactions", category=None, crisis=False),
              _t(3, "Graham aortic tear", category="Obituary & Tribute", crisis=False)]
    events = [{"name": "Lindsey Graham death", "topic_ids": [1, 2, 3], "confidence": 0.9}]
    p = plan_event_umbrellas(topics, events)[0]
    assert p.category == "Obituary & Tribute"
    assert p.crisis_relevant is False


def test_empty_inputs():
    assert plan_event_umbrellas([], []) == []
    assert plan_event_umbrellas([_t(1, "a")], []) == []


# --- adversarial-review hardening: degraded LLM verdicts must not fabricate or crash ---

def test_string_topic_ids_still_resolve():
    # LLMs commonly emit ids as JSON strings; "121" must resolve to topic 121,
    # else every child is dropped -> empty grouping -> (upstream) hierarchy wipe.
    topics = [_t(121, "a"), _t(583, "b"), _t(881, "c")]
    events = [{"name": "e", "topic_ids": ["121", "583", "881"], "confidence": 0.9}]
    plans = plan_event_umbrellas(topics, events)
    assert len(plans) == 1
    assert set(plans[0].child_ids) == {121, 583, 881}


def test_duplicate_ids_within_a_group_do_not_fabricate_umbrella_of_one():
    topics = [_t(121, "a"), _t(583, "b")]
    # [121,121] is ONE distinct child -> below min_size -> no umbrella
    assert plan_event_umbrellas(topics, [{"name": "e", "topic_ids": [121, 121], "confidence": 0.9}]) == []
    # [121,121,583] -> two distinct children, deduped
    plans = plan_event_umbrellas(topics, [{"name": "e", "topic_ids": [121, 121, 583], "confidence": 0.9}])
    assert set(plans[0].child_ids) == {121, 583}
    assert plans[0].child_ids.count(121) == 1


def test_non_numeric_confidence_skips_event_without_crashing():
    topics = [_t(1, "a"), _t(2, "b"), _t(3, "c"), _t(4, "d")]
    events = [
        {"name": "bad", "topic_ids": [1, 2], "confidence": "high"},   # malformed → skip
        {"name": "good", "topic_ids": [3, 4], "confidence": 0.9},     # valid → kept
    ]
    plans = plan_event_umbrellas(topics, events)
    names = {p.event_name for p in plans}
    assert names == {"good"}


def test_garbage_ids_yield_no_plans_not_a_crash():
    topics = [_t(1, "a"), _t(2, "b")]
    events = [{"name": "e", "topic_ids": ["not-an-id", None, 9991], "confidence": 0.9}]
    assert plan_event_umbrellas(topics, events) == []


def test_parse_distinguishes_valid_empty_from_malformed():
    # valid empty verdict -> [] (a real "no groups"); malformed -> None (parse failure)
    assert parse_same_event_response('{"events":[]}') == []
    assert parse_same_event_response("total garbage {{{") is None
    assert parse_same_event_response("") is None


# --- prompt + response parsing + index mapping (the LLM-call boundary) ---

def test_same_event_system_forbids_same_theme_merges():
    # The honesty invariant the centroid cut enforced must be in the prompt.
    s = SAME_EVENT_SYSTEM.lower()
    assert "same real-world event" in s or "same event" in s
    assert "precision" in s  # precision-first, the anti-chaining rule


def test_same_event_user_lists_id_label_category():
    topics = [_t(121, "US Bombards Iran", category="Armed conflict escalation"),
              _t(583, "US-Iran Strikes", category="Armed conflict escalation")]
    u = same_event_user(topics)
    assert "121" in u and "US Bombards Iran" in u
    assert "583" in u and "US-Iran Strikes" in u


def test_parse_same_event_response_extracts_events():
    raw = '{"events":[{"name":"US-Iran","topic_ids":[121,583,881],"confidence":0.85}]}'
    events = parse_same_event_response(raw)
    assert len(events) == 1
    assert events[0]["topic_ids"] == [121, 583, 881]


def test_parse_same_event_response_tolerates_fenced_json_and_junk():
    raw = 'Here you go:\n```json\n{"events":[{"name":"e","topic_ids":[1,2],"confidence":0.9}]}\n```'
    events = parse_same_event_response(raw)
    assert events[0]["topic_ids"] == [1, 2]


def test_parse_same_event_response_bad_json_returns_none():
    # None signals a PARSE FAILURE (must abort, never wipe); distinct from a
    # valid empty {"events":[]} which returns [].
    assert parse_same_event_response("not json at all") is None
    assert parse_same_event_response("") is None


def test_plans_to_index_groups_maps_topic_ids_to_row_indices():
    # rows in this order → indices 0,1,2,3
    ids_in_order = [121, 583, 881, 452]
    topics = [_t(121, "a"), _t(583, "b"), _t(881, "c"), _t(452, "d")]
    events = [{"name": "US-Iran", "topic_ids": [121, 583, 881], "confidence": 0.85}]
    plans = plan_event_umbrellas(topics, events)
    groups = plans_to_index_groups(ids_in_order, plans)
    # one group; its members are the row indices of 121,583,881 = {0,1,2}
    assert len(groups) == 1
    (members,) = groups.values()
    assert sorted(members) == [0, 1, 2]
    # every group has >= 2 members (the build_umbrella contract)
    assert all(len(v) >= 2 for v in groups.values())


def test_plans_to_index_groups_empty():
    assert plans_to_index_groups([1, 2], []) == {}
