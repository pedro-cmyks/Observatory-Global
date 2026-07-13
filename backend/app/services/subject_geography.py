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


def resolve_place_to_country(place: Any) -> str | None:
    """Resolve a NER-extracted place name to an ISO subject country.

    A place named in the story (via NER over the body) is genuine subject
    signal — not coverage — so it can verify geography for a headline that names
    only a local entity. Reuses the shared country patterns (which include
    capitals and major cities) plus the native-script table. Returns None for
    places outside the known geography (e.g. "Bondi Beach"): the gazetteer
    ceiling a fuller geocoder would lift, never a guess.
    """
    text = decode_headline(place)
    if not text:
        return None
    for pattern, code in _COUNTRY_PATTERNS:
        if pattern.search(text):
            return _SUBJECT_COUNTRY_ALIASES.get(str(code).upper(), str(code).upper())
    for pattern, code in _NATIVE_COUNTRY_PATTERNS:
        if pattern.search(text):
            return _SUBJECT_COUNTRY_ALIASES.get(str(code).upper(), str(code).upper())
    return None


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
        # C-clean: a place named in the story body (via NER) is subject signal,
        # so it corroborates geography for headlines that name only a local
        # entity. Activates when receipts carry NER `places`; a no-op until that
        # is plumbed through the serving layer (gated on NER throughput #184).
        for place in row.get("places") or []:
            code = resolve_place_to_country(place)
            if not code:
                continue
            item = evidence.setdefault(code, {
                "receipt_ids": set(),
                "outlets": set(),
                "methods": set(),
            })
            item["receipt_ids"].add(str(receipt_id))
            if outlet:
                item["outlets"].add(outlet)
            item["methods"].add("ner_place")

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


def measure_subject_geography_coherence(
    receipts: Sequence[dict[str, Any]],
    *,
    min_country_share: float = 0.15,
    cooccurrence_floor: float = 0.30,
) -> dict[str, Any]:
    """Separate a coherent multi-country story from a grab-bag umbrella (#257).

    A single story can genuinely span several countries (an Israel-US-Iran plot),
    and an incoherent umbrella can bundle unrelated country-stories under one
    label ("Canicule en Belgique" carrying France-Morocco football). Entropy
    cannot tell them apart — both look multi-country. Co-occurrence can: in a
    coherent story the significant countries appear *together* in the same
    receipts; in a grab-bag they appear in *disjoint* receipt groups.

    Read-only and deterministic. It measures; it never drops a receipt.
    """
    receipt_country_sets: list[set[str]] = []
    for row in receipts:
        codes = set(headline_country_evidence(row.get("headline")).keys())
        if codes:
            receipt_country_sets.append(codes)

    total = len(receipt_country_sets)
    if total == 0:
        return {
            "contract": "atlas-subject-coherence-v1",
            "status": "no_subject_geography_signal",
            "grab_bag": False,
            "significant_countries": [],
            "cooccurrence": None,
            "reason_codes": ["no_subject_geography_in_receipts"],
        }

    freq: dict[str, int] = {}
    for codes in receipt_country_sets:
        for code in codes:
            freq[code] = freq.get(code, 0) + 1

    significant = sorted(c for c, n in freq.items() if n / total >= min_country_share)
    dominant = max(freq, key=lambda c: (freq[c], c))
    if len(significant) < 2:
        return {
            "contract": "atlas-subject-coherence-v1",
            "status": "single_dominant_subject",
            "grab_bag": False,
            "significant_countries": significant or [dominant],
            "dominant_country": dominant,
            "cooccurrence": None,
            "reason_codes": ["single_dominant_subject_country"],
        }

    sig = set(significant)
    co = sum(1 for codes in receipt_country_sets if len(codes & sig) >= 2)
    cooccurrence = co / total
    grab_bag = cooccurrence < cooccurrence_floor
    return {
        "contract": "atlas-subject-coherence-v1",
        "status": "grab_bag" if grab_bag else "coherent_multi_country",
        "grab_bag": grab_bag,
        "significant_countries": significant,
        "dominant_country": dominant,
        "cooccurrence": round(cooccurrence, 3),
        "reason_codes": (
            ["disjoint_country_groups_grab_bag"] if grab_bag
            else ["significant_countries_co_occur"]
        ),
    }
