"""#176 reframe — typed SUBJECTS, not just persons.

Pedro: the panel asks "is this a person?" when it should ask "what TYPE of
subject is this?". A person is one type of subject; "El Niño" is a climate
*event* subject; "República Dominicana" is a *place*. The old gate threw those
away as non-persons; the typed model keeps them, labeled by type — so a
climate pattern surfaces as a climate subject instead of vanishing or
masquerading as a person.

classify_subject() assigns a product type, trusting NER's label when present
and otherwise inferring from a typed gazetteer (reusing the geo lexicon and
the old reject-lists as a TYPER). build_key_subjects() types, ranks
(syndication-resistant, person-gate only for persons), and returns a flat
typed list the frontend groups.
"""
from __future__ import annotations

import pytest

from app.services.subjects import classify_subject, build_key_subjects, merge_entity_rows


def test_merge_prefers_ner_typed_over_gdelt():
    ner = [{"name": "Gustavo Petro", "ner_type": "PERSON", "signal_count": 9,
            "distinct_outlets": 5, "distinct_headlines": 5}]
    gdelt = [{"name": "gustavo petro", "ner_type": None, "signal_count": 12,
              "distinct_outlets": 8, "distinct_headlines": 1},   # dup → dropped
             {"name": "Alvaro Uribe", "ner_type": None, "signal_count": 4,
              "distinct_outlets": 3, "distinct_headlines": 3}]
    merged = merge_entity_rows(ner, gdelt)
    names = [m["name"] for m in merged]
    assert "Gustavo Petro" in names and "Alvaro Uribe" in names
    assert "gustavo petro" not in names  # GDELT dup of the NER-typed name dropped
    petro = next(m for m in merged if m["name"] == "Gustavo Petro")
    assert petro["ner_type"] == "PERSON"  # NER row kept (typed)


def test_merge_keeps_first_ner_type_per_name():
    ner = [
        {"name": "Apple", "ner_type": "ORG", "signal_count": 9, "distinct_headlines": 5, "distinct_outlets": 5},
        {"name": "apple", "ner_type": "GPE", "signal_count": 2, "distinct_headlines": 1, "distinct_outlets": 1},
    ]
    merged = merge_entity_rows(ner, [])
    assert len(merged) == 1 and merged[0]["ner_type"] == "ORG"  # dominant (first) type


def test_merge_empty_ner_returns_gdelt_untyped():
    gdelt = [{"name": "Luis Diaz", "ner_type": None, "signal_count": 4,
              "distinct_outlets": 4, "distinct_headlines": 4}]
    assert merge_entity_rows([], gdelt) == gdelt


# ── classify_subject: NER-typed (trust spaCy's label) ──
@pytest.mark.parametrize("name,ner,expected", [
    ("Gustavo Petro", "PERSON", "person"),
    ("United Nations", "ORG", "organization"),
    ("Colombia", "GPE", "place"),
    ("Andes", "LOC", "place"),
    ("Pentagon", "FAC", "place"),
    ("Palestinians", "NORP", "group"),
    ("El Niño", "EVENT", "event"),
    ("2026", "DATE", None),          # uninteresting NER type → dropped
])
def test_classify_with_ner_type(name, ner, expected):
    assert classify_subject(name, ner_type=ner) == expected


# ── gazetteer OVERRIDES a NER mistype (2026-07-01, multilingual-NER noise fix) ──
@pytest.mark.parametrize("name,ner,expected", [
    ("England", "PERSON", "place"),        # NER mistype on sports headlines
    ("Brazil", "PERSON", "place"),
    ("LaLiga", "PERSON", "organization"),
    ("la liga", "PERSON", "organization"),
    ("el niño", "PERSON", "event"),
    # real people NOT in the gazetteer keep NER's type (override is exact-match only)
    ("H. Kane", "PERSON", "person"),
    ("Netanyahu", "PERSON", "person"),
    ("Gustavo Petro", "PERSON", "person"),
])
def test_gazetteer_overrides_ner_mistype(name, ner, expected):
    assert classify_subject(name, ner_type=ner) == expected


# ── classify_subject: untyped (GDELT) inference ──
@pytest.mark.parametrize("name,expected", [
    # places (the live leaks: español + truncated GDELT forms)
    ("republica dominicana", "place"),
    ("america latina", "place"),
    ("america latin", "place"),          # GDELT truncation
    ("saudi arabia", "place"),           # English geo blocklist
    ("estados unidos", "place"),
    ("corea del norte", "place"),
    # climate / nature → event
    ("el niño", "event"),
    ("la niña", "event"),
    # teams / institutions → organization
    ("bafana bafana", "organization"),
    ("naciones unidas", "organization"),
    # real people → person
    ("gustavo petro", "person"),
    ("luis diaz", "person"),
    # noise → dropped
    ("dar una patada", None),
    ("trump", None),                     # single token, unresolvable
])
def test_classify_untyped(name, expected):
    assert classify_subject(name) == expected


def _row(name, *, ner=None, headlines=2, outlets=2, signals=2):
    return {
        "name": name,
        "ner_type": ner,
        "distinct_headlines": headlines,
        "distinct_outlets": outlets,
        "signal_count": signals,
    }


def test_build_keeps_el_nino_as_event_not_discarded():
    rows = [
        _row("El Niño", ner="EVENT", headlines=3, outlets=5, signals=9),
        _row("Gustavo Petro", ner="PERSON", headlines=2, outlets=2, signals=4),
    ]
    out = build_key_subjects(rows)
    by_name = {s["name"]: s["type"] for s in out}
    assert by_name["El Niño"] == "event"          # kept, typed — not thrown away
    assert by_name["Gustavo Petro"] == "person"


def test_build_reclassifies_geo_leaks_as_place_not_person():
    rows = [
        _row("america latin", headlines=9, outlets=40, signals=99),   # GDELT untyped
        _row("republica dominicana", headlines=3, outlets=3, signals=5),
        _row("Luis Diaz", ner="PERSON", headlines=4, outlets=4, signals=6),
    ]
    out = build_key_subjects(rows)
    types = {s["name"]: s["type"] for s in out}
    assert types["america latin"] == "place"
    assert types["republica dominicana"] == "place"
    assert types["Luis Diaz"] == "person"
    # none of them is mislabeled "person"
    assert not any(s["type"] == "person" and "latin" in s["name"].lower() for s in out)


def test_build_drops_unclassifiable_noise():
    rows = [_row("dar una patada", headlines=5, outlets=5, signals=20)]
    assert build_key_subjects(rows) == []


def test_build_is_syndication_resistant_within_results():
    # Hockney: one obituary, 50 outlets, 1 headline. Local: 3 stories.
    rows = [
        _row("David Hockney", ner="PERSON", headlines=1, outlets=50, signals=50),
        _row("Dina Boluarte", ner="PERSON", headlines=3, outlets=3, signals=5),
    ]
    out = build_key_subjects(rows)
    assert [s["name"] for s in out] == ["Dina Boluarte"]


def test_build_marks_gdelt_sourced_as_unverified():
    rows = [
        _row("Gustavo Petro", ner="PERSON", headlines=2, outlets=2, signals=4),
        _row("luis diaz", ner=None, headlines=2, outlets=2, signals=4),  # GDELT untyped
    ]
    out = build_key_subjects(rows)
    flags = {s["name"]: s.get("unverified", False) for s in out}
    assert flags["Gustavo Petro"] is False       # NER-typed → verified
    assert flags["luis diaz"] is True            # GDELT-inferred → unverified
