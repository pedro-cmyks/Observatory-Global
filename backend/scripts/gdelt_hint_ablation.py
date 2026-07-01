"""GDELT theme-hint ablation — the reproducibility GATE on Paper 1's 41.6% (PR3-05).

The Atlas classifier (theme-hint-lex-v2) reaches a topic via the JOIN
`s.themes && t.gdelt_theme_hints` (a GDELT-theme overlap generates the candidate),
then records HOW it qualified: `evidence.theme_hits` (|themes ∩ hints|) and
`evidence.lex_count` (matched lexicon terms). The gdelt-decoupling spec §3.2 asks:
if we REMOVE the GDELT theme-hints, how many TRUE assignments vanish, and does the
semantic path recover them? Theme-hints STAY until this passes the decision rule —
so this script is the gate, and (per the paper ledger) it did not exist.

MECHANISM decomposition, per gold assignment:
  - lex_count >= 1  -> LEXICON-recoverable: a standalone lexicon matcher (no theme
    JOIN) keeps this assignment after theme-hints are removed.
  - lex_count == 0  -> THEME-HINT-DEPENDENT: only the GDELT-theme overlap carried
    it; it vanishes unless the SEMANTIC path recovers it.

STAGE 1 (pure, from the consensus gold — no model): baseline precision, the
ablated (lexicon-standalone) precision, the recall cost (theme-hint-dependent
CORRECT assignments lost), and the noise removed (theme-hint-dependent NOT-correct).

STAGE 2 (--semantic, needs the e5 embedder + DB topic descriptions): for each
theme-hint-dependent CORRECT assignment, embed headline vs the assigned topic's
label+description; cosine >= threshold => the semantic path recovers it. Reports
semantic recall on the lost set — the §3.2 decision input.

DECISION RULE (§3.2): remove theme-hints in prod ONLY IF semantic recall >=
theme-hint recall on the lost set (no net true-assignment loss), OR the lost
assignments are measurably noise (theme-hint-dependent precision << baseline).

Read-only, repeatable. Usage (from backend/):
    python -m scripts.gdelt_hint_ablation [--gold PATH] [--semantic] [--threshold 0.78]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_DEFAULT_GOLD = (
    "docs/research/atlas-paper/phase-1-validation/labels/"
    "2026-06-02-atlas-v2-batch-03.consensus-gold.jsonl"
)
# gold_decision values that count as a TRUE assignment vs a usable-but-not-true one.
_CORRECT = {"correct"}
_USABLE_NOT_CORRECT = {"incorrect", "partial"}  # 'unclear' is excluded from the denominator


def _load(path: str) -> list[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _lex_count(r: dict) -> int:
    e = r.get("evidence") or {}
    lc = e.get("lex_count")
    if lc is None:  # older rows: fall back to matched_terms length
        lc = len(e.get("matched_terms") or [])
    return int(lc or 0)


def _theme_hits(r: dict) -> int:
    e = r.get("evidence") or {}
    return int(e.get("theme_hits") or 0)


def stage1(rows: list[dict]) -> dict:
    usable = [r for r in rows if r.get("gold_decision") in (_CORRECT | _USABLE_NOT_CORRECT)]
    correct = [r for r in usable if r.get("gold_decision") in _CORRECT]

    # partition by mechanism
    lex_recoverable = [r for r in usable if _lex_count(r) >= 1]      # survives ablation
    theme_dependent = [r for r in usable if _lex_count(r) == 0]      # vanishes w/o theme-hints

    lex_correct = [r for r in lex_recoverable if r.get("gold_decision") in _CORRECT]
    dep_correct = [r for r in theme_dependent if r.get("gold_decision") in _CORRECT]
    dep_notcorrect = [r for r in theme_dependent if r.get("gold_decision") in _USABLE_NOT_CORRECT]

    def pct(a, b):
        return round(100.0 * a / b, 1) if b else None

    return {
        "n_total_rows": len(rows),
        "n_usable": len(usable),
        "baseline_correct": len(correct),
        "baseline_precision_pct": pct(len(correct), len(usable)),
        # ablated engine = lexicon standalone (theme-hints removed)
        "ablated_n_assignments": len(lex_recoverable),
        "ablated_correct": len(lex_correct),
        "ablated_precision_pct": pct(len(lex_correct), len(lex_recoverable)),
        # what theme-hints uniquely contribute
        "theme_dependent_n": len(theme_dependent),
        "theme_dependent_correct": len(dep_correct),      # recall cost (lost true assignments)
        "theme_dependent_notcorrect": len(dep_notcorrect),  # noise removed
        "theme_dependent_precision_pct": pct(len(dep_correct), len(theme_dependent)),
        "recall_cost_frac_of_correct_pct": pct(len(dep_correct), len(correct)),
        "_dep_correct_rows": dep_correct,  # handed to stage 2 (stripped before write)
    }


async def stage2(dep_correct: list[dict], threshold: float) -> dict:
    """Semantic recovery of the theme-hint-dependent CORRECT assignments."""
    from app.services.research_semantic import embed_texts, embedder_available
    if not embedder_available():
        return {"available": False, "note": "run from a model venv (torch/transformers)"}
    import asyncpg
    import numpy as np

    # assigned topic label+description for the recovery target
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        trows = await conn.fetch("SELECT slug, label, description FROM atlas_topics")
    finally:
        await conn.close()
    desc = {t["slug"]: f"{t['label']}. {t['description'] or ''}".strip() for t in trows}

    targets = [r for r in dep_correct if r.get("assigned_topic_slug") in desc]
    if not targets:
        return {"available": True, "n": 0, "note": "no dep-correct rows with a known topic desc"}

    head_vecs = embed_texts([f"query: {r['headline']}" for r in targets])
    topic_vecs = embed_texts([f"passage: {desc[r['assigned_topic_slug']]}" for r in targets])
    if head_vecs is None or topic_vecs is None:
        return {"available": True, "error": "embed failed"}

    hv = np.asarray(head_vecs, dtype=float)
    tv = np.asarray(topic_vecs, dtype=float)
    hv /= (np.linalg.norm(hv, axis=1, keepdims=True) + 1e-9)
    tv /= (np.linalg.norm(tv, axis=1, keepdims=True) + 1e-9)
    sims = (hv * tv).sum(axis=1)
    recovered = int((sims >= threshold).sum())
    return {
        "available": True,
        "threshold": threshold,
        "n_theme_dependent_correct": len(targets),
        "semantic_recovered": recovered,
        "semantic_recall_pct": round(100.0 * recovered / len(targets), 1),
        "sim_min": round(float(sims.min()), 3),
        "sim_median": round(float(np.median(sims)), 3),
        "sim_max": round(float(sims.max()), 3),
    }


def _verdict(s1: dict, s2: dict | None) -> str:
    dep_prec = s1["theme_dependent_precision_pct"] or 0
    base_prec = s1["baseline_precision_pct"] or 0
    noise = dep_prec < base_prec  # the theme-only assignments are worse than baseline
    if s2 and s2.get("available") and s2.get("n_theme_dependent_correct"):
        rec = s2["semantic_recall_pct"] or 0
        if rec >= 50 and noise:
            return (f"REMOVE-OK: theme-dependent is noise ({dep_prec}% < baseline {base_prec}%) "
                    f"AND semantic recovers {rec}% of the lost corrects.")
        if noise:
            return (f"REMOVE-OK-ON-NOISE: theme-dependent precision {dep_prec}% << baseline "
                    f"{base_prec}% (mostly false matches); semantic recovers only {rec}% but the "
                    f"lost set is small ({s1['theme_dependent_correct']} corrects).")
        return f"HOLD: semantic recall {rec}% insufficient and theme-dependent not clearly noise."
    if noise:
        return (f"REMOVE-OK-ON-NOISE (stage-1 only): theme-dependent precision {dep_prec}% << "
                f"baseline {base_prec}% — the theme-only path is mostly false matches; only "
                f"{s1['theme_dependent_correct']} correct assignments at risk. Run --semantic to "
                f"confirm recovery of those.")
    return "HOLD: theme-dependent path is not clearly noise; keep theme-hints pending semantic run."


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=_DEFAULT_GOLD)
    ap.add_argument("--semantic", action="store_true", help="run stage-2 semantic recovery")
    ap.add_argument("--threshold", type=float, default=0.78, help="cosine cut for recovery")
    ap.add_argument("--out", default="docs/research/embedding-ablation/2026-07-01-gdelt-hint-ablation.json")
    args = ap.parse_args()

    rows = _load(args.gold)
    s1 = stage1(rows)
    dep_correct = s1.pop("_dep_correct_rows")

    s2 = None
    if args.semantic:
        s2 = await stage2(dep_correct, args.threshold)

    verdict = _verdict(s1, s2)
    report = {"gold": args.gold, "stage1": s1, "stage2": s2, "verdict": verdict}

    print(json.dumps(report, indent=2))
    print("\n" + "=" * 72)
    print(f"BASELINE (with theme-hints):  {s1['baseline_correct']}/{s1['n_usable']} = "
          f"{s1['baseline_precision_pct']}%")
    print(f"ABLATED  (lexicon-standalone): {s1['ablated_correct']}/{s1['ablated_n_assignments']} = "
          f"{s1['ablated_precision_pct']}%")
    print(f"THEME-HINT-DEPENDENT: {s1['theme_dependent_n']} assignments, "
          f"{s1['theme_dependent_correct']} correct ({s1['theme_dependent_precision_pct']}%) — "
          f"recall cost = {s1['recall_cost_frac_of_correct_pct']}% of all corrects")
    if s2:
        print(f"SEMANTIC RECOVERY: {s2}")
    print(f"\nVERDICT: {verdict}")

    try:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nwrote {args.out}")
    except OSError as e:
        print(f"(could not write report: {e})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
