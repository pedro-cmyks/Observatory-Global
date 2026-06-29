"""Embedding-input ablation (spec 2026-06-29 §4B.3) — MEASURE BEFORE RE-EMBED.

Question: does enriching the e5 embedding input beyond the headline improve
cluster quality — specifically, does it pull DIVERSE real coverage (e.g. a Gaza
airstrike covered across languages/outlets/angles) into one coherent thread,
WITHOUT degrading rows that have no NER and WITHOUT over-clustering by geography?

It does NOT touch the "Las Vegas" syndication problem: the production clustering
input is headline-deduped (emergent_poc._clean_and_dedupe), so 25 identical
reprints already collapse to ~1 vector before clustering. Syndication inflation
lives in the SERVING/RANKING count (spec §4 headline_diversity), a different
layer — measured by syndication_audit.py, not here.

Read-only. Runs on the M1 (needs torch + transformers + hdbscan + the e5 model
+ DATABASE_URL). Free compute, no API tokens. Faithful to the real pipeline:
reuses emergent_poc._build_embedder / _cluster / _cluster_stats / _clean_headline
and the same `passage: ` prefix + HDBSCAN params.

Three input variants embedded + clustered independently on the SAME deduped rows:
  A  title-only           : "passage: {headline}"
  B  title + entities      : "passage: {headline} | {NER entities}"
  C  title + entities + cc : "passage: {headline} | {NER entities} | {country}"

Run (from repo root, on the M1 ML env):
  python -m backend.scripts.embedding_input_ablation --hours 168 --max-n 8000

Outputs JSON + Markdown under docs/research/embedding-ablation/.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path

import asyncpg
import numpy as np

from backend.scripts.emergent_poc import (  # faithful reuse of the real pipeline
    _build_embedder,
    _cluster,
    _cluster_stats,
    _clean_headline,
)

# spaCy/NER labels that carry TOPICAL, discriminative signal (actors, orgs,
# places, events). Deliberately EXCLUDES DATE/CARDINAL/MONEY/PERCENT/ORDINAL etc.
# — those are non-topical and would only add noise to the cluster geometry.
ENTITY_TYPES = {"PERSON", "ORG", "GPE", "LOC", "NORP", "EVENT", "FAC"}

# Minimal code -> English name map so variant C textualizes the country as a WORD
# e5 can embed (the 2-letter code "IR" is not a word). Fallback: the raw code.
_CC_NAME = {
    "US": "United States", "GB": "United Kingdom", "IL": "Israel", "PS": "Palestine",
    "IR": "Iran", "RU": "Russia", "UA": "Ukraine", "CN": "China", "IN": "India",
    "CO": "Colombia", "MX": "Mexico", "BR": "Brazil", "FR": "France", "DE": "Germany",
    "ES": "Spain", "TR": "Turkey", "SA": "Saudi Arabia", "AE": "United Arab Emirates",
    "EG": "Egypt", "SY": "Syria", "LB": "Lebanon", "PK": "Pakistan", "AU": "Australia",
    "CA": "Canada", "JP": "Japan", "KR": "South Korea", "KP": "North Korea",
    "VE": "Venezuela", "AR": "Argentina", "NG": "Nigeria", "ZA": "South Africa",
}


def _entities(nlp_persons, limit: int = 6) -> list[str]:
    """Extract topical entity names from the nlp_persons JSONB
    (array of {name, type}). Returns up to `limit` distinct names."""
    if not nlp_persons:
        return []
    data = json.loads(nlp_persons) if isinstance(nlp_persons, str) else nlp_persons
    out: list[str] = []
    seen: set[str] = set()
    for e in data:
        if not isinstance(e, dict):
            continue
        if e.get("type") not in ENTITY_TYPES:
            continue
        name = (e.get("name") or "").strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            out.append(name)
        if len(out) >= limit:
            break
    return out


async def _pull(conn: asyncpg.Connection, hours: int, max_n: int) -> list[dict]:
    """Stratified sample: a recent slice + guaranteed inclusion of a SYNDICATION
    probe (Las Vegas) and a DIVERSE-COVERAGE probe (Gaza/Israel) so the
    diagnostics always have their subjects present."""
    main = await conn.fetch(
        f"""
        SELECT id, headline, country_code, source_name, nlp_persons
        FROM signals_v2
        WHERE timestamp > NOW() - INTERVAL '{int(hours)} hours'
          AND headline IS NOT NULL AND length(headline) >= 25
        ORDER BY (nlp_persons IS NOT NULL) DESC, timestamp DESC
        LIMIT $1
        """,
        max_n,
    )
    vegas = await conn.fetch(
        f"""
        SELECT id, headline, country_code, source_name, nlp_persons
        FROM signals_v2
        WHERE timestamp > NOW() - INTERVAL '{int(hours)} hours'
          AND headline ILIKE '%las vegas%'
        LIMIT 200
        """
    )
    gaza = await conn.fetch(
        f"""
        SELECT id, headline, country_code, source_name, nlp_persons
        FROM signals_v2
        WHERE timestamp > NOW() - INTERVAL '{int(hours)} hours'
          AND headline ~* '(gaza|israel|palestin)'
        LIMIT 600
        """
    )
    merged: dict[int, dict] = {}
    for r in list(main) + list(vegas) + list(gaza):
        merged[r["id"]] = dict(r)
    return list(merged.values())


def _dedupe_clean(rows: list[dict]) -> list[dict]:
    """Faithful to the production clustering input: clean + dedupe by normalized
    headline (so syndicated identical copy collapses to one vector, exactly as
    snapshot_emergent_topics does)."""
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        cleaned = _clean_headline(r["headline"])
        if cleaned is None:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        r["headline"] = cleaned
        out.append(r)
    return out


def _build_texts(rows: list[dict]) -> dict[str, list[str]]:
    a, b, c = [], [], []
    for r in rows:
        h = r["headline"]
        ents = _entities(r.get("nlp_persons"))
        ent_str = ", ".join(ents)
        cc = r.get("country_code")
        cc_name = _CC_NAME.get(cc, cc) if cc else ""
        a.append(f"passage: {h}")
        b.append(f"passage: {h}" + (f" | {ent_str}" if ent_str else ""))
        c.append(
            f"passage: {h}"
            + (f" | {ent_str}" if ent_str else "")
            + (f" | {cc_name}" if cc_name else "")
        )
    return {"A_title": a, "B_title_entities": b, "C_title_entities_country": c}


def _probe_idxs(rows: list[dict], pattern_fn) -> list[int]:
    return [i for i, r in enumerate(rows) if pattern_fn(r["headline"].lower())]


def _recall_metric(labels: np.ndarray, idxs: list[int]) -> dict:
    """For a set of subject rows (e.g. Gaza), how well does ONE cluster capture
    them? recall = (largest cluster's share of the subject set). Higher = the
    diverse coverage was pulled together. Also reports how many fell to noise."""
    if not idxs:
        return {"n": 0, "best_cluster_recall": None, "noise_frac": None, "n_clusters_spanned": 0}
    labs = [int(labels[i]) for i in idxs]
    in_cluster = [l for l in labs if l != -1]
    noise = sum(1 for l in labs if l == -1)
    spanned = Counter(in_cluster)
    best = max(spanned.values()) if spanned else 0
    return {
        "n": len(idxs),
        "best_cluster_recall": round(best / len(idxs), 3),
        "noise_frac": round(noise / len(idxs), 3),
        "n_clusters_spanned": len(spanned),
    }


def _geo_purity(clusters: list[dict], rows: list[dict]) -> float:
    """Mean per-cluster country purity (max single-country share). HIGHER under
    variant C than A/B = the geographic over-clustering risk realized (clusters
    forming by country instead of by topic)."""
    if not clusters:
        return 0.0
    purities = []
    for cl in clusters:
        ccs = Counter(
            rows[i]["country_code"] for i in cl["all_idxs"] if rows[i]["country_code"]
        )
        if ccs:
            purities.append(max(ccs.values()) / sum(ccs.values()))
    return round(float(np.mean(purities)), 3) if purities else 0.0


def _variant_report(name, labels, embs, rows, gaza_idxs, vegas_idxs, min_cluster_size):
    clusters = _cluster_stats(labels, embs, rows)
    n = len(rows)
    noise = int((labels == -1).sum())
    return {
        "variant": name,
        "n_rows": n,
        "n_clusters": len(clusters),
        "noise_rate": round(noise / max(n, 1), 3),
        "mean_cohesion": round(
            float(np.mean([c["cohesion"] for c in clusters])) if clusters else 0.0, 3
        ),
        "largest_cluster": clusters[0]["size"] if clusters else 0,
        "geo_purity": _geo_purity(clusters, rows),
        "gaza_recall": _recall_metric(labels, gaza_idxs),
        "vegas_sanity": _recall_metric(labels, vegas_idxs),
        "top_clusters": [
            {
                "size": c["size"],
                "cohesion": round(c["cohesion"], 3),
                "top_countries": c["top_countries"],
                "sample_headline": rows[c["top_signal_idxs"][0]]["headline"][:80],
            }
            for c in clusters[:8]
        ],
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--max-n", type=int, default=8000)
    ap.add_argument("--min-cluster-size", type=int, default=5)
    ap.add_argument("--min-samples", type=int, default=3)
    ap.add_argument("--selection", default="leaf")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)

    conn = await asyncpg.connect(db)
    try:
        raw = await _pull(conn, args.hours, args.max_n)
    finally:
        await conn.close()
    rows = _dedupe_clean(raw)
    if len(rows) < args.min_cluster_size * 2:
        print(f"too few rows after dedupe: {len(rows)}", file=sys.stderr)
        sys.exit(2)

    ner_cov = sum(1 for r in rows if _entities(r.get("nlp_persons"))) / len(rows)
    print(f"sample: {len(rows)} deduped rows · NER coverage {ner_cov:.1%}", file=sys.stderr)

    gaza_idxs = _probe_idxs(rows, lambda h: ("gaza" in h or "israel" in h or "palestin" in h))
    vegas_idxs = _probe_idxs(rows, lambda h: "las vegas" in h)
    print(f"probes: gaza={len(gaza_idxs)} vegas(deduped)={len(vegas_idxs)}", file=sys.stderr)

    embed, device = _build_embedder()
    print(f"e5 on {device}", file=sys.stderr)

    texts = _build_texts(rows)
    variants = []
    for name, txt in texts.items():
        print(f"embedding {name}...", file=sys.stderr)
        embs = embed(txt).astype(np.float32)
        labels = _cluster(embs, args.min_cluster_size, args.min_samples, args.selection)
        variants.append(
            _variant_report(name, labels, embs, rows, gaza_idxs, vegas_idxs, args.min_cluster_size)
        )

    result = {
        "params": vars(args),
        "sample_size": len(rows),
        "ner_coverage": round(ner_cov, 3),
        "gaza_probe_n": len(gaza_idxs),
        "vegas_probe_deduped_n": len(vegas_idxs),
        "variants": variants,
    }

    out_dir = Path(__file__).resolve().parents[2] / "docs" / "research" / "embedding-ablation"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ablation-latest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))

    # Markdown summary (the decision artifact)
    lines = [
        "# Embedding-input ablation (spec §4B.3)", "",
        f"Sample: {len(rows)} deduped rows · NER coverage {ner_cov:.1%} · "
        f"gaza probe {len(gaza_idxs)} · vegas(deduped) {len(vegas_idxs)}", "",
        "| variant | clusters | noise | cohesion | geo_purity | gaza_recall | gaza_noise |",
        "|---|---|---|---|---|---|---|",
    ]
    for v in variants:
        gr = v["gaza_recall"]
        lines.append(
            f"| {v['variant']} | {v['n_clusters']} | {v['noise_rate']} | "
            f"{v['mean_cohesion']} | {v['geo_purity']} | "
            f"{gr['best_cluster_recall']} | {gr['noise_frac']} |"
        )
    lines += [
        "", "## Decision rule (§4B.3)",
        "- **Win** = B (or C) raises `gaza_recall` (diverse coverage pulled together) "
        "AND lowers `gaza_noise`, WITHOUT C's `geo_purity` jumping vs A/B "
        "(geographic over-clustering).",
        "- If B helps and C over-clusters → enrich with entities only, drop country.",
        "- If neither beats A → headline-only stays; do NOT run the full re-embed.",
        "- Reminder: this measures RECALL of diverse coverage only. The Las Vegas "
        "syndication problem is a ranking-count issue (spec §4), not here.",
    ]
    (out_dir / "ablation-latest.md").write_text("\n".join(lines))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nwrote {out_dir}/ablation-latest.{{json,md}}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
