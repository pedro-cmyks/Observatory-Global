#!/usr/bin/env python3
"""Focused live validation of a scope gate on ONE topic (read-only).

Pulls a topic's recent assignments, embeds "headline | label" with the gate's
model, scores through the gate, and prints: score percentiles, the per-topic
threshold, kept count, and the TOP headlines by score — so we can see whether a
0% keep is "correctly rejecting off-topic garbage" or "a ~0.99 threshold killing
genuine coverage". Writes nothing.

  python -m scripts.validate_gate_topic --gate <v1.json> --slug election-legitimacy-dispute
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_assignments_gate import (  # noqa: E402
    _build_embedder, _load_gate, _matched_terms, _score_and_decide, _text_for,
)

SQL = """
    SELECT s.headline, t.label, a.confidence, a.evidence
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    JOIN signals_v2 s   ON s.id = a.signal_id
    WHERE a.method='lexicon' AND a.model_version='theme-hint-lex-v2'
      AND t.slug=$1 AND s.headline IS NOT NULL
      AND s.timestamp > NOW() - ($2::int * INTERVAL '1 hour')
    ORDER BY a.assigned_at DESC LIMIT $3
"""


async def main() -> None:
    import asyncpg

    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", type=Path, required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--limit", type=int, default=400)
    args = ap.parse_args()

    gate = _load_gate(args.gate)
    model_name = gate["feature_spec"]["embedding_model"]
    thr = gate["per_topic_threshold"].get(args.slug) or gate["global_threshold"]
    embed, _ = _build_embedder(model_name)

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(SQL, args.slug, args.hours, args.limit)
    finally:
        await conn.close()
    if not rows:
        print("no rows"); return

    texts = [_text_for(model_name, r["headline"], r["label"]) for r in rows]
    emb = embed(texts)
    conf = np.array([float(r["confidence"]) for r in rows])
    mt = np.array([_matched_terms(r["evidence"]) for r in rows])
    scores, kept = _score_and_decide(gate, emb, conf, mt, [args.slug] * len(rows))

    order = np.argsort(-scores)
    print(f"topic={args.slug} model={model_name} n={len(rows)} threshold={thr:.4f}")
    pct = {p: round(float(np.percentile(scores, p)), 4) for p in (50, 75, 90, 95, 99)}
    print(f"score pctiles: {pct} | max {scores.max():.4f} | kept {int(sum(kept))}")
    print("TOP 15 by score (is it on-topic? is the threshold cutting real ones?):")
    for i in order[:15]:
        mark = "KEEP" if kept[i] else "  · "
        print(f"  {mark} {scores[i]:.3f} | {(rows[i]['headline'] or '')[:88]}")


if __name__ == "__main__":
    asyncio.run(main())
