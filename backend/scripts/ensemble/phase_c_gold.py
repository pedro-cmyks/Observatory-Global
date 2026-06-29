"""Taxonomy revision — Phase C gold (crisis-only, BATCHED) (#204).

Phase C's random sample was non-crisis-heavy, so its +20pp agreement was driven by
the reject class. This measures IN-CATEGORY separability on a crisis-only
(gate-kept) sample, and does it in ONE batched call per annotator (defeats the
per-signal 429/quota that broke the fan-out). Annotators that bill no Claude API:
  - deepseek, openai : one batched API call each (subscription/credits permitting)
  - claude           : the orchestrator labels the same batch (this session's
                       subscription) — `--combine` merges a claude-labels file.

Modes:
  (default) sample + DeepSeek/OpenAI batched labels → gold-batch.json (+ prints the
            numbered headlines for the Claude annotator)
  --combine <claude_labels.json>  merge Claude labels + report pairwise agreement

Run: python -m backend.scripts.ensemble.phase_c_gold --n 40
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import asyncpg
import httpx

from backend.scripts.ensemble.model_clients import call_llm, extract_json

CAND = "docs/research/taxonomy-revision/candidate-v2.json"
BATCH = "docs/research/taxonomy-revision/gold-batch.json"
API_ANNOTATORS = ("deepseek", "openai")


async def _sample(conn, n: int) -> list[dict]:
    rows = await conn.fetch(
        """SELECT DISTINCT ON (s.headline) s.id, s.headline
           FROM signal_topic_assignments a JOIN signals_v2 s ON s.id=a.signal_id
           WHERE a.model_version='theme-hint-lex-v2' AND a.gate_kept=true
             AND s.headline IS NOT NULL AND length(s.headline)>=25
             AND a.assigned_at > NOW() - INTERVAL '336 hours'
           ORDER BY s.headline, random() LIMIT $1""", n)
    return [{"n": i + 1, "headline": r["headline"]} for i, r in enumerate(rows)]


def _batch_prompt(cand, sample) -> str:
    cats = "\n".join(
        f"- {c['slug']}: INCL {c.get('includes','')[:60]} | EXCL {c.get('excludes','')[:60]}"
        for c in cand["categories"])
    items = "\n".join(f'{it["n"]}. {it["headline"]}' for it in sample)
    return (f"OUT_OF_SCOPE policy: {cand['out_of_scope_policy']}\n\n"
            f"Crisis categories:\n{cats}\n\n"
            f"Classify EACH headline into exactly one slug, or OUT_OF_SCOPE per the policy.\n"
            f"Headlines:\n{items}\n\n"
            'Reply ONLY JSON: {"labels": [{"n": 1, "slug": "..."}, ...]} for all of them.')


async def _annotate(provider, client, prompt, valid, n) -> dict[int, str]:
    txt = await call_llm(provider, system="You reply only with one valid JSON object.",
                         user=prompt, client=client, max_tokens=3000, json_mode=True)
    data = extract_json(txt)
    out = {}
    for lab in data.get("labels", []):
        try:
            i, s = int(lab["n"]), str(lab["slug"]).strip()
        except Exception:  # noqa: BLE001
            continue
        out[i] = s if s in valid else "OUT_OF_SCOPE"
    return out


def _agreement(labels_by_ann: dict[str, dict[int, str]], ns: list[int]) -> None:
    anns = list(labels_by_ann)
    import itertools
    print("\n=== pairwise in-category agreement (crisis-only sample) ===")
    for a, b in itertools.combinations(anns, 2):
        both = [n for n in ns if labels_by_ann[a].get(n) and labels_by_ann[b].get(n)]
        agree = sum(1 for n in both if labels_by_ann[a][n] == labels_by_ann[b][n])
        non_oos = [n for n in both if labels_by_ann[a][n] != "OUT_OF_SCOPE"
                   and labels_by_ann[b][n] != "OUT_OF_SCOPE"]
        agree_in = sum(1 for n in non_oos if labels_by_ann[a][n] == labels_by_ann[b][n])
        print(f"  {a} vs {b}: overall {agree}/{len(both)}={agree/max(len(both),1):.0%}  | "
              f"in-category (both non-OOS) {agree_in}/{len(non_oos)}={agree_in/max(len(non_oos),1):.0%}")
    # unanimous
    unan = sum(1 for n in ns if len({labels_by_ann[a].get(n) for a in anns if labels_by_ann[a].get(n)}) == 1
               and all(labels_by_ann[a].get(n) for a in anns))
    print(f"  unanimous (all {len(anns)} annotators agree): {unan}/{len(ns)} = {unan/max(len(ns),1):.0%}")


async def run(n: int) -> int:
    dsn = os.environ.get("DATABASE_URL")
    with open(CAND) as f:
        cand = json.load(f)
    conn = await asyncpg.connect(dsn)
    try:
        sample = await _sample(conn, n)
    finally:
        await conn.close()
    valid = {c["slug"] for c in cand["categories"]} | {"OUT_OF_SCOPE"}
    prompt = _batch_prompt(cand, sample)
    print(f"crisis-only sample={len(sample)} | v2 cats={len(cand['categories'])}")

    labels = {}
    async with httpx.AsyncClient(timeout=180.0) as client:
        for p in API_ANNOTATORS:
            try:
                labels[p] = await _annotate(p, client, prompt, valid, len(sample))
                print(f"  {p}: labeled {len(labels[p])}/{len(sample)}")
            except Exception as exc:  # noqa: BLE001
                print(f"  {p}: FAILED {str(exc)[:120]}", file=sys.stderr)
    out = {"candidate": "v2", "sample": sample, "labels": labels}
    os.makedirs(os.path.dirname(BATCH), exist_ok=True)
    with open(BATCH, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n  saved {BATCH}")
    print("  → CLAUDE annotator (this session, subscription): label the numbered "
          "headlines below into v2 slugs / OUT_OF_SCOPE, then re-run with "
          "--combine <claude.json> ([{\"n\":1,\"slug\":\"...\"}, ...]).\n")
    for it in sample:
        print(f"    {it['n']:>2}. {it['headline'][:110]}")
    return 0


def combine(claude_path: str) -> int:
    with open(BATCH) as f:
        data = json.load(f)
    with open(claude_path) as f:
        cl = json.load(f)
    claude = {int(x["n"]): str(x["slug"]).strip() for x in (cl if isinstance(cl, list) else cl.get("labels", []))}
    labels_by_ann = {**{k: {int(i): v for i, v in d.items()} for k, d in data["labels"].items()},
                     "claude": claude}
    ns = [it["n"] for it in data["sample"]]
    _agreement(labels_by_ann, ns)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--combine", type=str, default=None)
    args = ap.parse_args()
    if args.combine:
        return combine(args.combine)
    return asyncio.run(run(args.n))


if __name__ == "__main__":
    raise SystemExit(main())
