"""R3.4b — event→movement role: bind conflict events to their topic (#232, the Sudan answer).

`events_v2` (GDELT CAMEO) has no text -> not embeddable -> bound by CO-OCCURRENCE
(country + time-window + conflict quad_class), NOT centroid cosine. For each active
CRISIS topic with a primary country, its country's recent high-impact conflict events
(quad_class 3/4) are written as `topic_members(role='movement', member_kind='event',
basis='co_occurrence', verified=false)`. So "Sudan Conflict Escalation" finally carries
the Darfur events the anomaly panel shows but never connected to the thread.

Honest + coarse by design (country+time is the only signal a text-less event shares).
Capped per topic; the event stays independently addressable (never dissolves the topic).
  python -m backend.scripts.compute_event_movement --dry-run
  python -m backend.scripts.compute_event_movement --write
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

# CAMEO quad_class 3=verbal conflict, 4=material conflict — the events a conflict/crisis
# thread should carry. (Cooperation events 1/2 are not "movement" for a crisis thread.)
_CONFLICT_QUAD = (3, 4)
_CAP = 6  # events bound per topic

_TOPICS = """
    SELECT dt.id, dt.label, dt.crisis_class,
           (SELECT ec.top_country_codes[1]
            FROM dynamic_topic_members m JOIN emergent_clusters ec ON ec.id = m.emergent_cluster_id
            WHERE m.dynamic_topic_id = dt.id AND ec.top_country_codes IS NOT NULL
            ORDER BY m.snapshot_at DESC LIMIT 1) AS country
    FROM dynamic_topics dt
    WHERE dt.state = 'active' AND dt.is_umbrella = false
      AND dt.crisis_class IS NOT NULL AND dt.crisis_class <> 'non_crisis'
"""
_EVENTS = """
    SELECT global_event_id, action_location_name, event_root_code,
           COALESCE(num_articles, 0) AS arts, timestamp
    FROM events_v2
    WHERE action_country_code = $1
      AND timestamp > NOW() - INTERVAL '168 hours'
      AND quad_class = ANY($2::int[])
    ORDER BY COALESCE(num_articles, 0) DESC, timestamp DESC
    LIMIT $3
"""


async def main() -> None:
    ap = argparse.ArgumentParser(description="R3.4b event->movement co-occurrence binding.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--cap", type=int, default=_CAP)
    args = ap.parse_args()
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL required", file=sys.stderr); sys.exit(2)

    conn = await asyncpg.connect(db)
    try:
        topics = await conn.fetch(_TOPICS)
        bound = topics_with_events = 0
        # clear prior movement members (recomputed each pass)
        if args.write:
            await conn.execute(
                "DELETE FROM topic_members WHERE role='movement' AND member_kind='event' "
                "AND engine_version='movement-v1'")
        for t in topics:
            country = t["country"]
            if not country or country == "XX":
                continue
            events = await conn.fetch(_EVENTS, country, list(_CONFLICT_QUAD), args.cap)
            if not events:
                continue
            topics_with_events += 1
            topic_id = f"dynamic-topic-{int(t['id'])}"
            if args.dry_run and topics_with_events <= 8:
                loc = events[0]["action_location_name"] or country
                print(f"  {t['label'][:34]:36} ({country}) <- {len(events)} events "
                      f"e.g. [{loc[:30]}, {events[0]['arts']} articles]")
            if args.write:
                for e in events:
                    await conn.execute(
                        "INSERT INTO topic_members "
                        "(member_kind, member_ref, topic_id, role, basis, confidence, "
                        " gate_kept, source_family, engine_version) "
                        "VALUES ('event',$1,$2,'movement','co_occurrence',$3,false,'event','movement-v1') "
                        "ON CONFLICT DO NOTHING",
                        str(e["global_event_id"]), topic_id, float(min(1.0, e["arts"] / 50.0)))
                    bound += 1
        print(f"\n{topics_with_events}/{len(topics)} crisis topics have conflict events in-country · "
              f"{bound} movement members {'written' if args.write else '(dry)'}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
