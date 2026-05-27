#!/usr/bin/env python3
"""LLM zero-shot / few-shot baseline classifier for the Atlas topic benchmark.

For each gold/reviewed row, ask an LLM to pick the single best matching
atlas topic slug (or 'none'). Compare the prediction to the gold label
and to the production atlas v2 assignment.

Schema versions:
  - input:  atlas-topic-benchmark-v2 (gold/reviewed JSONL)
  - output: atlas-llm-baseline-v1 (predictions JSONL + score JSON)

Cost: ~$1 per 100 rows with Sonnet 4.6 zero-shot + few-shot.

Required env:
  ANTHROPIC_API_KEY

The atlas topic snapshot is read from a static JSON file to keep the
experiment reproducible. Regenerate the snapshot when the taxonomy changes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

try:
    import anthropic
except ImportError as exc:  # pragma: no cover
    print(f"missing dependency: {exc}", file=sys.stderr)
    sys.exit(2)


SCHEMA_VERSION = "atlas-llm-baseline-v1"
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 400
DEFAULT_TEMPERATURE = 0.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 4.0


SYSTEM_PROMPT = (
    "You are a topic classifier for global news headlines used in a "
    "narrative intelligence research benchmark. You must select the single "
    "best matching topic slug from a fixed taxonomy, or 'none' if no topic "
    "fits as primary evidence. Reply in strict JSON with the keys "
    "`predicted_slug`, `confidence` (0..1 float), and `reasoning` (one "
    "short sentence, no more than 30 words). Do not output any text outside "
    "the JSON object."
)


FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "headline": "Health ministry confirms 23 new Ebola cases in eastern province",
        "themes": ["MEDICAL", "TAX_DISEASE_EBOLA", "WB_2663_EBOLA"],
        "source_lang": "en",
        "country_code": "CD",
        "answer": {
            "predicted_slug": "disease-outbreak",
            "confidence": 0.95,
            "reasoning": "Explicit Ebola outbreak with case count is a disease outbreak primary event.",
        },
    },
    {
        "headline": "Supreme Court strikes down protest law, lawmakers vow constitutional appeal",
        "themes": ["GOV", "DEMOCRACY", "LEGISLATION"],
        "source_lang": "en",
        "country_code": "US",
        "answer": {
            "predicted_slug": "constitutional-institutional-crisis",
            "confidence": 0.78,
            "reasoning": "Judicial-legislative confrontation invoking constitutional process.",
        },
    },
    {
        "headline": "Bayern Munich striker scores hat-trick to seal title race",
        "themes": ["SOC_SPORT", "ENTERTAINMENT"],
        "source_lang": "en",
        "country_code": "DE",
        "answer": {
            "predicted_slug": "none",
            "confidence": 0.99,
            "reasoning": "Sports story, no narrative-intelligence topic applies.",
        },
    },
    {
        "headline": "Peso cae a mínimo histórico frente al dólar tras crisis bancaria",
        "themes": ["ECON", "ECON_STOCKMARKET", "ECON_TAXATION"],
        "source_lang": "es",
        "country_code": "AR",
        "answer": {
            "predicted_slug": "currency-debt-stress",
            "confidence": 0.92,
            "reasoning": "Peso devaluation tied to banking crisis is direct currency stress.",
        },
    },
    {
        "headline": "Public hospital reports four heat-related deaths during record heatwave",
        "themes": ["MEDICAL", "ENV_CLIMATECHANGE"],
        "source_lang": "en",
        "country_code": "IN",
        "answer": {
            "predicted_slug": "heat-health-risk",
            "confidence": 0.93,
            "reasoning": "Heatwave with health casualties is the canonical heat-health-risk primary event.",
        },
    },
]


@dataclass
class Prediction:
    signal_id: int
    headline: str
    country_code: str | None
    source_lang: str | None
    atlas_assigned_slug: str | None
    gold_decision: str | None
    gold_correct_slug: str | None
    llm_mode: str
    llm_model: str
    llm_predicted_slug: str
    llm_confidence: float | None
    llm_reasoning: str
    llm_raw_response: str
    api_attempts: int
    api_error: str | None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_topics_snapshot(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    topics = payload.get("topics", [])
    if not topics:
        raise ValueError(f"empty topics snapshot at {path}")
    return [{"slug": t["slug"], "label": t["label"]} for t in topics]


def _format_topic_menu(topics: list[dict[str, str]]) -> str:
    lines = []
    for entry in topics:
        lines.append(f"- {entry['slug']}: {entry['label']}")
    lines.append("- none: no topic fits as primary evidence")
    return "\n".join(lines)


def _build_user_prompt(row: dict[str, Any], topics: list[dict[str, str]], mode: str) -> str:
    sections = [
        "TASK: Classify the headline into the best matching atlas topic slug.",
        "",
        "TOPIC MENU:",
        _format_topic_menu(topics),
        "",
    ]

    if mode == "few_shot":
        sections.append("EXAMPLES:")
        for ex in FEW_SHOT_EXAMPLES:
            sections.append(
                "Example input:\n"
                f"headline: {ex['headline']}\n"
                f"themes: {', '.join(ex['themes'])}\n"
                f"source_lang: {ex['source_lang']}\n"
                f"country_code: {ex['country_code']}"
            )
            sections.append(
                "Example output:\n" + json.dumps(ex["answer"], ensure_ascii=False)
            )
            sections.append("")

    sections.append("INPUT:")
    themes = row.get("themes") or []
    if not isinstance(themes, list):
        themes = []
    sections.append(f"headline: {row.get('headline', '').strip()}")
    sections.append(f"themes: {', '.join(themes) if themes else '(none)'}")
    sections.append(f"source_lang: {row.get('source_lang') or 'unknown'}")
    sections.append(f"country_code: {row.get('country_code') or 'unknown'}")
    sections.append(f"source_name: {row.get('source_name') or 'unknown'}")
    sections.append("")
    sections.append("OUTPUT (strict JSON, no prose):")
    return "\n".join(sections)


_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def _parse_llm_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("empty response")
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        raise ValueError(f"no JSON object in response: {text[:120]!r}")
    payload = json.loads(match.group(0))
    if "predicted_slug" not in payload:
        raise ValueError(f"response missing predicted_slug: {payload}")
    slug = str(payload["predicted_slug"]).strip()
    confidence = payload.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = None
    reasoning = str(payload.get("reasoning") or "").strip()
    return {"predicted_slug": slug, "confidence": confidence, "reasoning": reasoning}


def _call_llm(
    client: "anthropic.Anthropic",
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
    retries: int,
    backoff_seconds: float,
) -> tuple[str, int, str | None]:
    last_error: str | None = None
    for attempt in range(1, retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = response.content
            text = "".join(block.text for block in content if getattr(block, "type", None) == "text")
            return text, attempt, None
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(backoff_seconds * attempt)
    return "", retries, last_error


def _select_topics_from_gold(rows: Iterable[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    seen: dict[int, dict[str, Any]] = {}
    for row in rows:
        sid = row.get("signal_id")
        if sid is None:
            continue
        seen[int(sid)] = row
    return seen


def predict_row(
    row: dict[str, Any],
    *,
    topics: list[dict[str, str]],
    client: "anthropic.Anthropic",
    model: str,
    mode: str,
    max_tokens: int,
    temperature: float,
    retries: int,
    backoff_seconds: float,
) -> Prediction:
    user_prompt = _build_user_prompt(row, topics, mode)
    raw_text, attempts, error = _call_llm(
        client,
        model=model,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        retries=retries,
        backoff_seconds=backoff_seconds,
    )
    predicted_slug = "none"
    confidence: float | None = None
    reasoning = ""
    if raw_text and not error:
        try:
            parsed = _parse_llm_response(raw_text)
            predicted_slug = parsed["predicted_slug"] or "none"
            confidence = parsed["confidence"]
            reasoning = parsed["reasoning"]
        except (ValueError, json.JSONDecodeError) as exc:
            error = f"parse_error: {exc}"

    return Prediction(
        signal_id=int(row.get("signal_id", -1)),
        headline=str(row.get("headline", "")).strip(),
        country_code=row.get("country_code"),
        source_lang=row.get("source_lang"),
        atlas_assigned_slug=row.get("assigned_topic_slug"),
        gold_decision=row.get("gold_decision") or row.get("reviewer_decision"),
        gold_correct_slug=_gold_correct_slug(row),
        llm_mode=mode,
        llm_model=model,
        llm_predicted_slug=predicted_slug,
        llm_confidence=confidence,
        llm_reasoning=reasoning,
        llm_raw_response=raw_text,
        api_attempts=attempts,
        api_error=error,
    )


def _gold_correct_slug(row: dict[str, Any]) -> str | None:
    """The atlas slug that the gold review judged correct (if any).

    For reviewed/gold rows where `gold_decision == 'correct'` the gold slug is
    the assigned slug itself. When the decision is `incorrect` we treat the
    gold slug as the reviewer's stated parent/child thread if provided,
    otherwise None (meaning: classifier prediction was wrong but no positive
    label is supplied for that headline).
    """
    decision = row.get("gold_decision") or row.get("reviewer_decision")
    if decision == "correct":
        return row.get("assigned_topic_slug")
    return None


def score_predictions(predictions: list[Prediction]) -> dict[str, Any]:
    by_mode: dict[str, dict[str, Any]] = {}
    for pred in predictions:
        mode_bucket = by_mode.setdefault(
            pred.llm_mode,
            {
                "labeled": 0,
                "llm_matches_gold_correct": 0,
                "llm_matches_atlas_assigned": 0,
                "gold_unlabeled_skipped": 0,
                "errors": 0,
                "by_topic": {},
                "confusion": {"tp": 0, "fn": 0, "fp_other": 0, "tn_none": 0},
            },
        )
        if pred.api_error:
            mode_bucket["errors"] += 1
            continue

        if pred.gold_decision == "unclear" or pred.gold_decision is None:
            mode_bucket["gold_unlabeled_skipped"] += 1
            continue

        mode_bucket["labeled"] += 1
        topic_key = pred.atlas_assigned_slug or "(no_atlas_slug)"
        topic_bucket = mode_bucket["by_topic"].setdefault(
            topic_key,
            {"labeled": 0, "llm_correct": 0, "llm_match_atlas": 0},
        )
        topic_bucket["labeled"] += 1

        if pred.llm_predicted_slug == pred.atlas_assigned_slug:
            mode_bucket["llm_matches_atlas_assigned"] += 1
            topic_bucket["llm_match_atlas"] += 1

        # Compare LLM prediction to gold.
        if pred.gold_decision == "correct":
            # Gold positive: gold correct slug == assigned slug.
            if pred.llm_predicted_slug == pred.gold_correct_slug:
                mode_bucket["llm_matches_gold_correct"] += 1
                topic_bucket["llm_correct"] += 1
                mode_bucket["confusion"]["tp"] += 1
            else:
                mode_bucket["confusion"]["fn"] += 1
        elif pred.gold_decision in {"incorrect", "partial"}:
            # Gold negative: assigned slug was wrong. LLM is "right" if it
            # also rejects the assigned slug (picks something else or 'none').
            if pred.llm_predicted_slug == pred.atlas_assigned_slug:
                mode_bucket["confusion"]["fp_other"] += 1
            else:
                mode_bucket["confusion"]["tn_none"] += 1
                mode_bucket["llm_matches_gold_correct"] += 1
                topic_bucket["llm_correct"] += 1

    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "modes": {},
    }
    for mode, bucket in by_mode.items():
        labeled = bucket["labeled"]
        precision = (
            bucket["llm_matches_gold_correct"] / labeled if labeled else 0.0
        )
        agreement = (
            bucket["llm_matches_atlas_assigned"] / labeled if labeled else 0.0
        )
        summary["modes"][mode] = {
            "labeled": labeled,
            "errors": bucket["errors"],
            "gold_unlabeled_skipped": bucket["gold_unlabeled_skipped"],
            "llm_matches_gold_correct": bucket["llm_matches_gold_correct"],
            "llm_matches_atlas_assigned": bucket["llm_matches_atlas_assigned"],
            "llm_precision_vs_gold": round(precision, 4),
            "llm_agreement_with_atlas": round(agreement, 4),
            "confusion": bucket["confusion"],
            "by_topic": bucket["by_topic"],
        }
    return summary


def _existing_signal_ids(path: Path, mode: str) -> set[int]:
    if not path.exists():
        return set()
    seen: set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("llm_mode") == mode:
            seen.add(int(row.get("signal_id", -1)))
    return seen


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM baseline classifier for atlas benchmark.")
    parser.add_argument("--input", required=True, nargs="+", type=Path)
    parser.add_argument("--topics-snapshot", required=True, type=Path)
    parser.add_argument("--output-jsonl", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--mode", choices=("zero_shot", "few_shot", "both"), default="both")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--backoff-seconds", type=float, default=DEFAULT_BACKOFF_SECONDS)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip rows already present in the output JSONL for the same mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(2)

    topics = _load_topics_snapshot(args.topics_snapshot)
    rows: list[dict[str, Any]] = []
    for path in args.input:
        rows.extend(_load_jsonl(path))
    if args.max_rows is not None:
        rows = rows[: args.max_rows]

    modes = ("zero_shot", "few_shot") if args.mode == "both" else (args.mode,)
    client = anthropic.Anthropic(api_key=api_key)

    all_predictions: list[Prediction] = []
    for mode in modes:
        skip_ids = _existing_signal_ids(args.output_jsonl, mode) if args.resume else set()
        for row in rows:
            sid = int(row.get("signal_id", -1))
            if sid in skip_ids:
                continue
            prediction = predict_row(
                row,
                topics=topics,
                client=client,
                model=args.model,
                mode=mode,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                retries=args.retries,
                backoff_seconds=args.backoff_seconds,
            )
            _append_jsonl(args.output_jsonl, asdict(prediction))
            all_predictions.append(prediction)
            print(
                f"[{mode}] signal_id={sid} predicted={prediction.llm_predicted_slug} "
                f"atlas={prediction.atlas_assigned_slug} gold_decision={prediction.gold_decision} "
                f"attempts={prediction.api_attempts} error={prediction.api_error}",
                file=sys.stderr,
            )

    # Reload all predictions from the JSONL so scoring is independent of skip logic.
    persisted: list[Prediction] = []
    if args.output_jsonl.exists():
        for line in args.output_jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            persisted.append(Prediction(**payload))

    summary = score_predictions(persisted)
    summary["inputs"] = [str(p) for p in args.input]
    summary["model"] = args.model
    summary["topics_snapshot"] = str(args.topics_snapshot)
    summary["topic_count"] = len(topics)
    summary["temperature"] = args.temperature
    summary["max_tokens"] = args.max_tokens

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(
        {
            "output_jsonl": str(args.output_jsonl),
            "output_json": str(args.output_json),
            "modes_run": list(modes),
            "summary": summary["modes"],
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
