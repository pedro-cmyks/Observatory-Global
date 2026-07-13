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
                        "source": "Reuters", "date": "2026-07-08", "url": None}
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
