"""Corroborate-v2 (spec 2026-08-11-corroborate-v2-design.md) — the five
pre-registered gate fixtures as unit tests, plus the math each one guards.

Each council witness gets a named test:
  G-STATE     ria+tass+rt corroborating each other = ONE government voice
  G-LOCALE    Indonesian "1.700" is 1700, not 1.7 (C-N17)
  G-TEMPLATE  a Mali ambush does not corroborate a Gaza strike (T-N19/DESK-N23)
  C-N22       a 6-week-old receipt cannot back a verdict dated today

Pure math only — no network, no DB. The pre-corroborate-v2 tests for this
module live in test_corroboration_lane.py (lane/degraded contract) and
test_dossier_corroboration.py (G2 independence + pin status).
"""
import datetime as dt


# ── Task 2 / G-STATE: independence counts VOICES ─────────────────────────────

def test_g_state_ria_interfax_tass_collapse_to_one_voice():
    """G-STATE (spec pre-registered): same state apparatus = ONE voice."""
    from app.services.corroboration import independence
    from app.services.source_tiers import ownership_group
    arts = [
        {"title": "Strikes hit depot in western region overnight", "outlet": "ria.ru"},
        {"title": "Military reports depot strike in western region", "outlet": "tass.com"},
        {"title": "Western region depot hit, officials say details", "outlet": "rt.com"},
        {"title": "Depot fire after overnight raid, residents flee", "outlet": "cnn.com"},
    ]
    out = independence(arts, group_fn=ownership_group)
    assert out["independent_outlets"] == 4          # outlets stay visible
    assert out["independent_voices"] == 2           # state:ru + cnn.com
    assert out["state_collapsed"] == 2              # 3 state outlets -> 1 voice
    groups = {c["outlet"]: c.get("ownership_group") for c in out["citations"]}
    assert groups["ria.ru"] == "state:ru" and groups["cnn.com"] is None


def test_independence_without_group_fn_backward_compatible():
    from app.services.corroboration import independence
    arts = [{"title": "A story about x y z", "outlet": "a.com"},
            {"title": "Different account of x", "outlet": "b.com"}]
    out = independence(arts)
    assert out["independent_voices"] == out["independent_outlets"] == 2


def test_pin_status_counts_voices_and_names_collapse():
    from app.services.corroboration import pin_status
    status, note = pin_status(2, True, outlets=4, state_collapsed=2)
    assert status == "unverified"       # 2 voices < 3, even though 4 outlets
    assert "state" in note
    status, _ = pin_status(3, True, outlets=3, state_collapsed=0)
    assert status == "established"


# ── Task 3 / G-LOCALE: numerals parse under the source language ──────────────

def test_g_locale_indonesian_dot_grouping():
    """G-LOCALE (spec): '1.700' in a comma-decimal locale is 1700, not 1.7."""
    from app.services.corroboration import extract_figure
    assert extract_figure("1.700 orang tewas akibat gempa", lang="id") == 1700.0
    assert extract_figure("1.700 muertos según el gobierno", lang="es") == 1700.0


def test_extract_figure_unambiguous_grouping_any_lang():
    from app.services.corroboration import extract_figure
    assert extract_figure("1.234.567 affected") == 1234567.0     # two dot groups
    assert extract_figure("1.234.567,89 total", lang="de") == 1234567.89
    assert extract_figure("1,234,567.89 total") == 1234567.89


def test_extract_figure_decimal_preserved():
    from app.services.corroboration import extract_figure
    assert extract_figure("magnitude 7.6 earthquake") == 7.6            # en default
    assert extract_figure("magnitud 7,6 del sismo", lang="es") == 7.6   # comma decimal
    assert extract_figure("1.700 dead") == 1.7   # lang unknown -> conservative, unchanged


def test_g_locale_relation_no_longer_inverts():
    """The C-N17 witness: same toll in two locales must corroborate."""
    from app.services.corroboration import classify_relation
    claim_terms = ["earthquake", "sulawesi", "dead", "1700"]
    claim_figure = 1700.0
    rel = classify_relation(
        claim_terms, claim_figure,
        "Gempa Sulawesi: 1.700 orang tewas, ribuan mengungsi",
        candidate_lang="id")
    assert rel != "contradicts"


# ── Task 4 / G-TEMPLATE: casualty boilerplate is not an event ────────────────

def test_g_template_mali_does_not_corroborate_gaza():
    """G-TEMPLATE (spec): same casualty template, disjoint entities."""
    from app.services.corroboration import classify_relation, extract_claim_terms
    claim = extract_claim_terms("Israeli strike kills 12 in Gaza refugee camp")
    rel = classify_relation(
        claim["terms"], 12.0,
        "Ambush kills 12 soldiers in northern Mali",
        similarity=0.87)          # template shapes embed close — the witness
    assert rel == "template_match"


def test_template_guard_spares_true_same_event():
    from app.services.corroboration import classify_relation, extract_claim_terms
    claim = extract_claim_terms("Israeli strike kills 12 in Gaza refugee camp")
    rel = classify_relation(
        claim["terms"], 12.0,
        "Gaza refugee camp hit by Israeli strike, 12 dead")
    assert rel == "corroborates"


def test_template_guard_exempts_cross_script_semantic():
    """Cross-language TRUE matches share zero Latin tokens — the semantic
    lane stays alive across scripts (anchor requirement is lexical)."""
    from app.services.corroboration import classify_relation, extract_claim_terms
    claim = extract_claim_terms("Israeli strike kills 12 in Gaza refugee camp")
    rel = classify_relation(
        claim["terms"], None,
        "غارة إسرائيلية تقتل 12 في مخيم للاجئين بغزة",
        similarity=0.90)
    assert rel == "corroborates"


def test_citation_verdict_excludes_template_matches():
    from app.services.corroboration import citation_verdict
    matches = [
        {"relation": "corroborates", "official": False},
        {"relation": "template_match", "official": True},
    ]
    v = citation_verdict(matches)
    assert v["corroborating"] == 1
    assert v["template_matches"] == 1
    assert "template" in v["note"]


# ── Task 5 / C-N22: a six-week-old receipt cannot back today ─────────────────

def test_aged_receipts_marked_and_not_counted():
    """C-N22 (spec R3): a 6-week-old receipt cannot back a verdict dated today."""
    from app.services.corroboration import citation_verdict
    today = dt.date(2026, 8, 11)
    matches = [
        {"relation": "corroborates", "official": True, "date": "2026-06-28"},
        {"relation": "corroborates", "official": False, "date": "2026-08-10"},
        {"relation": "corroborates", "official": False, "date": "20260809T120000Z"},
        {"relation": "corroborates", "official": False, "date": None},
    ]
    v = citation_verdict(matches, today=today)
    assert v["corroborating"] == 3          # dateless is NOT aged (can't claim)
    assert v["aged"] == 1
    assert matches[0]["aged"] is True and matches[1]["aged"] is False
    assert "aged" in v["note"]


def test_all_aged_means_uncorroborated_today():
    from app.services.corroboration import citation_verdict
    today = dt.date(2026, 8, 11)
    v = citation_verdict(
        [{"relation": "corroborates", "official": False, "date": "2026-06-01"}],
        today=today)
    assert v["status"] == "uncorroborated"
    assert v["aged"] == 1


def test_template_matches_visible_in_payload():
    """Spec F2: 'visible, never counted' — the payload must carry the rows
    the guard set aside, not vanish them (they appear in no other list)."""
    import asyncio
    from app.services.corroboration import corroborate_claim

    async def fake_doc20(_query, **_kw):
        return {"status": "down", "articles": []}

    class _FakeConn:
        async def fetch(self, *_a):
            return []

    async def fake_hot(_conn, _vec, _hours):
        # The T-N19 witness lives in the semantic lane: template shapes
        # embed close (0.87) while sharing zero event anchors.
        return [{"headline": "Ambush kills 12 soldiers in northern Mali",
                 "source_name": "x.example", "source_url": "https://x/1",
                 "country_code": "ML", "timestamp": "2026-08-11T00:00:00Z",
                 "similarity": 0.87, "source_lang": "en"}]

    res = asyncio.run(corroborate_claim(
        headline="Israeli strike kills 12 in Gaza refugee camp",
        doc20_fetch=fake_doc20,
        conn=_FakeConn(),
        embed_fn=lambda _t: [0.0] * 8,
        hot_fetch=fake_hot))
    assert [m["snippet"] for m in res["template_matches"]] == [
        "Ambush kills 12 soldiers in northern Mali"]
    assert res["verdict"]["template_matches"] == 1
    assert all(m["relation"] != "template_match"
               for lst in ("corroborating", "contradicting", "context")
               for m in res[lst])
