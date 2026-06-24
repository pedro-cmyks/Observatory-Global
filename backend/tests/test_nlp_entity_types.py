"""#176 — NER must keep EVENT entities so phenomena are typed at ingest.

The entity extractor kept only PERSON/ORG/NORP/FAC/GPE/LOC, so a climate
pattern like "El Niño" (spaCy label EVENT) was dropped at ingest and could only
ever reappear untyped via the GDELT persons array. Keeping EVENT lets the typed
SUBJECTS model surface phenomena as events from the NER source directly.
"""
from __future__ import annotations

from enrichment.nlp_pipeline import _extract_entities


class _Ent:
    def __init__(self, text, label):
        self.text = text
        self.label_ = label


class _Doc:
    def __init__(self, ents):
        self.ents = ents


def _fake_nlp(ents):
    return lambda _headline: _Doc(ents)


def test_event_entities_are_kept_and_typed():
    ents = [
        _Ent("Lula", "PERSON"),
        _Ent("El Niño", "EVENT"),     # climate phenomenon — must survive
        _Ent("Brazil", "GPE"),
        _Ent("2026", "DATE"),         # uninteresting type — dropped
    ]
    out = _extract_entities(_fake_nlp(ents), "headline text", None)
    types = {e["name"]: e["type"] for e in out}
    assert types == {"Lula": "PERSON", "El Niño": "EVENT", "Brazil": "GPE"}
