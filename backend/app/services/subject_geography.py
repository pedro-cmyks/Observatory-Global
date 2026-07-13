"""Deterministic subject-geography receipts shared by publication surfaces.

This module does not choose an editorially important country and never copies
coverage geography into subject geography.  It only verifies countries named
in frozen headlines across independent receipts and outlets.  Multi-country
events therefore keep every corroborated country instead of forcing a single
primary.
"""
from __future__ import annotations

from collections import defaultdict
import html
from typing import Any, Sequence

from app.services.ingest_rss import _COUNTRY_PATTERNS, _NATIVE_COUNTRY_PATTERNS


_SUBJECT_COUNTRY_ALIASES = {
    "GZ": "PS",
    "WE": "PS",
    "KU": "KW",
    "BX": "BN",
}


def decode_headline(value: Any) -> str:
    """Decode nested HTML entities found in GDELT/RSS headline snapshots."""
    text = str(value or "")
    for _ in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    return text


def headline_country_evidence(headline: Any) -> dict[str, set[str]]:
    """Return every country explicitly matched in one decoded headline."""
    text = decode_headline(headline)
    methods: dict[str, set[str]] = defaultdict(set)
    for pattern, code in _COUNTRY_PATTERNS:
        if pattern.search(text):
            normalized = _SUBJECT_COUNTRY_ALIASES.get(
                str(code).upper(), str(code).upper(),
            )
            methods[normalized].add("headline_pattern")
    for pattern, code in _NATIVE_COUNTRY_PATTERNS:
        if pattern.search(text):
            normalized = _SUBJECT_COUNTRY_ALIASES.get(
                str(code).upper(), str(code).upper(),
            )
            methods[normalized].add("native_pattern")
    return dict(methods)


def infer_receipt_subject_geography(
    receipts: Sequence[dict[str, Any]],
    *,
    minimum_receipts: int = 2,
    minimum_outlets: int = 2,
) -> dict[str, Any]:
    """Verify all countries independently named by the frozen evidence.

    The thresholds are corroboration requirements, not a semantic ranking
    score.  Every candidate remains in the returned ledger when it does not
    clear them.
    """
    evidence: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(receipts):
        receipt_id = row.get("id") or row.get("source_url") or f"row:{position}"
        outlet = str(row.get("source_name") or "").strip().casefold()
        for country, methods in headline_country_evidence(row.get("headline")).items():
            item = evidence.setdefault(country, {
                "receipt_ids": set(),
                "outlets": set(),
                "methods": set(),
            })
            item["receipt_ids"].add(str(receipt_id))
            if outlet:
                item["outlets"].add(outlet)
            item["methods"].update(methods)

    candidates = []
    for country, item in evidence.items():
        receipt_count = len(item["receipt_ids"])
        outlet_count = len(item["outlets"])
        candidates.append({
            "country": country,
            "receipt_count": receipt_count,
            "outlet_count": outlet_count,
            "methods": sorted(item["methods"]),
            "status": (
                "verified"
                if receipt_count >= minimum_receipts and outlet_count >= minimum_outlets
                else "candidate"
            ),
        })
    candidates.sort(
        key=lambda row: (-row["receipt_count"], -row["outlet_count"], row["country"]),
    )
    verified = sorted(
        row["country"] for row in candidates if row["status"] == "verified"
    )
    if verified:
        status = "verified"
        reasons: list[str] = []
    elif candidates:
        status = "partial"
        reasons = ["subject_geography_not_independently_corroborated"]
    else:
        status = "unavailable"
        reasons = ["no_explicit_subject_geography_in_receipts"]
    return {
        "contract": "atlas-subject-geography-v1",
        "status": status,
        "verified_subject_countries": verified,
        "candidates": candidates,
        "reason_codes": reasons,
        "method": "decoded_headline_country_patterns_distinct_receipt_outlet",
        "minimum_receipts": minimum_receipts,
        "minimum_outlets": minimum_outlets,
        "forced_primary_country": False,
        "coverage_geography_used": False,
        "truncated": False,
    }
