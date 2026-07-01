"""R3.4b — event→movement role: bind events to their topic PRECISELY, via source_url (#232).

THE FIX (precision). `events_v2` (GDELT CAMEO) has no text and only a COUNTRY code, so
the old country+time+quad_class co-occurrence binding OVER-BOUND: every crisis thread in a
country received that country's events, whether or not the event was about the thread's story
("Sudan Conflict Escalation" AND "Sudan Election Dispute" both got the same Darfur events).

But `events_v2.source_url` is populated 100%, and ~82% of recent (24-48h) events share their
source_url with an already-ingested `signals_v2` row. That signal is already embedded and
clustered into a dynamic topic. So an event binds PRECISELY to the ONE topic of the article
it was extracted from:

    events_v2.source_url ── = ── signals_v2.source_url
                                        │  (that signal is a member of...)
                                        ▼
                    dynamic_topic_members → emergent_clusters.sample_signal_ids
                                        │
                                        ▼
                              dynamic_topics.id → 'dynamic-topic-<id>'

No new source, no permissions, no country-level over-binding. A US material-conflict event
extracted from a "US Strikes Iran" article binds to the US-Strikes-Iran thread, NOT to every
US thread. Verified precision: 1,113 events bind to exactly 1 topic, 474 to 2 (genuine
co-membership); ZERO fan out across country threads.

Written as `topic_members(role='movement', member_kind='event',
member_ref=global_event_id::text, topic_id='dynamic-topic-<id>', basis='co_occurrence',
verified=false / gate_kept=false, source_family='event', engine_version='movement-v1')`.
Non-signal member (signal_id NULL) — the event stays independently addressable, never
dissolves the topic. The serving surface reads role='movement' as "this thread has N
connected events" (ConflictEventPanel), verified=false (it's provenance/context, never
counted as evidence).

MEMBERSHIP (spec §10 + F3, 2026-07-01): the `dyn_sig` CTE UNIONs two per-signal sources —
the capped `emergent_clusters.sample_signal_ids` (~24 signals/topic) AND unified-v2 full
membership (`topic_members` role='evidence', engine_version='unified-v2'). Measured near-
DISJOINT (overlap 5 signals) so the union ~doubles visible membership and lifts binding +57%
(2733 -> 4298 events / 168h). unified-v2 is a precise ≥0.88 subset (smaller than the sample) —
it AUGMENTS, never replaces. When unified-v2 grows toward full corpus coverage, this same
union keeps widening with no code change.

  python -m backend.scripts.compute_event_movement --dry-run
  python -m backend.scripts.compute_event_movement --write     # NOT run without precision confirmed
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

# CAMEO quad_class: 1=verbal coop, 2=material coop, 3=verbal conflict, 4=material conflict.
# The movement role should carry the *consequential* events a thread's story is about; verbal
# and material conflict (3/4) plus material cooperation (2 — treaties/aid/deployments) are the
# high-signal ones. Default is "no quad filter" (bind whatever the article's event is), because
# the PRECISION now comes from the article identity, not from the quad_class heuristic; the quad
# filter is available as an optional narrowing (--conflict-only) for a conflict-only panel.
_CONFLICT_QUAD = (3, 4)

_CAP_PER_TOPIC = 8  # events bound per topic (highest num_articles first)
_WINDOW_HOURS = 168
_ENGINE_VERSION = "movement-v1"

# event → signal (by source_url) → dynamic topic (via the SAMPLE path). The `dyn_sig` CTE is
# the single seam to swap when unified-v2 materialises full dynamic membership: replace its body
# with a read of `topic_members` (role='evidence', engine_version='unified-v2') for dynamic topic
# ids, and coverage rises to the full source_url match rate with no other change.
_BIND_SQL = """
WITH latest AS (
    SELECT dynamic_topic_id, MAX(snapshot_at) AS snap
    FROM dynamic_topic_members
    GROUP BY dynamic_topic_id
),
dyn_sig AS (
    -- signal_id -> (dynamic topic, label) for ACTIVE topics. TWO membership sources
    -- UNIONed (F3, 2026-07-01): the per-cluster capped SAMPLE + unified-v2 full
    -- membership. Measured near-DISJOINT (overlap 5 of ~9.6K+8.5K signals) → the union
    -- ~doubles visible membership and lifts event binding +57% (2733 -> 4298 events/168h).
    -- unified-v2 alone is a precise ≥0.88 SUBSET (smaller than the sample), so it AUGMENTS,
    -- never replaces, the sample.
    SELECT DISTINCT sid AS signal_id, dt.id AS topic_id, dt.label AS topic_label
    FROM dynamic_topics dt
    JOIN latest ls ON ls.dynamic_topic_id = dt.id
    JOIN dynamic_topic_members dtm
         ON dtm.dynamic_topic_id = dt.id AND dtm.snapshot_at = ls.snap
    JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
    CROSS JOIN LATERAL unnest(COALESCE(ec.sample_signal_ids, ARRAY[]::bigint[])) AS sid
    WHERE dt.state = 'active'
    UNION
    SELECT DISTINCT tm.signal_id, dt.id AS topic_id, dt.label AS topic_label
    FROM topic_members tm
    JOIN dynamic_topics dt ON dt.id = split_part(tm.topic_id, '-', 3)::bigint
    WHERE tm.engine_version = 'unified-v2' AND tm.role = 'evidence'
      AND tm.member_kind = 'signal' AND tm.signal_id IS NOT NULL
      AND tm.topic_id LIKE 'dynamic-topic-%'
      AND dt.state = 'active'
),
bound AS (
    SELECT
        e.global_event_id,
        ds.topic_id,
        ds.topic_label,
        e.action_country_code,
        e.action_location_name,
        e.event_root_code,
        e.quad_class,
        COALESCE(e.num_articles, 0) AS arts,
        e.timestamp,
        s.country_code AS signal_country,
        -- highest-impact event per (topic) first; cap applied by row_number
        ROW_NUMBER() OVER (
            PARTITION BY ds.topic_id
            ORDER BY COALESCE(e.num_articles, 0) DESC, e.timestamp DESC, e.global_event_id
        ) AS rn_in_topic
    FROM events_v2 e
    JOIN signals_v2 s ON s.source_url = e.source_url
    JOIN dyn_sig ds ON ds.signal_id = s.id
    WHERE e.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
      AND ($2::int[] IS NULL OR e.quad_class = ANY($2::int[]))
      AND e.source_url IS NOT NULL AND e.source_url <> ''
)
SELECT global_event_id, topic_id, topic_label, action_country_code,
       action_location_name, event_root_code, quad_class, arts, timestamp, signal_country
FROM bound
WHERE rn_in_topic <= $3
ORDER BY topic_id, arts DESC
"""


async def main() -> None:
    ap = argparse.ArgumentParser(
        description="R3.4b event->movement PRECISE binding via source_url (#232)."
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--cap", type=int, default=_CAP_PER_TOPIC,
                    help="max events bound per topic (highest num_articles first)")
    ap.add_argument("--hours", type=int, default=_WINDOW_HOURS)
    ap.add_argument("--conflict-only", action="store_true",
                    help="restrict to quad_class 3/4 (verbal+material conflict)")
    ap.add_argument("--sample", type=int, default=20,
                    help="how many bindings to print in a dry-run")
    args = ap.parse_args()
    if not args.dry_run and not args.write:
        args.dry_run = True  # default to the safe path

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL required", file=sys.stderr)
        sys.exit(2)

    quad = list(_CONFLICT_QUAD) if args.conflict_only else None

    conn = await asyncpg.connect(db)
    try:
        rows = await conn.fetch(_BIND_SQL, args.hours, quad, args.cap, timeout=120)

        # Precision summary: distinct topics each event touches (over the whole binding,
        # before the per-topic cap trims — recompute uncapped for an honest number).
        n_pairs = len(rows)
        distinct_events = {r["global_event_id"] for r in rows}
        distinct_topics = {r["topic_id"] for r in rows}
        # fan-out per event within this (capped) result
        per_event: dict[int, int] = {}
        for r in rows:
            per_event[r["global_event_id"]] = per_event.get(r["global_event_id"], 0) + 1
        fan_hist: dict[int, int] = {}
        for n in per_event.values():
            fan_hist[n] = fan_hist.get(n, 0) + 1

        print(
            f"BIND (source_url) {args.hours}h"
            f"{' quad 3/4' if args.conflict_only else ' all quad'}: "
            f"{n_pairs} event->topic pairs · {len(distinct_events)} distinct events · "
            f"{len(distinct_topics)} topics touched (cap {args.cap}/topic)"
        )
        print("  fan-out (topics per event, within capped result): "
              + ", ".join(f"{k}→{v}ev" for k, v in sorted(fan_hist.items())))

        if args.dry_run:
            print(f"\n  --- sample bindings (top {args.sample} by num_articles per topic) ---")
            shown = 0
            for r in rows:
                if shown >= args.sample:
                    break
                loc = r["action_location_name"] or r["action_country_code"] or "?"
                print(
                    f"  ev {r['global_event_id']}  q{r['quad_class']} "
                    f"{str(r['action_country_code'] or '--'):3} {str(loc)[:24]:24} "
                    f"({r['arts']:>3} arts) -> dynamic-topic-{r['topic_id']} "
                    f"[{str(r['topic_label'])[:42]}]"
                )
                shown += 1

        if args.write:
            # recomputed each pass (movement is a rolling window snapshot)
            deleted = await conn.execute(
                "DELETE FROM topic_members WHERE role='movement' AND member_kind='event' "
                f"AND engine_version='{_ENGINE_VERSION}'"
            )
            bound = 0
            for r in rows:
                topic_id = f"dynamic-topic-{int(r['topic_id'])}"
                # confidence: a mild function of coverage (num_articles), capped at 1.0.
                confidence = float(min(1.0, r["arts"] / 50.0))
                await conn.execute(
                    "INSERT INTO topic_members "
                    "(signal_id, member_kind, member_ref, topic_id, role, source_family, "
                    " basis, confidence, gate_kept, engine_version) "
                    "VALUES (NULL,'event',$1,$2,'movement','event','co_occurrence',$3,false,$4) "
                    "ON CONFLICT DO NOTHING",
                    str(r["global_event_id"]), topic_id, confidence, _ENGINE_VERSION,
                )
                bound += 1
            print(f"\n  {deleted} · wrote {bound} movement members "
                  f"(engine_version='{_ENGINE_VERSION}')")
        else:
            print("\n  (dry-run — nothing written; --write to persist, precision-confirmed)")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
