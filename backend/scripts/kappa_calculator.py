#!/usr/bin/env python3
"""Cohen's kappa between two annotators (e.g., Pedro vs LLM) on overlapping rows.

Reads:
  - one or more "gold" JSONL files exposing `signal_id` + `gold_decision`
  - one LLM annotator JSONL exposing `signal_id` + `annotator_decision`

Aligns rows by `signal_id`, computes:
  - observed agreement (Po)
  - chance agreement (Pe)
  - Cohen's kappa with bootstrap 95% CI
  - confusion matrix
  - Landis & Koch interpretation band

Rows where either annotator's decision is missing or unclear are excluded
by default (configurable). Schema: atlas-kappa-v1.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "atlas-kappa-v1"
DEFAULT_RESAMPLES = 10000
DEFAULT_SEED = 20260527
DEFAULT_CONFIDENCE = 0.95
LANDIS_KOCH = [
    (0.0, "poor"),
    (0.21, "slight"),
    (0.41, "fair"),
    (0.61, "moderate"),
    (0.81, "substantial"),
    (1.01, "almost_perfect"),
]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _index_by_signal(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        sid = row.get("signal_id")
        if sid is None:
            continue
        out[int(sid)] = row
    return out


def cohen_kappa(pairs: list[tuple[str, str]], categories: list[str]) -> dict[str, Any]:
    """Compute Cohen's kappa from list of (a, b) decision pairs."""
    n = len(pairs)
    if n == 0:
        return {
            "n": 0,
            "observed_agreement": 0.0,
            "chance_agreement": 0.0,
            "kappa": 0.0,
        }
    cat_index = {c: i for i, c in enumerate(categories)}
    size = len(categories)
    matrix = [[0] * size for _ in range(size)]
    for a, b in pairs:
        if a in cat_index and b in cat_index:
            matrix[cat_index[a]][cat_index[b]] += 1

    agree = sum(matrix[i][i] for i in range(size))
    observed = agree / n
    a_marginals = [sum(row) for row in matrix]
    b_marginals = [sum(matrix[i][j] for i in range(size)) for j in range(size)]
    expected = sum(a_marginals[i] * b_marginals[i] for i in range(size)) / (n * n)
    if 1 - expected == 0:
        kappa = 0.0
    else:
        kappa = (observed - expected) / (1 - expected)
    return {
        "n": n,
        "observed_agreement": observed,
        "chance_agreement": expected,
        "kappa": kappa,
        "confusion_matrix": matrix,
        "categories": categories,
    }


def bootstrap_kappa_ci(
    pairs: list[tuple[str, str]],
    categories: list[str],
    *,
    n_resamples: int = DEFAULT_RESAMPLES,
    confidence: float = DEFAULT_CONFIDENCE,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    if not pairs:
        return {"low": 0.0, "high": 0.0, "median": 0.0, "n_resamples": 0}
    rng = random.Random(seed)
    kappas: list[float] = []
    for _ in range(n_resamples):
        resample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        result = cohen_kappa(resample, categories)
        kappas.append(result["kappa"])
    kappas.sort()
    alpha = (1 - confidence) / 2
    low_idx = max(0, int(math.floor(alpha * n_resamples)))
    high_idx = min(n_resamples - 1, int(math.ceil((1 - alpha) * n_resamples)) - 1)
    return {
        "low": kappas[low_idx],
        "high": kappas[high_idx],
        "median": kappas[n_resamples // 2],
        "n_resamples": n_resamples,
    }


def landis_koch_band(kappa: float) -> str:
    for upper, label in LANDIS_KOCH:
        if kappa < upper:
            return label
    return "almost_perfect"


def build_report(
    *,
    gold_paths: list[Path],
    annotator_path: Path,
    exclude_unclear: bool = True,
    categories: list[str] | None = None,
    n_resamples: int = DEFAULT_RESAMPLES,
    confidence: float = DEFAULT_CONFIDENCE,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    gold_rows: list[dict[str, Any]] = []
    for path in gold_paths:
        gold_rows.extend(_read_jsonl(path))
    gold_index = _index_by_signal(gold_rows)
    annotator_index = _index_by_signal(_read_jsonl(annotator_path))

    if categories is None:
        categories = ["correct", "incorrect", "partial", "unclear"]
        if exclude_unclear:
            categories = [c for c in categories if c != "unclear"]

    pairs: list[tuple[str, str]] = []
    skipped_missing = 0
    skipped_unclear = 0
    skipped_other = 0
    matched_ids: list[int] = []

    overlap_ids = sorted(set(gold_index.keys()) & set(annotator_index.keys()))
    for sid in overlap_ids:
        g = gold_index[sid].get("gold_decision") or gold_index[sid].get("reviewer_decision")
        a = annotator_index[sid].get("annotator_decision")
        if g is None or a is None:
            skipped_missing += 1
            continue
        if exclude_unclear and ("unclear" in (g, a)):
            skipped_unclear += 1
            continue
        if g not in categories or a not in categories:
            skipped_other += 1
            continue
        pairs.append((g, a))
        matched_ids.append(sid)

    kappa_result = cohen_kappa(pairs, categories)
    bootstrap = bootstrap_kappa_ci(
        pairs,
        categories,
        n_resamples=n_resamples,
        confidence=confidence,
        seed=seed,
    )
    band = landis_koch_band(kappa_result["kappa"])

    return {
        "schema_version": SCHEMA_VERSION,
        "gold_inputs": [str(p) for p in gold_paths],
        "annotator_input": str(annotator_path),
        "categories": categories,
        "gold_rows": len(gold_index),
        "annotator_rows": len(annotator_index),
        "overlap_rows": len(overlap_ids),
        "matched_pairs": len(pairs),
        "skipped_missing": skipped_missing,
        "skipped_unclear": skipped_unclear,
        "skipped_other": skipped_other,
        "kappa": kappa_result["kappa"],
        "observed_agreement": kappa_result["observed_agreement"],
        "chance_agreement": kappa_result["chance_agreement"],
        "confusion_matrix": kappa_result.get("confusion_matrix"),
        "bootstrap_ci_low": bootstrap["low"],
        "bootstrap_ci_high": bootstrap["high"],
        "bootstrap_median": bootstrap["median"],
        "landis_koch_band": band,
        "matched_signal_ids": matched_ids,
    }


def render_markdown(report: dict[str, Any], *, title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"Schema: `{report['schema_version']}`",
        f"Resamples: {DEFAULT_RESAMPLES} · Categories: {report['categories']}",
        "",
        "## Inputs",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| Gold rows | {report['gold_rows']} |",
        f"| Annotator rows | {report['annotator_rows']} |",
        f"| Overlapping signal_ids | {report['overlap_rows']} |",
        f"| Matched pairs (after filters) | {report['matched_pairs']} |",
        f"| Skipped (missing decision) | {report['skipped_missing']} |",
        f"| Skipped (unclear) | {report['skipped_unclear']} |",
        f"| Skipped (other) | {report['skipped_other']} |",
        "",
        "## Cohen's kappa",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Cohen's kappa | {report['kappa']:.4f} |",
        f"| Observed agreement (Po) | {report['observed_agreement']:.4f} |",
        f"| Chance agreement (Pe) | {report['chance_agreement']:.4f} |",
        f"| Bootstrap 95% CI | [{report['bootstrap_ci_low']:.4f}, {report['bootstrap_ci_high']:.4f}] |",
        f"| Landis & Koch band | `{report['landis_koch_band']}` |",
        "",
        "## Confusion matrix (rows = gold, cols = annotator)",
        "",
    ]
    cats = report["categories"]
    header = "| | " + " | ".join(cats) + " |"
    sep = "|---|" + ("---:|" * len(cats))
    lines.append(header)
    lines.append(sep)
    matrix = report.get("confusion_matrix") or []
    for i, row in enumerate(matrix):
        lines.append(f"| **{cats[i]}** | " + " | ".join(str(v) for v in row) + " |")

    lines.extend([
        "",
        "## Interpretation notes",
        "",
        "- Landis & Koch bands: <0.21 slight, 0.21-0.40 fair, 0.41-0.60 moderate, "
        "0.61-0.80 substantial, >0.80 almost perfect.",
        "- Bootstrap CI is computed by resampling the matched-pair list with "
        "replacement; CIs are wider when matched pair count is small.",
        "- `unclear` decisions are excluded by default because they signal "
        "missing-decision rather than a positive labeling category. Toggle via "
        "`--include-unclear` to compare the full 4-category response space.",
        "- A high kappa does NOT mean both annotators are correct, only that "
        "they agree. Use this together with the benchmark precision report.",
    ])
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cohen's kappa between two atlas annotators.")
    parser.add_argument("--gold", required=True, nargs="+", type=Path)
    parser.add_argument("--annotator", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--title", default="Cohen's kappa — atlas annotator agreement")
    parser.add_argument("--include-unclear", action="store_true")
    parser.add_argument("--n-resamples", type=int, default=DEFAULT_RESAMPLES)
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = build_report(
        gold_paths=args.gold,
        annotator_path=args.annotator,
        exclude_unclear=not args.include_unclear,
        n_resamples=args.n_resamples,
        confidence=args.confidence,
        seed=args.seed,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(report, title=args.title), encoding="utf-8")
    print(json.dumps(
        {
            "output_json": str(args.output_json),
            "output_md": str(args.output_md),
            "matched_pairs": report["matched_pairs"],
            "kappa": report["kappa"],
            "bootstrap_ci": [report["bootstrap_ci_low"], report["bootstrap_ci_high"]],
            "landis_koch_band": report["landis_koch_band"],
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
