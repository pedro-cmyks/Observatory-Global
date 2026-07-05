#!/usr/bin/env python
"""Joint (gold + wild) tau_sem calibration — the base-rate-honest pass.

The gold-corpus calibration picks taus at a precision floor measured on
lexicon candidates (base rate 40-80%). The wildcheck showed those taus admit
~30% of RANDOM corpus (junk floods every topic) — classic base-rate transfer
failure. This script calibrates the other way around:

  tau_T = lowest tau whose WILD clearance (random hot sample, argmax rule)
          is <= --max-wild-fp rows per sample (default 1/2000 = 0.05%),
  then reports the GOLD positive recall surviving at that tau.

A topic keeps its lane only if that recall is still useful; everything else
gets tau NULL (lane off). Precision in the wild is then bounded by junk
density <= max-wild-fp per pass window, and the gate still grades whatever
enters.

Embeds gold + wild + anchors with text-embedding-3-small (~$0.01).

Usage:
  mlvenv/bin/python backend/scripts/calibrate_tau_wild.py \
      --corpus /tmp/goldgrowth/mega2-corpus.jsonl \
      --taxonomy docs/research/taxonomy-revision/candidate-v2.json \
      --sample 2000 --hours 48 --max-wild-fp 1 \
      --out docs/research/semantic-lane/2026-07-04-tau-sem-wild
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import sys
from pathlib import Path

import numpy as np

OPENAI_MODEL = "text-embedding-3-small"

SAMPLE_SQL = """
    SELECT s.id, s.headline, s.source_lang, s.country_code
    FROM signals_v2 s
    WHERE s.created_at > NOW() - ($1::int * INTERVAL '1 hour')
      AND s.headline IS NOT NULL AND length(s.headline) > 20
    ORDER BY random()
    LIMIT $2
"""


def openai_embed(texts: list[str]) -> np.ndarray:
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
        print(f"  embedded {min(i + 512, len(texts))}/{len(texts)}",
              file=sys.stderr)
    a = np.asarray(vecs, dtype=np.float32)
    return a / np.linalg.norm(a, axis=1, keepdims=True)


async def fetch_wild(hours: int, sample: int):
    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        raise SystemExit(2)
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        return await conn.fetch(SAMPLE_SQL, hours, sample)
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--taxonomy", required=True)
    ap.add_argument("--sample", type=int, default=2000)
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--max-wild-fp", type=int, default=1,
                    help="max wild rows allowed to clear per topic in the sample")
    ap.add_argument("--min-recall", type=float, default=0.10,
                    help="lane off for topics whose surviving gold recall < this")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.corpus) if l.strip()]
    tax = json.load(open(args.taxonomy))
    cats = {c["slug"]: c for c in tax["categories"]}
    rows = [r for r in rows if r["assigned_topic_slug"] in cats]
    slugs = sorted({r["assigned_topic_slug"] for r in rows})
    idx = {s: i for i, s in enumerate(slugs)}

    wild = asyncio.run(fetch_wild(args.hours, args.sample))
    print(f"gold {len(rows)} rows / wild {len(wild)} rows / "
          f"{len(slugs)} anchors", file=sys.stderr)

    anchor_texts = [
        f"{cats[s]['label']}. {cats[s]['definition']} {cats[s]['includes']}"
        for s in slugs
    ]
    A = openai_embed(anchor_texts)
    G = openai_embed([html.unescape(r["headline"]) for r in rows])
    W = openai_embed([html.unescape(r["headline"]) for r in wild])

    y = np.array([bool(r["is_evidence"]) for r in rows], dtype=int)
    topic_i = np.array([idx[r["assigned_topic_slug"]] for r in rows])

    gs = G @ A.T
    ws = W @ A.T
    g_top1 = gs.argmax(axis=1)
    w_top1 = ws.argmax(axis=1)
    w_top1_sim = ws[np.arange(len(wild)), w_top1]

    per_topic = {}
    lane_on = 0
    for s in slugs:
        j = idx[s]
        # wild sims routed to this topic by argmax
        wj = np.sort(w_top1_sim[w_top1 == j])[::-1]
        if len(wj) > args.max_wild_fp:
            # tau just above the (max_wild_fp+1)-th wild sim
            tau = float(wj[args.max_wild_fp]) + 1e-6
        else:
            # topic barely attracts wild rows; floor at the max wild sim seen
            tau = float(wj[0]) + 1e-6 if len(wj) else 0.25
        # gold recall at that tau under the argmax rule
        pos_mask = (topic_i == j) & (y == 1)
        n_pos = int(pos_mask.sum())
        caught = int(((g_top1 == j) & pos_mask &
                      (gs[:, j] >= tau)).sum())
        recall = caught / n_pos if n_pos else 0.0
        # in-corpus precision at tau (hard-negative bound, argmax-eligible)
        elig = (g_top1 == j) & (gs[:, j] >= tau)
        prec = float(y[elig].mean()) if elig.sum() else None
        keep = n_pos >= 10 and recall >= args.min_recall
        if keep:
            lane_on += 1
        per_topic[s] = {
            "tau": round(tau, 4), "n_positive": n_pos,
            "recall_at_tau": round(recall, 3), "caught": caught,
            "gold_precision_at_tau": None if prec is None else round(prec, 3),
            "wild_routed": int((w_top1 == j).sum()),
            "wild_cleared_at_tau": int((w_top1_sim[w_top1 == j] >= tau).sum()),
            "lane_on": keep,
        }

    result = {
        "schema": "tau-sem-wild-calibration-v0",
        "model": OPENAI_MODEL, "rule": "argmax",
        "corpus": args.corpus, "n_gold": len(rows), "n_wild": len(wild),
        "max_wild_fp": args.max_wild_fp, "min_recall": args.min_recall,
        "lanes_on": lane_on, "per_topic": per_topic,
        "note": "tau set by wild junk quantile (base-rate-honest); recall is "
                "gold argmax-recall at that tau; gold_precision is measured "
                "on lexicon hard negatives (upper bound irrelevant here — "
                "wild junk density is the binding constraint).",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(result, indent=1))

    lines = [
        "# tau_sem wild-calibrated (argmax, OpenAI space)",
        "",
        f"Rule: wild clearance <= {args.max_wild_fp}/{len(wild)} per topic; "
        f"lane ON iff gold recall at tau >= {args.min_recall} and >=10 "
        f"positives. **{lane_on}/{len(slugs)} lanes on.**",
        "",
        "| topic | tau | pos | recall@tau | goldP@tau | wild routed | wild clear | lane |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in slugs:
        e = per_topic[s]
        gp = e["gold_precision_at_tau"]
        gp_s = "—" if gp is None else f"{gp:.2f}"
        lines.append(
            f"| {s} | {e['tau']:.3f} | {e['n_positive']} | "
            f"{e['recall_at_tau']:.2f} | {gp_s} | "
            f"{e['wild_routed']} | {e['wild_cleared_at_tau']} | "
            f"{'ON' if e['lane_on'] else 'off'} |")
    out.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"lanes_on": lane_on,
                      "on": {s: e for s, e in per_topic.items() if e["lane_on"]}},
                     indent=1))
    print(f"wrote {out.with_suffix('.json')} + .md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
