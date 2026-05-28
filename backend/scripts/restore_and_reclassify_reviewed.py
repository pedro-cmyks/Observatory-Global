#!/usr/bin/env python3
"""Restore reviewed signals from local archive and re-classify in-Python.

Pipeline:
  1. Read reviewed gold JSONL files (signal_id, headline, assigned_topic_slug, gold_decision).
  2. Scan local archive (*.jsonl.gz) for those signal_ids; extract full rows.
  3. Read atlas_topics snapshot (post-migration lexicon_terms, gdelt_theme_hints).
  4. Re-classify each restored signal using the same scoring formula as
     `backfill_lexicon_topics.py` (theme-hint-lex-v2):
         lex_count = headline-substring matches with topic.lexicon_terms
         theme_hits = signals.themes intersect topic.gdelt_theme_hints
         confidence = 0.55
             + 0.10 * min(lex_count, 3)
             + 0.05 * min(theme_hits, 4)
             + 0.05 if (lex_count > 0 AND theme_hits >= 2) else 0
         keep top-N per signal by confidence with min_confidence threshold
  5. Compare new top-2 predictions to the (gold_decision, assigned_topic_slug)
     pairs. For each reviewed row, compute:
         post042_correct if any of the new top-2 predictions equals the
             slug Pedro confirmed correct (when gold_decision=='correct')
             OR if the original assigned slug was judged incorrect AND the
             new classifier rejects it (drops out of top-2).
     This mirrors the same outcome logic used in `llm_baseline_compare.py`.

Schema version: atlas-post042-reclassify-v1.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "atlas-post042-reclassify-v1"
DEFAULT_MIN_CONFIDENCE = 0.65
DEFAULT_MIN_HEADLINE_LEN = 20
DEFAULT_TOP_N = 2


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _load_gold(paths: list[Path]) -> dict[int, dict[str, Any]]:
    gold: dict[int, dict[str, Any]] = {}
    for path in paths:
        for row in _read_jsonl(path):
            sid = row.get("signal_id")
            if sid is None:
                continue
            gold[int(sid)] = {
                "assigned_slug": row.get("assigned_topic_slug"),
                "gold_decision": row.get("gold_decision") or row.get("reviewer_decision"),
                "headline": row.get("headline"),
                "country_code": row.get("country_code"),
                "source_lang": row.get("source_lang"),
                "source_family": row.get("source_family"),
                "source_name": row.get("source_name"),
            }
    return gold


def _scan_archives(archive_root: Path, target_ids: set[int]) -> dict[int, dict[str, Any]]:
    restored: dict[int, dict[str, Any]] = {}
    remaining = set(target_ids)
    files = sorted(archive_root.rglob("*.jsonl.gz"), reverse=True)
    for path in files:
        if not remaining:
            break
        # File-level substring gate: scan raw bytes once for any remaining id.
        try:
            with gzip.open(path, "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        hit_any = False
        for sid in list(remaining):
            needle = f'"id":{sid}'.encode("utf-8")
            if needle in raw:
                hit_any = True
                break
            needle2 = f'"id": {sid}'.encode("utf-8")
            if needle2 in raw:
                hit_any = True
                break
        if not hit_any:
            continue
        # Found at least one id in file; parse line-by-line.
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = row.get("id")
            if sid is None:
                continue
            if sid in remaining:
                restored[sid] = row
                remaining.discard(sid)
                if not remaining:
                    break
    return restored


def _load_topics_snapshot(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for entry in payload.get("topics", []):
        out.append({
            "slug": entry["slug"],
            "label": entry.get("label", entry["slug"]),
            "lexicon_terms": [t.lower() for t in entry.get("lexicon_terms", [])],
            "gdelt_theme_hints": list(entry.get("gdelt_theme_hints", [])),
        })
    return out


def classify_signal(
    signal: dict[str, Any],
    topics: list[dict[str, Any]],
    *,
    min_confidence: float,
    min_headline_len: int,
    top_n: int,
) -> list[dict[str, Any]]:
    headline = (signal.get("headline") or "").strip()
    if len(headline) < min_headline_len:
        return []
    headline_lower = headline.lower()
    themes = signal.get("themes") or []
    themes_set = set(themes) if isinstance(themes, list) else set()

    candidates: list[dict[str, Any]] = []
    for topic in topics:
        lex = topic["lexicon_terms"]
        theme_hints = topic["gdelt_theme_hints"]
        matched_lex = [t for t in lex if t and t in headline_lower]
        theme_hits = len(themes_set & set(theme_hints)) if theme_hints else 0
        if not matched_lex and theme_hits == 0:
            continue
        lex_count = len(matched_lex)
        confidence = min(
            0.95,
            0.55
            + 0.10 * min(lex_count, 3)
            + 0.05 * min(theme_hits, 4)
            + (0.05 if lex_count > 0 and theme_hits >= 2 else 0.0),
        )
        if confidence < min_confidence:
            continue
        candidates.append({
            "slug": topic["slug"],
            "confidence": round(confidence, 4),
            "lex_count": lex_count,
            "theme_hits": theme_hits,
            "matched_terms": matched_lex[:8],
        })

    candidates.sort(
        key=lambda c: (-c["confidence"], -c["theme_hits"], -c["lex_count"], c["slug"])
    )
    return candidates[:top_n]


def evaluate(
    gold: dict[int, dict[str, Any]],
    restored: dict[int, dict[str, Any]],
    topics: list[dict[str, Any]],
    *,
    min_confidence: float,
    min_headline_len: int,
    top_n: int,
) -> dict[str, Any]:
    per_row: list[dict[str, Any]] = []
    by_topic: dict[str, dict[str, int]] = {}
    counted = 0
    correct = 0
    incorrect = 0
    unclear = 0
    missing_signal = 0

    for sid, info in gold.items():
        decision = info["gold_decision"]
        assigned = info["assigned_slug"]
        if not assigned or decision is None:
            continue
        signal = restored.get(sid)
        if signal is None:
            missing_signal += 1
            per_row.append({
                "signal_id": sid,
                "missing_signal": True,
                "gold_decision": decision,
                "assigned_slug": assigned,
            })
            continue
        predictions = classify_signal(
            signal,
            topics,
            min_confidence=min_confidence,
            min_headline_len=min_headline_len,
            top_n=top_n,
        )
        predicted_slugs = [p["slug"] for p in predictions]

        if decision == "unclear":
            unclear += 1
            per_row.append({
                "signal_id": sid,
                "skipped_unclear": True,
                "predictions": predictions,
            })
            continue

        counted += 1
        topic_bucket = by_topic.setdefault(
            assigned,
            {"labeled": 0, "post042_correct": 0, "post042_incorrect": 0},
        )
        topic_bucket["labeled"] += 1
        if decision == "correct":
            ok = assigned in predicted_slugs
        else:
            ok = assigned not in predicted_slugs
        if ok:
            correct += 1
            topic_bucket["post042_correct"] += 1
        else:
            incorrect += 1
            topic_bucket["post042_incorrect"] += 1
        per_row.append({
            "signal_id": sid,
            "gold_decision": decision,
            "assigned_slug": assigned,
            "post042_predictions": predictions,
            "post042_correct": ok,
        })

    precision = correct / counted if counted else 0.0
    by_topic_summary: dict[str, dict[str, Any]] = {}
    for slug, m in sorted(by_topic.items()):
        n = m["labeled"]
        c = m["post042_correct"]
        by_topic_summary[slug] = {
            "labeled": n,
            "post042_correct": c,
            "post042_incorrect": m["post042_incorrect"],
            "post042_precision": round(c / n, 4) if n else None,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "min_confidence": min_confidence,
        "min_headline_len": min_headline_len,
        "top_n": top_n,
        "topics_used": len(topics),
        "gold_total": len(gold),
        "labeled": counted,
        "skipped_unclear": unclear,
        "missing_signal": missing_signal,
        "post042_correct": correct,
        "post042_incorrect": incorrect,
        "post042_precision": round(precision, 4),
        "by_topic": by_topic_summary,
        "per_row": per_row,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore reviewed signals and re-classify with post-042 lex.")
    parser.add_argument("--gold", required=True, nargs="+", type=Path)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--topics-snapshot", required=True, type=Path,
                        help="Topics snapshot (post-042 lexicon).")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--min-confidence", type=float, default=DEFAULT_MIN_CONFIDENCE)
    parser.add_argument("--min-headline-len", type=int, default=DEFAULT_MIN_HEADLINE_LEN)
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    gold = _load_gold(args.gold)
    target_ids = set(gold.keys())
    print(f"reviewed gold rows: {len(gold)}; target signal_ids: {len(target_ids)}")

    restored = _scan_archives(args.archive_root, target_ids)
    print(f"restored from archive: {len(restored)} / {len(target_ids)}")

    topics = _load_topics_snapshot(args.topics_snapshot)
    print(f"topics loaded: {len(topics)}")

    report = evaluate(
        gold,
        restored,
        topics,
        min_confidence=args.min_confidence,
        min_headline_len=args.min_headline_len,
        top_n=args.top_n,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "output": str(args.output),
        "labeled": report["labeled"],
        "missing": report["missing_signal"],
        "post042_precision": report["post042_precision"],
        "post042_correct": report["post042_correct"],
        "post042_incorrect": report["post042_incorrect"],
    }, indent=2))


if __name__ == "__main__":
    main()
