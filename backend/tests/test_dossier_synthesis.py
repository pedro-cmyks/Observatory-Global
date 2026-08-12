"""P0.6a publishable mini-article synthesis — pure-helper tests.

The article contract: numbered receipts [1..N] built server-side from the
request (authoritative), the model cites [n] inline, the server resolves the
markers back against its own table — an invented citation can never enter the
response.
"""
from app.services import publication_synthesis as dossier


def _pin(label, items=None, strings=None, **kw):
    return dossier.SynthPin(
        label=label,
        evidence_items=[dossier.SynthEvidenceItem(**it) for it in (items or [])],
        evidence=strings or [],
        **kw,
    )


# ── citation table ─────────────────────────────────────────────────────────────

def test_citation_table_numbers_globally_across_pins():
    req = dossier.SynthesizeRequest(pins=[
        _pin("A", items=[{"headline": "h1", "source": "Reuters", "date": "2026-07-08", "url": "http://x/1"},
                         {"headline": "h2"}]),
        _pin("B", items=[{"headline": "h3", "source": "AP"}]),
    ])
    table = dossier._citation_table(req)
    assert [r["n"] for r in table] == [1, 2, 3]
    assert table[0]["pin"] == "A" and table[2]["pin"] == "B"
    assert table[0]["url"] == "http://x/1"
    assert table[1]["source"] is None


def test_citation_table_parses_legacy_folded_strings():
    req = dossier.SynthesizeRequest(pins=[
        _pin("A", strings=["Trump orders cutoff — Reuters, 2026-07-08",
                           "Undated claim — Digi24",
                           "Bare headline"]),
    ])
    table = dossier._citation_table(req)
    assert table[0] == {"n": 1, "pin": "A", "pin_i": 0, "headline": "Trump orders cutoff",
                        "source": "Reuters", "date": "2026-07-08", "url": None,
                        "is_state_media": False}
    # "— Digi24" has no date → the legacy regex requires a date; kept whole.
    assert table[1]["headline"] == "Undated claim — Digi24"
    assert table[2]["headline"] == "Bare headline" and table[2]["date"] is None


def test_citation_table_duplicate_pin_labels_stay_separate():
    req = dossier.SynthesizeRequest(pins=[
        _pin("Same", items=[{"headline": "a"}]),
        _pin("Same", items=[{"headline": "b"}]),
    ])
    table = dossier._citation_table(req)
    assert [(r["n"], r["pin_i"]) for r in table] == [(1, 0), (2, 1)]


def test_citation_table_does_not_silently_cap_frozen_receipts():
    req = dossier.SynthesizeRequest(pins=[
        _pin("A", items=[{"headline": f"receipt-{i}"} for i in range(9)]),
    ])

    table = dossier._citation_table(req)

    assert len(table) == 9
    assert table[-1]["headline"] == "receipt-8"


# ── prompt rendering ───────────────────────────────────────────────────────────

def test_synth_user_numbers_evidence_and_flags_metadata_only():
    req = dossier.SynthesizeRequest(
        title="NATO-Ankara",
        pins=[
            _pin("Summit", items=[{"headline": "Erdogan hosts summit", "source": "AA", "date": "2026-07-07"}]),
            _pin("Ghost pin"),  # no evidence at all
        ],
    )
    out = dossier._synth_user(req)
    assert "[1] Erdogan hosts summit — AA, 2026-07-07" in out
    assert "metadata only — no frozen evidence captured" in out
    assert "cite as [n]" in out


def test_synth_system_carries_article_and_receipt_rules():
    s = dossier._SYNTH_SYSTEM
    assert "ARTICLE FORM WITH RECEIPTS" in s
    assert "[n]" in s
    assert "UNKNOWNS" in s
    assert "coverage lens" in s
    assert '"lede"' in s and '"body"' in s and '"unknowns"' in s
    # Frank-v2 glass-box rules survive the rewrite.
    assert "TEXT MENTIONS OVERRIDE" in s
    assert "GLASS BOX" in s
    assert "COVERAGE CONTEXT" in s
    assert "YYYY-MM-DD" in s
    # Council R3 P0: state media is never presented as neutral.
    assert "STATE MEDIA IS NEVER NEUTRAL" in s
    assert "[STATE MEDIA]" in s


def test_synth_user_tags_state_media_evidence_lines():
    # The state-media flag must reach the model on the evidence line so it can
    # attribute the claim instead of stating it as neutral fact (R3 P0).
    req = dossier.SynthesizeRequest(pins=[_pin("Drones", items=[
        {"headline": "381 drones destroyed", "source": "russian.rt.com",
         "date": "2026-07-20", "url": "http://rt/1", "is_state_media": True},
        {"headline": "Strike confirmed", "source": "reuters.com",
         "date": "2026-07-20", "url": "http://r/2"},
    ])])
    out = dossier._synth_user(req)
    assert "[1] 381 drones destroyed — russian.rt.com, 2026-07-20 [STATE MEDIA]" in out
    assert "[2] Strike confirmed — reuters.com, 2026-07-20" in out
    assert "[2] Strike confirmed — reuters.com, 2026-07-20 [STATE MEDIA]" not in out


def test_citation_table_carries_state_media_flag():
    req = dossier.SynthesizeRequest(pins=[_pin("A", items=[
        {"headline": "h1", "source": "rt.com", "is_state_media": True},
        {"headline": "h2", "source": "ap.org"},
    ])])
    table = dossier._citation_table(req)
    assert table[0]["is_state_media"] is True
    assert table[1]["is_state_media"] is False


def test_resolve_citations_carries_state_media_flag():
    table = [
        {"n": 1, "pin": "A", "pin_i": 0, "headline": "h1", "source": "rt.com",
         "date": None, "url": "http://rt/1", "is_state_media": True},
        {"n": 2, "pin": "A", "pin_i": 0, "headline": "h2", "source": "ap.org",
         "date": None, "url": "http://ap/2", "is_state_media": False},
    ]
    cites = dossier._resolve_citations(["lede [1] and [2]."], table)
    by_n = {c["n"]: c for c in cites}
    assert by_n[1]["is_state_media"] is True
    assert by_n[2]["is_state_media"] is False


# ── article parsing ────────────────────────────────────────────────────────────

def test_as_paragraphs_accepts_list_and_string():
    assert dossier._as_paragraphs(["one", " two ", ""]) == ["one", "two"]
    assert dossier._as_paragraphs("p1\n\np2") == ["p1", "p2"]
    assert dossier._as_paragraphs("- a\n- b") == ["a", "b"]
    assert dossier._as_paragraphs(None) is None
    assert dossier._as_paragraphs([]) is None


def test_resolve_citations_orders_dedupes_and_drops_out_of_range():
    table = [
        {"n": 1, "pin": "A", "pin_i": 0, "headline": "h1", "source": "S1", "date": "2026-07-08", "url": None},
        {"n": 2, "pin": "B", "pin_i": 1, "headline": "h2", "source": None, "date": None, "url": "http://x"},
    ]
    cites = dossier._resolve_citations(
        ["lede cites [2].", "body cites [1][2] and invents [7]."], table)
    assert [c["n"] for c in cites] == [2, 1]   # first-appearance order
    assert cites[0]["url"] == "http://x"
    assert all(c["n"] != 7 for c in cites)     # invented receipt never enters


# ── measured cross-read tensions vs the synthesis prose ───────────────────────
# Frank test 2026-08-12 (break d.1, "the single most publishable finding in the
# whole run and the prose drops it"): the cross-read measured
#   c10 naharnet  "Russia has yet to officially comment on the agreement."
#   c1  algemeiner "Russia's Foreign Ministry said on Tuesday that a deal …
#                   would boost ties"
# and flagged them ⚠ POSSIBLE TENSION — yet the synthesis asserted flatly
# "Russia said the base deal will boost ties…". The report contradicted itself
# and only the buried section was right. The measured tension is now handed to
# the model AND enforced deterministically after the pass: a sentence that
# asserts one side of a flagged pair, unqualified, is downgraded in place.

_WITNESS = dossier.SynthTension(
    a_quote="Russia has yet to officially comment on the agreement.",
    a_outlet="naharnet.com",
    b_quote="Russia's Foreign Ministry said on Tuesday that a deal would boost ties",
    b_outlet="algemeiner.com",
    note="c10 asserts Russia has not yet officially commented, while c1 attributes a statement to Russia's Foreign Ministry.",
)


def test_tension_guard_downgrades_the_unqualified_assertion_witness():
    texts = ["Russia said the base deal will boost ties, and a source said some Russian forces will stay [1]."]
    guarded, downgrades = dossier.apply_tension_guard(texts, [_WITNESS])

    assert len(downgrades) == 1
    out = guarded[0]
    assert "reported (uncorroborated)" in out
    # the counter-quote travels with the downgrade — the reader sees the tension
    assert "Russia has yet to officially comment on the agreement" in out
    assert "naharnet.com" in out
    # grammatical: the marker lands before the sentence's terminal period, once
    assert out.endswith(".")
    assert out.count("reported (uncorroborated)") == 1
    assert out.startswith("Russia said the base deal will boost ties")
    assert downgrades[0]["counter_outlet"] == "naharnet.com"


def test_tension_guard_leaves_prose_that_already_carries_both_sides():
    texts = ["Russia's Foreign Ministry said the deal would boost ties, though Russia has yet to officially comment on the agreement [1]."]
    guarded, downgrades = dossier.apply_tension_guard(texts, [_WITNESS])
    assert downgrades == []
    assert guarded == texts


def test_tension_guard_leaves_an_already_attributed_or_hedged_sentence():
    for text in [
        "According to algemeiner.com, the base deal will boost ties [1].",
        "The base deal will reportedly boost ties [1].",
    ]:
        guarded, downgrades = dossier.apply_tension_guard([text], [_WITNESS])
        assert downgrades == [], text
        assert guarded == [text], text


def test_tension_guard_ignores_sentences_about_something_else():
    texts = ["Syria will assume control of civilian facilities at Hmeimim Airport [2]."]
    guarded, downgrades = dossier.apply_tension_guard(texts, [_WITNESS])
    assert downgrades == []
    assert guarded == texts


def test_tension_guard_is_a_noop_without_measured_tensions():
    texts = ["Russia said the base deal will boost ties [1]."]
    assert dossier.apply_tension_guard(texts, []) == (texts, [])


def test_tension_guard_only_touches_the_offending_sentence_in_a_paragraph():
    para = ("Syria and Russia reached an agreement on the bases [3]. "
            "Russia said the base deal will boost ties [1]. "
            "The transition runs three months [3].")
    guarded, downgrades = dossier.apply_tension_guard([para], [_WITNESS])
    assert len(downgrades) == 1
    out = guarded[0]
    assert out.startswith("Syria and Russia reached an agreement on the bases [3]. ")
    assert out.endswith("The transition runs three months [3].")
    assert "reported (uncorroborated)" in out


def test_synth_user_hands_the_measured_tensions_to_the_model():
    req = dossier.SynthesizeRequest(
        pins=[_pin("A", items=[{"headline": "h1"}])], tensions=[_WITNESS],
    )
    user = dossier._synth_user(req)
    assert "MEASURED CROSS-READ TENSIONS" in user
    assert "Russia has yet to officially comment" in user
    assert "naharnet.com" in user
    assert "TENSION" in dossier._SYNTH_SYSTEM.upper()
