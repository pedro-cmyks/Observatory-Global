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
import re
import unicodedata
from typing import Any, Sequence

from app.core.iso_country_names import ISO_COUNTRY_NAMES
from app.services.ingest_rss import _COUNTRY_PATTERNS, _NATIVE_COUNTRY_PATTERNS


_SUBJECT_COUNTRY_ALIASES = {
    "GZ": "PS",
    "WE": "PS",
    "KU": "KW",
    "BX": "BN",
}


# ── Person-proxy demotion (#238, measured 2026-07-16) ─────────────────────────
# The ingest lexicons deliberately carry leader names (Putin→RU, Trump→US,
# Зеленськ→UA, …). That stays fine for coarse volume geo-tagging, but a person
# mention is NOT verify-grade SUBJECT geography: dt-714, a Romania-domestic
# politics thread, VERIFIED RU because "mesaj către Putin" receipts hit the
# Putin proxy across ≥2 outlets. Every person token appearing in
# _COUNTRY_PATTERNS / _NATIVE_COUNTRY_PATTERNS is listed here; a headline whose
# country evidence survives only via these tokens is demoted to method
# "person_proxy" and never counts toward the verified bar. Organizations
# (Hamas, IDF, Houthi, Taliban, Wagner…) are metonyms for parties to the story,
# not individual proxies — they stay verify-grade.
_PERSON_PROXY_TOKENS_LATIN = [
    # heads of state / leader surnames present in the Latin table
    "Khamenei", "Araghchi", "Zelenskyy", "Zelenskiy", "Putin", "Netanyahu",
    "Sharif", "Modi", "Xi Jinping", "Kim Jong", "Assad", "MBS", "Maduro",
    "Lula", "Flávio Dino", "Trump", "Starmer", "Macron", "Petro", "Boluarte",
    "Milei", "Boric", "Sheinbaum", "Noboa", "Arce", "Díaz-Canel", "Ortega",
    "El-Sisi", "Sisi", "Erdogan", "Erdoğan", "Saied", "Abdullah", "Tinubu",
    "Ruto", "Ramaphosa", "Mahama", "Museveni", "Mnangagwa", "Faye", "Traoré",
    "Tiani", "Marcos", "Duterte", "Prabowo", "Lee Hsien Loong",
    "Lawrence Wong", "Pita", "Anwar", "Hun Sen", "Hun Manet", "Yunus",
    "Dissanayake", "Albanese", "Trudeau", "Carney", "Meloni", "Tusk",
    "Kishida", "Ishiba",
]
_PERSON_PROXY_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(?:" + "|".join(re.escape(t) for t in _PERSON_PROXY_TOKENS_LATIN) + r")\b",
        re.I,
    ),
    # Cyrillic stems (Russian + Ukrainian orthographies) — same boundary
    # regime as the native table (stem prefix, no \b).
    re.compile(r"Путин|Путін|Зеленск|Зеленськ"),
    # Arabic-script el-Sisi (the EG native pattern carries him).
    re.compile(r"السیسی|السيسي"),
]


def _mask_person_tokens(text: str) -> str:
    """Blank every known person token so country patterns can be re-checked
    against the remaining, genuinely geographic, evidence."""
    for pattern in _PERSON_PROXY_PATTERNS:
        text = pattern.sub(" ", text)
    return text


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
    """Return every country explicitly matched in one decoded headline.

    A pattern that matches the raw headline but no longer matches once person
    tokens are masked was matching a PERSON, not a place — that country's
    method for this headline is ``person_proxy`` (candidate-grade only, #238).
    The country still appears in the result: demotion is labeling, never
    silent filtering.
    """
    text = decode_headline(headline)
    masked = _mask_person_tokens(text)
    methods: dict[str, set[str]] = defaultdict(set)
    for table, method in (
        (_COUNTRY_PATTERNS, "headline_pattern"),
        (_NATIVE_COUNTRY_PATTERNS, "native_pattern"),
    ):
        for pattern, code in table:
            if not pattern.search(text):
                continue
            normalized = _SUBJECT_COUNTRY_ALIASES.get(
                str(code).upper(), str(code).upper(),
            )
            if pattern.search(masked):
                methods[normalized].add(method)
            else:
                methods[normalized].add("person_proxy")
    return dict(methods)


# ── Place → country gazetteer (C-clean slice 2, #238) ─────────────────────────
# GeoNames-derived {normalized place: ISO2}, built by
# scripts/build_place_gazetteer.py (cities15000 + admin-1 regions, CC-BY —
# attribution in the JSON _meta). Lazy-loaded once per process, same pattern as
# the scope-gate extended thresholds. Missing/corrupt file → {} = gazetteer
# disabled; the country-pattern fallback still works.
_PLACE_GAZETTEER: dict[str, str] | None = None

_PLACE_WS = re.compile(r"\s+")

_COUNTRY_NAME_TO_ISO: dict[str, str] = {
    name.casefold(): code for code, name in ISO_COUNTRY_NAMES.items()
}


def _normalize_place(value: str) -> str:
    """Must stay in sync with scripts/build_place_gazetteer.py:normalize_place."""
    return _PLACE_WS.sub(" ", unicodedata.normalize("NFC", value).casefold()).strip()


def _place_gazetteer() -> dict[str, str]:
    global _PLACE_GAZETTEER
    if _PLACE_GAZETTEER is None:
        import json as _json
        from pathlib import Path as _Path
        p = _Path(__file__).resolve().parents[1] / "data" / "place_to_country.json"
        try:
            doc = _json.loads(p.read_text(encoding="utf-8"))
            _PLACE_GAZETTEER = dict(doc.get("places") or {})
        except Exception:
            _PLACE_GAZETTEER = {}
    return _PLACE_GAZETTEER


def _alias(code: Any) -> str:
    return _SUBJECT_COUNTRY_ALIASES.get(str(code).upper(), str(code).upper())


def normalize_subject_country(code: Any) -> str:
    """Public name for the subject-country alias fold (GZ/WE→PS, KU→KW,
    BX→BN). Serving surfaces compare their own country code on the SAME basis
    the detectors below emit — otherwise a 'Gaza …' label (GZ→PS) would read
    as contradicting the PS edition it belongs to."""
    return _alias(code)


def resolve_place_to_country(place: Any) -> str | None:
    """Resolve a NER-extracted place name to an ISO subject country.

    A place named in the story (via NER over the body) is genuine subject
    signal — not coverage — so it can verify geography for a headline that names
    only a local entity. Resolution order:

    1. country NAMES themselves (ISO_COUNTRY_NAMES reverse map: France→FR);
    2. the GeoNames gazetteer (cities >=15k + admin-1 regions; ascii/Latin
       forms only, ambiguous multi-country names pre-dropped at build time);
    3. the shared country patterns (Latin + native-script lexicons) — this
       keeps native-script country mentions (Херсон→UA-class tokens) working.

    Returns None for places outside the known geography (e.g. "Bondi Beach"):
    the gazetteer ceiling a fuller geocoder would lift, never a guess.
    """
    text = decode_headline(place)
    if not text:
        return None
    normalized = _normalize_place(text)
    if not normalized:
        return None
    code = _COUNTRY_NAME_TO_ISO.get(normalized)
    if code:
        return _alias(code)
    code = _place_gazetteer().get(normalized)
    if code:
        return _alias(code)
    for pattern, code in _COUNTRY_PATTERNS:
        if pattern.search(text):
            return _alias(code)
    for pattern, code in _NATIVE_COUNTRY_PATTERNS:
        if pattern.search(text):
            return _alias(code)
    return None


def resolve_gazetteer_place(place: Any) -> str | None:
    """GeoNames-ONLY resolution: a named CITY / admin-1 region → ISO country.

    Deliberately narrower than `resolve_place_to_country` above, for callers
    that must distinguish "the prose named a CITY" from "the prose named a
    country" (X3-B, the capital-as-proxy guard):

      * country NAMES resolve to None — "in Colombia" is not a city claim;
      * the leader/demonym lexicons (`_COUNTRY_PATTERNS`) are NOT consulted —
        they would resolve "Colombian" and "Petro" to CO, and a guard rewriting
        "in Colombian territory" to "in Colombia territory" is a regression.

    Returns None for anything the gazetteer does not carry (San José del Palmar,
    below the 15k floor): the same honest ceiling, never a guess.
    """
    text = decode_headline(place)
    if not text:
        return None
    normalized = _normalize_place(text)
    if not normalized or normalized in _COUNTRY_NAME_TO_ISO:
        return None
    code = _place_gazetteer().get(normalized)
    return _alias(code) if code else None


# ── Label ↔ receipt geography conjunct (council R4 N17, 2026-08-11) ──────────
# The label court entails a label against its receipts but never checks the
# label's OWN geography claim, and the country-edition slotter admits a thread
# whose subject countries contradict its label text. Both blind spots met on
# one front door: dt-8597 "Japan Earthquake Traps Shoppers" was stamped court
# `entailed` + subject-geo VERIFIED ['CO'] and led Colombia's edition on quake
# day, while every geo-bearing receipt under it read "terremoto 7,4 sacude
# Colombia".
#
# This is the ONE detector both guards ride. Deliberately narrow — a wrong
# `failed` (or a wrongly-emptied country door) is a regression, while a missed
# check is only the status quo — so it abstains on every ambiguity:
#
#   * ONE basis for both sides. Label and receipts are read with
#     `headline_country_evidence` above, the same function that already
#     decides subject geography. No new gazetteer enters the system, and the
#     two sides are always comparable.
#   * SUBJECT geography only — NEVER `signals_v2.country_code`. The stored
#     code is COVERAGE geography: dt-9434 "Japan Earthquake Casualties"
#     carries ten RU-tagged receipts that are literally about Japan
#     ("землетрясения в Японии"). Comparing a label against coverage codes
#     would have failed that correct label. Those Cyrillic forms resolve to
#     nothing in the shared lexicons, so they contribute no geography at all
#     and the check simply abstains — the safe direction, measured.
#   * A label naming ZERO or MORE THAN ONE country is skipped: it makes no
#     single falsifiable geography claim ("Russia Sanctions and Ukraine War
#     Updates" names two; "Global Markets Rally" names none).
#   * A person token is not a geography claim. `headline_country_evidence`
#     already demotes person proxies to `person_proxy` (#238); a label that
#     matches a country ONLY through a leader's name ("Trump Tariffs
#     Escalate" → US) is skipped here for the same reason.
#   * The named country must appear in ZERO receipts, AND one other country
#     must dominate the geo-bearing receipts, AND there must be enough of
#     them to mean something. Anything short of all three abstains.
#   * ABSENCE IS CHECKED WIDER THAN DOMINANCE (measured, see below). An
#     absence claim needs more evidence than a presence claim — the same
#     lesson label_court.py's own GB4/GB5 absence-contradiction detectors
#     learned — so callers may pass a larger `absence_receipts` pool while
#     dominance stays measured on the sample actually being judged.
#
# MEASURED before shipping (2026-08-11, read-only sweep over the 400 largest
# active+`entailed` story rows in prod; 137 of them carry a single-country
# label). On the judged 8-receipt window alone the check fired 6 times and
# hand-check put precision at ~50%: the false positives were all ACTOR-vs-
# TARGET labels in the Russia-Ukraine war ("Russian Drone Attacks on Emergency
# Workers" over Ukrainian receipts, "Ukraine Strikes Wildberries Warehouses"
# over Russian ones) — honest labels naming the actor country while the
# receipts name where it landed. Widening the ABSENCE pool to 40 receipts
# removed them (RU present 8×, UA present 1× once the window opened) along
# with a fusion case whose Gaza receipts simply sat outside the newest window
# (dt-817), and left the real mislabels standing (dt-8597 and dt-3963 — the
# N17 witness and its sibling — keep JP at 0 across 120 receipts).
#
# RESIDUAL, named not hidden: an actor country that the lexicons cannot read
# in the receipts' language still reads as absent (dt-3623 "Russia Strikes US
# UAV Factory" over Vietnamese/Ukrainian receipts where Russia appears only as
# "Nga"/"РФ"). One survivor in that sweep, and only ever reachable when the
# judge independently answers `entailed` — this veto never promotes anything.
#
# Honest limit (pinned in tests/test_label_geo_conjunct.py): a place the
# shared lexicons and the GeoNames gazetteer do not carry resolves to nothing,
# so the Syros≈Syria case (a Greek island whose largest town is under the
# gazetteer's 15k floor, serving on the SY edition because its signals are
# country-tagged SY) is NOT caught here. Closing that needs a fuller geocoder,
# not a guess.
LABEL_GEO_DOMINANCE_FLOOR = 0.70
LABEL_GEO_MIN_RECEIPTS = 3


def _non_proxy_countries(text: Any) -> set[str]:
    """Countries a text names as PLACES — person-proxy-only matches dropped."""
    return {
        code
        for code, methods in headline_country_evidence(text).items()
        if methods - {"person_proxy"}
    }


def label_subject_country(label: Any) -> str | None:
    """The single country a label explicitly names, or None.

    None means "no falsifiable geography claim" and is returned for a label
    naming nothing, a label naming two or more countries, and a label whose
    only country evidence is a person token. Callers treat None as SKIP.
    """
    codes = _non_proxy_countries(label)
    return next(iter(codes)) if len(codes) == 1 else None


def receipt_subject_country_counts(
    receipts: Sequence[dict[str, Any]] | None,
) -> tuple[dict[str, int], int]:
    """(country -> how many RECEIPTS name it, number of geo-bearing receipts).

    Counted per receipt, never per mention, so one headline repeating a
    country name cannot manufacture dominance.
    """
    counts: dict[str, int] = {}
    carrying = 0
    for row in receipts or []:
        codes = _non_proxy_countries((row or {}).get("headline"))
        if not codes:
            continue
        carrying += 1
        for code in codes:
            counts[code] = counts.get(code, 0) + 1
    return counts, carrying


def label_geography_conflict(
    label: Any,
    receipts: Sequence[dict[str, Any]] | None,
    *,
    absence_receipts: Sequence[dict[str, Any]] | None = None,
    dominance_floor: float = LABEL_GEO_DOMINANCE_FLOOR,
    min_geo_receipts: int = LABEL_GEO_MIN_RECEIPTS,
) -> dict[str, Any] | None:
    """The label's own country claim vs its receipts' subject geography.

    `receipts` is the sample the judgment is about — dominance is measured
    there. `absence_receipts`, when given, is the WIDER pool the "the label's
    country is named nowhere" claim must survive (defaults to `receipts`).

    Returns None (no measurable conflict — the overwhelmingly common case) or
    a receipt-grounded conflict block whose ``summary`` NAMES the mismatch
    ("label says Japan (JP); receipts 19/19 CO") so no caller has to assert a
    conflict it cannot show.
    """
    named = label_subject_country(label)
    if not named:
        return None
    counts, carrying = receipt_subject_country_counts(receipts)
    if carrying < min_geo_receipts:
        return None
    if counts.get(named, 0) > 0:
        # the label's claim is supported somewhere in its own receipts
        return None
    wide = absence_receipts if absence_receipts is not None else receipts
    wide_counts, wide_carrying = (
        receipt_subject_country_counts(wide) if wide is not receipts
        else (counts, carrying)
    )
    if wide_counts.get(named, 0) > 0:
        # present once the window opens: an ACTOR country the judged sample
        # happened not to name, not a label lying about its geography
        return None
    # count desc, code asc — deterministic on ties
    dominant, dominant_count = sorted(
        counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    if dominant_count < dominance_floor * carrying:
        return None
    label_name = ISO_COUNTRY_NAMES.get(named, named)
    return {
        "contract": "atlas-label-geo-conflict-v1",
        "label_country": named,
        "label_country_name": label_name,
        "dominant_country": dominant,
        "dominant_receipts": dominant_count,
        "geo_receipts": carrying,
        "total_receipts": len(receipts or []),
        "absence_geo_receipts": wide_carrying,
        "absence_pool": len(wide or []),
        "dominance_floor": dominance_floor,
        "reason_code": "label_country_absent_from_receipts",
        "summary": (
            f"label says {label_name} ({named}); "
            f"receipts {dominant_count}/{carrying} {dominant}"
        ),
    }


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

    Person-proxy demotion (#238): a receipt whose evidence for a country comes
    ONLY from person tokens (Putin→RU, Trump→US, …) is candidate-grade — the
    ≥minimum_receipts/≥minimum_outlets verified bar must be met by non-proxy
    receipts alone.  When that demotion suppresses a would-be verify, the
    candidate carries ``person_proxy_suppressed`` and the reason codes carry
    ``person_proxy_evidence_demoted`` — visible, never silent.
    """
    def _new_item() -> dict[str, Any]:
        return {
            "receipt_ids": set(),
            "outlets": set(),
            "methods": set(),
            "non_proxy_receipt_ids": set(),
            "non_proxy_outlets": set(),
        }

    evidence: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(receipts):
        receipt_id = row.get("id") or row.get("source_url") or f"row:{position}"
        outlet = str(row.get("source_name") or "").strip().casefold()
        for country, methods in headline_country_evidence(row.get("headline")).items():
            item = evidence.setdefault(country, _new_item())
            item["receipt_ids"].add(str(receipt_id))
            if outlet:
                item["outlets"].add(outlet)
            item["methods"].update(methods)
            if methods - {"person_proxy"}:
                item["non_proxy_receipt_ids"].add(str(receipt_id))
                if outlet:
                    item["non_proxy_outlets"].add(outlet)
        # C-clean: a place named in the story body (via NER) is subject signal,
        # so it corroborates geography for headlines that name only a local
        # entity. Activates when receipts carry NER `places`; a no-op until that
        # is plumbed through the serving layer (gated on NER throughput #184).
        for place in row.get("places") or []:
            code = resolve_place_to_country(place)
            if not code:
                continue
            item = evidence.setdefault(code, _new_item())
            item["receipt_ids"].add(str(receipt_id))
            if outlet:
                item["outlets"].add(outlet)
            item["methods"].add("ner_place")
            # a NER place is location evidence — verify-grade by construction
            item["non_proxy_receipt_ids"].add(str(receipt_id))
            if outlet:
                item["non_proxy_outlets"].add(outlet)

    candidates = []
    any_proxy_suppressed = False
    for country, item in evidence.items():
        receipt_count = len(item["receipt_ids"])
        outlet_count = len(item["outlets"])
        non_proxy_receipt_count = len(item["non_proxy_receipt_ids"])
        non_proxy_outlet_count = len(item["non_proxy_outlets"])
        is_verified = (
            non_proxy_receipt_count >= minimum_receipts
            and non_proxy_outlet_count >= minimum_outlets
        )
        # would the OLD (proxy-blind) bar have verified this country?
        person_proxy_suppressed = (
            not is_verified
            and "person_proxy" in item["methods"]
            and receipt_count >= minimum_receipts
            and outlet_count >= minimum_outlets
        )
        any_proxy_suppressed = any_proxy_suppressed or person_proxy_suppressed
        candidates.append({
            "country": country,
            "receipt_count": receipt_count,
            "outlet_count": outlet_count,
            "non_proxy_receipt_count": non_proxy_receipt_count,
            "non_proxy_outlet_count": non_proxy_outlet_count,
            "methods": sorted(item["methods"]),
            "person_proxy_suppressed": person_proxy_suppressed,
            "status": "verified" if is_verified else "candidate",
        })
    candidates.sort(
        key=lambda row: (-row["receipt_count"], -row["outlet_count"], row["country"]),
    )
    # #238 dominance cap (measured, 2026-07-16 post-fix remeasure §Simulation:
    # 66.7%/32.3% -> 86.7%/41.9%, above baseline on both axes): the recall
    # fixes exposed cluster SIDE-MENTIONS clearing the low 2-receipt/2-outlet
    # bar next to a dominant real subject. A verified country must hold
    # >= 1/3 of the leading verified country's receipts; the verified set is
    # capped at 2, ordered by receipts. Capped countries stay visible as
    # candidates with dominance_capped=true + a reason code — never silently
    # dropped (the no-silent-filtering guardrail).
    verified_rows = [row for row in candidates if row["status"] == "verified"]
    any_dominance_capped = False
    if len(verified_rows) > 1:
        lead_receipts = verified_rows[0]["receipt_count"]
        kept: list[dict] = []
        for row in verified_rows:
            if len(kept) < 2 and row["receipt_count"] * 3 >= lead_receipts:
                kept.append(row)
            else:
                row["status"] = "candidate"
                row["dominance_capped"] = True
                any_dominance_capped = True
        verified_rows = kept
    verified = [row["country"] for row in verified_rows]
    if verified:
        status = "verified"
        reasons: list[str] = []
    elif candidates:
        status = "partial"
        reasons = ["subject_geography_not_independently_corroborated"]
    else:
        status = "unavailable"
        reasons = ["no_explicit_subject_geography_in_receipts"]
    if any_proxy_suppressed:
        reasons.append("person_proxy_evidence_demoted")
    if any_dominance_capped:
        reasons.append("subject_geography_dominance_capped")
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
