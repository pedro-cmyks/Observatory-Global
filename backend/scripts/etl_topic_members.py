"""Unified Engine F0.2 — v1-compat ETL (spec 2026-06-29-atlas-unified-engine §2/§10).

Projects today's assignments into the unified `topic_members` table with
engine_version='v1-compat', so serving can read ONE typed model while construction
is untouched:
  - atlas `theme-hint-lex-v2`     -> role='evidence' (gate_kept, basis from evidence)
  - atlas `semantic-discussion-v1`-> role='discussion' (verified=false)
  - dynamic topics (sample)        -> role='evidence' (basis='semantic')

Constraint (spec §10): atlas has FULL per-signal membership; dynamic topics have
only `emergent_clusters.sample_signal_ids` (capped). So dynamic is projected by
its sample; full dynamic membership is delivered later by unified-v2 (F3).

Idempotent (ON CONFLICT DO NOTHING). Repeatable — runs as a cron beside the
current paths until the F4 cutover. `assigned_at` is carried from the SOURCE
assignment time (atlas/discussion: `signal_topic_assignments.assigned_at`;
dynamic: the snapshot time) — NOT the ETL insert time — so the F0.3 serving
read can window `topic_members.assigned_at` identically to THREADS_SQL and the
list parity is exact (6734=6734). A prior version stamped insert-time, which
would have served stale (aged-out) assignments; re-seed v1-compat after that
fix (DELETE WHERE engine_version='v1-compat' + re-run).

Run:  python -m backend.scripts.etl_topic_members --hours 168
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

_ATLAS_EVIDENCE = """
INSERT INTO topic_members
  (signal_id, topic_id, role, source_family, basis, confidence, gate_kept,
   engine_version, assigned_at)
SELECT a.signal_id, at.slug, 'evidence', s.source_family,
       CASE WHEN COALESCE((a.evidence->>'lex_count')::int, 0) > 0 THEN 'lexical'
            WHEN COALESCE((a.evidence->>'theme_hits')::int, 0) > 0 THEN 'theme'
            ELSE 'semantic' END,
       a.confidence, a.gate_kept, 'v1-compat', a.assigned_at
FROM signal_topic_assignments a
JOIN atlas_topics at ON at.id = a.topic_id
JOIN signals_v2 s ON s.id = a.signal_id
WHERE a.model_version = 'theme-hint-lex-v2'
  AND a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
ON CONFLICT DO NOTHING
"""

_DISCUSSION = """
INSERT INTO topic_members
  (signal_id, topic_id, role, source_family, basis, confidence, gate_kept,
   engine_version, assigned_at)
SELECT a.signal_id, at.slug, 'discussion', s.source_family, 'semantic',
       a.confidence, false, 'v1-compat', a.assigned_at
FROM signal_topic_assignments a
JOIN atlas_topics at ON at.id = a.topic_id
JOIN signals_v2 s ON s.id = a.signal_id
WHERE a.model_version = 'semantic-discussion-v1'
  AND a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
ON CONFLICT DO NOTHING
"""

_DYNAMIC_SAMPLE = """
WITH latest_snap AS (
    SELECT dynamic_topic_id, MAX(snapshot_at) AS snap
    FROM dynamic_topic_members GROUP BY dynamic_topic_id
)
INSERT INTO topic_members
  (signal_id, topic_id, role, source_family, basis, confidence, gate_kept,
   engine_version, assigned_at)
SELECT DISTINCT sid, 'dynamic-topic-' || dt.id, 'evidence', s.source_family,
       'semantic', dtm.match_score, true, 'v1-compat', ls.snap
FROM dynamic_topics dt
JOIN latest_snap ls ON ls.dynamic_topic_id = dt.id
JOIN dynamic_topic_members dtm
     ON dtm.dynamic_topic_id = dt.id AND dtm.snapshot_at = ls.snap
JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
CROSS JOIN LATERAL unnest(COALESCE(ec.sample_signal_ids, ARRAY[]::bigint[])) AS sid
JOIN signals_v2 s ON s.id = sid
ON CONFLICT DO NOTHING
"""


async def run(hours: int) -> None:
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    conn = await asyncpg.connect(db)
    try:
        ev = await conn.execute(_ATLAS_EVIDENCE, hours)
        di = await conn.execute(_DISCUSSION, hours)
        dy = await conn.execute(_DYNAMIC_SAMPLE)
        print(f"atlas evidence:  {ev}")
        print(f"discussion:      {di}")
        print(f"dynamic sample:  {dy}")
        # Parity check vs the source assignments (atlas evidence path).
        src = await conn.fetchval(
            """SELECT COUNT(*) FROM signal_topic_assignments a
               WHERE a.model_version = 'theme-hint-lex-v2'
                 AND a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')""", hours)
        dst = await conn.fetchval(
            "SELECT COUNT(*) FROM topic_members WHERE role='evidence' AND engine_version='v1-compat'")
        by_role = await conn.fetch(
            "SELECT role, COUNT(*) AS n FROM topic_members WHERE engine_version='v1-compat' GROUP BY role ORDER BY role")
        print(f"\nparity: atlas-evidence source rows ({hours}h) = {src}")
        print(f"topic_members evidence (all windows) = {dst}")
        print("topic_members by role:", {r['role']: r['n'] for r in by_role})
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168)
    args = ap.parse_args()
    asyncio.run(run(args.hours))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
