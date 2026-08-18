#!/usr/bin/env python3
"""Compute the grab-bag coherence measurement OFF-REQUEST for live rows (#257).

`measure_subject_geography_coherence` (atlas-subject-coherence-v1) separates a
coherent multi-country story from a mixed-geography grab-bag umbrella. It ran
only at seal time, so live /threads rows could never carry the mark. MEASURED
2026-08-18: inline in serving it costs ~3.4 ms/row (full country-pattern regex
tables per receipt headline, uncached) = ~137 ms median on a 40-row list —
~2.7x the 50 ms budget. So it runs HERE, over the SAME receipts the serving
lane renders (`dynamic_topics.sample_signal_ids` -> live `signals_v2`
headlines), and serving does a pure guarded read
(thread_intelligence._fetch_subject_coherence_map).

Storage: `dynamic_topic_subject_coherence` (mig 102) — one JSONB result per
topic + measured_at. Honesty rules:

  * a topic whose sample ids resolve to ZERO live headlines (7-day retention
    ate them — the member_sample_starved class) gets its stored row DELETED:
    a measurement about vanished receipts must not keep marking the row, and
    serving falls back to null (unmeasured), never false;
  * topics not covered by this pass keep serving null.

Scope: state='active' topics (parents AND children — the country view serves
R1 scoped children). Umbrella parents measure over their own sample ids like
serving renders them.

    dry-run (default):  python -m scripts.compute_subject_coherence
    write:              python -m scripts.compute_subject_coherence --execute

Run from backend/ (so `app` imports resolve), any venv with asyncpg — the
measurement is pure stdlib + compiled regex, no torch/model load. Not yet
wired to a cron: wiring reported as a pending one-liner (house rule: no cron
changes without reporting).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Any

import asyncpg

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.subject_geography import (  # noqa: E402
    measure_subject_geography_coherence,
)

# MIRRORS thread_intelligence._DYNAMIC_TOPICS_SELECT's sample_signal_ids
# subquery (latest-snapshot member clusters, DISTINCT sample ids, DESC before
# the cut so the slice prefers ids retention has not deleted, LIMIT 24): the
# stored mark must describe the SAME receipt population the list row renders.
# test_thread_grab_bag_serving freezes the sync textually.
_TOPICS_SQL = """
SELECT
    dt.id,
    ARRAY(
        SELECT DISTINCT sid
        FROM dynamic_topic_members dtm3
        JOIN emergent_clusters ec3 ON ec3.id = dtm3.emergent_cluster_id
        CROSS JOIN LATERAL unnest(COALESCE(ec3.sample_signal_ids, ARRAY[]::bigint[])) AS sid
        WHERE dtm3.dynamic_topic_id = dt.id
          AND dtm3.snapshot_at = (
              SELECT MAX(snapshot_at) FROM dynamic_topic_members
              WHERE dynamic_topic_id = dt.id
          )
        ORDER BY sid DESC
        LIMIT 24
    ) AS sample_signal_ids
FROM dynamic_topics dt
WHERE dt.state = 'active'
"""

_HEADLINES_SQL = """
SELECT id, headline
FROM signals_v2
WHERE id = ANY($1::bigint[]) AND headline IS NOT NULL
"""

_UPSERT_SQL = """
INSERT INTO dynamic_topic_subject_coherence (topic_id, result, measured_at)
VALUES ($1, $2::jsonb, NOW())
ON CONFLICT (topic_id)
DO UPDATE SET result = EXCLUDED.result, measured_at = EXCLUDED.measured_at
"""

_DELETE_SQL = "DELETE FROM dynamic_topic_subject_coherence WHERE topic_id = $1"

_CHUNK = 5_000

# The topics SELECT runs the correlated latest-snapshot subquery over EVERY
# active topic (serving only pays it for 80-400 candidates; measured 44.5s
# over 3,905 actives, 2026-08-18), and the chunked headline ANY() fetches also
# outran the pooler's default statement_timeout. ALL reads run inside one
# transaction with SET LOCAL — the sanctioned pooler pattern
# (cf. compute_topic_movement).
_STMT_TIMEOUT = os.environ.get("ATLAS_COHERENCE_STMT_TIMEOUT", "300s")


def build_receipts(
    sample_ids: list[int], headline_by_id: dict[int, str]
) -> list[dict[str, Any]]:
    """The receipt rows the measurement sees — same population serving renders."""
    return [
        {"headline": headline_by_id[sid]}
        for sid in sample_ids
        if sid in headline_by_id
    ]


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute", action="store_true",
        help="write results (default: dry-run report only)",
    )
    args = parser.parse_args()

    conn = await asyncpg.connect(
        os.environ["DATABASE_URL"], statement_cache_size=0
    )
    try:
        has_table = await conn.fetchval(
            "SELECT to_regclass('dynamic_topic_subject_coherence') IS NOT NULL"
        )
        if not has_table and args.execute:
            # Dry-run is pure SELECT + CPU, so it may preview before the
            # migration lands; only the write path requires the table.
            print(
                "dynamic_topic_subject_coherence missing — apply migration "
                "102_dynamic_topic_subject_coherence.sql first",
                file=sys.stderr,
            )
            return 2

        t0 = time.perf_counter()
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('statement_timeout', $1, true)", _STMT_TIMEOUT
            )
            topics = await conn.fetch(_TOPICS_SQL)

            all_ids: set[int] = set()
            for t in topics:
                all_ids.update(int(i) for i in (t["sample_signal_ids"] or []))

            headline_by_id: dict[int, str] = {}
            ids = sorted(all_ids)
            for i in range(0, len(ids), _CHUNK):
                rows = await conn.fetch(_HEADLINES_SQL, ids[i : i + _CHUNK])
                headline_by_id.update(
                    {int(r["id"]): r["headline"] for r in rows}
                )

        measured = grab_bags = starved = 0
        for t in topics:
            topic_id = int(t["id"])
            sample_ids = [int(i) for i in (t["sample_signal_ids"] or [])]
            receipts = build_receipts(sample_ids, headline_by_id)
            if not receipts:
                # Honest absence: retention ate the receipts; a stale mark
                # about vanished evidence must not keep serving.
                starved += 1
                if args.execute:
                    await conn.execute(_DELETE_SQL, topic_id)
                continue
            result = measure_subject_geography_coherence(receipts)
            measured += 1
            if result.get("grab_bag"):
                grab_bags += 1
            if args.execute:
                await conn.execute(_UPSERT_SQL, topic_id, json.dumps(result))

        dt = time.perf_counter() - t0
        mode = "EXECUTE" if args.execute else "DRY-RUN"
        print(
            f"[{mode}] topics={len(topics)} measured={measured} "
            f"grab_bags={grab_bags} sample_starved={starved} "
            f"headlines_fetched={len(headline_by_id)} in {dt:.1f}s"
        )
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
