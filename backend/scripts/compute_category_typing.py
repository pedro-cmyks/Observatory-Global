"""R3.1 — anchored-emergent category typing (#229, R3 unification).

Types every active story-topic into the anchored-emergent category model (spec §3.1):
- SEED anchors = the 32 candidate-v2 crisis categories (embedded definitions, same e5
  space as the story centroids). A topic whose centroid is >= threshold to a seed takes
  that crisis_class + the seed label (anchored).
- Emergent / non-crisis = topics matching NO seed → crisis_class='non_crisis' (the
  editorial-lens reject, NEVER suppression). The emergent super-category label is filled
  by a coarse residual clustering + DeepSeek at scale (off-peak, --write --cluster-emergent);
  the seed-anchor half needs no heavy compute.

Writes dynamic_topics.category / crisis_class / category_confidence.

  python -m backend.scripts.compute_category_typing --validate 30      # cheap design proof
  python -m backend.scripts.compute_category_typing --write            # seed-anchor typing (off-peak for emergent)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg
import numpy as np

_CANDIDATE = Path("docs/research/taxonomy-revision/candidate-v2.json")
SEED_THRESHOLD = 0.80  # centroid vs crisis-seed prototype (knob, calibrate on --validate)


def _load_seed_prototypes():
    # lazy import: emergent_poc pulls torch/sentence-transformers — only the
    # (weak) cosine path needs it; the DeepSeek 30-min cron path must stay light
    from backend.scripts.emergent_poc import _build_embedder  # multilingual-e5-base, mean-pool + L2 (centroid space)

    d = json.loads(_CANDIDATE.read_text())
    cats = d["categories"]
    labels = [c["label"] for c in cats]
    # embed each seed as `passage: {label}. {definition}` into the centroid space
    texts = [f"passage: {c['label']}. {c.get('definition', '')}" for c in cats]
    embed, _device = _build_embedder()
    protos = np.asarray(embed(texts), dtype=np.float32)
    protos /= (np.linalg.norm(protos, axis=1, keepdims=True) + 1e-9)
    return labels, protos


_DS_URL = "https://api.deepseek.com/chat/completions"


async def _ds_type(label: str, cat_labels: list[str], key: str) -> tuple[str, str]:
    """DeepSeek picks the crisis class (the semantic judgment cosine can't do).
    Returns (crisis_class, 'ds'). OUT_OF_SCOPE -> non_crisis (honest reject)."""
    import httpx
    cats = "\n".join(f"- {c}" for c in cat_labels)
    prompt = (
        "Classify this news TOPIC into the Atlas crisis taxonomy. Pick the SINGLE best "
        "category from the list, or answer OUT_OF_SCOPE if it is not a crisis / narrative-"
        "intelligence topic (sport, entertainment, lifestyle, travel, product launch, "
        "routine obituary, market-data roundup).\n\n"
        f"TOPIC: \"{label}\"\n\nCATEGORIES:\n{cats}\n\n"
        "Answer with ONLY the exact category label, or OUT_OF_SCOPE.")
    body = {"model": "deepseek-chat", "temperature": 0,
            "messages": [{"role": "user", "content": prompt}]}
    async with httpx.AsyncClient() as c:
        r = await c.post(_DS_URL, json=body,
                         headers={"Authorization": f"Bearer {key}"}, timeout=30.0)
        r.raise_for_status()
        ans = r.json()["choices"][0]["message"]["content"].strip()
    if ans.upper().startswith("OUT_OF_SCOPE") or ans not in cat_labels:
        return ("non_crisis", "ds") if ans.upper().startswith("OUT") else (
            (ans, "ds") if ans in cat_labels else ("non_crisis", "ds"))
    return ans, "ds"


def _type_one(centroid: np.ndarray, labels, protos, threshold):
    v = centroid / (np.linalg.norm(centroid) + 1e-9)
    sims = protos @ v
    j = int(np.argmax(sims))
    best = float(sims[j])
    if best >= threshold:
        return labels[j], labels[j], best          # (category, crisis_class, confidence) — anchored to seed
    return None, "non_crisis", best                # emergent/non-crisis (category filled off-peak by clustering)


async def main() -> None:
    ap = argparse.ArgumentParser(description="R3.1 anchored-emergent category typing.")
    ap.add_argument("--validate", type=int, default=0, help="type N topics, print, no write")
    ap.add_argument("--write", action="store_true", help="write typings to dynamic_topics")
    ap.add_argument("--threshold", type=float, default=SEED_THRESHOLD)
    ap.add_argument("--deepseek", action="store_true", help="type via DeepSeek (the real method; cosine alone is spurious)")
    ap.add_argument("--only-untyped", action="store_true",
                    help="incremental: only topics never typed (crisis_class IS NULL) — "
                         "the 30-min cron mode (spec R3.1 §3.1: fresh stories get their "
                         "badge within a cycle; steady-state = 0 API calls)")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL required", file=sys.stderr); sys.exit(2)

    # seed prototypes only needed for the (weak) cosine path
    labels, protos = _load_seed_prototypes() if not args.deepseek else (
        [c["label"] for c in json.loads(_CANDIDATE.read_text())["categories"]], None)
    conn = await asyncpg.connect(db)
    try:
        limit = args.validate or 1_000_000
        untyped = "AND crisis_class IS NULL " if args.only_untyped else ""
        rows = await conn.fetch(
            "SELECT id, label, agg_n_signals, centroid_vec FROM dynamic_topics "
            "WHERE state='active' AND is_umbrella=false AND centroid_vec IS NOT NULL "
            f"{untyped}"
            "ORDER BY agg_n_signals DESC LIMIT $1", limit)
        if not rows:
            print("no topics to type (all typed)" if args.only_untyped else "no topics")
            return
        typed = []
        for r in rows:
            if args.deepseek:
                key = os.environ["DEEPSEEK_API_KEY"]
                crisis, _ = await _ds_type(r["label"] or "?", labels, key)
                cat = crisis if crisis != "non_crisis" else None
                conf = 1.0
            else:
                cat, crisis, conf = _type_one(np.asarray(r["centroid_vec"], dtype=np.float32),
                                              labels, protos, args.threshold)
            typed.append((int(r["id"]), r["label"], cat, crisis, conf))

        if args.validate or not args.write:
            for _id, lbl, cat, crisis, conf in typed:
                mark = crisis if crisis != "non_crisis" else "· non-crisis/emergent"
                print(f"  [{conf:.3f}] {(lbl or '?')[:42]:44} -> {mark}")
            anchored = sum(1 for t in typed if t[3] != "non_crisis")
            print(f"\n{anchored}/{len(typed)} anchored to a crisis seed @thr={args.threshold} · "
                  f"{len(typed) - anchored} emergent/non-crisis (honest reject, not suppressed)")
            return

        if args.write:
            async with conn.transaction():
                for _id, _lbl, cat, crisis, conf in typed:
                    # R3 crisis-relevance-as-lens: category = the OPEN category (crisis
                    # seed label for crisis; emergent labeling fills non-crisis later),
                    # crisis_relevant = the flag. crisis_class kept legacy for back-compat.
                    await conn.execute(
                        "UPDATE dynamic_topics SET category=$2, crisis_class=$3, "
                        "crisis_relevant=$4, category_confidence=$5 WHERE id=$1",
                        _id, cat, crisis, crisis != "non_crisis", float(conf))
            print(f"wrote {len(typed)} typings (seed-anchored; emergent clustering = off-peak follow)")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
