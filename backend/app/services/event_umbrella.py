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

import json
from collections import Counter
from dataclasses import dataclass, field


# The validated same-event judge prompt (gap2_event_judge_probe.py proved it
# recovers {121,583,881} into one group while keeping Iran != Ukraine, no
# chaining). Precision-first is the cure for the negative-result chaining.
SAME_EVENT_SYSTEM = """You are an event-clustering analyst for a news-intelligence system.
You are given active narrative-thread labels. Group ONLY the threads that report
the SAME real-world event or a single tightly-coupled situation.

Rules:
- Fragments of one incident merge: same actors + place + episode, told from
  different angles (an attack, the condemnation of it, a spillover strike) = ONE
  event.
- Distinct events stay SEPARATE even in the same domain: two different wars, two
  different countries' elections, two unrelated crimes are NOT the same event.
- A recurring CATEGORY label (generic "Crime and Accidents", "TV News
  Broadcasts", "Job and Course Openings") is not an event — leave it ungrouped.
- Precision over recall: if you are unsure two threads are the same event, do
  NOT merge them. Only merge on a clear shared event.

Output STRICT JSON:
{"events":[{"name":"<short event name>","topic_ids":[<ids>],"confidence":0.0-1.0}]}
Only include groups with 2+ topic_ids. Omit everything else."""


def same_event_user(topics: list[dict]) -> str:
    """Render the active threads (id, label, category) for the judge."""
    lines = [
        f'{t["id"]}\t{t.get("label") or ""}\t[{t.get("category") or "-"}]'
        for t in topics
    ]
    return "Active threads (id, label, category):\n" + "\n".join(lines)


def parse_same_event_response(raw: str) -> list[dict]:
    """Tolerantly parse the judge's JSON into an events list. Handles fenced
    code blocks and surrounding prose; returns [] on any parse failure (the
    caller must never wipe umbrellas on a malformed/empty LLM response)."""
    if not raw or not raw.strip():
        return []
    for candidate in (raw, _first_json_object(raw)):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            events = data.get("events")
            if isinstance(events, list):
                return [e for e in events if isinstance(e, dict)]
    return []


def _first_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def plans_to_index_groups(
    ids_in_order: list[int], plans: list["UmbrellaPlan"]
) -> dict[int, list[int]]:
    """Map planned umbrellas (child topic ids) to the row-index groups the
    build_umbrella write path consumes: {group_root_index: [member_indices]},
    each with >= 2 members. ids_in_order is the loaded `rows` id order."""
    index_of = {tid: i for i, tid in enumerate(ids_in_order)}
    groups: dict[int, list[int]] = {}
    for p in plans:
        idxs = sorted(index_of[c] for c in p.child_ids if c in index_of)
        if len(idxs) >= 2:
            groups[idxs[0]] = idxs
    return groups


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
