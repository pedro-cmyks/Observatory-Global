#!/usr/bin/env python
"""Semantic assignment pass — OpenAI space, argmax rule, wild-calibrated taus.

Spec: docs/specs/2026-07-04-semantic-assignment-lane.md (+ the 2026-07-04
calibration arc: e5 absolute-cosine FAILED the noise floor; OpenAI
text-embedding-3-small + argmax + wild-junk-quantile taus passed — see
docs/research/semantic-lane/2026-07-04-tau-sem-wild.md, 24/30 lanes on).

Per run: embeds the anchors (candidate-v2 text) and every recent headline
with text-embedding-3-small (~$0.06 per 150k headlines), routes each signal
to its argmax anchor, and INSERTs (signal, topic) as method='embedding',
model_version='sem-assign-v0' when sim >= that topic's wild-calibrated tau
and no assignment to that topic exists yet (any lane). The scope gate then
grades these like any candidate (score_assignments_gate.py --lane semantic);
two-tier serving is untouched — the lane only widens the candidate universe.

Env: DATABASE_URL, OPENAI_API_KEY. Run on the M1 next to the classifier cron.

Usage:
  python backend/scripts/sem_assign_pass.py \
      --calibration docs/research/semantic-lane/2026-07-04-tau-sem-wild.json \
      --taxonomy docs/research/taxonomy-revision/candidate-v2.json \
      --window-hours 24 [--max-signals 200000] [--write]
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import sys

import numpy as np

OPENAI_MODEL = "text-embedding-3-small"
MODEL_VERSION = "sem-assign-v0"

SIGNALS_SQL = """
    SELECT s.id, s.headline
    FROM signals_v2 s
    WHERE s.created_at > NOW() - ($1::real * INTERVAL '1 hour')
      AND s.headline IS NOT NULL AND length(s.headline) > 20
    ORDER BY s.created_at DESC
    LIMIT $2
"""

EXISTING_SQL = """
    SELECT a.signal_id, a.topic_id
    FROM signal_topic_assignments a
    WHERE a.signal_id = ANY($1::bigint[])
"""

INSERT_SQL = """
    INSERT INTO signal_topic_assignments
        (signal_id, topic_id, method, confidence, model_name, model_version,
         evidence, assigned_at)
    VALUES ($1, $2, 'embedding', $3, $4, $5, $6::jsonb, NOW())
    ON CONFLICT (signal_id, topic_id, method, model_version) DO UPDATE SET
        confidence = EXCLUDED.confidence,
        evidence = EXCLUDED.evidence,
        assigned_at = NOW();
"""


def openai_embed(texts: list[str], tag: str) -> np.ndarray:
    import openai
    client = openai.OpenAI(timeout=120.0)
    vecs: list[list[float]] = []
    for i in range(0, len(texts), 512):
        chunk = [t[:2000] for t in texts[i : i + 512]]
        for attempt in range(1, 6):
            try:
                resp = client.embeddings.create(model=OPENAI_MODEL, input=chunk)
                break
            except Exception:  # noqa: BLE001
                if attempt == 5:
                    raise
                import time
                time.sleep(2.0 * attempt)
        vecs.extend(d.embedding for d in resp.data)
        if (i // 512) % 20 == 0:
            print(f"  {tag}: embedded {min(i + 512, len(texts))}/{len(texts)}",
                  file=sys.stderr)
    a = np.asarray(vecs, dtype=np.float32)
    return a / np.linalg.norm(a, axis=1, keepdims=True)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", required=True,
                    help="tau-sem-wild-calibration json (rule=argmax)")
    ap.add_argument("--taxonomy", required=True)
    ap.add_argument("--window-hours", type=float, default=24.0)
    ap.add_argument("--max-signals", type=int, default=200_000)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    calib = json.load(open(args.calibration))
    assert calib.get("rule") == "argmax" and calib.get("model") == OPENAI_MODEL
    tax = json.load(open(args.taxonomy))
    cats = {c["slug"]: c for c in tax["categories"]}
    lanes = {s: e for s, e in calib["per_topic"].items()
             if e.get("lane_on") and s in cats}
    if not lanes:
        print("no lanes on in calibration", file=sys.stderr)
        return 1
    slugs = sorted(lanes)

    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        topic_rows = await conn.fetch("SELECT id, slug FROM atlas_topics")
        id_of = {r["slug"]: r["id"] for r in topic_rows}
        slugs = [s for s in slugs if s in id_of]

        sig = await conn.fetch(SIGNALS_SQL, args.window_hours, args.max_signals)
        if len(sig) == args.max_signals:
            print(f"WARN: window truncated at --max-signals {args.max_signals}",
                  file=sys.stderr)
        if not sig:
            print("no signals in window")
            return 0
        est_tokens = sum(len(r["headline"]) for r in sig) / 4
        print(f"{len(sig)} signals / {len(slugs)} lanes; est embed cost "
              f"${est_tokens / 1e6 * 0.02:.3f}", file=sys.stderr)

        A = openai_embed(
            [f"{cats[s]['label']}. {cats[s]['definition']} {cats[s]['includes']}"
             for s in slugs], "anchors")
        H = openai_embed([html.unescape(r["headline"]) for r in sig], "signals")

        sims = H @ A.T
        top1 = sims.argmax(axis=1)
        top1_sim = sims[np.arange(len(sig)), top1]
        taus = np.array([lanes[s]["tau"] for s in slugs], dtype=np.float32)
        hit = top1_sim >= taus[top1]

        hit_idx = np.where(hit)[0]
        hit_ids = [int(sig[i]["id"]) for i in hit_idx]
        existing = await conn.fetch(EXISTING_SQL, hit_ids) if hit_ids else []
        already = {(r["signal_id"], r["topic_id"]) for r in existing}

        per_topic: dict[str, int] = {}
        wrote = skipped_existing = 0
        for i in hit_idx:
            s = slugs[top1[i]]
            tid = id_of[s]
            sid = int(sig[i]["id"])
            if (sid, tid) in already:
                skipped_existing += 1
                continue
            per_topic[s] = per_topic.get(s, 0) + 1
            if args.write:
                await conn.execute(
                    INSERT_SQL, sid, tid, float(top1_sim[i]),
                    OPENAI_MODEL, MODEL_VERSION,
                    json.dumps({"lane": "semantic", "rule": "argmax",
                                "anchor_sim": round(float(top1_sim[i]), 4),
                                "tau_sem": float(taus[top1[i]])}))
                wrote += 1

        for s in sorted(per_topic, key=lambda k: -per_topic[k]):
            print(f"  {s}: +{per_topic[s]}")
        print(f"{'wrote' if args.write else 'DRY-RUN'} "
              f"{wrote if args.write else sum(per_topic.values())} semantic "
              f"assignments ({skipped_existing} already assigned; "
              f"{len(hit_ids)} cleared of {len(sig)} scanned, "
              f"{len(hit_ids)/len(sig):.2%})")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
