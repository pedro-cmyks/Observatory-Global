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
