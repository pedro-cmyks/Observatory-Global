"""Typed SUBJECTS — the #176 reframe.

The entity panel used to ask "is this a person?" and discard everything else,
so "El Niño" (a climate pattern), "República Dominicana" (a country in
Spanish), and "America Latin" (a truncated GDELT region) either vanished or
masqueraded as people. The honest model is a *subject* with a TYPE — a person
is one type; a place, an organization, a group, and an event are others.

``classify_subject`` assigns a product type. When NER gave the entity a label
(spaCy PERSON/ORG/GPE/…) we trust it. When the name comes untyped from GDELT
we infer from a small typed gazetteer that REPURPOSES the old reject-lists as
a typer (geo names → place, climate patterns → event, teams/institutions →
organization) before falling back to the person validator. Nothing relevant
is thrown away: it is re-typed.

``build_key_subjects`` types a batch of aggregated entity rows, drops
unclassifiable noise, applies the same syndication-resistant ranking as the
person panel (so a republished wire story can't lead), and flags GDELT-sourced
subjects as ``unverified``.
"""
from __future__ import annotations

from app.utils import _GEO_NAME_BLOCKLIST, _is_valid_person

# spaCy NER label -> product subject type. Labels not listed (DATE, MONEY,
# CARDINAL, …) are uninteresting as subjects and map to None (dropped).
_SPACY_TYPE_MAP: dict[str, str] = {
    "PERSON": "person",
    "ORG": "organization",
    "NORP": "group",          # nationalities / religious / political groups
    "GPE": "place",           # countries, cities, states
    "LOC": "place",           # non-GPE locations (mountains, water bodies)
    "FAC": "place",           # facilities (airports, bridges)
    "EVENT": "event",         # named events / phenomena (El Niño, summits)
}

# Typed gazetteer for UNTYPED (GDELT) names. Exact full-name match only — never
# substring — so a person named "Israel" is not mistaken for the place.
_EVENT_NAMES: frozenset[str] = frozenset({
    "el niño", "la niña", "el nino", "la nina",
})
_ORG_NAMES: frozenset[str] = frozenset({
    "bafana bafana", "naciones unidas", "united nations", "union europea",
    "unión europea", "european union", "african union", "union africana",
    "estado islamico", "estado islámico", "islamic state",
})
_PLACE_NAMES: frozenset[str] = frozenset({
    "america latina", "america latin", "latina america", "latin america",
    "estados unidos", "reino unido", "reino saudita", "oriente medio",
    "medio oriente", "corea del norte", "corea del sur", "arabia saudita",
    "emiratos arabes", "casa blanca", "nueva york", "nueva delhi",
    "ciudad de mexico", "ciudad de méxico", "sudafrica", "sudáfrica",
    "republica dominicana", "república dominicana",
})


def classify_subject(name: str, ner_type: str | None = None) -> str | None:
    """Return a product subject type for ``name``, or None if it is not a
    surfaceable subject. Trusts ``ner_type`` (spaCy label) when present."""
    if not name:
        return None
    if ner_type:
        return _SPACY_TYPE_MAP.get(ner_type)
    lower = name.lower().strip()
    if lower in _EVENT_NAMES:
        return "event"
    if lower in _ORG_NAMES:
        return "organization"
    if lower in _PLACE_NAMES or lower in _GEO_NAME_BLOCKLIST:
        return "place"
    if _is_valid_person(name):
        return "person"
    return None


def merge_entity_rows(ner_rows, gdelt_rows) -> list:
    """Merge NER-typed entity rows with the untyped GDELT person rows.

    NER (spaCy) carries a real type, so it wins: the first NER row per name
    (case-insensitive; SQL orders by signal_count DESC, so that's the dominant
    type) is kept, and GDELT rows are appended only for names NER never saw —
    flagged untyped (``ner_type`` None) so ``classify_subject`` infers them and
    ``build_key_subjects`` marks them unverified."""
    seen: set[str] = set()
    merged: list = []
    for r in ner_rows:
        name = (r.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(r)
    for r in gdelt_rows:
        name = (r.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(r)
    return merged


def build_key_subjects(rows, *, limit: int = 8, min_headlines: int = 2) -> list:
    """Type, filter, and rank aggregated entity rows into typed subjects.

    ``rows`` are dicts carrying ``name`` and optionally ``ner_type``, plus the
    ranking columns ``signal_count`` / ``distinct_outlets`` /
    ``distinct_headlines``. Ranking is syndication-resistant (distinct stories,
    then outlets, then raw mentions) with a corroboration floor that falls back
    so a low-coverage panel is never blanked. Subjects with no NER type (i.e.
    inferred from the GDELT array) are flagged ``unverified``."""
    typed = []
    for r in rows:
        subject_type = classify_subject(r.get("name", ""), r.get("ner_type"))
        if subject_type is None:
            continue
        typed.append({
            "name": r["name"],
            "type": subject_type,
            "signal_count": int(r.get("signal_count") or 0),
            "distinct_outlets": int(r.get("distinct_outlets") or 1),
            "distinct_headlines": int(r.get("distinct_headlines") or 1),
            "unverified": r.get("ner_type") is None,
        })

    corroborated = [s for s in typed if s["distinct_headlines"] >= min_headlines]
    pool = corroborated or typed  # fallback: never blank a populated panel
    pool.sort(
        key=lambda s: (s["distinct_headlines"], s["distinct_outlets"], s["signal_count"]),
        reverse=True,
    )
    return pool[:limit]
