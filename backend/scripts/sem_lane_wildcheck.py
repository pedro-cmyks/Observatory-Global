#!/usr/bin/env python
"""Wild-corpus inflow check for the semantic assignment lane (OpenAI space).

The tau_sem calibration runs on the gold corpus — a lexicon-biased sample
whose negatives share vocabulary with the topics (hard negatives). What it
CANNOT measure is the wrong-candidate INFLOW rate on the real hot corpus:
random signals are mostly off-ALL-topics, and the argmax rule still hands
each one a top-1 anchor. This script samples random recent headlines, embeds
them with text-embedding-3-small, applies the calibrated argmax+tau rule and
reports the clearance rate per topic + example headlines for the eyeball.

Go/no-go: if random-corpus clearance is small and the cleared examples are
plausibly on-topic, the lane's candidate precision in the wild is bounded
by the gate downstream; if clearance is large/junk, the lane needs a higher
floor before it exists.

Usage:
  python backend/scripts/sem_lane_wildcheck.py \
      --calibration docs/research/semantic-lane/2026-07-04-tau-sem-openai.json \
      --taxonomy docs/research/taxonomy-revision/candidate-v2.json \
      --sample 2000 --hours 48 \
      --out docs/research/semantic-lane/2026-07-04-wildcheck
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
    SELECT s.id, s.headline, s.source_lang, s.country_code,
           EXISTS (SELECT 1 FROM signal_topic_assignments a
                   WHERE a.signal_id = s.id) AS has_assignment
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
    a = np.asarray(vecs, dtype=np.float32)
    return a / np.linalg.norm(a, axis=1, keepdims=True)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", required=True)
    ap.add_argument("--taxonomy", required=True)
    ap.add_argument("--sample", type=int, default=2000)
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--rule", default="argmax", choices=["argmax"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    calib = json.load(open(args.calibration))
    assert calib["engine"] == "openai", "wildcheck is for the openai lane"
    fk = str(calib["primary_floor"])
    taus = {}
    for slug, e in calib["rules"]["argmax"].items():
        f = e["floors"].get(fk)
        if f:
            taus[slug] = f["tau"]
    tax = json.load(open(args.taxonomy))
    cats = {c["slug"]: c for c in tax["categories"]}
    slugs = [s for s in taus if s in cats]

    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        rows = await conn.fetch(SAMPLE_SQL, args.hours, args.sample)
    finally:
        await conn.close()
    if not rows:
        print("no rows sampled", file=sys.stderr)
        return 1

    anchor_texts = [
        f"{cats[s]['label']}. {cats[s]['definition']} {cats[s]['includes']}"
        for s in slugs
    ]
    print(f"sampled {len(rows)} random signals ({args.hours}h window); "
          f"embedding + {len(slugs)} anchors...", file=sys.stderr)
    A = openai_embed(anchor_texts)
    H = openai_embed([html.unescape(r["headline"]) for r in rows])
    sims = H @ A.T
    top1 = sims.argmax(axis=1)
    top1_sim = sims[np.arange(len(rows)), top1]

    tau_vec = np.array([taus[s] for s in slugs])
    clears = top1_sim >= tau_vec[top1]

    per_topic: dict[str, dict] = {s: {"cleared": 0, "examples": []} for s in slugs}
    for i in np.where(clears)[0]:
        s = slugs[top1[i]]
        per_topic[s]["cleared"] += 1
        if len(per_topic[s]["examples"]) < 8:
            per_topic[s]["examples"].append(
                {"headline": rows[i]["headline"][:140],
                 "sim": round(float(top1_sim[i]), 3),
                 "lang": rows[i]["source_lang"],
                 "cc": rows[i]["country_code"],
                 "already_assigned": bool(rows[i]["has_assignment"])})

    n_clear = int(clears.sum())
    already = int(sum(1 for i in np.where(clears)[0] if rows[i]["has_assignment"]))
    result = {
        "schema": "sem-lane-wildcheck-v0",
        "n_sampled": len(rows), "hours": args.hours,
        "n_cleared": n_clear,
        "clearance_rate": n_clear / len(rows),
        "cleared_already_assigned": already,
        "cleared_new_candidates": n_clear - already,
        "per_topic": {s: v for s, v in per_topic.items() if v["cleared"]},
        "taus_used": taus,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(result, indent=1))

    lines = [
        "# Semantic-lane wild-corpus inflow check",
        "",
        f"{len(rows)} random hot signals ({args.hours}h) vs argmax+tau "
        f"(floor {fk}): **{n_clear} clear ({n_clear/len(rows):.1%})** — "
        f"{already} already lexicon-assigned, {n_clear - already} would be "
        "NEW lane candidates (the gate still grades them downstream).",
        "",
    ]
    for s, v in sorted(result["per_topic"].items(), key=lambda kv: -kv[1]["cleared"]):
        lines.append(f"## {s} — {v['cleared']} cleared (tau {taus[s]:.3f})")
        for ex in v["examples"]:
            flag = " [assigned]" if ex["already_assigned"] else ""
            lines.append(f"- {ex['sim']:.3f} [{ex['lang']}/{ex['cc']}] "
                         f"{ex['headline']}{flag}")
        lines.append("")
    out.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print(json.dumps({k: result[k] for k in
                      ("n_sampled", "n_cleared", "clearance_rate",
                       "cleared_new_candidates")}, indent=1))
    print(f"wrote {out.with_suffix('.json')} + .md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
