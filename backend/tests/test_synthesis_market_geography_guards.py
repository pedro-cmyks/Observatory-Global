"""X3 (vagón veracidad 2026-08-13) — two synthesis-honesty guards, both pure.

Both defects come from the SAME hole: the mini-article's prose is generated,
and the only deterministic check after the pass was the measured-tension guard.
Everything else the model wrote about the world was taken on trust.

(A) MARKET DIRECTION WITHOUT A RECEIPT — veracity scorecard claim 6, the ONLY
    place in the 12-claim set where Atlas asserted the OPPOSITE of the
    measurable: the Colombia edition's prose said Colombian stocks were rising
    while the served market receipt measured COLCAP -0.51% (Investing.com
    confirmed shares FELL after the quake). A synthesis narrative arc
    ("aid + resilience" -> optimism) inventing a market direction.

(B) CAPITAL-AS-PROXY GEOGRAPHY — scorecard claim 1: one tester read
    "epicenter near Bogotá" while another read the correct Chocó variant. The
    epicenter was San José del Palmar, Chocó, ~240 km WEST of Bogotá (USGS).
    No code maps a country to its capital: the city entered through the
    generative lede, which had no city-vs-receipt check.

The discipline follows apply_tension_guard exactly: lexical, conservative,
never drops the finding, and the marker is the same "reported (uncorroborated)"
clause the reader already knows.
"""
import pytest

from app.services import publication_synthesis as dossier


def _pin(label, items=None, strings=None, **kw):
    return dossier.SynthPin(
        label=label,
        evidence_items=[dossier.SynthEvidenceItem(**it) for it in (items or [])],
        evidence=strings or [],
        **kw,
    )


def _mkt(**kw):
    base = {"symbol": "COLCAP.CL", "label": "COLCAP index", "asset_class": "equity-index",
            "role": "index", "country_code": "CO", "last_close": 1712.4,
            "last_close_at": "2026-08-12", "change_pct": -0.51}
    return dossier.SynthMarketReceipt(**{**base, **kw})


# ── (A) market direction ─────────────────────────────────────────────────────

# THE WITNESS. Prose asserting the rise; the served receipt measures the fall.
_FELL = _mkt()
_ROSE = _mkt(change_pct=+0.83)
_WITNESS_EN = ("Colombian stocks rose alongside the aid pledges, with Bancolombia "
               "and Ecopetrol advancing [1].")
_WITNESS_ES = "Las acciones colombianas cerraron al alza tras el terremoto [1]."


@pytest.mark.parametrize("text", [_WITNESS_EN, _WITNESS_ES])
def test_market_guard_downgrades_a_direction_the_receipt_contradicts(text):
    guarded, ledger = dossier.apply_market_direction_guard([text], [_FELL])

    assert len(ledger) == 1
    out = guarded[0]
    assert "reported (uncorroborated)" in out
    # the measured figure travels with the downgrade — the reader sees the receipt
    assert "COLCAP index" in out and "-0.51%" in out
    assert "2026-08-12" in out
    assert out.startswith(text[:30])
    assert out.endswith(".")
    assert ledger[0]["basis"] == "contradicted"
    assert ledger[0]["symbol"] == "COLCAP.CL"
    assert ledger[0]["claim"] == "up"


def test_market_guard_leaves_a_direction_the_receipt_corroborates():
    guarded, ledger = dossier.apply_market_direction_guard([_WITNESS_EN], [_ROSE])
    assert ledger == []
    assert guarded == [_WITNESS_EN]


def test_market_guard_downgrades_a_direction_with_no_market_receipt_at_all():
    guarded, ledger = dossier.apply_market_direction_guard([_WITNESS_EN], [])
    assert len(ledger) == 1
    assert ledger[0]["basis"] == "uncorroborated"
    assert "reported (uncorroborated)" in guarded[0]
    assert "no market receipt" in guarded[0]


def test_market_guard_leaves_a_direction_a_cited_headline_carries():
    # The press reported the move: the claim has a receipt, just not a measured
    # one. It stays, exactly as the tension guard leaves an attributed sentence.
    guarded, ledger = dossier.apply_market_direction_guard(
        [_WITNESS_EN], [],
        cited_headlines={1: "Colombian shares rally as aid pledges land — Reuters"},
    )
    assert ledger == []
    assert guarded == [_WITNESS_EN]


def test_market_guard_ignores_a_cited_headline_pointing_the_other_way():
    guarded, ledger = dossier.apply_market_direction_guard(
        [_WITNESS_EN], [], cited_headlines={1: "Colombian shares slide after the quake"},
    )
    assert len(ledger) == 1


def test_market_guard_ignores_movement_that_is_not_a_market():
    texts = ["The death toll rose to 224 as rescues continued [1].",
             "Aid pledges climbed past US$1 billion [2]."]
    assert dossier.apply_market_direction_guard(texts, [_FELL]) == (texts, [])


def test_market_guard_never_settles_a_currency_direction_from_a_quote():
    # An FX quote carries no declared convention (USD/COP down IS the peso up),
    # so a currency claim can never be corroborated OR contradicted by it —
    # it is uncorroborated, never "the opposite".
    fx = _mkt(symbol="COP=X", label="Colombian peso", asset_class="fx",
              role="currency", change_pct=-0.42)
    text = "The peso strengthened against the dollar after the aid announcement [1]."
    guarded, ledger = dossier.apply_market_direction_guard([text], [fx])
    assert len(ledger) == 1
    assert ledger[0]["basis"] == "uncorroborated"
    assert "the opposite" not in guarded[0]


def test_market_guard_never_settles_a_bond_direction_from_a_quote():
    rate = _mkt(symbol="CO10Y", label="Colombia 10-year", asset_class="rate",
                role=None, change_pct=+1.2)
    text = "Colombian bonds fell after the quake [1]."
    _guarded, ledger = dossier.apply_market_direction_guard([text], [rate])
    assert ledger and ledger[0]["basis"] == "uncorroborated"


def test_market_guard_reads_generic_markets_prose_as_equities():
    # "markets fell" is an equities claim in everyday prose; it must NOT be
    # corroborated by an unrelated instrument that happened to move that way.
    oil = _mkt(symbol="CL=F", label="Crude oil, front-month", asset_class="energy",
               role=None, country_code=None, change_pct=-0.62)
    text = "Markets fell in the hours after the quake [1]."
    assert dossier.apply_market_direction_guard([text], [_FELL]) == ([text], [])
    _guarded, ledger = dossier.apply_market_direction_guard([text], [oil])
    assert ledger and ledger[0]["basis"] == "uncorroborated"


def test_market_guard_leaves_a_sentence_that_names_both_directions():
    text = "Colombian stocks rose early before falling back by the close [1]."
    assert dossier.apply_market_direction_guard([text], [_FELL]) == ([text], [])


def test_market_guard_leaves_a_level_without_a_direction():
    text = "The dollar traded at 3,135 pesos on Wednesday [1]."
    assert dossier.apply_market_direction_guard([text], [_FELL]) == ([text], [])


def test_market_guard_is_a_noop_on_empty_prose():
    assert dossier.apply_market_direction_guard([], [_FELL]) == ([], [])


def test_market_guard_only_touches_the_offending_sentence_in_a_paragraph():
    para = ("Rescuers pulled a baby from the rubble in Cali [3]. "
            + _WITNESS_EN + " The toll reached 224 [2].")
    guarded, ledger = dossier.apply_market_direction_guard([para], [_FELL])
    assert len(ledger) == 1
    out = guarded[0]
    assert out.startswith("Rescuers pulled a baby from the rubble in Cali [3]. ")
    assert out.endswith("The toll reached 224 [2].")
    assert out.count("reported (uncorroborated)") == 1


def test_market_guard_headline_downgrade_is_terse():
    guarded, ledger = dossier.apply_market_direction_guard(
        ["Colombian Stocks Rally as Aid Lands"], [_FELL], terse=True)
    assert len(ledger) == 1
    assert guarded[0] == "Colombian Stocks Rally as Aid Lands (uncorroborated)"


def test_market_guard_matches_an_instrument_by_its_own_name():
    champ = _mkt(symbol="EC", label="Ecopetrol", asset_class="equity-single",
                 role="champion", change_pct=-1.4)
    text = "Ecopetrol climbed as the government pledged reconstruction spending [1]."
    _guarded, ledger = dossier.apply_market_direction_guard([text], [champ])
    assert ledger and ledger[0]["basis"] == "contradicted"
    assert ledger[0]["symbol"] == "EC"


def test_market_guard_ignores_an_instrument_with_no_measured_change():
    pending = _mkt(change_pct=None, last_close=None)
    _guarded, ledger = dossier.apply_market_direction_guard([_WITNESS_EN], [pending])
    # a pending price is not a measurement — the claim is uncorroborated, not contradicted
    assert ledger and ledger[0]["basis"] == "uncorroborated"


# ── (B) capital-as-proxy geography ───────────────────────────────────────────

_QUAKE_RECEIPTS = [
    "Rescataron con vida a un bebé entre los escombros en Cali tras el terremoto",
    "Death toll from Colombia earthquake rises to 224",
]


def test_geography_guard_replaces_the_invented_capital_with_the_country():
    texts = ["The magnitude 7.4 quake struck near Bogotá on Monday morning [1]."]
    guarded, ledger = dossier.apply_geography_guard(texts, _QUAKE_RECEIPTS)

    assert len(ledger) == 1
    assert guarded[0] == "The magnitude 7.4 quake struck in Colombia on Monday morning [1]."
    assert "Bogotá" not in guarded[0]
    assert ledger[0]["place"] == "Bogotá"
    assert ledger[0]["country_code"] == "CO"


def test_geography_guard_keeps_a_city_a_receipt_carries():
    texts = ["Rescuers pulled a six-month-old from the rubble in Cali [1]."]
    assert dossier.apply_geography_guard(texts, _QUAKE_RECEIPTS) == (texts, [])


@pytest.mark.parametrize("prose_place,receipt", [
    ("Chocó", "Terremoto de 7.4 en Colombia tuvo epicentro en Choco"),   # prose accented
    ("Galati", "Dronă prăbușită pe un bloc în Galați"),                  # receipt accented
])
def test_geography_guard_folds_accents_when_checking_the_receipts(prose_place, receipt):
    texts = [f"The strike hit in {prose_place} [1]."]
    assert dossier.apply_geography_guard(texts, [receipt]) == (texts, [])


def test_geography_guard_leaves_a_country_named_directly():
    texts = ["The quake struck in Colombia on Monday [1]."]
    assert dossier.apply_geography_guard(texts, _QUAKE_RECEIPTS) == (texts, [])


def test_geography_guard_leaves_a_place_it_cannot_resolve():
    # San José del Palmar is below the gazetteer's 15k floor: unresolvable, so the
    # guard says nothing rather than guessing (and NEVER falls back to the "San
    # José" prefix, which would file a Chocó town in Costa Rica).
    texts = ["The epicenter sat near San José del Palmar [1]."]
    guarded, ledger = dossier.apply_geography_guard(texts, _QUAKE_RECEIPTS)
    assert (guarded, ledger) == (texts, [])


def test_geography_guard_handles_the_spanish_preposition():
    texts = ["El epicentro se ubicó cerca de Bogotá [1]."]
    guarded, ledger = dossier.apply_geography_guard(texts, _QUAKE_RECEIPTS)
    assert guarded[0] == "El epicentro se ubicó en Colombia [1]."
    assert len(ledger) == 1


def test_geography_guard_carries_the_article_for_the_united_states():
    texts = ["The announcement was made in Washington on Tuesday [1]."]
    guarded, ledger = dossier.apply_geography_guard(texts, ["Colombia quake aid pledged"])
    assert guarded[0] == "The announcement was made in the United States on Tuesday [1]."
    assert ledger[0]["country_code"] == "US"


def test_geography_guard_leaves_no_orphan_on_a_washington_dc_rewrite():
    texts = ["The pledge was announced in Washington, D.C. on Tuesday [1]."]
    guarded, ledger = dossier.apply_geography_guard(texts, ["Colombia quake aid pledged"])
    assert guarded[0] == "The pledge was announced in the United States on Tuesday [1]."
    assert len(ledger) == 1


def test_geography_guard_is_a_noop_without_receipts():
    # With no receipt corpus there is nothing to check against; the guard refuses
    # to rewrite geography it cannot judge.
    texts = ["The quake struck near Bogotá [1]."]
    assert dossier.apply_geography_guard(texts, []) == (texts, [])


def test_geography_guard_only_touches_the_unbacked_place():
    para = ("Rescuers worked in Cali through the night [1]. "
            "Officials briefed reporters near Bogotá [2].")
    guarded, ledger = dossier.apply_geography_guard([para], _QUAKE_RECEIPTS)
    assert len(ledger) == 1
    assert guarded[0] == ("Rescuers worked in Cali through the night [1]. "
                          "Officials briefed reporters in Colombia [2].")


# ── wiring: both guards run on the generated article ─────────────────────────

class _FakeInsight:
    def __init__(self, payload):
        self.payload = payload

    async def __call__(self, system, user, **kw):
        return self.payload, "deepseek", None, None


@pytest.mark.asyncio
async def test_synthesized_article_is_guarded_end_to_end(monkeypatch):
    payload = (
        '{"headline": "Colombian Stocks Rally After Quake",'
        ' "lede": "A magnitude 7.4 quake struck near Bogotá on Monday, killing 224 [1].",'
        ' "body": ["Colombian stocks rose alongside the aid pledges [1]."],'
        ' "unknowns": ["The full toll is unknown."]}'
    )
    monkeypatch.setattr(dossier, "generate_insight", _FakeInsight(payload))

    req = dossier.SynthesizeRequest(
        title="Earthquake in Colombia",
        pins=[_pin("Earthquake in Colombia", items=[
            {"headline": "Death toll from Colombia earthquake rises to 224",
             "source": "Gulf News", "date": "2026-08-12"},
        ])],
        markets=[_FELL],
    )
    out = await dossier.synthesize_publication_article(req)

    # (B) the invented capital is gone from BOTH the lede and the ledger
    assert "Bogotá" not in out["lede"]
    assert "in Colombia" in out["lede"]
    assert out["geography_downgrades"] and out["geography_downgrades"][0]["place"] == "Bogotá"
    # (A) the market direction is downgraded against the served receipt
    assert "reported (uncorroborated)" in out["body"][0]
    assert out["market_downgrades"][0]["basis"] == "contradicted"
    # and the headline variant cannot survive while its own lede was downgraded
    assert out["headline"].endswith("(uncorroborated)")
    # citations still resolve against the authoritative table
    assert [c["n"] for c in out["citations"]] == [1]


@pytest.mark.asyncio
async def test_healthy_prose_comes_back_untouched(monkeypatch):
    payload = (
        '{"headline": "Colombia Quake Toll Reaches 224",'
        ' "lede": "A magnitude 7.4 quake killed 224 people in Colombia [1].",'
        ' "body": ["Rescuers pulled a six-month-old from the rubble in Cali [1]."],'
        ' "unknowns": ["The final toll is unknown."]}'
    )
    monkeypatch.setattr(dossier, "generate_insight", _FakeInsight(payload))
    req = dossier.SynthesizeRequest(pins=[_pin("Earthquake in Colombia", items=[
        {"headline": "Rescataron a un bebé entre los escombros en Cali", "source": "Infobae"},
    ])], markets=[_FELL])

    out = await dossier.synthesize_publication_article(req)
    assert out["lede"] == "A magnitude 7.4 quake killed 224 people in Colombia [1]."
    assert out["body"] == ["Rescuers pulled a six-month-old from the rubble in Cali [1]."]
    assert out["headline"] == "Colombia Quake Toll Reaches 224"
    assert out["market_downgrades"] is None and out["geography_downgrades"] is None


# ── the served receipt: last SESSION, never the 30-day arc ───────────────────

def test_session_change_is_the_last_close_not_the_trailing_window():
    from app.services.market_receipts import session_change_pct
    # rose over 30 days, fell in the last session — the guard must read the fall
    assert session_change_pct([1600.0, 1700.0, 1721.2, 1712.4]) == -0.51
    assert session_change_pct([1712.4]) is None
    assert session_change_pct(None) is None
    assert session_change_pct([0.0, 5.0]) is None


def test_market_receipt_row_serializes_into_the_synth_shape():
    from app.services.market_receipts import market_receipt_from_row
    receipt = market_receipt_from_row({
        "symbol": "COLCAP.CL", "label": "COLCAP index", "asset_class": "equity-index",
        "role": "index", "country_code": "CO", "last_close": 1712.4,
        "last_close_at": "2026-08-12", "spark_30d": [1721.2, 1712.4],
    })
    assert receipt["change_pct"] == -0.51
    assert dossier.SynthMarketReceipt(**receipt).symbol == "COLCAP.CL"


def test_lead_payload_carries_the_market_receipts_into_the_request():
    from app.services.daily_publication import build_lead_synthesis_payload
    payload = build_lead_synthesis_payload(
        "Earthquake in Colombia",
        [{"headline": "Toll rises to 224", "source_name": "Gulf News"}],
        gaps=[],
        markets=[_FELL.model_dump()],
    )
    req = dossier.SynthesizeRequest(**payload)
    assert [m.symbol for m in req.markets] == ["COLCAP.CL"]
    # and the model is told what was measured (glass box before enforcement)
    assert "SERVED MARKET RECEIPTS" in dossier._synth_user(req)
    assert "-0.51% last session" in dossier._synth_user(req)
