"""Inter-annotator reliability on the gold base (#204) — Fleiss' kappa.

The formal methodological number for the paper: Fleiss' kappa measures multi-rater
agreement above chance. Computed over the items all 3 scriptable annotators
(DeepSeek, OpenAI, Codex) labeled, on the 32-category + OUT_OF_SCOPE label space.
Also reports kappa on the binary in-scope/out-of-scope decision (the reject class)
and per-label agreement.

Interpretation (Landis & Koch): <0 poor, 0–.20 slight, .21–.40 fair, .41–.60
moderate, .61–.80 substantial, .81–1 almost perfect.

Run: python -m backend.scripts.ensemble.kappa
"""
from __future__ import annotations

import json
from collections import Counter

GOLD = "docs/research/taxonomy-revision/goldset.json"
ANNS = ("deepseek", "openai", "codex")


def fleiss_kappa(rows: list[dict], categories: list[str]) -> tuple[float, int]:
    """rows: each a dict label->count (counts per category for one item, summing to n)."""
    cat_idx = {c: i for i, c in enumerate(categories)}
    N = len(rows)
    if N == 0:
        return 0.0, 0
    n = sum(rows[0].values())
    mat = [[0] * len(categories) for _ in range(N)]
    for i, r in enumerate(rows):
        for c, k in r.items():
            mat[i][cat_idx[c]] += k
    # P_i per item
    P = []
    for i in range(N):
        s = sum(v * v for v in mat[i])
        P.append((s - n) / (n * (n - 1)))
    P_bar = sum(P) / N
    # p_j marginal
    totals = [0] * len(categories)
    for i in range(N):
        for j in range(len(categories)):
            totals[j] += mat[i][j]
    p = [t / (N * n) for t in totals]
    P_e = sum(x * x for x in p)
    kappa = (P_bar - P_e) / (1 - P_e) if (1 - P_e) else 0.0
    return kappa, N


def band(k: float) -> str:
    return ("almost perfect" if k >= 0.81 else "substantial" if k >= 0.61 else
            "moderate" if k >= 0.41 else "fair" if k >= 0.21 else "slight" if k >= 0 else "poor")


def main() -> int:
    with open(GOLD) as f:
        data = json.load(f)
    recs = [r for r in data["records"] if all(r.get(a) for a in ANNS)]
    cats = sorted({r[a] for r in recs for a in ANNS})

    # full 32+OOS label space
    full = [Counter(r[a] for a in ANNS) for r in recs]
    k_full, n_full = fleiss_kappa([dict(c) for c in full], cats)

    # binary in-scope vs OUT_OF_SCOPE (the reject decision)
    bin_rows = [{("OOS" if r[a] == "OUT_OF_SCOPE" else "IN"): 0 for a in ANNS} for r in recs]
    bin_rows = []
    for r in recs:
        c = Counter("OOS" if r[a] == "OUT_OF_SCOPE" else "IN" for a in ANNS)
        bin_rows.append(dict(c))
    k_bin, _ = fleiss_kappa(bin_rows, ["IN", "OOS"])

    # in-scope-only label space (exclude items where majority is OOS) — pure
    # category separability among crisis types
    in_recs = [r for r in recs if Counter(r[a] for a in ANNS).most_common(1)[0][0] != "OUT_OF_SCOPE"]
    in_cats = sorted({r[a] for r in in_recs for a in ANNS})
    k_in, n_in = fleiss_kappa([dict(Counter(r[a] for a in ANNS)) for r in in_recs], in_cats)

    print(f"=== Fleiss' kappa — gold base (#204), {len(recs)} items, 3 annotators ===")
    print(f"  full label space (32 cats + OOS) : kappa = {k_full:.3f}  ({band(k_full)})  n={n_full}")
    print(f"  binary in-scope / OUT_OF_SCOPE   : kappa = {k_bin:.3f}  ({band(k_bin)})")
    print(f"  in-category (crisis types only)  : kappa = {k_in:.3f}  ({band(k_in)})  n={n_in}")
    unan = sum(1 for r in recs if len({r[a] for a in ANNS}) == 1)
    print(f"  unanimous (3/3)                  : {unan}/{len(recs)} = {unan/len(recs):.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
