#!/usr/bin/env python3
"""Mine the reasoning strings from LLM baseline classifier predictions.

For each atlas topic, separate the rows where the LLM agreed with Atlas
v2 from the rows where it disagreed. Surface frequent terms in each
bucket as candidate signals for distillation back into the Atlas
classifier (lex term additions, disqualifier patterns, scope hints).

This is a zero-API-cost first pass over existing predictions: it does
not call any model. Output is a Markdown brief + a JSON dump suitable
for review before any classifier migration is proposed.

Schema version: atlas-llm-reasoning-mine-v1
"""

from __future__ import annotations

import argparse
import collections
import html
import json
import re
import string
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "atlas-llm-reasoning-mine-v1"

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "to", "for", "from",
    "with", "by", "is", "are", "was", "were", "be", "been", "being",
    "as", "at", "this", "that", "these", "those", "it", "its", "their",
    "his", "her", "they", "them", "we", "our", "i", "me", "my", "you",
    "your", "but", "not", "no", "do", "does", "did", "have", "has",
    "had", "will", "would", "should", "could", "can", "may", "might",
    "than", "then", "so", "if", "while", "when", "where", "what", "which",
    "who", "whom", "why", "how", "any", "all", "some", "such", "more",
    "most", "much", "very", "also", "just", "only", "still", "now",
    "headline", "story", "topic", "atlas", "label", "slug", "matches",
    "directly", "indicates", "relates", "relating", "involves",
    "concerns", "describes", "discusses", "between", "into", "about",
    "without", "within", "across", "via", "per", "vs",
}

TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_\-]+")


def _tokens(text: str) -> list[str]:
    if not text:
        return []
    cleaned = text.lower()
    out = []
    for tok in TOKEN_RE.findall(cleaned):
        tok = tok.strip(string.punctuation + "-")
        if not tok or tok in STOPWORDS or len(tok) < 3:
            continue
        out.append(tok)
    return out


def _bigrams(tokens: Iterable[str]) -> list[str]:
    tokens = list(tokens)
    return [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]


def _read_predictions(path: Path) -> list[dict[str, Any]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def mine(predictions: list[dict[str, Any]], *, mode_filter: str | None = None) -> dict[str, Any]:
    per_topic_agree_tokens: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    per_topic_disagree_tokens: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    per_topic_agree_bigrams: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    per_topic_disagree_bigrams: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    per_topic_disagree_targets: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    per_topic_agree_count: dict[str, int] = collections.defaultdict(int)
    per_topic_disagree_count: dict[str, int] = collections.defaultdict(int)

    total_rows = 0
    for row in predictions:
        if mode_filter and row.get("llm_mode") != mode_filter:
            continue
        if row.get("api_error"):
            continue
        atlas = row.get("atlas_assigned_slug")
        llm = row.get("llm_predicted_slug")
        reasoning = row.get("llm_reasoning") or ""
        if not atlas:
            continue
        total_rows += 1
        tokens = _tokens(reasoning)
        bigrams = _bigrams(tokens)
        if atlas == llm:
            per_topic_agree_count[atlas] += 1
            per_topic_agree_tokens[atlas].update(tokens)
            per_topic_agree_bigrams[atlas].update(bigrams)
        else:
            per_topic_disagree_count[atlas] += 1
            per_topic_disagree_tokens[atlas].update(tokens)
            per_topic_disagree_bigrams[atlas].update(bigrams)
            per_topic_disagree_targets[atlas][llm or "none"] += 1

    topics = sorted(set(per_topic_agree_count.keys()) | set(per_topic_disagree_count.keys()))
    by_topic: dict[str, dict[str, Any]] = {}
    for topic in topics:
        agree_n = per_topic_agree_count[topic]
        dis_n = per_topic_disagree_count[topic]
        total = agree_n + dis_n
        by_topic[topic] = {
            "rows": total,
            "agree_rows": agree_n,
            "disagree_rows": dis_n,
            "llm_atlas_agreement": (agree_n / total) if total else 0.0,
            "top_agree_terms": per_topic_agree_tokens[topic].most_common(15),
            "top_disagree_terms": per_topic_disagree_tokens[topic].most_common(15),
            "top_agree_bigrams": per_topic_agree_bigrams[topic].most_common(8),
            "top_disagree_bigrams": per_topic_disagree_bigrams[topic].most_common(8),
            "disagree_targets": per_topic_disagree_targets[topic].most_common(),
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "mode_filter": mode_filter,
        "total_rows_considered": total_rows,
        "by_topic": by_topic,
    }


def render_markdown(report: dict[str, Any], *, title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"Schema: `{report['schema_version']}`",
        f"Mode filter: `{report['mode_filter'] or '(any)'}` · Rows considered: {report['total_rows_considered']}",
        "",
        "## Reading this report",
        "",
        "- `top_agree_terms` shows the frequent unigram signals the LLM cited when it confirmed the Atlas assignment. These hint at the lexical vocabulary the Atlas classifier could safely incorporate.",
        "- `top_disagree_terms` shows the frequent signals the LLM cited when it diverged from Atlas. These hint at distractor vocabulary the Atlas classifier may be over-weighting, or at signals that flip the headline scope.",
        "- `disagree_targets` lists the slug the LLM picked when it disagreed with Atlas. `none` indicates the LLM judged no topic fit.",
        "- This is a zero-API-cost first pass over existing predictions. Treat as input to a manual migration review, NOT as an automated rule.",
        "",
        "## Per-topic mining",
    ]
    for topic, m in sorted(report["by_topic"].items(), key=lambda kv: -kv[1]["rows"]):
        lines.append("")
        lines.append(f"### `{topic}`")
        lines.append("")
        lines.append(
            f"- rows: {m['rows']} · agree: {m['agree_rows']} · disagree: {m['disagree_rows']} · "
            f"agreement: {m['llm_atlas_agreement'] * 100:.1f}%"
        )
        if m["top_agree_terms"]:
            lines.append(
                "- top agree terms: " + ", ".join(f"`{t}` ({c})" for t, c in m["top_agree_terms"])
            )
        if m["top_disagree_terms"]:
            lines.append(
                "- top disagree terms: " + ", ".join(f"`{t}` ({c})" for t, c in m["top_disagree_terms"])
            )
        if m["top_agree_bigrams"]:
            lines.append(
                "- top agree bigrams: " + ", ".join(f"`{html.escape(t)}` ({c})" for t, c in m["top_agree_bigrams"])
            )
        if m["top_disagree_bigrams"]:
            lines.append(
                "- top disagree bigrams: " + ", ".join(f"`{html.escape(t)}` ({c})" for t, c in m["top_disagree_bigrams"])
            )
        if m["disagree_targets"]:
            lines.append(
                "- disagree targets: " + ", ".join(f"`{s}` ({c})" for s, c in m["disagree_targets"])
            )
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mine LLM reasoning strings per atlas topic.")
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--title", default="LLM reasoning mining per atlas topic")
    parser.add_argument("--mode", default="zero_shot", help="Filter by llm_mode; pass 'all' to keep both.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    mode_filter = None if args.mode == "all" else args.mode
    predictions = _read_predictions(args.predictions)
    report = mine(predictions, mode_filter=mode_filter)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(report, title=args.title), encoding="utf-8")
    print(json.dumps({
        "output_json": str(args.output_json),
        "output_md": str(args.output_md),
        "topics": len(report["by_topic"]),
        "rows_considered": report["total_rows_considered"],
    }, indent=2))


if __name__ == "__main__":
    main()
