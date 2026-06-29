"""Taxonomy revision — Phase C: inter-annotator agreement v1 vs v2 (#204).

The paper-grade test: does the candidate v2 (categories + OUT_OF_SCOPE reject +
per-category excludes) make independent annotators AGREE MORE than the current v1
taxonomy? Higher agreement = a clearer, more separable taxonomy. This is the
unconfounded benchmark the production-label LLM judge could not give.

For a sample of signals, each annotator (DeepSeek, GPT-4o) classifies the SAME
headline under both the v1 prompt and the v2 prompt; we compare pairwise agreement
(do the two models pick the same slug?) and the OUT_OF_SCOPE rate under each.

Run: python -m backend.scripts.ensemble.phase_c_agreement --n 40
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

ANNOTATORS = ("deepseek", "openai")
CAND = "docs/research/taxonomy-revision/candidate-v2.json"


async def _load_v1(conn) -> list[dict]:
    rows = await conn.fetch("SELECT slug, label, COALESCE(description,'') d FROM atlas_topics ORDER BY slug")
    return [dict(r) for r in rows]


async def _sample(conn, n: int) -> list[str]:
    # broad sample: recent signals (gate-kept and not) so we test real separability
    rows = await conn.fetch(
        """SELECT DISTINCT ON (headline) headline FROM signals_v2
           WHERE headline IS NOT NULL AND length(headline) >= 25
             AND timestamp > NOW() - INTERVAL '72 hours'
           ORDER BY headline, random() LIMIT $1""", n)
    return [r["headline"] for r in rows]


def _v1_prompt(v1, headline) -> str:
    cats = "\n".join(f"- {t['slug']}: {t['label']} — {t['d']}" for t in v1)
    return ("Classify the headline into one of these crisis categories, or "
            'OUT_OF_SCOPE if none fits.\n\n' f"{cats}\n\nHeadline: \"{headline}\"\n"
            'Reply ONLY JSON: {"slug": "<slug-or-OUT_OF_SCOPE>"}')


def _v2_prompt(cand, headline) -> str:
    cats = "\n".join(
        f"- {c['slug']}: {c.get('label','')} — INCLUDES {c.get('includes','')} | "
        f"EXCLUDES {c.get('excludes','')}" for c in cand["categories"])
    return (f"OUT_OF_SCOPE POLICY: {cand['out_of_scope_policy']}\n\n"
            f"Categories:\n{cats}\n\nHeadline: \"{headline}\"\n"
            'Assign exactly one slug, or OUT_OF_SCOPE per the policy. '
            'Reply ONLY JSON: {"slug": "<slug-or-OUT_OF_SCOPE>"}')


async def _classify(provider, client, prompt, valid) -> str | None:
    try:
        txt = await call_llm(provider, system="You reply only with compact JSON.",
                             user=prompt, client=client, max_tokens=40)
        s = str(extract_json(txt).get("slug", "")).strip()
        return s if s in valid else None
    except Exception as exc:  # noqa: BLE001
        print(f"  ({provider} err {str(exc)[:50]})", file=sys.stderr)
        return None


async def run(n: int) -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    with open(CAND) as f:
        cand = json.load(f)
    conn = await asyncpg.connect(dsn)
    try:
        v1 = await _load_v1(conn)
        sample = await _sample(conn, n)
    finally:
        await conn.close()
    v1_valid = {t["slug"] for t in v1} | {"OUT_OF_SCOPE"}
    v2_valid = {c["slug"] for c in cand["categories"]} | {"OUT_OF_SCOPE"}
    print(f"sample={len(sample)} | v1={len(v1)} cats | v2={len(cand['categories'])} cats | annotators={ANNOTATORS}")

    sem = asyncio.Semaphore(6)
    agree = {"v1": 0, "v2": 0}
    both = {"v1": 0, "v2": 0}
    oos = {"v1": 0, "v2": 0}
    seen = {"v1": 0, "v2": 0}

    async with httpx.AsyncClient(timeout=60.0) as client:
        async def one(headline):
            async with sem:
                p1 = {a: await _classify(a, client, _v1_prompt(v1, headline), v1_valid) for a in ANNOTATORS}
                p2 = {a: await _classify(a, client, _v2_prompt(cand, headline), v2_valid) for a in ANNOTATORS}
            for tag, picks in (("v1", p1), ("v2", p2)):
                a, b = picks[ANNOTATORS[0]], picks[ANNOTATORS[1]]
                if a and b:
                    both[tag] += 1
                    if a == b:
                        agree[tag] += 1
                for x in (a, b):
                    if x:
                        seen[tag] += 1
                        if x == "OUT_OF_SCOPE":
                            oos[tag] += 1
        await asyncio.gather(*[one(h) for h in sample])

    print("\n=== Phase C — inter-annotator agreement (DeepSeek vs GPT-4o) ===")
    for tag in ("v1", "v2"):
        ag = agree[tag] / both[tag] if both[tag] else 0
        oo = oos[tag] / seen[tag] if seen[tag] else 0
        print(f"  {tag}: agreement {agree[tag]}/{both[tag]} = {ag:.0%}  | OUT_OF_SCOPE {oo:.0%}")
    d = (agree['v2'] / both['v2'] if both['v2'] else 0) - (agree['v1'] / both['v1'] if both['v1'] else 0)
    print(f"\n  v2 agreement delta: {d:+.0%}")
    print("  VERDICT:", "v2 MORE separable — rewrite validated" if d > 0.03
          else ("comparable — v2's win is the honest reject, not separability" if d > -0.03
                else "v2 LESS separable — revise contested categories"))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    return asyncio.run(run(ap.parse_args().n))


if __name__ == "__main__":
    raise SystemExit(main())
