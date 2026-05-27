#!/usr/bin/env python3
"""Bootstrap and Wilson confidence intervals for Atlas topic benchmark labels.

Reads one or more reviewed/gold JSONL files produced by
`atlas_label_workflow.py finalize-review`, computes per-topic Wilson 95% CIs
and an overall stratified-bootstrap 95% CI for precision, and renders a
forest-plot SVG plus a Markdown summary.

No external dependencies. Stdlib only.

Schema version: atlas-bootstrap-ci-v1
"""

from __future__ import annotations

import argparse
import html
import json
import math
import random
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "atlas-bootstrap-ci-v1"
DEFAULT_RESAMPLES = 10000
DEFAULT_CONFIDENCE = 0.95
DEFAULT_MINIMUM = 0.85
DEFAULT_TARGET = 0.90

CHART_WIDTH = 920
ROW_HEIGHT = 26
ROW_GAP = 6
LEFT_MARGIN = 220
RIGHT_MARGIN = 80
TOP_MARGIN = 80
BOTTOM_MARGIN = 60


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _decision_of(row: dict[str, Any]) -> str | None:
    decision = (
        row.get("gold_decision")
        or row.get("reviewer_decision")
        or row.get("decision")
    )
    if decision in {"correct", "incorrect", "partial", "unclear"}:
        return decision
    return None


def _topic_of(row: dict[str, Any]) -> str | None:
    return row.get("assigned_topic_slug") or row.get("topic_slug")


def wilson_interval(k: int, n: int, confidence: float = DEFAULT_CONFIDENCE) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        return (0.0, 0.0)
    z = _z_for_confidence(confidence)
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return (low, high)


def _z_for_confidence(confidence: float) -> float:
    table = {0.90: 1.6449, 0.95: 1.9600, 0.99: 2.5758}
    return table.get(round(confidence, 2), 1.9600)


def stratified_bootstrap_precision(
    strata: dict[str, list[int]],
    *,
    n_resamples: int,
    confidence: float,
    seed: int,
) -> dict[str, Any]:
    """Stratified bootstrap CI for overall precision.

    Each stratum holds 0/1 outcomes for one topic. Resample with replacement
    within each stratum to its original size, compute precision across the
    pooled resample, repeat N times. CI is the percentile interval.
    """
    rng = random.Random(seed)
    precisions: list[float] = []
    pooled_n = sum(len(values) for values in strata.values())
    if pooled_n == 0:
        return {"low": 0.0, "high": 0.0, "median": 0.0, "n_resamples": 0}

    for _ in range(n_resamples):
        correct = 0
        for values in strata.values():
            for _i in range(len(values)):
                if values[rng.randrange(len(values))] == 1:
                    correct += 1
        precisions.append(correct / pooled_n)

    precisions.sort()
    alpha = (1 - confidence) / 2
    low_idx = int(math.floor(alpha * n_resamples))
    high_idx = int(math.ceil((1 - alpha) * n_resamples)) - 1
    low_idx = max(0, min(low_idx, n_resamples - 1))
    high_idx = max(0, min(high_idx, n_resamples - 1))
    median = precisions[n_resamples // 2]
    return {
        "low": precisions[low_idx],
        "high": precisions[high_idx],
        "median": median,
        "n_resamples": n_resamples,
    }


def gate_label(precision: float, minimum: float, target: float) -> str:
    if precision >= target:
        return "pass_target"
    if precision >= minimum:
        return "pass_minimum"
    return "fail"


def compute_report(
    rows: list[dict[str, Any]],
    *,
    n_resamples: int,
    confidence: float,
    minimum: float,
    target: float,
    seed: int,
    inputs: list[str],
) -> dict[str, Any]:
    by_topic_outcomes: dict[str, list[int]] = {}
    unclear_per_topic: dict[str, int] = {}
    incorrect_per_topic: dict[str, int] = {}
    correct_per_topic: dict[str, int] = {}
    total_labeled = 0
    total_correct = 0
    total_incorrect = 0
    total_unclear = 0

    for row in rows:
        decision = _decision_of(row)
        topic = _topic_of(row)
        if not topic or decision is None:
            continue
        if decision == "unclear":
            unclear_per_topic[topic] = unclear_per_topic.get(topic, 0) + 1
            total_unclear += 1
            continue
        outcome = 1 if decision == "correct" else 0
        by_topic_outcomes.setdefault(topic, []).append(outcome)
        if outcome == 1:
            correct_per_topic[topic] = correct_per_topic.get(topic, 0) + 1
            total_correct += 1
        else:
            incorrect_per_topic[topic] = incorrect_per_topic.get(topic, 0) + 1
            total_incorrect += 1
        total_labeled += 1

    by_topic: dict[str, dict[str, Any]] = {}
    for topic, outcomes in sorted(by_topic_outcomes.items()):
        n = len(outcomes)
        k = sum(outcomes)
        precision = k / n if n else 0.0
        low, high = wilson_interval(k, n, confidence)
        by_topic[topic] = {
            "labeled": n,
            "correct": k,
            "incorrect": incorrect_per_topic.get(topic, 0),
            "unclear": unclear_per_topic.get(topic, 0),
            "precision": round(precision, 4),
            "wilson_ci_low": round(low, 4),
            "wilson_ci_high": round(high, 4),
            "gate": gate_label(precision, minimum, target),
        }

    overall_precision = total_correct / total_labeled if total_labeled else 0.0
    overall_wilson = wilson_interval(total_correct, total_labeled, confidence)
    overall_bootstrap = stratified_bootstrap_precision(
        by_topic_outcomes,
        n_resamples=n_resamples,
        confidence=confidence,
        seed=seed,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "inputs": inputs,
        "n_resamples": n_resamples,
        "confidence_level": confidence,
        "seed": seed,
        "gate": {"minimum": minimum, "target": target},
        "overall": {
            "labeled": total_labeled,
            "correct": total_correct,
            "incorrect": total_incorrect,
            "unclear": total_unclear,
            "precision": round(overall_precision, 4),
            "wilson_ci_low": round(overall_wilson[0], 4),
            "wilson_ci_high": round(overall_wilson[1], 4),
            "bootstrap_ci_low": round(overall_bootstrap["low"], 4),
            "bootstrap_ci_high": round(overall_bootstrap["high"], 4),
            "bootstrap_median": round(overall_bootstrap["median"], 4),
            "gate": gate_label(overall_precision, minimum, target),
        },
        "by_topic": by_topic,
    }


def render_forest_svg(report: dict[str, Any], output_path: Path, *, title: str) -> None:
    topics = sorted(
        report["by_topic"].items(),
        key=lambda kv: (-(kv[1]["labeled"]), kv[0]),
    )
    rows: list[tuple[str, float, float, float, int]] = [
        (slug, m["precision"], m["wilson_ci_low"], m["wilson_ci_high"], m["labeled"])
        for slug, m in topics
    ]
    overall = report["overall"]
    rows.append(
        (
            "OVERALL",
            overall["precision"],
            overall["bootstrap_ci_low"],
            overall["bootstrap_ci_high"],
            overall["labeled"],
        )
    )

    height = TOP_MARGIN + len(rows) * (ROW_HEIGHT + ROW_GAP) + BOTTOM_MARGIN
    plot_width = CHART_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    minimum = report["gate"]["minimum"]
    target = report["gate"]["target"]

    def x_of(value: float) -> float:
        return LEFT_MARGIN + value * plot_width

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CHART_WIDTH}" height="{height}" '
        f'viewBox="0 0 {CHART_WIDTH} {height}">',
        '<rect width="100%" height="100%" fill="#071016"/>',
        f'<text x="24" y="32" fill="#d7fbe8" font-family="Inter, Arial, sans-serif" '
        f'font-size="18" font-weight="700">{html.escape(title)}</text>',
        f'<text x="24" y="54" fill="#7f93a4" font-family="Inter, Arial, sans-serif" '
        f'font-size="12">precision with 95% CI · Wilson per topic · stratified bootstrap overall</text>',
    ]

    # axis ticks at 0, 0.25, 0.5, 0.75, 1.0
    axis_y = height - BOTTOM_MARGIN + 18
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        tx = x_of(tick)
        lines.append(
            f'<line x1="{tx}" y1="{TOP_MARGIN - 6}" x2="{tx}" y2="{axis_y - 18}" '
            f'stroke="#1c2f3d" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{tx}" y="{axis_y}" fill="#7f93a4" font-family="Inter, Arial, sans-serif" '
            f'font-size="11" text-anchor="middle">{tick:.2f}</text>'
        )

    # gate lines
    for value, color, label in (
        (minimum, "#f1bf5b", f"min {minimum:.2f}"),
        (target, "#5ee6a8", f"target {target:.2f}"),
    ):
        gx = x_of(value)
        lines.append(
            f'<line x1="{gx}" y1="{TOP_MARGIN - 6}" x2="{gx}" y2="{axis_y - 18}" '
            f'stroke="{color}" stroke-width="1" stroke-dasharray="4 4" opacity="0.7"/>'
        )
        lines.append(
            f'<text x="{gx + 4}" y="{TOP_MARGIN + 4}" fill="{color}" '
            f'font-family="Inter, Arial, sans-serif" font-size="10">{html.escape(label)}</text>'
        )

    for index, (label, precision, low, high, n) in enumerate(rows):
        y = TOP_MARGIN + index * (ROW_HEIGHT + ROW_GAP)
        bar_color = "#75aaff" if label == "OVERALL" else "#5ee6a8"
        if precision < minimum:
            bar_color = "#ff6d7a" if label != "OVERALL" else "#75aaff"
        lines.append(
            f'<text x="24" y="{y + 17}" fill="#dbe8f2" font-family="Inter, Arial, sans-serif" '
            f'font-size="13">{html.escape(label)}</text>'
        )
        lines.append(
            f'<text x="{LEFT_MARGIN - 12}" y="{y + 17}" fill="#7f93a4" '
            f'font-family="Inter, Arial, sans-serif" font-size="11" '
            f'text-anchor="end">n={n}</text>'
        )
        # whisker
        x_low = x_of(low)
        x_high = x_of(high)
        cy = y + ROW_HEIGHT / 2
        lines.append(
            f'<line x1="{x_low}" y1="{cy}" x2="{x_high}" y2="{cy}" '
            f'stroke="{bar_color}" stroke-width="2" opacity="0.6"/>'
        )
        lines.append(
            f'<line x1="{x_low}" y1="{cy - 6}" x2="{x_low}" y2="{cy + 6}" '
            f'stroke="{bar_color}" stroke-width="2" opacity="0.6"/>'
        )
        lines.append(
            f'<line x1="{x_high}" y1="{cy - 6}" x2="{x_high}" y2="{cy + 6}" '
            f'stroke="{bar_color}" stroke-width="2" opacity="0.6"/>'
        )
        # point
        px = x_of(precision)
        lines.append(
            f'<circle cx="{px}" cy="{cy}" r="5" fill="{bar_color}"/>'
        )
        # value text
        lines.append(
            f'<text x="{CHART_WIDTH - RIGHT_MARGIN + 8}" y="{y + 17}" fill="#f4f7fb" '
            f'font-family="Inter, Arial, sans-serif" font-size="12">{precision * 100:.1f}%</text>'
        )

    lines.append("</svg>\n")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def render_markdown(report: dict[str, Any], *, title: str, forest_path: Path | None) -> str:
    overall = report["overall"]
    gate = report["gate"]
    lines = [
        f"# {title}",
        "",
        f"Schema: `{report['schema_version']}`",
        f"Resamples: {report['n_resamples']} · Confidence: {int(report['confidence_level'] * 100)}% · Seed: {report['seed']}",
        "",
        "## Overall",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Labeled | {overall['labeled']} |",
        f"| Correct | {overall['correct']} |",
        f"| Incorrect | {overall['incorrect']} |",
        f"| Unclear (excluded) | {overall['unclear']} |",
        f"| Precision | {overall['precision'] * 100:.2f}% |",
        f"| Wilson 95% CI | [{overall['wilson_ci_low'] * 100:.2f}%, {overall['wilson_ci_high'] * 100:.2f}%] |",
        f"| Bootstrap 95% CI (stratified) | [{overall['bootstrap_ci_low'] * 100:.2f}%, {overall['bootstrap_ci_high'] * 100:.2f}%] |",
        f"| Gate minimum | {gate['minimum'] * 100:.0f}% |",
        f"| Gate target | {gate['target'] * 100:.0f}% |",
        f"| Gate result | `{overall['gate']}` |",
        "",
        "## Per-topic precision (Wilson 95% CI)",
        "",
        "| Topic | n | correct | incorrect | unclear | precision | CI low | CI high | gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for slug, m in sorted(report["by_topic"].items(), key=lambda kv: (-kv[1]["labeled"], kv[0])):
        lines.append(
            f"| `{slug}` | {m['labeled']} | {m['correct']} | {m['incorrect']} | "
            f"{m['unclear']} | {m['precision'] * 100:.2f}% | "
            f"{m['wilson_ci_low'] * 100:.2f}% | {m['wilson_ci_high'] * 100:.2f}% | "
            f"`{m['gate']}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation notes",
            "",
            "- Wilson intervals are exact for binomial proportions and behave well when `n` is small or `p` is near 0/1.",
            "- The overall bootstrap CI uses stratified resampling: each topic stratum is resampled with replacement to its original size, then precision is recomputed on the pooled set. This preserves the topic mix and avoids degenerate CIs when one stratum is small.",
            "- Topics with `n = 1` produce wide Wilson intervals by design. Treat them as anecdotal until additional labels arrive.",
            "- A `pass_minimum` row clears the 85% floor but not the 90% target; treat as developing.",
        ]
    )

    if forest_path is not None:
        rel = forest_path.name
        lines.extend(
            [
                "",
                "## Forest plot",
                "",
                f"![Forest plot]({rel})",
            ]
        )

    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap and Wilson CIs for atlas benchmark labels.")
    parser.add_argument("--input", required=True, nargs="+", help="One or more reviewed/gold JSONL files.")
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--output-svg", required=True, type=Path)
    parser.add_argument("--title", default="Atlas benchmark — bootstrap CI")
    parser.add_argument("--n-resamples", type=int, default=DEFAULT_RESAMPLES)
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    parser.add_argument("--minimum", type=float, default=DEFAULT_MINIMUM)
    parser.add_argument("--target", type=float, default=DEFAULT_TARGET)
    parser.add_argument("--seed", type=int, default=20260527)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    rows: list[dict[str, Any]] = []
    for path in args.input:
        rows.extend(_read_jsonl(Path(path)))

    report = compute_report(
        rows,
        n_resamples=args.n_resamples,
        confidence=args.confidence,
        minimum=args.minimum,
        target=args.target,
        seed=args.seed,
        inputs=[str(p) for p in args.input],
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    render_forest_svg(report, args.output_svg, title=args.title)
    md = render_markdown(report, title=args.title, forest_path=args.output_svg)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(md, encoding="utf-8")

    print(json.dumps(
        {
            "output_json": str(args.output_json),
            "output_md": str(args.output_md),
            "output_svg": str(args.output_svg),
            "labeled": report["overall"]["labeled"],
            "precision": report["overall"]["precision"],
            "wilson_ci": [
                report["overall"]["wilson_ci_low"],
                report["overall"]["wilson_ci_high"],
            ],
            "bootstrap_ci": [
                report["overall"]["bootstrap_ci_low"],
                report["overall"]["bootstrap_ci_high"],
            ],
            "gate": report["overall"]["gate"],
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
