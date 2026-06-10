"""Read-only calibration run for research ranking weights + normalizers.

Usage (from backend/, with DATABASE_URL set):

    .venv/bin/python -m scripts.calibrate_research_ranking [--hours 168]

Pulls live thread distributions and the forcing-case anchor sets, calibrates
normalization midpoints from real percentiles, searches the weight simplex
against the gold ordering constraints plus live constraints, and writes a
JSON + Markdown report under docs/research/ranking-calibration/.

Does NOT mutate the database or production config: applying the recommended
values to ``research_ranking.py`` is an explicit, reviewed code change.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg

REPORT_DIR = Path(__file__).resolve().parents[2] / "docs" / "research" / "ranking-calibration"

FORCING_QUERIES = [
    "Iran climate water drought",
    "manipulación de clima Irán y ataques a bases estadounidenses satélite",
]


def _live_constraints(plans: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Live forcing-case constraint: every direct/context thread anchor must
    outrank every weak_support thread anchor within the same plan."""
    constraints: list[dict[str, Any]] = []
    for query, plan in plans.items():
        intent = plan["intent"]
        threads = [a for a in plan["all_anchors"] if a["anchor_type"] == "thread"]
        matched = [a for a in threads if a["evidence_label"] in ("direct_evidence", "context")]
        weak = [a for a in threads if a["evidence_label"] == "weak_support"]
        for m in matched:
            for w in weak:
                constraints.append({
                    "id": f"live:{query[:24]}:{m['id']}>{w['id']}",
                    "description": f"Live: '{m['label']}' (match) must outrank "
                                   f"'{w['label']}' (unmatched).",
                    "intent": intent,
                    "winner": m,
                    "loser": w,
                })
    return constraints


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=168)
    parser.add_argument("--samples", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    from app import db
    db.pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    from app.services.research_anchor_discovery import discover_anchors
    from app.services.research_plan import parse_research_intent
    from app.services.research_ranking import NORMALIZATION_MIDPOINTS, RANKING_WEIGHTS
    from app.services.research_ranking_calibration import (
        build_gold_constraints,
        evaluate_constraints,
        recommend_midpoints,
        search_weights,
    )
    from app.services.thread_intelligence import fetch_threads

    # ── 1. live thread population for normalizer calibration ────────────────
    # Anchors come from BOTH global threads (dynamic topics, large aggregates)
    # and country-scoped atlas threads (small, gated). Calibrating midpoints
    # on the global population alone would crush evidence_strength for every
    # country thread, so the population pools both shapes.
    population = list(await fetch_threads(hours=args.hours, limit=50))
    for code in ("IR", "US", "CO", "IL", "SA"):
        population.extend(
            await fetch_threads(hours=args.hours, limit=24, country_codes=[code])
        )
    midpoints = recommend_midpoints(population)

    # ── 2. forcing-case anchor sets (un-ranked, full candidate set) ─────────
    plans: dict[str, dict[str, Any]] = {}
    for query in FORCING_QUERIES:
        intent = parse_research_intent(query)
        plan = await discover_anchors(
            intent, hours=args.hours,
            fetch_threads_fn=fetch_threads, fetch_attention_fn=None,
        )
        plans[query] = {"intent": intent, "all_anchors": plan["anchors"]}

    await db.pool.close()

    # ── 3. constraints + weight search ──────────────────────────────────────
    gold = build_gold_constraints()
    live = _live_constraints(plans)
    constraints = gold + live
    result = search_weights(constraints, n_samples=args.samples, seed=args.seed)

    detail_best = evaluate_constraints(result["weights"], constraints)
    detail_gold = evaluate_constraints(result["weights"], gold)
    detail_live = evaluate_constraints(result["weights"], live)

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": now.isoformat(),
        "hours": args.hours,
        "seed": args.seed,
        "n_samples": args.samples,
        "thread_population_size": len(population),
        "current_weights": RANKING_WEIGHTS,
        "current_midpoints": NORMALIZATION_MIDPOINTS,
        "recommended_midpoints": midpoints,
        "recommended_weights": result["weights"],
        "baseline_evaluation": result["baseline_evaluation"],
        "best_evaluation": detail_best,
        "gold_evaluation": detail_gold,
        "live_evaluation": detail_live,
        "improved_over_baseline": result["improved_over_baseline"],
        "constraint_count": {"gold": len(gold), "live": len(live)},
        "violations": detail_best["violations"],
    }
    json_path = REPORT_DIR / f"{stamp}-ranking-calibration.json"
    json_path.write_text(json.dumps(report, indent=2, default=str))

    md_lines = [
        f"# Research ranking calibration — {stamp}",
        "",
        f"Window: {args.hours}h · thread population: {len(population)} · "
        f"seed {args.seed} · {args.samples} samples",
        "",
        "## Normalization midpoints (live medians → 0.5)",
        "",
        "| Normalizer | Current | Recommended |",
        "|---|---|---|",
    ]
    for key in ("evidence_signals", "source_count", "movement_changed_10h"):
        md_lines.append(
            f"| {key} | {NORMALIZATION_MIDPOINTS[key]} | {midpoints[key]} |"
        )
    md_lines += [
        "",
        "## Weights",
        "",
        f"Baseline satisfies {result['baseline_evaluation']['satisfied']}/"
        f"{result['baseline_evaluation']['total']} constraints "
        f"(min margin {result['baseline_evaluation']['min_margin']}).",
        f"Best satisfies {detail_best['satisfied']}/{detail_best['total']} "
        f"(min margin {detail_best['min_margin']}); gold "
        f"{detail_gold['satisfied']}/{detail_gold['total']}, live "
        f"{detail_live['satisfied']}/{detail_live['total']}.",
        "",
        "| Component | Current | Recommended |",
        "|---|---|---|",
    ]
    for key in RANKING_WEIGHTS:
        md_lines.append(
            f"| {key} | {RANKING_WEIGHTS[key]} | {result['weights'][key]} |"
        )
    if detail_best["violations"]:
        md_lines += ["", "## Unsatisfied constraints", ""]
        md_lines += [f"- `{v}`" for v in detail_best["violations"]]
    md_lines += [
        "",
        "## Method",
        "",
        "Weights are fit against pairwise ordering constraints derived from the",
        "spec's acceptance criteria (gold) plus live forcing-case anchors, not",
        "from the source-quality audit: source metrics inform at most",
        "`source_actor_value`/`noise_risk` and cannot trade `intent_match`",
        "against `evidence_strength`. Midpoints are live medians. Rerun this",
        "script when the data distribution shifts or when real user relevance",
        "judgments become available.",
        "",
    ]
    md_path = REPORT_DIR / f"{stamp}-ranking-calibration.md"
    md_path.write_text("\n".join(md_lines))

    print(json.dumps({
        "report_json": str(json_path),
        "report_md": str(md_path),
        "recommended_midpoints": midpoints,
        "recommended_weights": result["weights"],
        "baseline": result["baseline_evaluation"],
        "best": detail_best,
    }, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
