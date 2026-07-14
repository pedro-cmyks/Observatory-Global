"""Gap 2 — pure planning of event umbrellas from an LLM same-event verdict.

Turns (active topics + the LLM's same-event groups) into UmbrellaPlan objects.
Representation-independent: a separate writer creates the umbrella dynamic_topics
rows and sets parent_id on the children. All guardrails live here so they are
unit-tested without a DB or LLM call:

- confidence floor (precision-first — the negative-result cure for chaining),
- min group size (an umbrella needs >= 2 real children),
- hallucinated-id drop (LLM may name ids not in the active set),
- no double-parenting (an existing umbrella never becomes a child),
- one event per topic (first/most-confident group claims it),
- category / crisis_relevant resolution (LLM fields first, else inherit the
  dominant non-null child value — the "labels correctos" consistency fix).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class UmbrellaPlan:
    event_name: str
    child_ids: list[int]
    confidence: float
    category: str | None = None
    crisis_relevant: bool | None = None
    _members: list[dict] = field(default_factory=list, repr=False)


def _dominant(values: list) -> object | None:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return Counter(vals).most_common(1)[0][0]


def plan_event_umbrellas(
    topics: list[dict],
    events: list[dict],
    *,
    min_confidence: float = 0.7,
    min_size: int = 2,
) -> list[UmbrellaPlan]:
    by_id: dict[int, dict] = {t["id"]: t for t in topics}
    claimed: set[int] = set()
    plans: list[UmbrellaPlan] = []

    for ev in events:
        conf = float(ev.get("confidence") or 0.0)
        if conf < min_confidence:
            continue
        child_ids: list[int] = []
        for tid in ev.get("topic_ids", []):
            t = by_id.get(tid)
            if t is None or t.get("is_umbrella") or tid in claimed:
                continue
            child_ids.append(tid)
        if len(child_ids) < min_size:
            continue
        claimed.update(child_ids)
        members = [by_id[tid] for tid in child_ids]

        if "category" in ev and ev["category"]:
            category = ev["category"]
        else:
            category = _dominant([m.get("category") for m in members])
        if "crisis_relevant" in ev and ev["crisis_relevant"] is not None:
            crisis = bool(ev["crisis_relevant"])
        else:
            crisis = _dominant([m.get("crisis_relevant") for m in members])

        plans.append(UmbrellaPlan(
            event_name=str(ev.get("name") or "").strip() or "Event",
            child_ids=child_ids,
            confidence=conf,
            category=category,
            crisis_relevant=crisis,
            _members=members,
        ))
    return plans
