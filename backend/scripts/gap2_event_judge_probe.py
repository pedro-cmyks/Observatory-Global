"""Gap 2 — event-level umbrella via an LLM same-event judge (read-only probe).

The shared-actor umbrella was a negative result (docs/state/2026-07-14-ner-184-
diagnosis-plan.md): event fragments do NOT share distinctive actors — the US-Iran
war fragments (121 "US Bombards Iran Over Ormuz Attack", 583 "US-Iran Military
Strikes", 881 "Bahrain Accuses Iran of Drone Attack") carry different persons, so
centroid+actor linkage either chains unrelated wars (loose) or drops every edge
(tight). The connector is the EVENT, not a shared byline.

This probe tests the alternative: give an LLM the active thread labels and ask it
to group SAME-real-world-event fragments, keeping distinct events (different wars,
different countries) apart. If it recovers {121,583,881} and {452,439} while NOT
merging Iran with Ukraine or the World Cup, the event-judge design is validated.

Read-only. No writes. Run on the M1 mlvenv or backend .venv with DATABASE_URL +
DEEPSEEK_API_KEY in env.
"""
from __future__ import annotations

import asyncio
import json
import os

import asyncpg
import httpx

from scripts.ensemble.model_clients import call_llm

_SYSTEM = """You are an event-clustering analyst for a news-intelligence system.
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


def _user(rows: list[dict]) -> str:
    lines = [
        f'{r["id"]}\t{r["label"]}\t[{r.get("category") or "-"}]'
        for r in rows
    ]
    return "Active threads (id, label, category):\n" + "\n".join(lines)


async def main() -> None:
    db = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db)
    rows = await conn.fetch(
        """
        SELECT id, label, category
        FROM dynamic_topics
        WHERE state='active' AND centroid_vec IS NOT NULL
          AND COALESCE(is_junk,false)=false AND label IS NOT NULL
        ORDER BY agg_n_signals DESC NULLS LAST
        LIMIT 60
        """
    )
    await conn.close()
    items = [{"id": r["id"], "label": r["label"], "category": r["category"]} for r in rows]
    by_id = {r["id"]: r["label"] for r in rows}
    print(f"{len(items)} active threads → LLM same-event judge\n")

    async with httpx.AsyncClient(timeout=90.0) as client:
        raw = await call_llm(
            "deepseek", system=_SYSTEM, user=_user(items), client=client,
            max_tokens=1500, temperature=0.0, json_mode=True,
        )
    data = json.loads(raw)
    events = [e for e in data.get("events", []) if len(e.get("topic_ids", [])) >= 2]

    print(f"=== {len(events)} same-event groups ===")
    for e in sorted(events, key=lambda x: -x.get("confidence", 0)):
        print(f'\n● {e["name"]}  (conf {e.get("confidence", 0):.2f})')
        for tid in e["topic_ids"]:
            print(f'    {tid:>5}  {by_id.get(tid, "??")}')

    # Acceptance: the US-Iran fragments must land in ONE group, distinct from Ukraine.
    def group_of(tid: int) -> str | None:
        for e in events:
            if tid in e.get("topic_ids", []):
                return e["name"]
        return None

    print("\n=== ACCEPTANCE ===")
    iran = {121, 583, 881}
    iran_groups = {group_of(t) for t in iran if group_of(t)}
    iran_merged = len(iran_groups) == 1 and all(group_of(t) for t in iran)
    print(f"US-Iran fragments {sorted(iran)} → one group: {iran_merged} ({iran_groups})")
    ukr_group = group_of(452)
    iran_g = group_of(121)
    print(f"Iran group != Ukraine group (no cross-war merge): {iran_g != ukr_group} "
          f"(iran={iran_g!r} ukraine={ukr_group!r})")


if __name__ == "__main__":
    asyncio.run(main())
