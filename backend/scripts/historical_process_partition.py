"""Process archived Atlas signals into compact historical product aggregates."""
from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts.archive_common import parse_timestamp


MODEL_VERSION_DEFAULT = "atlas-hist-v1"

TOPIC_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "energy-grid-instability",
        ("energy", "electricity", "blackout", "power outage", "grid", "rationing"),
        ("ENERGY", "INFRASTRUCTURE"),
    ),
    (
        "food-price-stress",
        ("food price", "food prices", "bread", "rice", "hunger", "shortage", "inflation"),
        ("FOOD_SECURITY", "ECON_INFLATION"),
    ),
    (
        "armed-conflict-escalation",
        ("airstrike", "shelling", "clashes", "offensive", "militia", "rebels", "battle"),
        ("ARMEDCONFLICT", "MILITARY", "KILL"),
    ),
    (
        "water-stress-drought",
        ("drought", "water shortage", "reservoir", "dry season", "water rationing"),
        ("ENV_CLIMATECHANGE", "WATER_SECURITY"),
    ),
    (
        "labor-strike-disruption",
        ("strike", "union", "walkout", "wage dispute", "labor protest"),
        ("LABOR", "STRIKE", "PROTEST"),
    ),
    (
        "migration-border-pressure",
        ("migrant", "migration", "border crossing", "asylum", "deportation", "refugee"),
        ("MIGRATION", "REFUGEES"),
    ),
    (
        "corruption-investigation",
        ("corruption", "bribery", "embezzlement", "procurement scandal", "kickback"),
        ("CORRUPTION", "INVESTIGATION"),
    ),
    (
        "transport-corridor-disruption",
        ("port", "road blockade", "rail strike", "canal", "bridge collapse", "shipping"),
        ("TRANSPORT", "ECON_TRADE"),
    ),
    (
        "disease-outbreak",
        ("outbreak", "epidemic", "virus", "vaccination", "public health emergency"),
        ("HEALTH", "MEDICAL"),
    ),
    (
        "sanctions-diplomatic-pressure",
        ("sanctions", "diplomatic pressure", "embassy", "treaty", "negotiations"),
        ("SANCTION", "TAX_DIPLOMACY", "TREATY"),
    ),
)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def infer_topic_slug(row: dict[str, Any]) -> str:
    """Map raw source hints into Atlas-owned topic slugs."""
    headline = (row.get("headline") or "").lower()
    themes = {str(theme).upper() for theme in _as_list(row.get("themes"))}

    for slug, headline_terms, theme_hints in TOPIC_RULES:
        if any(term in headline for term in headline_terms):
            return slug
        if any(hint in themes for hint in theme_hints):
            return slug
    return "general-monitoring"


def _normalized_sentiment(row: dict[str, Any]) -> tuple[float | None, bool]:
    nlp_value = row.get("nlp_sentiment")
    if nlp_value is not None:
        return float(nlp_value), True

    gdelt_value = row.get("sentiment")
    if gdelt_value is None:
        return None, False
    return max(-1.0, min(1.0, float(gdelt_value) / 10.0)), False


def _has_entities(row: dict[str, Any]) -> bool:
    return bool(_as_list(row.get("nlp_persons")) or _as_list(row.get("persons")))


def build_daily_topic_country_rows(
    rows: list[dict[str, Any]],
    *,
    model_version: str,
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    source_names: dict[tuple[str, str, str, str, str], set[str]] = defaultdict(set)

    for row in rows:
        ts_raw = row.get("timestamp") or row.get("created_at")
        if not ts_raw:
            continue
        day = parse_timestamp(str(ts_raw)).date().isoformat()
        topic_slug = infer_topic_slug(row)
        country_code = (row.get("country_code") or "XX").upper()
        source_family = row.get("source_family") or "unknown"
        signal_class = row.get("signal_class") or "unknown"
        key = (day, topic_slug, country_code, source_family, signal_class)

        bucket = buckets.setdefault(
            key,
            {
                "day": day,
                "topic_slug": topic_slug,
                "country_code": country_code,
                "source_family": source_family,
                "signal_class": signal_class,
                "signal_count": 0,
                "_sentiment_sum": 0.0,
                "_sentiment_n": 0,
                "_nlp_sentiment_n": 0,
                "_topic_n": 0,
                "_entity_n": 0,
                "model_version": model_version,
            },
        )

        bucket["signal_count"] += 1
        sentiment, came_from_nlp = _normalized_sentiment(row)
        if sentiment is not None:
            bucket["_sentiment_sum"] += sentiment
            bucket["_sentiment_n"] += 1
            if came_from_nlp:
                bucket["_nlp_sentiment_n"] += 1
        if topic_slug != "general-monitoring":
            bucket["_topic_n"] += 1
        if _has_entities(row):
            bucket["_entity_n"] += 1
        if row.get("source_name"):
            source_names[key].add(str(row["source_name"]).lower())

    output: list[dict[str, Any]] = []
    for key, bucket in buckets.items():
        count = bucket["signal_count"]
        sentiment_n = bucket.pop("_sentiment_n")
        sentiment_sum = bucket.pop("_sentiment_sum")
        nlp_sentiment_n = bucket.pop("_nlp_sentiment_n")
        topic_n = bucket.pop("_topic_n")
        entity_n = bucket.pop("_entity_n")
        unique_sources = len(source_names[key])

        bucket["avg_sentiment"] = round(sentiment_sum / sentiment_n, 4) if sentiment_n else None
        bucket["sentiment_coverage"] = round(nlp_sentiment_n / count, 4)
        bucket["topic_coverage"] = round(topic_n / count, 4)
        bucket["entity_coverage"] = round(entity_n / count, 4)
        bucket["local_voice_ratio"] = None
        bucket["source_diversity"] = round(unique_sources / count, 4) if count else None
        bucket["evidence_sample_count"] = 0
        output.append(bucket)

    return sorted(
        output,
        key=lambda item: (
            item["day"],
            item["topic_slug"],
            item["country_code"],
            item["source_family"],
            item["signal_class"],
        ),
    )


def iter_jsonl_gzip(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process local Atlas archive partition")
    parser.add_argument("--input", required=True, help="Path to archived .jsonl.gz partition")
    parser.add_argument("--output", required=True, help="Output JSON artifact path")
    parser.add_argument("--model-version", default=MODEL_VERSION_DEFAULT)
    args = parser.parse_args()

    rows = list(iter_jsonl_gzip(Path(args.input)))
    aggregate_rows = build_daily_topic_country_rows(rows, model_version=args.model_version)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "input": str(Path(args.input).resolve()),
                "model_version": args.model_version,
                "input_rows": len(rows),
                "aggregate_rows": len(aggregate_rows),
                "rows": aggregate_rows,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "input_rows": len(rows),
                "aggregate_rows": len(aggregate_rows),
                "output": str(output_path),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
