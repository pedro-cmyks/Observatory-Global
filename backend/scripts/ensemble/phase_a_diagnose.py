"""Taxonomy revision — Phase A: data-grounded diagnosis (#204).

Hypothesis (from the engine A/B): the current Atlas taxonomy is 100% crisis/risk
framed, so signals the gate KEEPS as evidence that are NOT a crisis get force-fit
into the nearest crisis bucket → low topical precision. This script quantifies it:
the ensemble classifies a sample of gate-kept evidence headlines against the
current 30 categories WITH an explicit OUT_OF_SCOPE option, and we measure the
force-fit (out-of-scope) rate + agreement with the current label.

Read-only on prod (samples signals). Calls DeepSeek + GPT-4o per headline.
Run:  python -m backend.scripts.ensemble.phase_a_diagnose --n 60
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import asyncpg
import httpx

from backend.scripts.ensemble.model_clients import API_PROVIDERS, call_llm, extract_json

DIAG_PROVIDERS = [p for p in API_PROVIDERS if p in ("deepseek", "openai")]


async def _load_taxonomy(conn) -> list[dict]:
    rows = await conn.fetch(
        "SELECT slug, label, COALESCE(description,'') AS description FROM atlas_topics ORDER BY slug")
    return [dict(r) for r in rows]


async def _load_sample(conn, n: int) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (s.headline) s.id, at.slug AS current_slug, s.headline
        FROM signal_topic_assignments a
        JOIN atlas_topics at ON at.id = a.topic_id
        JOIN signals_v2 s ON s.id = a.signal_id
        WHERE a.model_version='theme-hint-lex-v2' AND a.gate_kept = true
          AND s.headline IS NOT NULL AND length(s.headline) >= 25
          AND a.assigned_at > NOW() - INTERVAL '336 hours'
        ORDER BY s.headline, random()
        LIMIT $1
        """,
        n,
    )
    return [dict(r) for r in rows]


def _prompt(taxonomy: list[dict], headline: str) -> str:
    cats = "\n".join(f"- {t['slug']}: {t['label']} — {t['description']}" for t in taxonomy)
    return (
        "You are classifying a news headline into Atlas's crisis/risk taxonomy.\n"
        "Atlas tracks SIGNIFICANT crisis/risk narratives only. If the headline is "
        "NOT substantively about one of these crisis categories (e.g. routine "
        "politics, business/markets, sport, culture, a human-interest or local "
        "story, satire, or a procedural/legal item that isn't itself a crisis), "
        'answer "OUT_OF_SCOPE".\n\n'
        f"Categories:\n{cats}\n\n"
        f'Headline: "{headline}"\n\n'
        'Reply ONLY JSON: {"slug": "<category-slug-or-OUT_OF_SCOPE>", "confident": true|false}'
    )


async def _classify(provider, client, taxonomy, headline) -> str | None:
    try:
        txt = await call_llm(
            provider, system="You reply only with compact JSON.",
            user=_prompt(taxonomy, headline), client=client, max_tokens=40)
        return str(extract_json(txt).get("slug", "")).strip()
    except Exception as exc:  # noqa: BLE001
        print(f"  ({provider} err: {str(exc)[:70]})", file=sys.stderr)
        return None


async def run(n: int) -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn)
    try:
        taxonomy = await _load_taxonomy(conn)
        sample = await _load_sample(conn, n)
    finally:
        await conn.close()
    valid = {t["slug"] for t in taxonomy} | {"OUT_OF_SCOPE"}
    print(f"taxonomy={len(taxonomy)} categories | sample={len(sample)} distinct headlines | "
          f"providers={DIAG_PROVIDERS}")

    sem = asyncio.Semaphore(8)
    rows: list[dict] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        async def one(item):
            async with sem:
                picks = await asyncio.gather(*[
                    _classify(p, client, taxonomy, item["headline"]) for p in DIAG_PROVIDERS])
            d = {"headline": item["headline"], "current": item["current_slug"]}
            for p, pk in zip(DIAG_PROVIDERS, picks):
                d[p] = pk if pk in valid else None
            rows.append(d)
        await asyncio.gather(*[one(it) for it in sample])

    # metrics
    oos = {p: 0 for p in DIAG_PROVIDERS}
    agree_current = {p: 0 for p in DIAG_PROVIDERS}
    scored = {p: 0 for p in DIAG_PROVIDERS}
    both_oos = ens_oos = 0
    for d in rows:
        picks = [d.get(p) for p in DIAG_PROVIDERS if d.get(p)]
        if picks and all(x == "OUT_OF_SCOPE" for x in picks):
            ens_oos += 1
        for p in DIAG_PROVIDERS:
            pk = d.get(p)
            if not pk:
                continue
            scored[p] += 1
            if pk == "OUT_OF_SCOPE":
                oos[p] += 1
            elif pk == d["current"]:
                agree_current[p] += 1

    print("\n=== Phase A — force-fit diagnosis (gate-kept EVIDENCE sample) ===")
    for p in DIAG_PROVIDERS:
        s = scored[p] or 1
        print(f"  {p:9s}: OUT_OF_SCOPE {oos[p]}/{scored[p]} = {oos[p]/s:.0%}  | "
              f"agrees-with-current {agree_current[p]}/{scored[p]} = {agree_current[p]/s:.0%}")
    print(f"  ENSEMBLE unanimous OUT_OF_SCOPE: {ens_oos}/{len(rows)} = {ens_oos/max(len(rows),1):.0%}")
    print("  → the unanimous OOS rate is the floor on force-fit: evidence the gate "
          "kept that the taxonomy has no honest home for.")

    # show a few force-fit examples (both models say OOS but current assigned a crisis)
    examples = [d for d in rows
                if all(d.get(p) == "OUT_OF_SCOPE" for p in DIAG_PROVIDERS if d.get(p))][:8]
    if examples:
        print("\n  force-fit examples (ensemble OOS, but gate-kept under a crisis label):")
        for d in examples:
            print(f"    [{d['current']}] {d['headline'][:90]}")

    out = {"taxonomy_size": len(taxonomy), "sample": len(rows),
           "providers": DIAG_PROVIDERS, "rows": rows,
           "oos": oos, "scored": scored, "ensemble_oos": ens_oos}
    art = "docs/research/taxonomy-revision/phase-a-diagnosis.json"
    os.makedirs(os.path.dirname(art), exist_ok=True)
    with open(art, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  artifact: {art}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    return asyncio.run(run(ap.parse_args().n))


if __name__ == "__main__":
    raise SystemExit(main())
