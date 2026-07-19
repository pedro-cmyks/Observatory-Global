"""#204: never serve a placeholder/failed thread label.

The thread TITLE was passed through verbatim, so DeepSeek's "(label failed)"
stub and other placeholders leaked to the Brief front page and the console.
`clean_thread_label` is the serving-layer choke point: a real label passes
through (HTML-unescaped); a placeholder falls back to a clean representative
evidence headline; if no clean headline exists, the generic fallback is used.
"""

from app.services.thread_intelligence import clean_thread_label


def _sig(headline: str) -> dict:
    return {"headline": headline}


def test_real_label_passes_through():
    assert (
        clean_thread_label("Ukraine War Updates", [_sig("anything")], "dynamic topic 1")
        == "Ukraine War Updates"
    )


def test_label_failed_stub_falls_back_to_headline():
    out = clean_thread_label(
        "(label failed)",
        [_sig("Khamenei rejects Trump ceasefire terms as talks collapse")],
        "dynamic topic 1309",
    )
    assert out == "Emerging: Khamenei rejects Trump ceasefire terms as talks collapse"


def test_empty_and_placeholder_labels_fall_back():
    sigs = [_sig("France to license Aster missile production for Ukraine")]
    expected = "Emerging: France to license Aster missile production for Ukraine"
    for placeholder in ("", "(no label)", "none", "NULL", "(label failed.)"):
        assert clean_thread_label(placeholder, sigs, "cluster 7") == expected


def test_none_label_falls_back():
    assert (
        clean_thread_label(None, [_sig("Denmark rejects Trump bid for Greenland")], "cluster 7")
        == "Emerging: Denmark rejects Trump bid for Greenland"
    )


def test_placeholder_skips_junk_headlines_to_first_clean_one():
    sigs = [_sig("Doc 12.Shtml"), _sig("5,250,037"), _sig("NATO summit opens in Ankara")]
    assert (
        clean_thread_label("(label failed)", sigs, "dynamic topic 42")
        == "Emerging: NATO summit opens in Ankara"
    )


def test_placeholder_with_no_clean_headline_uses_generic_fallback():
    sigs = [_sig("Doc 12.Shtml"), _sig("")]
    assert clean_thread_label("(label failed)", sigs, "dynamic topic 42") == "dynamic topic 42"


def test_placeholder_with_no_signals_uses_generic_fallback():
    assert clean_thread_label("(label failed)", [], "cluster 99") == "cluster 99"


def test_real_label_is_html_unescaped():
    assert (
        clean_thread_label("Trump &amp; Meloni clash", [], "dynamic topic 1")
        == "Trump & Meloni clash"
    )


def test_long_headline_is_truncated():
    long_head = (
        "Coalition of the willing lines up a post-ceasefire force for Ukraine as the "
        "European Union haggles over a twenty-first sanctions package against Russia"
    )
    out = clean_thread_label("(label failed)", [_sig(long_head)], "dynamic topic 1")
    assert out.startswith("Emerging: Coalition of the willing")
    assert out.endswith("…")
    assert len(out) <= len("Emerging: ") + 90

# --- Lane A (2026-07-18) extensions: geo-prefixed receipt fallback, stale
# "Emerging:" refresh, and the untyped-foreign-headline rule ------------------

from app.services.thread_intelligence import _NO_CATEGORY  # noqa: E402


def test_placeholder_fallback_carries_dominant_geo():
    out = clean_thread_label(
        "(label failed)",
        [_sig("Caracas hospitals overwhelmed after quake")],
        "dynamic topic 9",
        country_codes=["VE", "CO"],
    )
    assert out == "Emerging (VE): Caracas hospitals overwhelmed after quake"


def test_stale_emerging_label_refreshes_from_current_receipts():
    # build_unified_topics persists "Emerging: <headline>" at creation time; the
    # serving guard refreshes it from the receipts actually in hand today.
    out = clean_thread_label(
        "Emerging: old frozen headline from creation night",
        [_sig("Peru election board orders partial recount")],
        "dynamic topic 12",
        country_codes=["PE"],
    )
    assert out == "Emerging (PE): Peru election board orders partial recount"


def test_stale_emerging_label_kept_when_no_receipts():
    # never degrade a receipt-derived label to a raw id
    stored = "Emerging: Peru election recount ordered"
    assert clean_thread_label(stored, [], "dynamic topic 12") == stored


def test_real_emerging_titled_label_passes_through():
    # a genuine title that merely starts with the word must NOT be rewritten
    label = "Emerging Markets Debt Crisis"
    assert (
        clean_thread_label(label, [_sig("some receipt")], "dynamic topic 3") == label
    )


def test_untyped_foreign_script_label_gets_receipt_fallback():
    # category served and NULL + non-Latin raw-headline label → neutral fallback
    out = clean_thread_label(
        "زلزال يضرب فنزويلا ويخلف مئات القتلى في كاراكاس",
        [_sig("Venezuela earthquake death toll rises")],
        "dynamic topic 77",
        country_codes=["VE"],
        category=None,
    )
    assert out == "Emerging (VE): Venezuela earthquake death toll rises"


def test_typed_foreign_script_label_is_served_untouched():
    label = "زلزال فنزويلا"
    out = clean_thread_label(
        label, [_sig("whatever")], "dynamic topic 77",
        category="natural-disaster",
    )
    assert out == label


def test_foreign_script_label_untouched_when_category_unknown():
    # emergent clusters never carry a category — the rule must stay off
    label = "地震で数百人が死亡"
    assert clean_thread_label(label, [_sig("x")], "cluster 5") == label
    assert (
        clean_thread_label(label, [_sig("x")], "cluster 5", category=_NO_CATEGORY)
        == label
    )


def test_latin_real_label_with_category_null_passes_through():
    # Spanish/French/etc. labels are Latin-script: never rewritten by the rule
    label = "Atentado a Ranucci en Roma"
    assert (
        clean_thread_label(label, [_sig("x")], "dynamic topic 8", category=None)
        == label
    )


# --- 2026-07-19: LLM-refusal PROSE is a placeholder, never a title ----------
# Live hole: prod /threads served "Unable to determine a single news cluster
# from these diverse headlines" at rank #8 — refusal prose is a labeler
# failure the fixed sentinel set cannot enumerate. Precision-first shape test:
# refusal stem at the START + a self-referential task word ANYWHERE.

_REFUSALS = [
    "Unable to determine a single news cluster from these diverse headlines",
    "Unable to determine a single event or majority cluster from these diverse headlines",
    "Cannot identify a coherent grouping from the provided headlines",
    "No single event connects these headlines",
    "I cannot determine a majority topic from these articles",
]


def test_llm_refusal_prose_falls_back_to_receipt():
    sigs = [_sig("Ebola outbreak spreads to third Congolese province")]
    for refusal in _REFUSALS:
        out = clean_thread_label(refusal, sigs, "dynamic topic 9")
        assert out == "Emerging: Ebola outbreak spreads to third Congolese province", refusal


def test_llm_refusal_without_receipt_uses_generic_fallback():
    for refusal in _REFUSALS:
        assert clean_thread_label(refusal, [], "dynamic topic 9") == "dynamic topic 9"


def test_headline_like_unable_label_is_not_a_refusal():
    # A real title can start with a refusal stem — without a self-referential
    # task word it must pass through untouched (precision-first).
    for real in (
        "Unable to determine cause of deadly blast, officials say",
        "Cannot afford rent: eviction crisis deepens in US cities",
    ):
        assert clean_thread_label(real, [_sig("x y z words")], "f") == real
