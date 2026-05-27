#!/usr/bin/env python3
"""LLM multilingual vocabulary mining per atlas topic.

For each atlas topic in the snapshot, ask the LLM to propose:
  - up to N positive lexicon terms in EN, ES, PT, IT, FR, DE, AR that
    strongly indicate the topic when found in a news headline;
  - up to M negative terms that look like they would match but indicate
    something else (distractors / false friends).

Output: JSONL with one record per topic. Per-term fields include
`term`, `lang`, `confidence`, `evidence`, plus the topic identifier.

This is a generative pass with the LLM and consumes API credit. Run
once per migration cycle, not per benchmark cycle. Schema version:
atlas-llm-vocab-mine-v1.

Required env: ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import anthropic
except ImportError as exc:  # pragma: no cover
    print(f"missing dependency: {exc}", file=sys.stderr)
    sys.exit(2)


SCHEMA_VERSION = "atlas-llm-vocab-mine-v1"
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_LANGS = ["en", "es", "pt", "it", "fr", "de", "ar"]
DEFAULT_POSITIVE_PER_TOPIC = 28
DEFAULT_NEGATIVE_PER_TOPIC = 10
DEFAULT_MAX_TOKENS = 1500
DEFAULT_TEMPERATURE = 0.2
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 4.0


SYSTEM_PROMPT = (
    "You are a multilingual lexicon engineer for a narrative-intelligence "
    "classifier. You propose lexicon terms used to substring-match against "
    "news headlines. Be concrete and minimal: prefer specific phrases over "
    "generic single words. Avoid stopwords. Avoid terms that match too many "
    "unrelated stories. Reply in strict JSON with two keys, `positive` and "
    "`negative`. Each entry has `term` (string, lowercased, 1-5 words), "
    "`lang` (one of en/es/pt/it/fr/de/ar), `confidence` (0..1 float), and "
    "`why` (one short sentence). Output the JSON object only, no prose."
)


def _load_topics(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    topics = payload.get("topics", [])
    if not topics:
        raise ValueError(f"empty topics snapshot at {path}")
    return [{"slug": t["slug"], "label": t["label"]} for t in topics]


def _build_user_prompt(
    topic: dict[str, str],
    *,
    langs: list[str],
    positive_n: int,
    negative_n: int,
) -> str:
    lang_list = ", ".join(langs)
    return "\n".join(
        [
            f"TOPIC SLUG: {topic['slug']}",
            f"TOPIC LABEL: {topic['label']}",
            "",
            f"Propose up to {positive_n} POSITIVE lexicon terms across these "
            f"languages: {lang_list}. Distribute roughly evenly across the "
            "languages when possible. Each positive term must, by itself, "
            "indicate this topic as the primary subject of a news headline.",
            "",
            f"Then propose up to {negative_n} NEGATIVE terms — words that "
            "look like they would match this topic but in real headlines "
            "usually indicate something else. Explain why in the `why` field.",
            "",
            "OUTPUT (strict JSON, no prose):",
            "{",
            '  "positive": [{"term": "...", "lang": "en", "confidence": 0.0, "why": "..."}, ...],',
            '  "negative": [{"term": "...", "lang": "en", "confidence": 0.0, "why": "..."}, ...]',
            "}",
        ]
    )


_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def _parse_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("empty response")
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        raise ValueError(f"no JSON object: {text[:200]!r}")
    payload = json.loads(match.group(0))

    def _normalize_entries(items: Any, expected_role: str) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        out = []
        for item in items:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term", "")).strip().lower()
            if not term:
                continue
            lang = str(item.get("lang", "")).strip().lower() or "unknown"
            confidence = item.get("confidence")
            try:
                confidence = float(confidence) if confidence is not None else None
            except (TypeError, ValueError):
                confidence = None
            why = str(item.get("why", "")).strip()
            out.append(
                {
                    "term": term,
                    "lang": lang,
                    "confidence": confidence,
                    "why": why,
                    "role": expected_role,
                }
            )
        return out

    positives = _normalize_entries(payload.get("positive"), "positive")
    negatives = _normalize_entries(payload.get("negative"), "negative")
    return {"positive": positives, "negative": negatives}


def _call_llm(
    client: "anthropic.Anthropic",
    *,
    model: str,
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
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            )
            return text, attempt, None
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(backoff_seconds * attempt)
    return "", retries, last_error


def _existing_topic_slugs(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        slug = row.get("topic_slug")
        if slug:
            out.add(slug)
    return out


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def mine_topic(
    topic: dict[str, str],
    *,
    client: "anthropic.Anthropic",
    model: str,
    langs: list[str],
    positive_n: int,
    negative_n: int,
    max_tokens: int,
    temperature: float,
    retries: int,
    backoff_seconds: float,
) -> dict[str, Any]:
    user_prompt = _build_user_prompt(
        topic,
        langs=langs,
        positive_n=positive_n,
        negative_n=negative_n,
    )
    raw, attempts, error = _call_llm(
        client,
        model=model,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        retries=retries,
        backoff_seconds=backoff_seconds,
    )
    positive: list[dict[str, Any]] = []
    negative: list[dict[str, Any]] = []
    if raw and not error:
        try:
            parsed = _parse_response(raw)
            positive = parsed["positive"]
            negative = parsed["negative"]
        except (ValueError, json.JSONDecodeError) as exc:
            error = f"parse_error: {exc}"
    return {
        "schema_version": SCHEMA_VERSION,
        "topic_slug": topic["slug"],
        "topic_label": topic["label"],
        "model": model,
        "langs": langs,
        "positive_count_requested": positive_n,
        "negative_count_requested": negative_n,
        "positive": positive,
        "negative": negative,
        "raw_response": raw,
        "api_attempts": attempts,
        "api_error": error,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM multilingual vocab mining per atlas topic.")
    parser.add_argument("--topics-snapshot", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--langs", nargs="+", default=DEFAULT_LANGS)
    parser.add_argument("--positive-per-topic", type=int, default=DEFAULT_POSITIVE_PER_TOPIC)
    parser.add_argument("--negative-per-topic", type=int, default=DEFAULT_NEGATIVE_PER_TOPIC)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-topics", type=int, default=None)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--backoff-seconds", type=float, default=DEFAULT_BACKOFF_SECONDS)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(2)

    topics = _load_topics(args.topics_snapshot)
    if args.max_topics is not None:
        topics = topics[: args.max_topics]
    skip = _existing_topic_slugs(args.output) if args.resume else set()
    client = anthropic.Anthropic(api_key=api_key)

    written = 0
    for topic in topics:
        if topic["slug"] in skip:
            continue
        result = mine_topic(
            topic,
            client=client,
            model=args.model,
            langs=args.langs,
            positive_n=args.positive_per_topic,
            negative_n=args.negative_per_topic,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            retries=args.retries,
            backoff_seconds=args.backoff_seconds,
        )
        _append_jsonl(args.output, result)
        written += 1
        print(
            f"topic={topic['slug']} pos={len(result['positive'])} "
            f"neg={len(result['negative'])} attempts={result['api_attempts']} "
            f"error={result['api_error']}",
            file=sys.stderr,
        )

    print(json.dumps({
        "output": str(args.output),
        "topics_written": written,
        "model": args.model,
    }, indent=2))


if __name__ == "__main__":
    main()
