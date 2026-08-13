#!/usr/bin/env python3
"""Populate topic_movement — the SINGLE shared movement field (#219 Kalman).

Runs the pilot's tiny Kalman (estimate_state) over each active dynamic topic's
HOURLY signal volume from signals_v2 (the SAME lineage as changed_10h and the
Narrative Threads '▲ Accelerating' — one movement number, no split-brain), and
writes smoothed_intensity/velocity/uncertainty/surprise/trend per topic.

Consistency, founded 2026-07-03: movement is defined ONCE (signals_v2 timestamp
volume) → Kalman smooths it → every surface reads topic_movement. Raw
changed_10h is the fallback when a topic has no row yet.

Read-only on signals_v2; only writes topic_movement. Mindful — bounded per
topic, numpy-light. Run standalone or from the snapshot cron.
"""
import argparse
import asyncio
import os
from datetime import datetime, timezone

import asyncpg

try:  # works as `-m scripts.compute_topic_movement` and standalone
    from scripts.dynamic_topic_state_report import Observation, estimate_state
except ImportError:
    from dynamic_topic_state_report import Observation, estimate_state

ENGINE_VERSION = "movement-kalman-v1"
WINDOW_DAYS = 7
BUCKET_HOURS = 3  # coarser than 1h → smoother, cheaper, less zero-noise

# Per-statement budget for the one big aggregate below. The pooler's effective
# statement_timeout is 2min (server config), and the aggregate measured 28.6s
# uncontended at 169k topic_members (2026-08-13) — only ~4x headroom, and this
# runs in the nightly right after the snapshot mass-rewrites topic_members
# (cold cache + stale planner stats). SET LOCAL inside the statement's own
# transaction is the sanctioned pooler pattern (cf. etl_topic_members).
STMT_TIMEOUT = os.environ.get("ATLAS_MOVEMENT_STMT_TIMEOUT", "540s")


async def _series_by_topic(conn) -> dict[str, list[Observation]]:
    """Hourly volume per topic over topic_members — the UNIFIED membership, so
    this covers atlas categories AND dynamic stories in one pass (movement is
    ONE field for the whole thread population, Pedro 2026-07-03)."""
    async with conn.transaction():
        await conn.execute(
            "SELECT set_config('statement_timeout', $1, true)", STMT_TIMEOUT
        )
        rows = await conn.fetch(
            f"""
            SELECT tm.topic_id,
                   date_bin('{BUCKET_HOURS} hours', s.timestamp,
                            TIMESTAMPTZ '2020-01-01') AS bucket,
                   COUNT(*) AS n
            FROM topic_members tm JOIN signals_v2 s ON s.id = tm.signal_id
            WHERE tm.role = 'evidence'
              AND s.timestamp > NOW() - INTERVAL '{WINDOW_DAYS} days'
            GROUP BY tm.topic_id, bucket
            ORDER BY tm.topic_id, bucket
            """
        )
    out: dict[str, list[Observation]] = {}
    for r in rows:
        out.setdefault(r["topic_id"], []).append(
            Observation(snapshot_at=r["bucket"], n_signals=int(r["n"]))
        )
    return out


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = await asyncpg.connect(os.environ["DATABASE_URL"], statement_cache_size=0)
    try:
        series = await _series_by_topic(conn)
        now = datetime.now(timezone.utc)
        written = 0
        rows_out = []
        for topic_id, obs in series.items():
            if not obs:
                continue
            est = estimate_state(obs)
            total = sum(o.n_signals for o in obs)
            rows_out.append((
                topic_id, now, total, ENGINE_VERSION,
                est.smoothed_intensity, est.velocity, est.uncertainty,
                est.surprise, est.trend, est.n_observations,
            ))

        if args.dry_run:
            top = sorted(rows_out, key=lambda r: -r[5])[:8]
            print(f"[dry-run] {len(rows_out)} topics; top by velocity:")
            for r in top:
                print(f"  {r[0]:<22} vel={r[5]:+.3f} surprise={r[7]:.2f} trend={r[8]} n={r[9]}")
            return

        # Idempotent upsert on the PK (topic_id, window_end, engine_version).
        await conn.executemany(
            """
            INSERT INTO topic_movement
                (topic_id, window_end, volume, engine_version,
                 smoothed_intensity, velocity, uncertainty, surprise,
                 trend, n_observations, computed_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10, now())
            ON CONFLICT (topic_id, window_end, engine_version) DO UPDATE SET
                volume = EXCLUDED.volume,
                smoothed_intensity = EXCLUDED.smoothed_intensity,
                velocity = EXCLUDED.velocity,
                uncertainty = EXCLUDED.uncertainty,
                surprise = EXCLUDED.surprise,
                trend = EXCLUDED.trend,
                n_observations = EXCLUDED.n_observations,
                computed_at = now()
            """,
            rows_out,
        )
        written = len(rows_out)
        print(f"[compute_topic_movement] wrote {written} topic_movement rows "
              f"({ENGINE_VERSION})")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
