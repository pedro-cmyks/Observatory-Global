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


async def _hourly_observations(conn, topic_id: str) -> list[Observation]:
    rows = await conn.fetch(
        f"""
        SELECT date_bin('{BUCKET_HOURS} hours', s.timestamp,
                        TIMESTAMPTZ '2020-01-01') AS bucket,
               COUNT(*) AS n
        FROM topic_members tm JOIN signals_v2 s ON s.id = tm.signal_id
        WHERE tm.topic_id = $1 AND tm.role = 'evidence'
          AND s.timestamp > NOW() - INTERVAL '{WINDOW_DAYS} days'
        GROUP BY 1 ORDER BY 1
        """,
        topic_id,
    )
    return [
        Observation(snapshot_at=r["bucket"], n_signals=int(r["n"]))
        for r in rows
    ]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = await asyncpg.connect(os.environ["DATABASE_URL"], statement_cache_size=0)
    try:
        topics = await conn.fetch(
            "SELECT id FROM dynamic_topics WHERE state = 'active' AND NOT is_umbrella"
        )
        now = datetime.now(timezone.utc)
        written = 0
        rows_out = []
        for t in topics:
            topic_id = f"dynamic-topic-{t['id']}"
            obs = await _hourly_observations(conn, topic_id)
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
