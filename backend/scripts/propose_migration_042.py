#!/usr/bin/env python3
"""Propose migration 042 from LLM vocab mining + reasoning mining outputs.

Combines two signals:
  - Vocab mining: LLM-proposed positive/negative lexicon terms per topic
    in multiple languages (`llm_topic_vocab_mine.py` output).
  - Reasoning mining: aggregated top_agree/top_disagree terms per topic
    derived from existing LLM baseline predictions
    (`llm_reasoning_mine.py` output).

For each atlas topic, the tool emits:
  - terms_to_add: high-confidence positive terms not already in the
    production `atlas_topics.lexicon_terms`. Multilingual, deduped.
  - terms_to_monitor: negative ("false friend") terms flagged for
    operator review; not applied automatically.
  - terms_to_flag_for_removal: existing terms that appear in the
    LLM's negative list OR appear strongly in the disagree side of
    reasoning mining. These should be reviewed manually before
    removal; the tool does NOT emit a DROP statement for them.

Outputs:
  - Markdown report listing per-topic recommendations.
  - SQL migration draft (text-only) that adds high-confidence terms.
    The SQL is NOT applied. Pedro reviews and runs via Supabase MCP.

Schema version: atlas-migration-042-proposal-v1.

This tool is read-only and consumes no API credit.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "atlas-migration-042-proposal-v1"

# Minimum confidence to include a vocab-mined positive term in the SQL draft.
DEFAULT_MIN_VOCAB_CONFIDENCE = 0.75

# Drop short/noisy candidate terms.
MIN_TERM_LENGTH = 3
MAX_TERM_LENGTH = 60


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _load_topics_snapshot(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for entry in payload.get("topics", []):
        slug = entry["slug"]
        out[slug] = {
            "label": entry["label"],
            "existing_lexicon": [t.lower() for t in entry.get("lexicon_terms", [])],
        }
    return out


def _normalize_term(term: str) -> str | None:
    term = (term or "").strip().lower()
    if not term:
        return None
    # Strip outer quotes/punctuation but allow internal hyphens / accents.
    term = term.strip("\"'`,.;:!?()[]{}<>")
    term = re.sub(r"\s+", " ", term)
    if len(term) < MIN_TERM_LENGTH or len(term) > MAX_TERM_LENGTH:
        return None
    # Drop if it is mostly digits / punctuation.
    letters = sum(1 for ch in term if ch.isalpha())
    if letters < max(2, len(term) // 2):
        return None
    return term


def _cross_topic_distractors(vocab_rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    """For each topic, collect terms that appear as POSITIVE in OTHER topics.

    These are cross-topic distractors: if topic A's positive list includes
    "energy crisis" and topic B's positive list also claims it, the term
    is ambiguous and should not be applied to either topic without review.
    """
    by_topic_positive: dict[str, set[str]] = {}
    for row in vocab_rows:
        topic = row["topic_slug"]
        positives = set()
        for entry in row.get("positive", []):
            norm = _normalize_term(entry.get("term"))
            if norm:
                positives.add(norm)
        by_topic_positive[topic] = positives

    distractors: dict[str, set[str]] = {}
    for topic, terms in by_topic_positive.items():
        other = set()
        for other_topic, other_terms in by_topic_positive.items():
            if other_topic == topic:
                continue
            other |= other_terms
        distractors[topic] = terms & other
    return distractors


def _build_proposal(
    *,
    vocab_rows: list[dict[str, Any]],
    reasoning_report: dict[str, Any],
    topics_meta: dict[str, dict[str, Any]],
    min_vocab_confidence: float,
) -> dict[str, Any]:
    cross_distractors = _cross_topic_distractors(vocab_rows)
    reasoning_by_topic = reasoning_report.get("by_topic", {})

    per_topic: dict[str, dict[str, Any]] = {}

    for vocab_row in vocab_rows:
        slug = vocab_row["topic_slug"]
        meta = topics_meta.get(slug, {"existing_lexicon": [], "label": slug})
        existing = set(meta.get("existing_lexicon", []))

        terms_to_add: list[dict[str, Any]] = []
        seen_add: set[str] = set()
        rejected_low_conf: list[dict[str, Any]] = []
        rejected_distractor: list[dict[str, Any]] = []

        for entry in vocab_row.get("positive", []):
            norm = _normalize_term(entry.get("term"))
            if not norm:
                continue
            if norm in existing or norm in seen_add:
                continue
            confidence = entry.get("confidence")
            if confidence is None or confidence < min_vocab_confidence:
                rejected_low_conf.append({**entry, "term": norm})
                continue
            if norm in cross_distractors.get(slug, set()):
                rejected_distractor.append({**entry, "term": norm})
                continue
            seen_add.add(norm)
            terms_to_add.append({
                "term": norm,
                "lang": entry.get("lang"),
                "confidence": confidence,
                "why": entry.get("why"),
            })

        terms_to_monitor: list[dict[str, Any]] = []
        for entry in vocab_row.get("negative", []):
            norm = _normalize_term(entry.get("term"))
            if not norm:
                continue
            terms_to_monitor.append({
                "term": norm,
                "lang": entry.get("lang"),
                "confidence": entry.get("confidence"),
                "why_not": entry.get("why"),
            })

        # Reasoning-mining signals: terms strongly cited when LLM disagreed
        # with Atlas. If those terms are currently in lexicon_terms, flag
        # for manual review.
        terms_to_flag_for_removal: list[dict[str, Any]] = []
        reasoning_info = reasoning_by_topic.get(slug, {})
        for term, count in reasoning_info.get("top_disagree_terms", [])[:15]:
            norm = _normalize_term(term)
            if norm and norm in existing and count >= 2:
                terms_to_flag_for_removal.append({
                    "term": norm,
                    "disagree_count": count,
                    "reason": "frequent in LLM rejection reasoning",
                })

        per_topic[slug] = {
            "label": meta.get("label", slug),
            "existing_lexicon_count": len(existing),
            "vocab_positive_proposed": len(vocab_row.get("positive", [])),
            "vocab_negative_proposed": len(vocab_row.get("negative", [])),
            "terms_to_add": terms_to_add,
            "terms_to_monitor": terms_to_monitor,
            "terms_to_flag_for_removal": terms_to_flag_for_removal,
            "rejected_low_confidence": rejected_low_conf,
            "rejected_cross_topic_distractor": rejected_distractor,
            "reasoning_top_agree_terms": reasoning_info.get("top_agree_terms", [])[:10],
            "reasoning_top_disagree_terms": reasoning_info.get("top_disagree_terms", [])[:10],
            "llm_atlas_agreement": reasoning_info.get("llm_atlas_agreement"),
        }

    summary = {
        "schema_version": SCHEMA_VERSION,
        "min_vocab_confidence": min_vocab_confidence,
        "topics_total": len(per_topic),
        "topics_with_proposed_adds": sum(
            1 for m in per_topic.values() if m["terms_to_add"]
        ),
        "total_terms_to_add": sum(len(m["terms_to_add"]) for m in per_topic.values()),
        "total_terms_to_monitor": sum(len(m["terms_to_monitor"]) for m in per_topic.values()),
        "total_terms_to_flag_for_removal": sum(
            len(m["terms_to_flag_for_removal"]) for m in per_topic.values()
        ),
        "by_topic": per_topic,
    }
    return summary


def render_sql_draft(proposal: dict[str, Any]) -> str:
    lines: list[str] = [
        "-- Migration 042 (DRAFT) — LLM-distilled multilingual lexicon expansion.",
        "-- Source: docs/research/atlas-paper/phase-1-validation/labels/llm-vocab-mining/",
        "-- Generated by: backend/scripts/propose_migration_042.py",
        "-- Schema version: " + proposal["schema_version"],
        f"-- Minimum vocab confidence: {proposal['min_vocab_confidence']}",
        "--",
        "-- This file is INTENTIONALLY not applied automatically. Pedro reviews",
        "-- each topic block, removes any unsafe term, then applies via Supabase",
        "-- MCP `apply_migration`. After applying, delete v2 assignments for the",
        "-- changed topics and re-run backfill_lexicon_topics.py before",
        "-- re-benchmarking.",
        "",
        "BEGIN;",
        "",
    ]
    for slug, meta in sorted(proposal["by_topic"].items()):
        adds = meta["terms_to_add"]
        if not adds:
            continue
        lines.append(f"-- {slug} ({meta['label']})")
        lines.append(f"--   existing lexicon size: {meta['existing_lexicon_count']}")
        lines.append(f"--   proposed adds: {len(adds)}")
        flags = meta.get("terms_to_flag_for_removal", [])
        if flags:
            lines.append("--   flagged for manual removal review:")
            for f in flags:
                lines.append(f"--     - {f['term']} ({f['disagree_count']} disagree mentions)")
        terms_sql_literal = ", ".join(_sql_literal(a["term"]) for a in adds)
        lines.append(
            f"UPDATE atlas_topics\n"
            f"SET lexicon_terms = ARRAY(\n"
            f"    SELECT DISTINCT unnest(lexicon_terms || ARRAY[{terms_sql_literal}])\n"
            f")\n"
            f"WHERE slug = {_sql_literal(slug)};"
        )
        lines.append("")
    lines.append("COMMIT;")
    lines.append("")
    return "\n".join(lines)


def _sql_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def render_markdown(proposal: dict[str, Any]) -> str:
    lines = [
        "# Migration 042 proposal — LLM-distilled multilingual lexicon expansion",
        "",
        f"Schema: `{proposal['schema_version']}`",
        f"Min vocab confidence threshold: {proposal['min_vocab_confidence']}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Topics covered | {proposal['topics_total']} |",
        f"| Topics with proposed additions | {proposal['topics_with_proposed_adds']} |",
        f"| Total new terms proposed | {proposal['total_terms_to_add']} |",
        f"| Total negative terms to monitor | {proposal['total_terms_to_monitor']} |",
        f"| Existing terms flagged for removal review | {proposal['total_terms_to_flag_for_removal']} |",
        "",
        "## How to use this proposal",
        "",
        "1. Read the SQL draft (`migration-042-draft.sql`).",
        "2. For each topic block, drop any term that does not feel safe.",
        "3. Apply via Supabase MCP `apply_migration`.",
        "4. Delete v2 assignments for the touched topics.",
        "5. Re-run `backend/scripts/backfill_lexicon_topics.py` over a recent 24h window.",
        "6. Re-benchmark Atlas v2 with the bootstrap CI tool against existing gold.",
        "7. Compare lift vs prior Wilson CI baseline `[46.50%, 70.46%]`.",
        "",
        "## Per-topic detail",
    ]

    for slug, meta in sorted(
        proposal["by_topic"].items(),
        key=lambda kv: -len(kv[1]["terms_to_add"]),
    ):
        lines.append("")
        lines.append(f"### `{slug}`")
        lines.append("")
        agreement = meta.get("llm_atlas_agreement")
        if agreement is not None:
            lines.append(
                f"- LLM-Atlas agreement on reviewed sample: {agreement * 100:.1f}%"
            )
        lines.append(f"- existing lexicon size: {meta['existing_lexicon_count']}")
        lines.append(
            f"- vocab mining proposed: {meta['vocab_positive_proposed']} positive, "
            f"{meta['vocab_negative_proposed']} negative"
        )
        lines.append(
            f"- terms to add (high-confidence, not yet in lexicon): {len(meta['terms_to_add'])}"
        )
        for entry in meta["terms_to_add"]:
            lines.append(
                f"  - `{entry['term']}` [{entry['lang']}] conf={entry['confidence']:.2f}"
                f" — {entry['why']}"
            )
        if meta["terms_to_monitor"]:
            lines.append(f"- negative monitors ({len(meta['terms_to_monitor'])}):")
            for entry in meta["terms_to_monitor"][:8]:
                lines.append(
                    f"  - `{entry['term']}` [{entry['lang']}] — {entry['why_not']}"
                )
        if meta["terms_to_flag_for_removal"]:
            lines.append(
                f"- flagged for manual removal review ({len(meta['terms_to_flag_for_removal'])}):"
            )
            for entry in meta["terms_to_flag_for_removal"]:
                lines.append(
                    f"  - `{entry['term']}` ({entry['disagree_count']} LLM disagree mentions)"
                )
        if meta["rejected_cross_topic_distractor"]:
            lines.append(
                f"- rejected cross-topic distractors ({len(meta['rejected_cross_topic_distractor'])}):"
            )
            for entry in meta["rejected_cross_topic_distractor"][:6]:
                lines.append(f"  - `{entry['term']}` [{entry['lang']}]")
        if meta["rejected_low_confidence"]:
            lines.append(
                f"- rejected below confidence threshold "
                f"({len(meta['rejected_low_confidence'])}):"
            )
            for entry in meta["rejected_low_confidence"][:6]:
                lines.append(f"  - `{entry['term']}` [{entry['lang']}] "
                             f"conf={entry.get('confidence')}")

    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Propose migration 042 from LLM mining outputs.")
    parser.add_argument("--vocab", required=True, type=Path,
                        help="Vocab mining JSONL from llm_topic_vocab_mine.py")
    parser.add_argument("--reasoning", required=True, type=Path,
                        help="Reasoning mining JSON from llm_reasoning_mine.py")
    parser.add_argument("--topics-snapshot", required=True, type=Path,
                        help="Atlas topics snapshot JSON.")
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--output-sql", required=True, type=Path)
    parser.add_argument("--min-vocab-confidence", type=float, default=DEFAULT_MIN_VOCAB_CONFIDENCE)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    vocab_rows = _read_jsonl(args.vocab)
    reasoning_report = json.loads(args.reasoning.read_text(encoding="utf-8"))
    topics_meta = _load_topics_snapshot(args.topics_snapshot)

    proposal = _build_proposal(
        vocab_rows=vocab_rows,
        reasoning_report=reasoning_report,
        topics_meta=topics_meta,
        min_vocab_confidence=args.min_vocab_confidence,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(proposal), encoding="utf-8")
    args.output_sql.parent.mkdir(parents=True, exist_ok=True)
    args.output_sql.write_text(render_sql_draft(proposal), encoding="utf-8")

    print(json.dumps({
        "output_json": str(args.output_json),
        "output_md": str(args.output_md),
        "output_sql": str(args.output_sql),
        "topics_total": proposal["topics_total"],
        "topics_with_proposed_adds": proposal["topics_with_proposed_adds"],
        "total_terms_to_add": proposal["total_terms_to_add"],
        "total_terms_to_monitor": proposal["total_terms_to_monitor"],
        "total_terms_to_flag_for_removal": proposal["total_terms_to_flag_for_removal"],
    }, indent=2))


if __name__ == "__main__":
    main()
