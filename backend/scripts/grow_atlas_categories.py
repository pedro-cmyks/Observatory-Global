#!/usr/bin/env python
"""Anchored-emergent category growth — the atlas corpus stops being frozen.

Pedro 2026-07-04: categories must be neither a fixed count nor hand-updated.
The R3 spec always said the crisis-32 are SEED ANCHORS and the set GROWS;
this is the missing mechanism. Source of growth = the R3.1 typer's
free-form categories (compute_category_typing writes an OPEN `category`
string per story — "Earthquake or volcanic disaster", "Obituary & Tribute").

Per run:
 1. Aggregate free-form categories over recent active/candidate stories.
 2. Candidates: >= --min-topics distinct stories, not crisis_class-mapped
    to an existing seed.
 3. Overlap filter (MEASURED, not guessed): embed candidate text vs every
    existing atlas anchor (OpenAI, same space as the semantic lane); reject
    if max-sim >= the p90 of the existing anchors' own pairwise sims — a new
    category must be MORE distinct from the corpus than the corpus is from
    itself.
 4. Survivors: DeepSeek drafts {label, definition, includes, excludes} from
    member story labels + sample headlines.
 5. --write: INSERT atlas_topics (origin='auto', lexicon_terms empty — the
    category is born as a typing/semantic lens; the lexical lane and the
    gate cover it as gold accumulates). Cap --max-new per run. Ledger
    appended to docs/research/taxonomy-revision/auto-growth-ledger.md.

Seeds are never modified or deleted. Kill-switch: don't run it.

Env: DATABASE_URL, OPENAI_API_KEY, DEEPSEEK_API_KEY.
Usage:
  python backend/scripts/grow_atlas_categories.py [--days 30]
      [--min-topics 3] [--max-new 2] [--write]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

OPENAI_MODEL = "text-embedding-3-small"

CANDIDATES_SQL = """
    SELECT dt.category, count(*) AS n_topics,
           array_agg(dt.label ORDER BY dt.agg_n_signals DESC) AS labels,
           sum(dt.agg_n_signals)::int AS n_signals
    FROM dynamic_topics dt
    WHERE dt.category IS NOT NULL
      AND dt.state IN ('active', 'candidate')
      AND dt.last_seen > NOW() - ($1::int * INTERVAL '1 day')
      AND (dt.crisis_class IS NULL OR dt.crisis_class = 'non_crisis')
    GROUP BY dt.category
    HAVING count(*) >= $2
    ORDER BY count(*) DESC
"""

DRAFT_PROMPT = """You maintain a news-crisis monitoring taxonomy. A recurring story
category has emerged from clustering. Draft its taxonomy entry.

Emergent category name: {name}
Member story labels: {labels}

Return JSON: {{"label": <clean 2-6 word category label>,
"slug": <kebab-case slug>,
"definition": <one sentence, what belongs>,
"includes": <comma list of concrete inclusions>,
"excludes": <comma list of near-miss exclusions>,
"parent_domain": <one of: climate-disaster, conflict-security, governance-rights,
economy-resources, health-social, technology-infrastructure, culture-society>}}
Generic grab-bags ("Mixed", "Various", "Roundup", "Daily") must return
{{"reject": "grab-bag"}} instead."""


def openai_embed(texts: list[str]) -> np.ndarray:
    import openai
    client = openai.OpenAI(timeout=120.0)
    vecs: list[list[float]] = []
    for i in range(0, len(texts), 512):
        resp = client.embeddings.create(model=OPENAI_MODEL,
                                        input=[t[:2000] for t in texts[i:i+512]])
        vecs.extend(d.embedding for d in resp.data)
    a = np.asarray(vecs, dtype=np.float32)
    return a / np.linalg.norm(a, axis=1, keepdims=True)


async def deepseek_draft(name: str, labels: list[str]) -> dict | None:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    import httpx
    body = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": DRAFT_PROMPT.format(
            name=name, labels="; ".join(labels[:10]))}],
        "response_format": {"type": "json_object"},
        "temperature": 0.2, "max_tokens": 300,
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post("https://api.deepseek.com/chat/completions",
                                  json=body,
                                  headers={"Authorization": f"Bearer {key}"},
                                  timeout=40.0)
            r.raise_for_status()
            return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception as exc:  # noqa: BLE001
        print(f"  draft failed for {name!r}: {exc}", file=sys.stderr)
        return None


_GRABBAG = re.compile(r"\b(mixed|various|roundup|daily|updates?|news|misc)\b", re.I)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--min-topics", type=int, default=3)
    ap.add_argument("--max-new", type=int, default=2)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--ledger",
                    default="docs/research/taxonomy-revision/auto-growth-ledger.md")
    args = ap.parse_args()

    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        existing = await conn.fetch(
            "SELECT slug, label, description FROM atlas_topics WHERE is_active")
        cands = await conn.fetch(CANDIDATES_SQL, args.days, args.min_topics)
        if not cands:
            print("no recurring free-form categories above threshold")
            return 0

        seed_labels = {str(r["label"]).strip().lower() for r in existing}
        cands = [c for c in cands
                 if str(c["category"]).strip().lower() not in seed_labels
                 and not _GRABBAG.search(str(c["category"]))]
        if not cands:
            print("all recurring categories already covered or grab-bags")
            return 0

        # measured overlap bar: p90 of the existing corpus' own pairwise sims
        ex_texts = [f"{r['label']}. {r['description'] or ''}" for r in existing]
        E = openai_embed(ex_texts)
        pair = E @ E.T
        iu = np.triu_indices(len(ex_texts), k=1)
        overlap_bar = float(np.percentile(pair[iu], 90))
        print(f"overlap bar (p90 of {len(ex_texts)} anchors' pairwise sims): "
              f"{overlap_bar:.3f}", file=sys.stderr)

        cand_texts = [f"{c['category']}. {'; '.join((c['labels'] or [])[:6])}"
                      for c in cands]
        C = openai_embed(cand_texts)
        max_sim = (C @ E.T).max(axis=1)

        proposals = []
        for c, ms in zip(cands, max_sim):
            status = "covered" if float(ms) >= overlap_bar else "candidate"
            print(f"  {c['category'][:50]:52s} topics={c['n_topics']:3d} "
                  f"maxSim={float(ms):.3f} -> {status}")
            if status == "candidate":
                proposals.append((c, float(ms)))

        proposals = proposals[: args.max_new]
        inserted = []
        for c, ms in proposals:
            draft = await deepseek_draft(str(c["category"]), list(c["labels"] or []))
            if not draft or draft.get("reject") or not draft.get("slug"):
                print(f"  skip {c['category']!r}: "
                      f"{(draft or {}).get('reject', 'no draft')}")
                continue
            slug = re.sub(r"[^a-z0-9-]", "", str(draft["slug"]).lower())[:60]
            if args.write:
                row = await conn.fetchrow(
                    """INSERT INTO atlas_topics
                       (slug, label, description, parent_domain, lexicon_terms,
                        is_active, origin)
                       VALUES ($1,$2,$3,$4,'{}',true,'auto')
                       ON CONFLICT (slug) DO NOTHING RETURNING id""",
                    slug, draft["label"],
                    f"{draft['definition']} Includes: {draft['includes']}. "
                    f"Excludes: {draft['excludes']}.",
                    draft.get("parent_domain"),
                )
                if row:
                    inserted.append((slug, draft, c, ms))
                    print(f"  INSERTED auto category: {slug} (id {row['id']})")
            else:
                inserted.append((slug, draft, c, ms))
                print(f"  DRY-RUN would insert: {slug} — {draft['label']}")

        if inserted:
            from datetime import datetime, timezone
            led = Path(args.ledger)
            led.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            lines = [f"\n## {stamp} ({'WRITE' if args.write else 'dry-run'})\n"]
            for slug, draft, c, ms in inserted:
                lines.append(
                    f"- **{slug}** ← emergent \"{c['category']}\" "
                    f"({c['n_topics']} stories, {c['n_signals']} signals, "
                    f"maxSim vs corpus {ms:.3f})\n"
                    f"  - {draft['definition']}\n")
            with open(led, "a") as f:
                f.writelines(lines)
        print(f"{'wrote' if args.write else 'proposed'} {len(inserted)} "
              f"auto categories (cap {args.max_new})")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
