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

Timeout discipline (2026-08-13): the single windowed INSERT..SELECT over the
full --hours window outran the pooler's 2min statement_timeout under
post-snapshot contention two nights running (08-12 + 08-13, Step 3.5 of the
nightly). The window is now sliced into fixed slabs anchored to ONE client-side
timestamp (no NOW()-drift gaps between statements; the newest slab stays
open-ended so coverage is identical to the old single statement), and every
statement runs inside its own transaction with a SET LOCAL statement_timeout —
the sanctioned pattern for heavy statements through the transaction pooler.

Run:  python -m backend.scripts.etl_topic_members --hours 168
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import asyncpg

# Slab width for the windowed inserts + the per-statement timeout override.
SLAB_HOURS = int(os.environ.get("ATLAS_ETL_MEMBERS_SLAB_HOURS", "24") or "24")
STMT_TIMEOUT = os.environ.get("ATLAS_ETL_MEMBERS_STMT_TIMEOUT", "540s")

# $1/$2 = half-open (lo, hi] slab bounds; $2 NULL = open-ended newest slab
# (matches the old `> NOW() - hours` upper-unbounded window exactly).
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
  AND a.assigned_at > $1::timestamptz
  AND ($2::timestamptz IS NULL OR a.assigned_at <= $2::timestamptz)
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
  AND a.assigned_at > $1::timestamptz
  AND ($2::timestamptz IS NULL OR a.assigned_at <= $2::timestamptz)
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


def slab_bounds(
    anchor: datetime, hours: int, slab_hours: int = SLAB_HOURS
) -> list[tuple[datetime, datetime | None]]:
    """Half-open (lo, hi] slabs covering (anchor-hours, +inf), oldest first.

    Pure. Anchored to ONE timestamp so consecutive statements cannot open a
    NOW()-drift gap at a slab boundary; the final slab's hi is None (open
    upper bound = the old single statement's coverage). slab_hours<=0 returns
    the whole window as ONE open-ended slab (explicit legacy opt-out).
    """
    if slab_hours <= 0 or hours <= slab_hours:
        return [(anchor - timedelta(hours=hours), None)]
    bounds: list[tuple[datetime, datetime | None]] = []
    lo_h = hours
    while lo_h > 0:
        hi_h = max(lo_h - slab_hours, 0)
        bounds.append((
            anchor - timedelta(hours=lo_h),
            None if hi_h == 0 else anchor - timedelta(hours=hi_h),
        ))
        lo_h = hi_h
    return bounds


def _rowcount(status: str) -> int:
    """'INSERT 0 123' -> 123 (0 on anything unparseable)."""
    try:
        return int(status.rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


async def _execute_guarded(conn, sql: str, *args) -> int:
    """One statement in its own transaction with SET LOCAL statement_timeout."""
    async with conn.transaction():
        await conn.execute(
            "SELECT set_config('statement_timeout', $1, true)", STMT_TIMEOUT
        )
        return _rowcount(await conn.execute(sql, *args))


async def run(hours: int) -> None:
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    conn = await asyncpg.connect(db)
    try:
        anchor = datetime.now(timezone.utc)
        slabs = slab_bounds(anchor, hours)
        ev = sum([await _execute_guarded(conn, _ATLAS_EVIDENCE, lo, hi) for lo, hi in slabs])
        di = sum([await _execute_guarded(conn, _DISCUSSION, lo, hi) for lo, hi in slabs])
        dy = await _execute_guarded(conn, _DYNAMIC_SAMPLE)
        print(f"atlas evidence:  INSERT 0 {ev} ({len(slabs)} slabs)")
        print(f"discussion:      INSERT 0 {di} ({len(slabs)} slabs)")
        print(f"dynamic sample:  INSERT 0 {dy}")
        # Parity check vs the source assignments (atlas evidence path).
        src = await conn.fetchval(
            """SELECT COUNT(*) FROM signal_topic_assignments a
               WHERE a.model_version = 'theme-hint-lex-v2'
                 AND a.assigned_at > $1::timestamptz""", anchor - timedelta(hours=hours))
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
