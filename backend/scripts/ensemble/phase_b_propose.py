"""Taxonomy revision — Phase B: ensemble proposals (#204).

Each model wears a distinct analyst PERSONA (model × persona diversity) and
proposes a revised taxonomy grounded in the Phase A diagnosis (30–46% of gate-kept
evidence is force-fit) + the current 30 categories. The orchestrator (Claude)
synthesizes the proposals into a candidate v2 — and contributes the geopolitics-
analyst lens directly.

Brief (shared, non-negotiable): Atlas serves the narrative analyst doing honest
situational awareness on crises/risks. KEEP the crisis/risk focus (don't expand
to all-news) but ADD a rigorous OUT_OF_SCOPE policy so non-crisis content is
rejected, not force-fit. Fix the measured force-fits.

Saves each proposal to docs/research/taxonomy-revision/proposals/<persona>.json.
Run: python -m backend.scripts.ensemble.phase_b_propose
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import asyncpg
import httpx

from backend.scripts.ensemble.model_clients import call_gemini, call_llm, extract_json

# (provider, persona-key, persona-brief). One persona per model = model + lens diversity.
PERSONAS = [
    ("deepseek", "wire-taxonomist",
     "You are a wire-service topic taxonomist (Reuters/AP IPTC style). You value "
     "clean, mutually-exclusive subject codes that a desk can apply consistently "
     "at scale, with crisp inclusion/exclusion rules."),
    ("openai", "ontology-purist",
     "You are an ontology designer. You value a MECE hierarchy: no overlap, clear "
     "parent domains, each category defined by necessary-and-sufficient criteria, "
     "and an explicit reject class for everything out of scope."),
    ("gemini", "newsroom-editor",
     "You are a newsroom desk editor for a global-affairs outlet. You value "
     "categories that match how analysts actually think about unfolding crises and "
     "that a journalist would find legible and non-overlapping under deadline."),
]

BRIEF_TMPL = """{persona}

Atlas is a narrative-intelligence system for analysts doing honest situational
awareness on global CRISES and RISKS (conflict, disasters, economic/political/
health/security stress). It is NOT a general news tagger.

PROBLEM (measured): the current taxonomy is 100% crisis-framed with no
out-of-scope option, so ~30-46% of signals the relevance gate KEEPS get force-fit
into the nearest crisis bucket. Examples of force-fit (these should be REJECTED,
not categorized): a shopping article mentioning a heatwave; a book review; a local
human-interest memorial; routine business/markets; sport; culture.

CURRENT TAXONOMY ({n} categories):
{current}

YOUR TASK: propose a REVISED crisis/risk taxonomy. Keep the crisis focus (do NOT
expand into all-news), fix overlaps/gaps, and define each category by what it
INCLUDES and EXCLUDES so the force-fits above are excluded. Also define the
out-of-scope policy.

Reply ONLY JSON:
{{
  "categories": [
    {{"slug": "kebab-case", "label": "Short Label", "parent_domain": "domain-slug",
      "definition": "one sentence", "includes": "...", "excludes": "..."}}
  ],
  "out_of_scope_policy": "when to reject a signal as not-a-crisis-narrative",
  "changes_vs_current": "what you merged / split / added / dropped and why (2-4 sentences)"
}}"""


async def _load_current(conn) -> list[dict]:
    rows = await conn.fetch(
        "SELECT slug, label, parent_domain, COALESCE(description,'') AS description "
        "FROM atlas_topics ORDER BY parent_domain, slug")
    return [dict(r) for r in rows]


def _current_text(cur: list[dict]) -> str:
    return "\n".join(
        f"- [{t['parent_domain']}] {t['slug']}: {t['label']} — {t['description']}" for t in cur)


async def run() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn)
    try:
        current = await _load_current(conn)
    finally:
        await conn.close()
    cur_text = _current_text(current)
    outdir = "docs/research/taxonomy-revision/proposals"
    os.makedirs(outdir, exist_ok=True)

    async def propose_api(provider, persona_key, persona_brief, client):
        brief = BRIEF_TMPL.format(persona=persona_brief, n=len(current), current=cur_text)
        try:
            txt = await call_llm(
                provider, system="You reply only with a single valid JSON object.",
                user=brief, client=client, max_tokens=4000, json_mode=True)
            data = extract_json(txt)
            data["_persona"] = persona_key
            data["_provider"] = provider
            with open(f"{outdir}/{persona_key}.json", "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            n = len(data.get("categories", []))
            print(f"  [{provider}/{persona_key}] {n} categories proposed → {persona_key}.json")
            return data
        except Exception as exc:  # noqa: BLE001
            print(f"  [{provider}/{persona_key}] FAILED: {str(exc)[:140]}", file=sys.stderr)
            return None

    async with httpx.AsyncClient(timeout=180.0) as client:
        await asyncio.gather(*[
            propose_api(p, k, b, client) for (p, k, b) in PERSONAS if p != "gemini"])

    # gemini (CLI, sync) — newsroom-editor persona
    for (p, k, b) in PERSONAS:
        if p != "gemini":
            continue
        brief = BRIEF_TMPL.format(persona=b, n=len(current), current=cur_text)
        try:
            txt = call_gemini(brief + "\n\nReturn ONLY the JSON object, no prose.", timeout=150)
            data = extract_json(txt)
            data["_persona"], data["_provider"] = k, p
            with open(f"{outdir}/{k}.json", "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  [gemini/{k}] {len(data.get('categories', []))} categories → {k}.json")
        except Exception as exc:  # noqa: BLE001
            print(f"  [gemini/{k}] FAILED: {str(exc)[:140]}", file=sys.stderr)

    print(f"\n  proposals in {outdir}/ — synthesize into candidate v2 next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
