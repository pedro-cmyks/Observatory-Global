"""Gap 2 — pure planning of event umbrellas from an LLM same-event verdict.

The planner is representation-independent: it turns (active topics + the LLM's
same-event groups) into UmbrellaPlan objects (which children roll up, the event
label, the inherited/LLM type). A separate writer creates the umbrella rows and
sets parent_id. Guardrails live here so they are unit-tested without a DB or LLM:
confidence floor, min group size, hallucinated-id drop, no double-parenting, one
event per topic, category/crisis_relevant resolution.
"""
from __future__ import annotations

from app.services.event_umbrella import UmbrellaPlan, plan_event_umbrellas


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
