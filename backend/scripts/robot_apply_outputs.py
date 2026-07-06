#!/usr/bin/env python
"""Apply the robot's EVENT and SAME-STORY outputs to the identity store.

Spec docs/specs/2026-07-05-category-robot.md §2: the robot's three outputs
map onto the two-column product — categories (handled by the robot itself),
CANONICAL EVENTS -> persistent umbrellas (ONE parent row in the left
column: "Venezuela Earthquake", sub-stories in the drill-down), and
SAME-STORY groups -> identity FUSION (the ×25 re-founded duplicates merge
so the list cleans itself).

Reads the robot's groups.json (machine-readable dump). Two appliers:

  events    For each kind='event' group with >=2 DB-identity members:
            INSERT dynamic_topics umbrella (identity_key 'u2ev-*',
            is_umbrella=true, e5 centroid = mean of children centroids,
            state 'candidate' if any child seen <=7d else 'retired' —
            historical umbrellas exist but stay serving-hidden) + set
            children parent_id. Label = most-central child label (v1;
            DeepSeek naming can upgrade later). Additive + reversible
            (DELETE umbrella row + NULL parent_id).

  fusions   CONSERVATIVE: only groups with intra >= --min-intra (default
            0.90) and ALL members DB identities. Keeper = earliest
            first_seen (the original identity). Merged ids: repoint
            dynamic_topic_members + topic_members, transfer aggregates,
            state='deprecated'. --apply required; default = dry-run list.

Usage:
  python backend/scripts/robot_apply_outputs.py \
      --groups docs/research/taxonomy-revision/robot-v1-<stamp>.groups.json \
      [--events] [--fusions] [--apply] [--min-intra 0.90]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone


async def apply_events(conn, groups, apply: bool) -> int:
    made = 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    for gr in groups:
        if gr["kind"] != "event":
            continue
        db_ids = [m["db_id"] for m in gr["members"] if m.get("db_id")]
        if len(db_ids) < 2:
            continue  # archive-only events have no children rows to bind (yet)
        rows = await conn.fetch(
            """SELECT id, label, centroid_vec, last_seen, agg_n_signals,
                      parent_id, is_umbrella
               FROM dynamic_topics WHERE id = ANY($1::bigint[])""", db_ids)
        rows = [r for r in rows if not r["is_umbrella"]]
        if len(rows) < 2 or any(r["parent_id"] for r in rows):
            continue  # already parented (R2 build or a prior run) — skip
        vecs = [r["centroid_vec"] for r in rows if r["centroid_vec"]]
        if not vecs:
            continue
        import numpy as np
        c = np.mean(np.asarray(vecs, dtype=np.float64), axis=0)
        n = np.linalg.norm(c)
        if n == 0:
            continue
        c = (c / n).tolist()
        # umbrella label = label of the biggest child (most evidence)
        biggest = max(rows, key=lambda r: int(r["agg_n_signals"] or 0))
        import re as _re
        if _re.search(r"\b(mixed|various|roundup|listings|lottery|headlines)\b",
                      str(biggest["label"]), _re.I):
            print(f"  EVENT g{gr['group']}: SKIP grab-bag label "
                  f"\"{biggest['label'][:50]}\"")
            continue
        recent = any(r["last_seen"] and
                     (datetime.now(timezone.utc) - r["last_seen"]).days <= 7
                     for r in rows)
        state = "candidate" if recent else "retired"
        print(f"  EVENT g{gr['group']}: umbrella \"{biggest['label'][:60]}\" "
              f"({len(rows)} children, state={state})")
        if apply:
            row = await conn.fetchrow(
                """INSERT INTO dynamic_topics
                   (identity_key, state, label, centroid_vec, first_seen,
                    last_seen, n_snapshots, agg_n_signals, mean_cohesion,
                    is_roundup, snapshots_since_seen, is_umbrella,
                    last_state_change)
                   VALUES ($1,$2,$3,$4,NOW(),NOW(),1,$5,NULL,false,0,true,NOW())
                   ON CONFLICT (identity_key) DO NOTHING RETURNING id""",
                f"u2ev-{stamp}-{gr['group']}", state, biggest["label"], c,
                sum(int(r["agg_n_signals"] or 0) for r in rows))
            if row:
                await conn.execute(
                    "UPDATE dynamic_topics SET parent_id=$1 "
                    "WHERE id = ANY($2::bigint[])",
                    int(row["id"]), [int(r["id"]) for r in rows])
                made += 1
    return made


async def apply_fusions(conn, groups, apply: bool, min_intra: float) -> int:
    done = 0
    for gr in groups:
        if gr["kind"] != "same-story" or gr["intra"] < min_intra:
            continue
        members = gr["members"]
        if not all(m.get("db_id") for m in members):
            continue  # archive units have no identity rows to merge
        ids = [int(m["db_id"]) for m in members]
        rows = await conn.fetch(
            """SELECT id, label, state, first_seen, last_seen, agg_n_signals,
                      n_snapshots, is_umbrella FROM dynamic_topics
               WHERE id = ANY($1::bigint[]) AND is_umbrella = false""", ids)
        if len(rows) < 2:
            continue
        keeper = min(rows, key=lambda r: r["first_seen"] or datetime.max
                     .replace(tzinfo=timezone.utc))
        merged = [r for r in rows if r["id"] != keeper["id"]
                  and r["state"] != "deprecated"]
        if not merged:
            continue
        print(f"  FUSION g{gr['group']} (intra {gr['intra']}): keep "
              f"{keeper['id']} \"{keeper['label'][:50]}\" ← "
              f"{[int(r['id']) for r in merged]}")
        if apply:
            mids = [int(r["id"]) for r in merged]
            async with conn.transaction():
                await conn.execute(
                    """UPDATE dynamic_topic_members SET dynamic_topic_id=$1
                       WHERE dynamic_topic_id = ANY($2::bigint[])
                         AND emergent_cluster_id NOT IN (
                           SELECT emergent_cluster_id FROM dynamic_topic_members
                           WHERE dynamic_topic_id=$1)""", keeper["id"], mids)
                await conn.execute(
                    "DELETE FROM dynamic_topic_members "
                    "WHERE dynamic_topic_id = ANY($1::bigint[])", mids)
                # topic_members references 'dynamic-topic-<id>' strings —
                # repoint, tolerating PK collisions (row already on keeper)
                await conn.execute(
                    """DELETE FROM topic_members tm
                       WHERE tm.topic_id = ANY($1::text[])
                         AND EXISTS (SELECT 1 FROM topic_members k
                              WHERE k.signal_id=tm.signal_id AND k.topic_id=$2
                                AND k.role=tm.role
                                AND k.engine_version=tm.engine_version)""",
                    [f"dynamic-topic-{i}" for i in mids],
                    f"dynamic-topic-{keeper['id']}")
                await conn.execute(
                    "UPDATE topic_members SET topic_id=$2 "
                    "WHERE topic_id = ANY($1::text[])",
                    [f"dynamic-topic-{i}" for i in mids],
                    f"dynamic-topic-{keeper['id']}")
                await conn.execute(
                    """UPDATE dynamic_topics SET
                         agg_n_signals = agg_n_signals + $2,
                         n_snapshots = n_snapshots + $3,
                         last_seen = GREATEST(last_seen, $4),
                         updated_at = NOW()
                       WHERE id = $1""",
                    keeper["id"],
                    sum(int(r["agg_n_signals"] or 0) for r in merged),
                    sum(int(r["n_snapshots"] or 0) for r in merged),
                    max(r["last_seen"] for r in merged if r["last_seen"]),
                )
                await conn.execute(
                    """UPDATE dynamic_topics
                       SET state='deprecated', last_state_change=NOW(),
                           updated_at=NOW()
                       WHERE id = ANY($1::bigint[])""", mids)
            done += 1
    return done


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", required=True)
    ap.add_argument("--events", action="store_true")
    ap.add_argument("--fusions", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-intra", type=float, default=0.90)
    args = ap.parse_args()

    data = json.load(open(args.groups))
    groups = data["groups"]
    print(f"{len(groups)} groups loaded "
          f"({sum(1 for g in groups if g['kind']=='event')} event, "
          f"{sum(1 for g in groups if g['kind']=='same-story')} same-story)"
          + ("" if args.apply else "  [DRY-RUN]"))

    import asyncpg
    conn = await asyncpg.connect(os.environ["DATABASE_URL"],
                                 statement_cache_size=0)
    try:
        if args.events:
            n = await apply_events(conn, groups, args.apply)
            print(f"events: {'made' if args.apply else 'would make'} "
                  f"{n} umbrellas" if args.apply else "events: dry-run above")
        if args.fusions:
            n = await apply_fusions(conn, groups, args.apply, args.min_intra)
            print(f"fusions: {'applied' if args.apply else 'listed (dry-run)'}"
                  f" {n}" if args.apply else "fusions: dry-run above")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
