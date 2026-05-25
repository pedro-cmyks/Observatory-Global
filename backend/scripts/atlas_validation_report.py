#!/usr/bin/env python3
"""Render Atlas validation score reports as Markdown plus SVG charts."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


BAR_HEIGHT = 24
BAR_GAP = 10
LABEL_WIDTH = 230
VALUE_WIDTH = 80
CHART_WIDTH = 760


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def _sorted_items(values: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(values.items(), key=lambda item: (-item[1], item[0]))


def render_bar_svg(
    *,
    title: str,
    values: dict[str, int],
    output_path: Path,
    x_label: str = "rows",
) -> None:
    items = _sorted_items(values)
    max_value = max((value for _, value in items), default=1)
    plot_width = CHART_WIDTH - LABEL_WIDTH - VALUE_WIDTH - 40
    height = 64 + len(items) * (BAR_HEIGHT + BAR_GAP)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CHART_WIDTH}" height="{height}" viewBox="0 0 {CHART_WIDTH} {height}">',
        '<rect width="100%" height="100%" fill="#071016"/>',
        f'<text x="24" y="32" fill="#d7fbe8" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="700">{html.escape(title)}</text>',
        f'<text x="{CHART_WIDTH - 120}" y="32" fill="#7f93a4" font-family="Inter, Arial, sans-serif" font-size="12">{html.escape(x_label)}</text>',
    ]

    for index, (label, value) in enumerate(items):
        y = 56 + index * (BAR_HEIGHT + BAR_GAP)
        width = int((value / max_value) * plot_width) if max_value else 0
        lines.extend(
            [
                f'<text x="24" y="{y + 17}" fill="#b7c7d4" font-family="Inter, Arial, sans-serif" font-size="13">{html.escape(label)}</text>',
                f'<rect x="{LABEL_WIDTH}" y="{y}" width="{plot_width}" height="{BAR_HEIGHT}" rx="3" fill="#10202b"/>',
                f'<rect x="{LABEL_WIDTH}" y="{y}" width="{width}" height="{BAR_HEIGHT}" rx="3" fill="#5ee6a8"/>',
                f'<text x="{LABEL_WIDTH + plot_width + 16}" y="{y + 17}" fill="#f4f7fb" font-family="Inter, Arial, sans-serif" font-size="13">{value}</text>',
            ]
        )

    lines.append("</svg>\n")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))


def _topic_precision_values(score: dict[str, Any]) -> dict[str, int]:
    values: dict[str, int] = {}
    for topic, payload in score.get("by_topic", {}).items():
        precision = payload.get("precision")
        if precision is not None:
            values[topic] = round(float(precision) * 100)
    return values


def render_markdown_report(
    *,
    score: dict[str, Any],
    title: str,
    label_quality: str,
    chart_paths: dict[str, Path],
) -> str:
    overall = score.get("overall", {})
    gate = score.get("gate", {})

    lines = [
        f"# {title}",
        "",
        f"Label quality: `{label_quality}`",
        f"Schema: `{score.get('schema_version', 'unknown')}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Labeled denominator | {overall.get('labeled', 0)} |",
        f"| Correct | {overall.get('correct', 0)} |",
        f"| Incorrect | {overall.get('incorrect', 0)} |",
        f"| Unclear | {overall.get('unclear', 0)} |",
        f"| Precision | {_format_pct(overall.get('precision'))} |",
        f"| Gate | `{overall.get('gate', 'n/a')}` |",
        f"| Minimum gate | {_format_pct(gate.get('minimum'))} |",
        f"| Target gate | {_format_pct(gate.get('target'))} |",
        "",
        "## Visuals",
        "",
    ]

    for label, path in chart_paths.items():
        lines.extend([f"### {label}", "", f"![{label}]({path.name})", ""])

    lines.extend(
        [
            "## Per-Topic Precision",
            "",
            "| Topic | Labeled | Correct | Incorrect | Unclear | Precision | Gate |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for topic, payload in sorted(score.get("by_topic", {}).items()):
        lines.append(
            "| "
            + " | ".join(
                [
                    topic,
                    str(payload.get("labeled", 0)),
                    str(payload.get("correct", 0)),
                    str(payload.get("incorrect", 0)),
                    str(payload.get("unclear", 0)),
                    _format_pct(payload.get("precision")),
                    f"`{payload.get('gate', 'n/a')}`",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Guardrail",
            "",
            "This report may be useful for workflow debugging and internal model design. "
            "Do not treat non-gold labels as paper-grade evidence. Assistant-pilot labels require human review or adjudication before they can support final claims.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_report(
    *,
    score_path: Path,
    output_dir: Path,
    title: str,
    label_quality: str,
    report_name: str,
) -> Path:
    score = _read_json(score_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    chart_specs = {
        "Semantic Scope": ("scope.svg", score.get("by_scope", {}), "rows"),
        "Evidence Role": ("evidence-role.svg", score.get("by_evidence_role", {}), "rows"),
        "Supported Questions": (
            "supported-questions.svg",
            score.get("by_supported_question", {}),
            "rows",
        ),
        "Per-Topic Precision": ("topic-precision.svg", _topic_precision_values(score), "percent"),
    }

    chart_paths: dict[str, Path] = {}
    for chart_title, (filename, values, x_label) in chart_specs.items():
        path = output_dir / f"{report_name}-{filename}"
        render_bar_svg(title=chart_title, values=values, output_path=path, x_label=x_label)
        chart_paths[chart_title] = path

    report_path = output_dir / f"{report_name}.md"
    report_path.write_text(
        render_markdown_report(
            score=score,
            title=title,
            label_quality=label_quality,
            chart_paths=chart_paths,
        )
    )
    return report_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Atlas validation score report")
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--label-quality", required=True)
    parser.add_argument("--report-name", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report_path = generate_report(
        score_path=args.score,
        output_dir=args.output_dir,
        title=args.title,
        label_quality=args.label_quality,
        report_name=args.report_name,
    )
    print(json.dumps({"report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
