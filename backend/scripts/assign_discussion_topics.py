"""Semantic discussion-membership assignment (spec 2026-06-26, Tier 2).

Forums (and other no-GDELT-theme sources) never enter the thread inference
because the lexical classifier matches GDELT GKG themes, which forum posts lack.
This pass assigns each embedded social signal to the topic of its nearest
gate-kept neighbour (kNN over the persisted embedding corpus), writing it as a
DISCUSSION member:

    method='semantic', model_version='semantic-discussion-v1', gate_kept=false

The distinct model_version means the existing thread serving (which filters
model_version='theme-hint-lex-v2') ignores these rows entirely — zero regression.
They are read additively for discussion_count and the connections 'member' basis.
A forum signal is NEVER gate-kept and never counts as evidence.

Usage (from backend/, DATABASE_URL set):
    .venv/bin/python scripts/assign_discussion_topics.py --hours 336 --threshold 0.80 [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

DISCUSSION_MODEL_VERSION = "semantic-discussion-v1"

# Restrict the neighbour search to recent gate-kept material so the kNN stays in
# the HNSW index and fresh discussion attaches to currently-living threads.
_NEIGHBOR_SQL = """
SELECT a.topic_id, 1 - (e.vec <=> $1::halfvec) AS sim
FROM signal_embeddings e
JOIN signal_topic_assignments a
  ON a.signal_id = e.signal_id
 AND a.model_version = 'theme-hint-lex-v2'
 AND a.gate_kept = true
JOIN signals_v2 s ON s.id = e.signal_id
WHERE s.timestamp > NOW() - ($2::int * INTERVAL '1 hour')
ORDER BY e.vec <=> $1::halfvec
LIMIT 1
"""

_PENDING_SQL = """
SELECT s.id, e.vec::text AS vec
FROM signals_v2 s
JOIN signal_embeddings e ON e.signal_id = s.id
WHERE s.source_family = 'social'
  AND s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
  AND NOT EXISTS (
    SELECT 1 FROM signal_topic_assignments a
    WHERE a.signal_id = s.id AND a.model_version = $2
  )
ORDER BY s.timestamp DESC
LIMIT $3
"""

_INSERT_SQL = """
INSERT INTO signal_topic_assignments
    (signal_id, topic_id, method, confidence, model_name, model_version,
     gate_kept, evidence, assigned_at)
VALUES ($1, $2, 'embedding', $3, 'knn-discussion', $4, false,
        jsonb_build_object('basis', 'semantic_discussion', 'neighbor_sim', $3),
        NOW())
ON CONFLICT (signal_id, topic_id, method, model_version) DO NOTHING
"""


async def run(hours: int, threshold: float, limit: int, neighbor_hours: int,
              dry_run: bool) -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("SET statement_timeout = 30000")
        pending = await conn.fetch(_PENDING_SQL, hours, DISCUSSION_MODEL_VERSION, limit)
        print(f"pending embedded social signals: {len(pending)}")
        assigned = skipped = 0
        for row in pending:
            nb = await conn.fetchrow(_NEIGHBOR_SQL, row["vec"], neighbor_hours)
            if nb is None or float(nb["sim"]) < threshold:
                skipped += 1
                continue
            if dry_run:
                assigned += 1
                continue
            await conn.execute(
                _INSERT_SQL, int(row["id"]), int(nb["topic_id"]),
                round(float(nb["sim"]), 4), DISCUSSION_MODEL_VERSION,
            )
            assigned += 1
        print(f"assigned: {assigned} | below-threshold skipped: {skipped}"
              + (" (dry-run)" if dry_run else ""))
        return 0
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=336,
                    help="window of social signals to assign")
    ap.add_argument("--neighbor-hours", type=int, default=336,
                    help="window of gate-kept neighbours to match against")
    ap.add_argument("--threshold", type=float, default=0.90,
                    help="min cosine similarity to the nearest gate-kept neighbour. "
                         "0.90 is precision-first: below it, short conversational "
                         "forum posts force-match broad threads (measured 2026-06-26 "
                         "— 'AYA bank'->Armed conflict 0.83, meme->Gender violence 0.88). "
                         "Discussion membership should look smart, not noisy.")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return asyncio.run(run(args.hours, args.threshold, args.limit,
                           args.neighbor_hours, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
