#!/usr/bin/env python
"""Category robot v1 — structure-first, over ALL processed story history.

Pedro 2026-07-05: "un robot que va por encima de todos los temas siempre y
se pregunta ¿esto se puede agrupar?" — group by STRUCTURE first, name the
group ONCE after (v0 grow_atlas_categories was name-first: it aggregated the
typer's free-form labels and depended on naming vocabulary converging).

Input units = every dynamic_topics identity EVER (all states — active,
candidate, retired; the retention model never deletes), optionally plus
external story units (--units-jsonl, e.g. archive-era clusters from the
archive_embed_pipeline once Stage B lands). NOT hot-only by design.

Pass:
 1. Embed unit labels in OpenAI space (e5 centroid space is compressed at
    this granularity: p50 0.94 — measured 2026-06-29/07-04).
 2. MEASURE the grouping threshold: sweep average-linkage cuts over a grid,
    pick by silhouette (never guessed).
 3. Groups >= --min-members -> DeepSeek names + drafts the taxonomy entry.
 4. Overlap bar vs existing atlas anchors (p90 of their own pairwise sims):
    covered groups are reported, not inserted.
 5. --write: INSERT atlas_topics origin='auto' (cap --max-new), ledger +
    full group->members report for the eyeball.
 6. Recursion sketch (report-only): re-agglomerate group centroids at a
    coarser cut -> domain layer.

Env: DATABASE_URL, OPENAI_API_KEY, DEEPSEEK_API_KEY.
Usage:
  python backend/scripts/robot_categories_v1.py [--min-members 3]
      [--max-new 2] [--units-jsonl extra_units.jsonl] [--write]
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

_BAD_LABEL = re.compile(
    r"\b(roundup|label failed|mixed:|various|daily digest)\b|^emerging:", re.I)

UNITS_SQL = """
    SELECT id, label, state, agg_n_signals, first_seen::date AS first_seen,
           last_seen::date AS last_seen, crisis_class
    FROM dynamic_topics
    WHERE label IS NOT NULL AND length(label) >= 8
"""

DRAFT_PROMPT = """You maintain a news-monitoring taxonomy. A structural cluster of
story topics has emerged. Name the CATEGORY they share.

Member story labels ({n} stories, {span}):
{labels}

Return JSON: {{"label": <2-6 word category label>,
"slug": <kebab-case>,
"definition": <one sentence>,
"includes": <comma list>,
"excludes": <comma list of near-misses>,
"parent_domain": <one of: climate-disaster, conflict-security,
governance-rights, economy-resources, health-social,
technology-infrastructure, culture-society>}}
If the members share no coherent category (grab-bag), return {{"reject": "grab-bag"}}."""


def openai_embed(texts: list[str]) -> np.ndarray:
    import openai
    client = openai.OpenAI(timeout=120.0)
    vecs: list[list[float]] = []
    for i in range(0, len(texts), 512):
        resp = client.embeddings.create(
            model=OPENAI_MODEL, input=[t[:2000] for t in texts[i:i+512]])
        vecs.extend(d.embedding for d in resp.data)
    a = np.asarray(vecs, dtype=np.float32)
    return a / np.linalg.norm(a, axis=1, keepdims=True)


async def deepseek_draft(labels: list[str], span: str) -> dict | None:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    import httpx
    body = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": DRAFT_PROMPT.format(
            n=len(labels), span=span,
            labels="\n".join(f"- {l[:100]}" for l in labels[:20]))}],
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
        print(f"  draft failed: {exc}", file=sys.stderr)
        return None


def measured_cut(V: np.ndarray, grid: list[float]) -> tuple[float, dict]:
    """Average-linkage over cosine distance; pick the cut by silhouette
    (computed on grouped points only). Returns (best_cut, diagnostics)."""
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    S = V @ V.T
    D = np.clip(1.0 - S, 0.0, 2.0)
    np.fill_diagonal(D, 0.0)
    Z = linkage(squareform(D, checks=False), method="average")

    diag = {}
    best_cut, best_sil = grid[0], -1.0
    for cut in grid:
        labels = fcluster(Z, t=cut, criterion="distance")
        sizes = np.bincount(labels)
        grouped = np.array([sizes[l] >= 3 for l in labels])
        n_groups = int(sum(1 for s in sizes if s >= 3))
        if n_groups < 2 or grouped.sum() < 10:
            diag[cut] = {"groups>=3": n_groups, "silhouette": None}
            continue
        # cheap silhouette on grouped points
        sil_vals = []
        for i in np.where(grouped)[0]:
            same = (labels == labels[i]); same[i] = False
            if not same.any():
                continue
            a = float(D[i, same].mean())
            b = min(float(D[i, labels == g].mean())
                    for g in set(labels[grouped]) if g != labels[i])
            sil_vals.append((b - a) / max(a, b, 1e-9))
        sil = float(np.mean(sil_vals)) if sil_vals else -1.0
        diag[cut] = {"groups>=3": n_groups,
                     "grouped_pts": int(grouped.sum()),
                     "silhouette": round(sil, 3)}
        if sil > best_sil:
            best_sil, best_cut = sil, cut
    return best_cut, diag


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-members", type=int, default=3)
    ap.add_argument("--max-new", type=int, default=2)
    ap.add_argument("--units-jsonl", default=None,
                    help="extra story units: {label, first_seen?, last_seen?}")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--report-dir", default="docs/research/taxonomy-revision")
    args = ap.parse_args()

    import asyncpg
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        rows = [dict(r) for r in await conn.fetch(UNITS_SQL)]
        if args.units_jsonl:
            for line in open(args.units_jsonl):
                d = json.loads(line)
                d.setdefault("state", "external")
                rows.append(d)
        units = [r for r in rows if not _BAD_LABEL.search(str(r["label"]))]
        print(f"{len(rows)} units loaded, {len(units)} after label hygiene "
              f"(states: all — full processed history)", file=sys.stderr)

        V = openai_embed([str(u["label"]) for u in units])

        grid = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
        cut, diag = measured_cut(V, grid)
        print("cut sweep:", json.dumps(diag), file=sys.stderr)
        print(f"chosen cut (silhouette): {cut}", file=sys.stderr)

        from scipy.cluster.hierarchy import fcluster, linkage
        from scipy.spatial.distance import squareform
        D = np.clip(1.0 - V @ V.T, 0.0, 2.0)
        np.fill_diagonal(D, 0.0)
        Z = linkage(squareform(D, checks=False), method="average")
        labels = fcluster(Z, t=cut, criterion="distance")

        groups: dict[int, list[int]] = {}
        for i, g in enumerate(labels):
            groups.setdefault(int(g), []).append(i)
        big = {g: idxs for g, idxs in groups.items()
               if len(idxs) >= args.min_members}
        print(f"{len(big)} groups >= {args.min_members} members "
              f"({sum(len(v) for v in big.values())} of {len(units)} units)",
              file=sys.stderr)

        # overlap bar vs existing anchors (same rule as grow v0)
        existing = await conn.fetch(
            "SELECT slug, label, description FROM atlas_topics WHERE is_active")
        E = openai_embed([f"{r['label']}. {r['description'] or ''}"
                          for r in existing])
        pair = E @ E.T
        iu = np.triu_indices(len(existing), k=1)
        overlap_bar = float(np.percentile(pair[iu], 90))

        from datetime import datetime, timezone
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        report = [f"# Robot v1 run — {stamp}",
                  f"\nunits={len(units)} cut={cut} groups>= "
                  f"{args.min_members}: {len(big)} · overlap bar {overlap_bar:.3f}\n"]
        inserted = 0
        dup_groups = 0
        # biggest groups first — most evidence first
        for g, idxs in sorted(big.items(), key=lambda kv: -len(kv[1])):
            centroid = V[idxs].mean(axis=0)
            centroid /= np.linalg.norm(centroid)
            ms = float((centroid @ E.T).max())
            member_labels = [str(units[i]["label"]) for i in idxs]
            span_dates = [u.get("first_seen") for u in
                          (units[i] for i in idxs) if u.get("first_seen")]
            span = (f"{min(span_dates)} → {max(span_dates)}"
                    if span_dates else "n/a")
            # LEVEL GUARD (first-run finding, 2026-07-05): a tight group of
            # near-duplicate labels ("Venezuela Earthquake Death Toll" x25)
            # is ONE STORY re-founded across snapshots (the identity-
            # continuity fossil record), not a category. Category = DIVERSE
            # members sharing a theme. Median intra-group sim discriminates:
            # same-story groups sit ~0.8+; real category groups are looser.
            gs = V[idxs] @ V[idxs].T
            giu = np.triu_indices(len(idxs), k=1)
            intra = float(np.median(gs[giu])) if len(idxs) > 1 else 1.0
            # second discriminator: one content token dominating the labels
            # ("venezuela"/"earthquake" in 25/25, "world cup" in 35/35) =
            # ONE EVENT with varied sub-labels — umbrella material, still
            # not a category. A real category's members share a THEME, not
            # a token.
            stop = {"the", "and", "of", "in", "for", "on", "de", "la", "el",
                    "updates", "update", "news", "coverage", "crisis", "2026"}
            from collections import Counter
            tok_docs: Counter[str] = Counter()
            for l in member_labels:
                toks = {t for t in re.findall(r"[a-zà-ÿ]{4,}", l.lower())
                        if t not in stop}
                tok_docs.update(toks)
            dom = (tok_docs.most_common(1)[0][1] / len(member_labels)
                   if tok_docs else 0.0)
            if intra >= 0.80:
                dup_groups += 1
                status = f"SAME-STORY (intra {intra:.2f} — identity-dedup case)"
            elif dom >= 0.60:
                status = (f"EVENT-LEVEL (token '{tok_docs.most_common(1)[0][0]}' "
                          f"in {dom:.0%} of labels — umbrella, not category)")
            elif ms >= overlap_bar:
                status = "covered"
            else:
                status = "NEW-candidate"
            report.append(f"## group {g}: {len(idxs)} stories · maxSim "
                          f"{ms:.3f} · {status} · {span}")
            report.extend(f"- {l[:90]}" for l in member_labels[:12])
            report.append("")
            if status != "NEW-candidate" or inserted >= args.max_new:
                continue
            draft = await deepseek_draft(member_labels, span)
            if not draft or draft.get("reject") or not draft.get("slug"):
                report.append(f"  -> draft rejected: "
                              f"{(draft or {}).get('reject', 'no draft')}\n")
                continue
            slug = re.sub(r"[^a-z0-9-]", "", str(draft["slug"]).lower())[:60]
            report.append(f"  -> DRAFT {slug}: {draft['definition']}\n")
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
                    draft.get("parent_domain"))
                if row:
                    inserted += 1
                    print(f"  INSERTED {slug} (id {row['id']})")
            else:
                inserted += 1

        # recursion sketch: domains (report-only)
        if len(big) >= 4:
            gids = list(big)
            C = np.vstack([V[big[g]].mean(axis=0) for g in gids])
            C /= np.linalg.norm(C, axis=1, keepdims=True)
            Dg = np.clip(1.0 - C @ C.T, 0.0, 2.0)
            np.fill_diagonal(Dg, 0.0)
            Zg = linkage(squareform(Dg, checks=False), method="average")
            dl = fcluster(Zg, t=min(cut + 0.15, 0.75), criterion="distance")
            report.append("## domain sketch (recursion, report-only)")
            doms: dict[int, list[int]] = {}
            for gi, d in zip(gids, dl):
                doms.setdefault(int(d), []).append(gi)
            for d, gs in doms.items():
                names = ["/".join(str(units[i]['label'])[:30]
                                  for i in big[g][:2]) for g in gs]
                report.append(f"- domain {d}: groups {gs} — e.g. {names[:3]}")

        rp = Path(args.report_dir) / f"robot-v1-{stamp}.md"
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text("\n".join(report) + "\n")
        print(f"report: {rp}")
        print(f"{'inserted' if args.write else 'would insert'} {inserted} "
              f"new categories (cap {args.max_new})")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
