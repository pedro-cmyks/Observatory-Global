"""F3a — body_mention basis (spec 2026-07-20 §6): the mention scan reads
fetched article bodies through the same _mention_terms contract as headlines."""
from __future__ import annotations

import re

from app.routers.dossier import ConnectionsRequest, _label_key_tokens, _mention_terms


def _body_tuple(text: str):
    low = text.lower()
    return (low, frozenset(re.split(r"[^\w]+", low)))


def test_request_accepts_optional_evidence_urls():
    req = ConnectionsRequest(topic_ids=["dynamic-topic-1"], evidence_urls={
        "dynamic-topic-1": ["https://x.com/a"]})
    assert req.evidence_urls["dynamic-topic-1"] == ["https://x.com/a"]
    # backward compatible: absent field defaults empty
    assert ConnectionsRequest(topic_ids=["t"]).evidence_urls == {}


def test_mention_terms_finds_deep_body_reference():
    # the paragraph-6 reference no headline carries: pin B's actor named deep
    # inside pin A's fetched body.
    body = _body_tuple(
        "Primer párrafo sobre la refinería. Segundo sobre logística. "
        "Al final, el financista Carlos Restrepo aparece vinculado al esquema "
        "de tarifas que investiga la fiscalía de Ankara.")
    label_tokens = _label_key_tokens("Ankara Tariff Scheme")
    terms = _mention_terms([body], label_tokens, ["carlos restrepo"])
    assert "carlos restrepo" in terms


def test_mention_terms_label_needs_two_tokens_in_body():
    body = _body_tuple("texto largo que menciona ankara una sola vez sin contexto")
    # only 1 of the 2+ label key-tokens present → no label match (generic word
    # can't fire alone), and no actor present either.
    terms = _mention_terms([body], _label_key_tokens("Ankara Tariff Scheme"), [])
    assert terms == []
