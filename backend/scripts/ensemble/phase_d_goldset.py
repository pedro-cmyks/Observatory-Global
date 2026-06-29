"""Taxonomy revision — Phase D: broad ensemble gold base (#204).

A big general pass over many topics: stratified sample across ALL categories +
random recent (for out-of-scope diversity), labeled by the 3 scriptable models
(DeepSeek + OpenAI + Codex/ChatGPT-sub) under the v2 taxonomy, batched in chunks.
Builds a reusable LABELED EMBEDDING BASE — (signal_id, headline, e5 embedding
present?, the 3 model labels, the majority gold label, agreement) — the training/
eval foundation for a v2 gate. Disagreements are flagged for Claude (senior
annotator) adjudication.

Grows our base + validates the taxonomy at scale, no Claude API.
Run: python -m backend.scripts.ensemble.phase_d_goldset --per-slug 5 --random 40 --chunk 30
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter

import asyncpg
import httpx

from backend.scripts.ensemble.model_clients import call_codex, call_llm, extract_json

CAND = "docs/research/taxonomy-revision/candidate-v2.json"
OUT = "docs/research/taxonomy-revision/goldset.json"
API = ("deepseek", "openai")


async def _stratified(conn, per_slug: int, n_random: int) -> list[dict]:
    strat = await conn.fetch(
        """
        WITH ranked AS (
          SELECT s.id, s.headline, at.slug AS cur,
                 row_number() OVER (PARTITION BY at.slug ORDER BY random()) AS rn,
                 (e.signal_id IS NOT NULL) AS embedded
          FROM signal_topic_assignments a
          JOIN atlas_topics at ON at.id=a.topic_id
          JOIN signals_v2 s ON s.id=a.signal_id
          LEFT JOIN signal_embeddings e ON e.signal_id=s.id
          WHERE a.model_version='theme-hint-lex-v2' AND a.gate_kept=true
            AND s.headline IS NOT NULL AND length(s.headline)>=25
            AND a.assigned_at > NOW() - INTERVAL '672 hours'
        )
        SELECT id, headline, cur, embedded FROM ranked WHERE rn <= $1
        """, per_slug)
    rnd = await conn.fetch(
        """SELECT DISTINCT ON (s.headline) s.id, s.headline, NULL::text AS cur,
                  (e.signal_id IS NOT NULL) AS embedded
           FROM signals_v2 s LEFT JOIN signal_embeddings e ON e.signal_id=s.id
           WHERE s.headline IS NOT NULL AND length(s.headline)>=25
             AND s.timestamp > NOW() - INTERVAL '72 hours'
           ORDER BY s.headline, random() LIMIT $1""", n_random)
    seen, out = set(), []
    for r in list(strat) + list(rnd):
        h = r["headline"]
        if h in seen:
            continue
        seen.add(h)
        out.append({"n": len(out) + 1, "id": r["id"], "headline": h,
                    "cur": r["cur"], "embedded": r["embedded"]})
    return out


def _prompt(cand, chunk) -> str:
    cats = "\n".join(f"- {c['slug']}: INCL {c.get('includes','')[:55]} | EXCL {c.get('excludes','')[:55]}"
                     for c in cand["categories"])
    items = "\n".join(f'{it["n"]}. {it["headline"]}' for it in chunk)
    return (f"OUT_OF_SCOPE policy: {cand['out_of_scope_policy']}\n\nCategories:\n{cats}\n\n"
            f"Classify EACH headline into one slug or OUT_OF_SCOPE per the policy.\n{items}\n\n"
            'Reply ONLY JSON {"labels":[{"n":N,"slug":"..."}]} for ALL of them.')


def _parse(txt, valid) -> dict[int, str]:
    out = {}
    for lab in extract_json(txt).get("labels", []):
        try:
            out[int(lab["n"])] = (str(lab["slug"]).strip()
                                  if str(lab["slug"]).strip() in valid else "OUT_OF_SCOPE")
        except Exception:  # noqa: BLE001
            continue
    return out


async def run(per_slug: int, n_random: int, chunk: int) -> int:
    dsn = os.environ.get("DATABASE_URL")
    with open(CAND) as f:
        cand = json.load(f)
    valid = {c["slug"] for c in cand["categories"]} | {"OUT_OF_SCOPE"}
    conn = await asyncpg.connect(dsn)
    try:
        sample = await _stratified(conn, per_slug, n_random)
    finally:
        await conn.close()
    chunks = [sample[i:i + chunk] for i in range(0, len(sample), chunk)]
    print(f"sample={len(sample)} ({sum(s['embedded'] for s in sample)} embedded) | "
          f"{len(chunks)} chunks of ≤{chunk} | annotators=deepseek,openai,codex")

    labels = {a: {} for a in (*API, "codex")}
    async with httpx.AsyncClient(timeout=180.0) as client:
        for ci, ch in enumerate(chunks):
            prompt = _prompt(cand, ch)
            base = {it["n"]: it for it in ch}
            for a in API:
                try:
                    for n, sl in _parse(await call_llm(a, system="Reply only one JSON object.",
                                                       user=prompt, client=client, max_tokens=2600), valid).items():
                        if n in base:
                            labels[a][n] = sl
                except Exception as exc:  # noqa: BLE001
                    print(f"  chunk{ci} {a} FAIL {str(exc)[:80]}", file=sys.stderr)
            try:
                for n, sl in _parse(call_codex(prompt), valid).items():
                    if n in base:
                        labels["codex"][n] = sl
            except Exception as exc:  # noqa: BLE001
                print(f"  chunk{ci} codex FAIL {str(exc)[:80]}", file=sys.stderr)
            print(f"  chunk {ci+1}/{len(chunks)} done")

    # aggregate → gold (majority of 3) + agreement
    anns = [a for a in (*API, "codex")]
    records, unanimous, disagree, oos = [], 0, [], 0
    for it in sample:
        n = it["n"]
        votes = [labels[a].get(n) for a in anns if labels[a].get(n)]
        if not votes:
            continue
        c = Counter(votes)
        gold, top = c.most_common(1)[0]
        rec = {"id": it["id"], "headline": it["headline"], "current": it["cur"],
               "embedded": it["embedded"], **{a: labels[a].get(n) for a in anns},
               "gold": gold, "agree_n": top, "n_votes": len(votes)}
        records.append(rec)
        if top == len(votes) and len(votes) == len(anns):
            unanimous += 1
        if top == 1 and len(votes) >= 2:  # 3-way split → no majority
            disagree.append(rec)
        if gold == "OUT_OF_SCOPE":
            oos += 1

    # ACCUMULATE: merge with any existing goldset (dedupe by signal id) so repeated
    # broad passes grow the base instead of overwriting it.
    prior = {}
    if os.path.exists(OUT):
        try:
            with open(OUT) as f:
                for r in json.load(f).get("records", []):
                    prior[r["id"]] = r
        except Exception:  # noqa: BLE001
            pass
    for r in records:
        prior[r["id"]] = r
    all_records = list(prior.values())
    tot_unan = sum(1 for r in all_records
                   if r.get("agree_n") == r.get("n_votes") == len(anns))
    tot_oos = sum(1 for r in all_records if r.get("gold") == "OUT_OF_SCOPE")
    tot_emb = sum(1 for r in all_records if r.get("embedded"))
    with open(OUT, "w") as f:
        json.dump({"candidate": "v2", "annotators": anns, "n": len(all_records),
                   "unanimous": tot_unan, "oos_gold": tot_oos, "embedded": tot_emb,
                   "records": all_records}, f, indent=2, ensure_ascii=False)
    print(f"  ACCUMULATED base now: {len(all_records)} labeled "
          f"({tot_unan} unanimous, {tot_oos} OOS, {tot_emb} embedded)")
    print(f"\n=== goldset base: {len(records)} labeled ===")
    print(f"  unanimous (3/3): {unanimous}/{len(records)} = {unanimous/max(len(records),1):.0%}")
    print(f"  3-way disagreements (need Claude adjudication): {len(disagree)}")
    print(f"  gold OUT_OF_SCOPE: {oos}/{len(records)} = {oos/max(len(records),1):.0%}")
    print(f"  embedded (labeled-embedding base): {sum(r['embedded'] for r in records)}/{len(records)}")
    # gold distribution
    dist = Counter(r["gold"] for r in records)
    print("  gold label distribution (top 12):")
    for sl, k in dist.most_common(12):
        print(f"    {sl:34s} {k}")
    print(f"\n  saved {OUT} (disagreements flagged for adjudication)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-slug", type=int, default=5)
    ap.add_argument("--random", type=int, default=40)
    ap.add_argument("--chunk", type=int, default=30)
    args = ap.parse_args()
    return asyncio.run(run(args.per_slug, args.random, args.chunk))


if __name__ == "__main__":
    raise SystemExit(main())
