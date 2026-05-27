#!/usr/bin/env python3
"""Compare Atlas v2 classifier against LLM zero-shot / few-shot baselines.

Reads:
  - reviewed/gold JSONL files (Atlas v2 outcomes via gold_decision)
  - LLM predictions JSONL (atlas-llm-baseline-v1)

Computes for each method (atlas_v2, llm_zero_shot, llm_few_shot):
  - per-topic correct/incorrect counts and Wilson 95% CI
  - overall stratified bootstrap 95% CI

Outputs:
  - JSON comparison summary
  - Markdown comparison report
  - Forest plot SVG with three method colors

Reuses `benchmark_bootstrap` for statistical helpers.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_bootstrap as bb


SCHEMA_VERSION = "atlas-baseline-compare-v1"

METHOD_ATLAS = "atlas_v2"
METHOD_ZS = "llm_zero_shot"
METHOD_FS = "llm_few_shot"

METHOD_COLORS = {
    METHOD_ATLAS: "#75aaff",
    METHOD_ZS: "#5ee6a8",
    METHOD_FS: "#f1bf5b",
}

METHOD_LABELS = {
    METHOD_ATLAS: "Atlas v2 (lex + theme)",
    METHOD_ZS: "LLM zero-shot",
    METHOD_FS: "LLM few-shot",
}


def _load_gold(paths: list[Path]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            sid = row.get("signal_id")
            if sid is None:
                continue
            out[int(sid)] = row
    return out


def _load_predictions(path: Path) -> dict[str, dict[int, dict[str, Any]]]:
    out: dict[str, dict[int, dict[str, Any]]] = {METHOD_ZS: {}, METHOD_FS: {}}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        sid = row.get("signal_id")
        mode = row.get("llm_mode")
        if sid is None:
            continue
        if mode == "zero_shot":
            out[METHOD_ZS][int(sid)] = row
        elif mode == "few_shot":
            out[METHOD_FS][int(sid)] = row
    return out


def _outcomes_for_atlas(gold_rows: dict[int, dict[str, Any]]) -> dict[str, list[int]]:
    """Atlas v2 outcomes: 1 if gold_decision==correct, 0 if incorrect/partial."""
    by_topic: dict[str, list[int]] = {}
    for sid, row in gold_rows.items():
        decision = row.get("gold_decision") or row.get("reviewer_decision")
        if decision not in {"correct", "incorrect", "partial"}:
            continue
        topic = row.get("assigned_topic_slug")
        if not topic:
            continue
        outcome = 1 if decision == "correct" else 0
        by_topic.setdefault(topic, []).append(outcome)
    return by_topic


def _outcomes_for_llm(
    gold_rows: dict[int, dict[str, Any]],
    predictions: dict[int, dict[str, Any]],
) -> dict[str, list[int]]:
    """LLM outcomes: stratified by atlas-assigned topic so comparison is row-aligned.

    Per row:
      - if gold_decision == "correct": LLM is correct iff its predicted slug
        equals the atlas slug (which equals the gold slug here).
      - if gold_decision == "incorrect" / "partial": LLM is correct iff it
        rejected the atlas slug (predicted something else or "none").
      - unclear/missing: skipped.
    """
    by_topic: dict[str, list[int]] = {}
    for sid, gold in gold_rows.items():
        decision = gold.get("gold_decision") or gold.get("reviewer_decision")
        if decision not in {"correct", "incorrect", "partial"}:
            continue
        topic = gold.get("assigned_topic_slug")
        if not topic:
            continue
        pred = predictions.get(sid)
        if pred is None or pred.get("api_error"):
            continue
        llm_slug = pred.get("llm_predicted_slug")
        if decision == "correct":
            outcome = 1 if llm_slug == topic else 0
        else:
            outcome = 0 if llm_slug == topic else 1
        by_topic.setdefault(topic, []).append(outcome)
    return by_topic


def _method_report(
    outcomes: dict[str, list[int]],
    *,
    n_resamples: int,
    confidence: float,
    minimum: float,
    target: float,
    seed: int,
) -> dict[str, Any]:
    by_topic: dict[str, dict[str, Any]] = {}
    total_correct = 0
    total_labeled = 0
    for topic, values in sorted(outcomes.items()):
        n = len(values)
        k = sum(values)
        precision = k / n if n else 0.0
        low, high = bb.wilson_interval(k, n, confidence)
        by_topic[topic] = {
            "labeled": n,
            "correct": k,
            "incorrect": n - k,
            "precision": round(precision, 4),
            "wilson_ci_low": round(low, 4),
            "wilson_ci_high": round(high, 4),
            "gate": bb.gate_label(precision, minimum, target),
        }
        total_correct += k
        total_labeled += n

    overall_precision = total_correct / total_labeled if total_labeled else 0.0
    overall_wilson = bb.wilson_interval(total_correct, total_labeled, confidence)
    overall_bootstrap = bb.stratified_bootstrap_precision(
        outcomes,
        n_resamples=n_resamples,
        confidence=confidence,
        seed=seed,
    )
    return {
        "overall": {
            "labeled": total_labeled,
            "correct": total_correct,
            "incorrect": total_labeled - total_correct,
            "precision": round(overall_precision, 4),
            "wilson_ci_low": round(overall_wilson[0], 4),
            "wilson_ci_high": round(overall_wilson[1], 4),
            "bootstrap_ci_low": round(overall_bootstrap["low"], 4),
            "bootstrap_ci_high": round(overall_bootstrap["high"], 4),
            "gate": bb.gate_label(overall_precision, minimum, target),
        },
        "by_topic": by_topic,
    }


def build_comparison(
    *,
    gold_paths: list[Path],
    predictions_path: Path,
    n_resamples: int,
    confidence: float,
    minimum: float,
    target: float,
    seed: int,
) -> dict[str, Any]:
    gold = _load_gold(gold_paths)
    predictions = _load_predictions(predictions_path)
    atlas_outcomes = _outcomes_for_atlas(gold)
    zs_outcomes = _outcomes_for_llm(gold, predictions[METHOD_ZS])
    fs_outcomes = _outcomes_for_llm(gold, predictions[METHOD_FS])

    methods = {
        METHOD_ATLAS: _method_report(
            atlas_outcomes,
            n_resamples=n_resamples,
            confidence=confidence,
            minimum=minimum,
            target=target,
            seed=seed,
        ),
        METHOD_ZS: _method_report(
            zs_outcomes,
            n_resamples=n_resamples,
            confidence=confidence,
            minimum=minimum,
            target=target,
            seed=seed,
        ),
        METHOD_FS: _method_report(
            fs_outcomes,
            n_resamples=n_resamples,
            confidence=confidence,
            minimum=minimum,
            target=target,
            seed=seed,
        ),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "gold_inputs": [str(p) for p in gold_paths],
        "predictions_input": str(predictions_path),
        "n_resamples": n_resamples,
        "confidence_level": confidence,
        "seed": seed,
        "gate": {"minimum": minimum, "target": target},
        "methods": methods,
    }


def render_forest_svg(report: dict[str, Any], output_path: Path, *, title: str) -> None:
    methods = list(report["methods"].keys())
    # Use Atlas topic list as union of topics across methods.
    topic_union: list[str] = []
    seen: set[str] = set()
    for method in methods:
        for topic in report["methods"][method]["by_topic"].keys():
            if topic not in seen:
                seen.add(topic)
                topic_union.append(topic)
    topic_union.sort(
        key=lambda t: -max(
            report["methods"][m]["by_topic"].get(t, {}).get("labeled", 0)
            for m in methods
        )
    )

    chart_width = 1000
    left_margin = 230
    right_margin = 80
    plot_width = chart_width - left_margin - right_margin
    row_block = 60  # height per topic block (3 methods stacked)
    top_margin = 90
    bottom_margin = 70
    rows_count = len(topic_union) + 1  # +1 for overall block
    height = top_margin + rows_count * row_block + bottom_margin

    minimum = report["gate"]["minimum"]
    target = report["gate"]["target"]

    def x_of(value: float) -> float:
        return left_margin + value * plot_width

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{chart_width}" height="{height}" '
        f'viewBox="0 0 {chart_width} {height}">',
        '<rect width="100%" height="100%" fill="#071016"/>',
        f'<text x="24" y="32" fill="#d7fbe8" font-family="Inter, Arial, sans-serif" '
        f'font-size="18" font-weight="700">{html.escape(title)}</text>',
        f'<text x="24" y="54" fill="#7f93a4" font-family="Inter, Arial, sans-serif" '
        f'font-size="12">precision with 95% CI · Wilson per topic · stratified bootstrap overall</text>',
    ]

    # Legend
    legend_x = 24
    legend_y = 76
    for idx, method in enumerate(methods):
        color = METHOD_COLORS[method]
        lx = legend_x + idx * 230
        lines.append(
            f'<circle cx="{lx}" cy="{legend_y}" r="6" fill="{color}"/>'
        )
        lines.append(
            f'<text x="{lx + 12}" y="{legend_y + 4}" fill="#dbe8f2" '
            f'font-family="Inter, Arial, sans-serif" font-size="12">'
            f'{html.escape(METHOD_LABELS[method])}</text>'
        )

    # axis ticks
    axis_y = height - bottom_margin + 18
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        tx = x_of(tick)
        lines.append(
            f'<line x1="{tx}" y1="{top_margin - 6}" x2="{tx}" y2="{axis_y - 18}" '
            f'stroke="#1c2f3d" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{tx}" y="{axis_y}" fill="#7f93a4" font-family="Inter, Arial, sans-serif" '
            f'font-size="11" text-anchor="middle">{tick:.2f}</text>'
        )

    for value, color, label in (
        (minimum, "#f1bf5b", f"min {minimum:.2f}"),
        (target, "#5ee6a8", f"target {target:.2f}"),
    ):
        gx = x_of(value)
        lines.append(
            f'<line x1="{gx}" y1="{top_margin - 6}" x2="{gx}" y2="{axis_y - 18}" '
            f'stroke="{color}" stroke-width="1" stroke-dasharray="4 4" opacity="0.7"/>'
        )
        lines.append(
            f'<text x="{gx + 4}" y="{top_margin + 4}" fill="{color}" '
            f'font-family="Inter, Arial, sans-serif" font-size="10">{html.escape(label)}</text>'
        )

    def _emit_block(block_label: str, block_y: float, method_rows: list[tuple[str, float, float, float, int]]) -> None:
        lines.append(
            f'<text x="24" y="{block_y + 14}" fill="#dbe8f2" '
            f'font-family="Inter, Arial, sans-serif" font-size="13" '
            f'font-weight="600">{html.escape(block_label)}</text>'
        )
        for sub_idx, (method, precision, low, high, n) in enumerate(method_rows):
            sub_y = block_y + 6 + sub_idx * 16
            color = METHOD_COLORS[method]
            lines.append(
                f'<text x="{left_margin - 12}" y="{sub_y + 6}" fill="#7f93a4" '
                f'font-family="Inter, Arial, sans-serif" font-size="11" '
                f'text-anchor="end">n={n}</text>'
            )
            x_low = x_of(low)
            x_high = x_of(high)
            lines.append(
                f'<line x1="{x_low}" y1="{sub_y}" x2="{x_high}" y2="{sub_y}" '
                f'stroke="{color}" stroke-width="2" opacity="0.6"/>'
            )
            lines.append(
                f'<line x1="{x_low}" y1="{sub_y - 5}" x2="{x_low}" y2="{sub_y + 5}" '
                f'stroke="{color}" stroke-width="2" opacity="0.6"/>'
            )
            lines.append(
                f'<line x1="{x_high}" y1="{sub_y - 5}" x2="{x_high}" y2="{sub_y + 5}" '
                f'stroke="{color}" stroke-width="2" opacity="0.6"/>'
            )
            lines.append(
                f'<circle cx="{x_of(precision)}" cy="{sub_y}" r="4" fill="{color}"/>'
            )
            lines.append(
                f'<text x="{chart_width - right_margin + 8}" y="{sub_y + 4}" fill="#f4f7fb" '
                f'font-family="Inter, Arial, sans-serif" font-size="11">{precision * 100:.1f}%</text>'
            )

    for index, topic in enumerate(topic_union):
        block_y = top_margin + index * row_block
        method_rows = []
        for method in methods:
            m = report["methods"][method]["by_topic"].get(topic)
            if m is None:
                continue
            method_rows.append(
                (method, m["precision"], m["wilson_ci_low"], m["wilson_ci_high"], m["labeled"])
            )
        _emit_block(topic, block_y, method_rows)

    overall_y = top_margin + len(topic_union) * row_block + 8
    method_rows = []
    for method in methods:
        overall = report["methods"][method]["overall"]
        method_rows.append(
            (
                method,
                overall["precision"],
                overall["bootstrap_ci_low"],
                overall["bootstrap_ci_high"],
                overall["labeled"],
            )
        )
    _emit_block("OVERALL (bootstrap CI)", overall_y, method_rows)

    lines.append("</svg>\n")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def render_markdown(report: dict[str, Any], *, title: str, forest_path: Path | None) -> str:
    methods = list(report["methods"].keys())
    lines = [
        f"# {title}",
        "",
        f"Schema: `{report['schema_version']}`",
        f"Resamples: {report['n_resamples']} · Confidence: {int(report['confidence_level'] * 100)}% · Seed: {report['seed']}",
        "",
        "## Overall precision (gold-aligned outcomes)",
        "",
        "| Method | n | correct | precision | Wilson 95% CI | Bootstrap 95% CI | Gate |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for method in methods:
        overall = report["methods"][method]["overall"]
        lines.append(
            f"| **{METHOD_LABELS[method]}** | {overall['labeled']} | {overall['correct']} | "
            f"{overall['precision'] * 100:.2f}% | "
            f"[{overall['wilson_ci_low'] * 100:.2f}%, {overall['wilson_ci_high'] * 100:.2f}%] | "
            f"[{overall['bootstrap_ci_low'] * 100:.2f}%, {overall['bootstrap_ci_high'] * 100:.2f}%] | "
            f"`{overall['gate']}` |"
        )

    lines.extend([
        "",
        "## Per-topic precision",
        "",
        "| Topic | Method | n | correct | precision | Wilson 95% CI | Gate |",
        "|---|---|---:|---:|---:|---|---|",
    ])
    # union of topics across methods, sorted by total atlas labeled desc
    topic_union: list[str] = []
    seen: set[str] = set()
    for method in methods:
        for topic in report["methods"][method]["by_topic"].keys():
            if topic not in seen:
                seen.add(topic)
                topic_union.append(topic)
    topic_union.sort(
        key=lambda t: -max(
            report["methods"][m]["by_topic"].get(t, {}).get("labeled", 0)
            for m in methods
        )
    )

    for topic in topic_union:
        for method in methods:
            m = report["methods"][method]["by_topic"].get(topic)
            if m is None:
                continue
            lines.append(
                f"| `{topic}` | {METHOD_LABELS[method]} | {m['labeled']} | {m['correct']} | "
                f"{m['precision'] * 100:.2f}% | "
                f"[{m['wilson_ci_low'] * 100:.2f}%, {m['wilson_ci_high'] * 100:.2f}%] | "
                f"`{m['gate']}` |"
            )

    lines.extend([
        "",
        "## Interpretation",
        "",
        "- LLM outcomes are stratified by the Atlas-assigned topic. Each row "
        "contributes one outcome per method: 1 if the method's prediction aligns "
        "with the gold judgement of the Atlas assignment, 0 otherwise.",
        "- For LLM rows with `gold_decision == 'correct'`: success means the LLM "
        "predicted the same slug as Atlas. For `gold_decision == 'incorrect'`: "
        "success means the LLM rejected the Atlas slug (predicted something else "
        "or 'none').",
        "- Per-topic CIs are Wilson exact intervals. Overall CIs use stratified "
        "bootstrap resampling.",
        "- The LLM zero-shot result here is an upper bound, not a deployment "
        "claim: it costs an API call per signal, has no multilingual lex coverage "
        "outside the model, and reflects a single inference per row at "
        "temperature 0.",
    ])

    if forest_path is not None:
        lines.extend([
            "",
            "## Forest plot",
            "",
            f"![Forest plot]({forest_path.name})",
        ])

    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Atlas v2 vs LLM baselines.")
    parser.add_argument("--gold", required=True, nargs="+", type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--output-svg", required=True, type=Path)
    parser.add_argument("--title", default="Atlas v2 vs LLM baselines — benchmark comparison")
    parser.add_argument("--n-resamples", type=int, default=10000)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--minimum", type=float, default=0.85)
    parser.add_argument("--target", type=float, default=0.90)
    parser.add_argument("--seed", type=int, default=20260527)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = build_comparison(
        gold_paths=args.gold,
        predictions_path=args.predictions,
        n_resamples=args.n_resamples,
        confidence=args.confidence,
        minimum=args.minimum,
        target=args.target,
        seed=args.seed,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    render_forest_svg(report, args.output_svg, title=args.title)
    md = render_markdown(report, title=args.title, forest_path=args.output_svg)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(md, encoding="utf-8")

    overall_summary = {
        method: report["methods"][method]["overall"]
        for method in report["methods"]
    }
    print(json.dumps(
        {
            "output_json": str(args.output_json),
            "output_md": str(args.output_md),
            "output_svg": str(args.output_svg),
            "overall": overall_summary,
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
