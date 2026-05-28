#!/usr/bin/env python3
"""Multi-annotator agreement across human + LLM annotators.

Takes N annotator sources, each a JSONL with a signal_id and a decision
field. Computes:
  - per-annotator decision distribution (strictness profile)
  - pairwise Cohen's kappa for every annotator pair (on their overlap)
  - Fleiss' kappa across all annotators on the subset every annotator labeled
  - majority-vote consensus label per item (on the all-labeled subset)

Decision categories default to {correct, incorrect, partial}; `unclear`
and missing are dropped per item.

Schema version: atlas-multi-annotator-v1. No API calls.

Source spec format: NAME:FIELD:PATH
  e.g. pedro:gold_decision:docs/.../batch-01.reviewed.jsonl
       sonnet46:annotator_decision:docs/.../sonnet46.annotations.jsonl
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "atlas-multi-annotator-v1"
DEFAULT_CATEGORIES = ["correct", "incorrect", "partial"]
LANDIS_KOCH = [
    (0.0, "poor"),
    (0.21, "slight"),
    (0.41, "fair"),
    (0.61, "moderate"),
    (0.81, "substantial"),
    (1.01, "almost_perfect"),
]


def landis_koch_band(kappa: float) -> str:
    for upper, label in LANDIS_KOCH:
        if kappa < upper:
            return label
    return "almost_perfect"


def _read_decisions(path: Path, field: str, categories: set[str]) -> dict[int, str]:
    out: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        sid = row.get("signal_id")
        if sid is None:
            continue
        dec = row.get(field)
        if dec in categories:
            out[int(sid)] = dec
    return out


def cohen_kappa(pairs: list[tuple[str, str]], categories: list[str]) -> dict[str, Any]:
    n = len(pairs)
    if n == 0:
        return {"n": 0, "kappa": 0.0, "observed": 0.0, "expected": 0.0}
    idx = {c: i for i, c in enumerate(categories)}
    size = len(categories)
    matrix = [[0] * size for _ in range(size)]
    for a, b in pairs:
        if a in idx and b in idx:
            matrix[idx[a]][idx[b]] += 1
    agree = sum(matrix[i][i] for i in range(size))
    observed = agree / n
    a_marg = [sum(row) for row in matrix]
    b_marg = [sum(matrix[i][j] for i in range(size)) for j in range(size)]
    expected = sum(a_marg[i] * b_marg[i] for i in range(size)) / (n * n)
    kappa = 0.0 if (1 - expected) == 0 else (observed - expected) / (1 - expected)
    return {"n": n, "kappa": kappa, "observed": observed, "expected": expected}


def fleiss_kappa(
    items: list[dict[str, str]],
    annotators: list[str],
    categories: list[str],
) -> dict[str, Any]:
    """Fleiss' kappa on items every annotator labeled."""
    common = [it for it in items if all(a in it for a in annotators)]
    n_ann = len(annotators)
    N = len(common)
    if N == 0 or n_ann < 2:
        return {"n_items": N, "n_annotators": n_ann, "kappa": 0.0}
    k = len(categories)
    cat_idx = {c: i for i, c in enumerate(categories)}

    n_ij = []
    for it in common:
        counts = [0] * k
        for a in annotators:
            counts[cat_idx[it[a]]] += 1
        n_ij.append(counts)

    # P_i per item
    P_i = []
    for counts in n_ij:
        s = sum(c * c for c in counts)
        P_i.append((s - n_ann) / (n_ann * (n_ann - 1)))
    P_bar = sum(P_i) / N

    # category proportions
    p_j = [0.0] * k
    for counts in n_ij:
        for j in range(k):
            p_j[j] += counts[j]
    total = N * n_ann
    p_j = [x / total for x in p_j]
    P_e = sum(x * x for x in p_j)

    kappa = 0.0 if (1 - P_e) == 0 else (P_bar - P_e) / (1 - P_e)
    return {
        "n_items": N,
        "n_annotators": n_ann,
        "kappa": kappa,
        "mean_observed_agreement": P_bar,
        "expected_agreement": P_e,
        "landis_koch_band": landis_koch_band(kappa),
    }


def _parse_source(spec: str) -> tuple[str, str, Path]:
    name, field, path = spec.split(":", 2)
    return name, field, Path(path)


def build_report(sources: list[str], categories: list[str]) -> dict[str, Any]:
    cat_set = set(categories)
    parsed = [_parse_source(s) for s in sources]
    decisions: dict[str, dict[int, str]] = {}
    distributions: dict[str, dict[str, int]] = {}
    for name, field, path in parsed:
        d = _read_decisions(path, field, cat_set)
        decisions[name] = d
        dist: dict[str, int] = {c: 0 for c in categories}
        for v in d.values():
            dist[v] += 1
        distributions[name] = {"total": len(d), **dist}

    names = list(decisions.keys())

    pairwise = []
    for a, b in itertools.combinations(names, 2):
        da, db = decisions[a], decisions[b]
        overlap = sorted(set(da.keys()) & set(db.keys()))
        pairs = [(da[s], db[s]) for s in overlap]
        result = cohen_kappa(pairs, categories)
        pairwise.append({
            "annotator_a": a,
            "annotator_b": b,
            "overlap": len(overlap),
            "kappa": round(result["kappa"], 4),
            "observed_agreement": round(result["observed"], 4),
            "landis_koch_band": landis_koch_band(result["kappa"]),
        })

    # Build per-item annotator maps for Fleiss.
    all_sids: set[int] = set()
    for d in decisions.values():
        all_sids |= set(d.keys())
    items = []
    for sid in sorted(all_sids):
        item = {}
        for name in names:
            if sid in decisions[name]:
                item[name] = decisions[name][sid]
        items.append(item)

    fleiss_all = fleiss_kappa(items, names, categories)

    # Also Fleiss across LLM-only annotators (exclude any named 'pedro'/human).
    llm_names = [n for n in names if n.lower() not in {"pedro", "human"}]
    fleiss_llm = (
        fleiss_kappa(items, llm_names, categories) if len(llm_names) >= 2 else None
    )

    # Majority vote consensus on all-annotator subset.
    consensus = []
    common_items = [it for it in items if all(a in it for a in names)]
    for it in common_items:
        votes: dict[str, int] = {}
        for name in names:
            votes[it[name]] = votes.get(it[name], 0) + 1
        top = max(votes.items(), key=lambda kv: kv[1])
        consensus.append({"votes": votes, "majority": top[0], "agreement": top[1] / len(names)})
    unanimous = sum(1 for c in consensus if c["agreement"] == 1.0)

    return {
        "schema_version": SCHEMA_VERSION,
        "categories": categories,
        "annotators": names,
        "distributions": distributions,
        "pairwise_cohen_kappa": pairwise,
        "fleiss_kappa_all": fleiss_all,
        "fleiss_kappa_llm_only": fleiss_llm,
        "consensus_subset_size": len(common_items),
        "unanimous_items": unanimous,
        "unanimous_rate": round(unanimous / len(common_items), 4) if common_items else None,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Multi-annotator agreement",
        "",
        f"Schema: `{report['schema_version']}`",
        f"Categories: {report['categories']}",
        f"Annotators: {', '.join(report['annotators'])}",
        "",
        "## Strictness profile (decision distribution)",
        "",
        "| Annotator | total | correct | incorrect | partial |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, dist in report["distributions"].items():
        lines.append(
            f"| {name} | {dist['total']} | {dist.get('correct',0)} | "
            f"{dist.get('incorrect',0)} | {dist.get('partial',0)} |"
        )

    lines.extend([
        "",
        "## Pairwise Cohen's kappa",
        "",
        "| Pair | overlap | kappa | observed agreement | band |",
        "|---|---:|---:|---:|---|",
    ])
    for p in report["pairwise_cohen_kappa"]:
        lines.append(
            f"| {p['annotator_a']} vs {p['annotator_b']} | {p['overlap']} | "
            f"{p['kappa']:.4f} | {p['observed_agreement']:.4f} | `{p['landis_koch_band']}` |"
        )

    fa = report["fleiss_kappa_all"]
    lines.extend([
        "",
        "## Fleiss' kappa",
        "",
        f"- All annotators: kappa = {fa['kappa']:.4f} over {fa['n_items']} "
        f"items x {fa['n_annotators']} annotators "
        f"(`{fa.get('landis_koch_band','n/a')}`)",
    ])
    fl = report.get("fleiss_kappa_llm_only")
    if fl:
        lines.append(
            f"- LLM-only annotators: kappa = {fl['kappa']:.4f} over "
            f"{fl['n_items']} items x {fl['n_annotators']} annotators "
            f"(`{fl.get('landis_koch_band','n/a')}`)"
        )

    lines.extend([
        "",
        "## Consensus",
        "",
        f"- All-annotator overlap subset: {report['consensus_subset_size']} items",
        f"- Unanimous: {report['unanimous_items']} "
        f"({(report['unanimous_rate'] or 0) * 100:.1f}%)",
        "",
        "## Interpretation",
        "",
        "- Landis & Koch: <0.21 slight, 0.21-0.40 fair, 0.41-0.60 moderate, "
        "0.61-0.80 substantial, >0.80 almost perfect.",
        "- High LLM-only Fleiss kappa means the LLM annotators agree with "
        "each other and can serve as a consensus reference without circular "
        "dependence on any single model.",
        "- A large strictness gap between annotators (very different "
        "correct/incorrect splits) explains precision-estimate divergence "
        "even when kappa is moderate.",
    ])
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-annotator agreement (Cohen + Fleiss).")
    parser.add_argument("--source", required=True, nargs="+",
                        help="NAME:FIELD:PATH triples.")
    parser.add_argument("--categories", nargs="+", default=DEFAULT_CATEGORIES)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = build_report(args.source, args.categories)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({
        "output_json": str(args.output_json),
        "output_md": str(args.output_md),
        "annotators": report["annotators"],
        "pairwise": [
            {"pair": f"{p['annotator_a']}/{p['annotator_b']}", "kappa": p["kappa"], "overlap": p["overlap"]}
            for p in report["pairwise_cohen_kappa"]
        ],
        "fleiss_all": report["fleiss_kappa_all"]["kappa"],
        "fleiss_llm_only": (report["fleiss_kappa_llm_only"] or {}).get("kappa"),
    }, indent=2))


if __name__ == "__main__":
    main()
