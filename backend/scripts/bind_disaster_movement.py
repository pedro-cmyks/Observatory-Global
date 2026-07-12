"""
Bind structured disaster events -> disaster-category topics (event-source-evaluation §2).

The companion to compute_event_movement (which binds GDELT CAMEO by source_url). Disasters
have NO news source_url (they are authoritative physical-event records, not articles), so
they bind GEO-TEMPORALLY: a disaster of type T in country CC at time τ attaches to the
ACTIVE, crisis-relevant dynamic_topics whose category matches T AND whose dominant country
is CC AND whose activity window covers τ. That is the precise cut — a Japan quake binds to
the Japan-earthquake thread, NOT to every quake thread and NOT to every Japan thread.

Writes topic_members(role='movement', member_kind='event', member_ref='disaster:<event_id>',
source_family='event', basis='co_occurrence', gate_kept=false, engine_version='disaster-v1').
(basis is the geo+temporal co-occurrence of the hazard with the topic; engine_version +
member_ref='disaster:' + source_family='event' encode the disaster-specific provenance.)
verified=false by construction — a disaster is CONTEXT ("this thread corresponds to a real
hazard"), never evidence. Recomputed each pass (DELETE the engine_version then re-insert) =
a rolling snapshot. Per-topic cap keeps a quake-swarm country from flooding one thread.

The topic's country is the mode of its evidence members' country_code (the same derivation
serving uses). When unified-v2 F3 lands full per-signal dynamic membership, this join gets
strictly more topics for free — no code change (it already reads topic_members evidence).

Usage (from backend/, DATABASE_URL set):
    python -m scripts.bind_disaster_movement [--hours 336] [--per-topic 8] [--write]
"""
from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timezone

import asyncpg

try:
    from scripts.event_binding_util import (
        apply_session_budget, build_receipt, fetch_with_retry, print_receipt,
    )
except ImportError:  # invoked as backend.scripts.*
    from backend.scripts.event_binding_util import (
        apply_session_budget, build_receipt, fetch_with_retry, print_receipt,
    )

_ENGINE_VERSION = "disaster-v1"

_INSERT_SQL = (
    "INSERT INTO topic_members "
    "(signal_id, member_kind, member_ref, topic_id, role, source_family, "
    " basis, confidence, gate_kept, engine_version) "
    "VALUES (NULL,'event',$1,$2,'movement','event','co_occurrence',$3,false,$4) "
    "ON CONFLICT DO NOTHING"
)

# disaster event_type -> the R3.1 category string on dynamic_topics. drought has no clean
# disaster category (slow-onset, not a discrete hazard thread) -> intentionally unbound.
_CATEGORY_FOR_TYPE = {
    "earthquake": "Earthquake or volcanic disaster",
    "volcano": "Earthquake or volcanic disaster",
    "flood": "Flood and Landslide Disaster",
    "wildfire": "Wildfire or severe-storm disaster",
    "cyclone": "Wildfire or severe-storm disaster",
}

_ALERT_CONF = {"red": 0.9, "orange": 0.65, "green": 0.35}


def _confidence(mag, alert) -> float:
    """Blend magnitude (USGS) + alert level (GDACS) into [0,1]; whichever is present."""
    c = 0.0
    if mag is not None:
        c = max(c, min(1.0, float(mag) / 8.0))  # M8 ~= max
    if alert:
        c = max(c, _ALERT_CONF.get(str(alert).lower(), 0.3))
    return round(c or 0.3, 3)


async def _topic_country(conn, topic_ids: list[str]) -> dict:
    """topic_id -> dominant evidence-member country (mode), the serving derivation.

    BOUNDED to the disaster-category topics (#256): the unbounded version aggregated
    every dynamic topic's evidence (45K+ index probes) and timed out under
    post-snapshot contention; only the handful of disaster topics ever need a country.
    """
    if not topic_ids:
        return {}
    rows = await fetch_with_retry(
        conn,
        "SELECT tm.topic_id, mode() WITHIN GROUP (ORDER BY s.country_code) AS cc "
        "FROM topic_members tm JOIN signals_v2 s ON s.id = tm.signal_id "
        "WHERE tm.role='evidence' AND tm.topic_id = ANY($1::text[]) "
        "  AND s.country_code IS NOT NULL "
        "GROUP BY tm.topic_id",
        topic_ids,
    )
    return {r["topic_id"]: r["cc"] for r in rows}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=336,  # 14d — disaster threads persist
                    help="only bind disaster events newer than this")
    ap.add_argument("--per-topic", type=int, default=8)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await apply_session_budget(conn)

        # active, crisis-relevant disaster-category topics + their activity window
        # (FIRST, so _topic_country only aggregates these — #256 bounded query)
        topics = await fetch_with_retry(
            conn,
            "SELECT ('dynamic-topic-'||id) AS topic_id, category, first_seen, last_seen "
            "FROM dynamic_topics "
            "WHERE state='active' AND crisis_relevant IS TRUE "
            "  AND category = ANY($1::text[])",
            list(set(_CATEGORY_FOR_TYPE.values())),
        )
        topic_cc = await _topic_country(conn, [t["topic_id"] for t in topics])
        # index topics by (category, country)
        by_cat_cc: dict = {}
        for t in topics:
            cc = topic_cc.get(t["topic_id"])
            if not cc:
                continue
            by_cat_cc.setdefault((t["category"], cc), []).append(t)

        events = await fetch_with_retry(
            conn,
            "SELECT event_id, event_type, country_code, magnitude, alert_level, event_time "
            "FROM disaster_events_v2 "
            "WHERE country_code IS NOT NULL "
            f"  AND event_time > NOW() - INTERVAL '{int(args.hours)} hours' "
            "  AND event_type = ANY($1::text[])",
            list(_CATEGORY_FOR_TYPE.keys()),
        )

        # match: (type->category, country) + time-overlap of event within topic window (±2d)
        from datetime import timedelta
        pairs: list[tuple] = []  # (topic_id, event_id, confidence, event_time)
        for e in events:
            cat = _CATEGORY_FOR_TYPE.get(e["event_type"])
            if not cat:
                continue
            for t in by_cat_cc.get((cat, e["country_code"]), []):
                if (t["first_seen"] - timedelta(days=2) <= e["event_time"]
                        <= t["last_seen"] + timedelta(days=2)):
                    pairs.append((t["topic_id"], e["event_id"],
                                  _confidence(e["magnitude"], e["alert_level"]),
                                  e["event_time"]))

        # per-topic cap: keep the highest-confidence events per topic
        from collections import defaultdict
        by_topic: dict = defaultdict(list)
        for p in pairs:
            by_topic[p[0]].append(p)
        capped: list[tuple] = []
        for tid, ps in by_topic.items():
            ps.sort(key=lambda x: (x[2], x[3]), reverse=True)
            capped.extend(ps[: args.per_topic])

        print(f"disaster bind: {len(events)} events · {len(topics)} disaster topics "
              f"({len(by_cat_cc)} cat×country cells) -> {len(capped)} members "
              f"across {len(by_topic)} topics")
        for tid, ps in sorted(by_topic.items())[:12]:
            print(f"  {tid}: {min(len(ps), args.per_topic)} events "
                  f"(top conf {max(p[2] for p in ps):.2f})")

        wrote = 0
        if args.write:
            deleted = await conn.execute(
                "DELETE FROM topic_members WHERE role='movement' AND member_kind='event' "
                f"AND engine_version='{_ENGINE_VERSION}'"
            )
            for tid, eid, conf, _t in capped:
                await conn.execute(_INSERT_SQL, f"disaster:{eid}", tid, conf, _ENGINE_VERSION)
                wrote += 1
            print(f"  {deleted} · wrote {wrote} members (engine_version='{_ENGINE_VERSION}')")
        else:
            print("  (dry-run — --write to persist)")

        # #256 freshness receipt — lag between freshest eligible ingested event and
        # the freshest event this pass actually bound (machine-readable, grep RECEIPT)
        print_receipt(build_receipt(
            engine=_ENGINE_VERSION,
            ingested_max=max((e["event_time"] for e in events), default=None),
            bound_max=max((p[3] for p in capped), default=None),
            scanned=len(events), matched=len(capped), written=wrote,
            window_hours=args.hours,
            now=datetime.now(timezone.utc),
        ))
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
