#!/usr/bin/env python
"""W2a(i) — re-measure the research semantic-lane taus with the wild-junk
quantile method (the 2026-07-04 sem-assign calibration finding: gold-derived
taus transfer badly; the honest tau is the one an in-the-wild RANDOM corpus
almost never clears).

Everything runs in SQL over pgvector — signal_embeddings (e5) and
dynamic_topics.centroid_vec live in the DB, so no local model is needed.

Measures:
  1. POOL HEALTH: active centroid count (the substrate guard threshold input).
  2. MEMBER-CENTROID basis (current tau 0.80): max cosine of N random recent
     signal embeddings vs every active centroid → quantile table. The random
     corpus is topic-agnostic, so its max-similarity distribution IS the junk
     floor for query↔centroid matching in this pool.
  3. SIGNAL-HEADLINE basis (current tau 0.84): pairwise max cosine between two
     disjoint random signal samples (random signal treated as a pseudo-query)
     → junk floor for query↔headline matching.

Suggested tau = the similarity at which ≤ --clearance (default 0.5%) of the
random corpus clears. Compare against the hardcoded values in
app/services/research_semantic.py and update them THERE (with a dated note).

Usage:
  python backend/scripts/recalibrate_research_taus.py [--sample 1500]
      [--clearance 0.005] [--hours 96]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

POOL_SQL = """
    SELECT count(*) AS n_active
    FROM dynamic_topics
    WHERE state = 'active' AND is_roundup = FALSE AND centroid_vec IS NOT NULL
"""

# Max cosine of each random signal vs ALL active centroids (junk floor for the
# member_centroid basis). Random recent signals = the wild corpus.
CENTROID_FLOOR_SQL = """
    WITH sample AS (
        SELECT e.signal_id, e.vec
        FROM signal_embeddings e
        JOIN signals_v2 s ON s.id = e.signal_id
        WHERE s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
        ORDER BY random()
        LIMIT $2
    )
    SELECT sample.signal_id,
           max(1 - (sample.vec <=> dt.centroid_vec::halfvec)) AS max_sim
    FROM sample
    CROSS JOIN dynamic_topics dt
    WHERE dt.state = 'active' AND dt.is_roundup = FALSE AND dt.centroid_vec IS NOT NULL
    GROUP BY sample.signal_id
"""

# Pairwise max cosine between two disjoint random samples (junk floor for the
# signal_headline basis: a random 'query' vs the corpus).
SIGNAL_FLOOR_SQL = """
    WITH q AS (
        SELECT e.signal_id, e.vec
        FROM signal_embeddings e
        JOIN signals_v2 s ON s.id = e.signal_id
        WHERE s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
          AND e.signal_id % 2 = 0
        ORDER BY random()
        LIMIT $2
    ), corpus AS (
        SELECT e.vec
        FROM signal_embeddings e
        JOIN signals_v2 s ON s.id = e.signal_id
        WHERE s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
          AND e.signal_id % 2 = 1
        ORDER BY random()
        LIMIT $3
    )
    SELECT q.signal_id, max(1 - (q.vec <=> corpus.vec)) AS max_sim
    FROM q CROSS JOIN corpus
    GROUP BY q.signal_id
"""


def _quantiles(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {}
    v = sorted(vals)
    n = len(v)
    pick = lambda p: v[min(n - 1, int(p * n))]  # noqa: E731
    return {"p50": pick(0.50), "p90": pick(0.90), "p95": pick(0.95),
            "p99": pick(0.99), "p995": pick(0.995), "max": v[-1]}


def _suggest_tau(vals: list[float], clearance: float) -> float | None:
    """Smallest similarity that ≤ `clearance` of the random corpus clears."""
    if not vals:
        return None
    v = sorted(vals)
    idx = min(len(v) - 1, int((1.0 - clearance) * len(v)))
    return v[idx]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=1500)
    ap.add_argument("--corpus", type=int, default=4000,
                    help="corpus size for the signal-headline floor")
    ap.add_argument("--clearance", type=float, default=0.005)
    ap.add_argument("--hours", type=int, default=96)
    args = ap.parse_args()

    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        pool_row = await conn.fetchrow(POOL_SQL)
        n_active = pool_row["n_active"]
        print(f"pool health: {n_active} active centroids "
              f"({'HEALTHY' if n_active >= 80 else 'THIN — guard active, centroid taus unreliable'})")

        cent = await conn.fetch(CENTROID_FLOOR_SQL, args.hours, args.sample, timeout=300)
        cent_sims = [float(r["max_sim"]) for r in cent]

        sig = await conn.fetch(SIGNAL_FLOOR_SQL, args.hours, args.sample, args.corpus, timeout=300)
        sig_sims = [float(r["max_sim"]) for r in sig]
    finally:
        await conn.close()

    out = {
        "pool_active_centroids": n_active,
        "sampled": {"centroid_basis": len(cent_sims), "signal_basis": len(sig_sims)},
        "member_centroid": {
            "current_tau": 0.80,
            "junk_quantiles": {k: round(x, 4) for k, x in _quantiles(cent_sims).items()},
            "suggested_tau": (round(t, 4) if (t := _suggest_tau(cent_sims, args.clearance)) else None),
        },
        "signal_headline": {
            "current_tau": 0.84,
            "junk_quantiles": {k: round(x, 4) for k, x in _quantiles(sig_sims).items()},
            "suggested_tau": (round(t, 4) if (t := _suggest_tau(sig_sims, args.clearance)) else None),
        },
        "clearance": args.clearance,
        "note": ("suggested_tau = similarity that only `clearance` of a RANDOM "
                 "recent corpus clears (wild-junk-quantile, sem-assign method "
                 "2026-07-04). If suggested >> current, the current tau admits "
                 "junk; if suggested << current, recall is being left on the "
                 "table. Update research_semantic.py constants with a dated note."),
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
