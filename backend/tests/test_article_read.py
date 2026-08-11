"""F2 AI-read — the quote gate is the whole point: hallucinated claims must be
unrepresentable. Spec 2026-07-20 §5 / decision 3."""
from __future__ import annotations

import pytest

from app.services import article_read as ar
from app.services import research_leads as rl

pytestmark = pytest.mark.asyncio

TEXT = (
    "El ministro anunció que la refinería de Bandar Abbas reanudó operaciones. "
    "Según fuentes navales, tres buques cambiaron su ruta por el estrecho. "
    "La OPEP redujo su pronóstico de demanda global por segunda vez."
)


# ── validate_reading (quote gate) ────────────────────────────────────────────

def test_quote_gate_keeps_verbatim_claim():
    parsed = {"claims": [{
        "text": "The refinery resumed operations.",
        "quote": "la refinería de Bandar Abbas reanudó operaciones",
        "attribution": "asserted",
    }]}
    r = ar.validate_reading(parsed, TEXT)
    assert len(r["claims"]) == 1 and r["dropped_claims"] == 0


def test_quote_gate_drops_paraphrased_quote():
    parsed = {"claims": [{
        "text": "Ships rerouted.",
        "quote": "tres buques fueron desviados del estrecho",   # paraphrase — not in text
        "attribution": "asserted",
    }]}
    r = ar.validate_reading(parsed, TEXT)
    assert r["claims"] == [] and r["dropped_claims"] == 1


def test_quote_gate_normalizes_whitespace_and_curly_quotes():
    parsed = {"claims": [{
        "text": "OPEC cut its forecast.",
        "quote": "La  OPEP redujo su pronóstico\nde demanda global",
        "attribution": "attributed", "attributed_to": "OPEC report",
    }]}
    r = ar.validate_reading(parsed, TEXT)
    assert len(r["claims"]) == 1
    assert r["claims"][0]["attributed_to"] == "OPEC report"


def test_quoteless_and_oversized_claims_drop():
    parsed = {"claims": [
        {"text": "No quote at all."},
        {"text": "Giant quote.", "quote": "x" * 400},
    ]}
    r = ar.validate_reading(parsed, TEXT)
    assert r["claims"] == [] and r["dropped_claims"] == 2


def test_attribution_defaults_to_asserted():
    parsed = {"claims": [{
        "text": "c", "quote": "Según fuentes navales", "attribution": "invented-kind",
    }]}
    r = ar.validate_reading(parsed, TEXT)
    assert r["claims"][0]["attribution"] == "asserted"
    assert r["claims"][0]["attributed_to"] is None


def test_actor_and_gap_caps():
    parsed = {
        "claims": [],
        "actors": [{"name": f"Actor Number {i}", "kind": "person", "role": "r"} for i in range(20)],
        "gaps": [f"gap {i}" for i in range(20)],
        "numbers": [{"value": "3", "what": "ships"}],
    }
    r = ar.validate_reading(parsed, TEXT)
    assert len(r["actors"]) == 10 and len(r["gaps"]) == 6 and len(r["numbers"]) == 1


def test_extract_json_repairs_truncated_output():
    # a max_tokens cutoff mid-claim: complete claims survive, the tail is lost.
    truncated = (
        '{"claims":[{"text":"c1","quote":"q1","attribution":"asserted"},'
        '{"text":"c2","quote":"q2","attribution":"asserted"},'
        '{"text":"c3","quote":"q3","attrib'
    )
    parsed = ar._extract_json(truncated)
    assert parsed is not None
    assert [c["text"] for c in parsed["claims"]] == ["c1", "c2"]


# ── read_articles cache path ─────────────────────────────────────────────────

async def test_read_articles_cache_first_never_calls_llm(monkeypatch):
    called = {"llm": 0}

    async def fake_cached(hashes):
        return {ar.url_hash("https://x.com/a"): {"claims": [], "actors": [], "model": "m"}}

    async def fake_insight(*a, **k):
        called["llm"] += 1
        return None, None, "err", None
    monkeypatch.setattr(ar, "_cached_readings", fake_cached)
    monkeypatch.setattr(ar, "generate_insight", fake_insight)
    out = await ar.read_articles(["https://x.com/a"])
    assert "https://x.com/a" in out and called["llm"] == 0


async def test_read_articles_absent_text_is_absent_entry(monkeypatch):
    async def fake_cached(hashes):
        return {}

    async def fake_texts(urls, cap_chars=6000):
        return {}   # nothing fetched → nothing to read
    monkeypatch.setattr(ar, "_cached_readings", fake_cached)
    monkeypatch.setattr(ar, "full_texts_for", fake_texts)
    assert await ar.read_articles(["https://x.com/a"]) == {}


# ── cross-read validation ────────────────────────────────────────────────────

def _readings_two():
    return {
        "https://x.com/a": {"claims": [{"text": "A1", "quote": "qa", "attribution": "asserted"}]},
        "https://x.com/b": {"claims": [{"text": "B1", "quote": "qb", "attribution": "attributed"}]},
    }


def test_cross_input_ids_and_table():
    user, table = ar.build_cross_input(_readings_two())
    assert set(table.keys()) == {"c1", "c2"}
    assert "[c1]" in user and "[c2]" in user and "quote:" in user


def test_validate_cross_drops_unknown_self_and_same_article():
    _, table = ar.build_cross_input(_readings_two())
    parsed = {"findings": [
        {"kind": "tension", "a": "c1", "b": "c2", "note": "differs"},
        {"kind": "tension", "a": "c1", "b": "c1", "note": "self"},
        {"kind": "tension", "a": "c1", "b": "c99", "note": "unknown"},
        {"kind": "invented", "a": "c1", "b": "c2", "note": "bad kind"},
    ]}
    out = ar.validate_cross(parsed, table)
    assert len(out) == 1 and out[0]["kind"] == "tension"
    assert out[0]["a"]["quote"] == "qa" and out[0]["b"]["quote"] == "qb"


async def test_cross_read_needs_two_claimful_articles(monkeypatch):
    async def fake_read(urls):
        return {"https://x.com/a": {"claims": [{"text": "t", "quote": "q"}]}}
    monkeypatch.setattr(ar, "read_articles", fake_read)
    out = await ar.cross_read(["https://x.com/a"])
    assert out["findings"] == [] and "fewer than two" in out["reason"]


# ── cross-read source independence (Council R3 P1) ───────────────────────────
# Syndicated wire copies (same story, different mastheads) must NOT count as
# mutual corroboration — that inflates confidence on the exact surface built to
# establish it. Reuses thread_ranking's masthead-strip + a content/outlet check.

def test_registrable_folds_subdomain_keeps_wire_family_distinct():
    assert ar._registrable("edition.cnn.com") == "cnn.com"
    assert ar._registrable("www.cnn.com") == "cnn.com"
    # AU wire family: distinct registrable domains — only wire_sig unifies them.
    assert ar._registrable("katherinetimes.com.au") == "katherinetimes.com.au"
    assert ar._registrable("katherinetimes.com.au") != ar._registrable("blayneychronicle.com.au")


def test_articles_independent_same_outlet():
    a = ar.source_signature("https://cnn.com/x", {"outlet": "cnn.com", "title": "One"})
    b = ar.source_signature("https://edition.cnn.com/y", {"outlet": "edition.cnn.com", "title": "Two"})
    indep, reason = ar.articles_independent(a, b)
    assert indep is False and reason == "same_outlet"


def test_articles_independent_same_wire_headline():
    a = ar.source_signature("https://katherinetimes.com.au/x",
                            {"outlet": "katherinetimes.com.au",
                             "title": "Refinery resumes operations | Katherine Times"})
    b = ar.source_signature("https://blayneychronicle.com.au/y",
                            {"outlet": "blayneychronicle.com.au",
                             "title": "Refinery resumes operations | Blayney Chronicle"})
    indep, reason = ar.articles_independent(a, b)
    assert indep is False and reason == "same_wire"


def test_articles_independent_same_content_hash_beats_distinct_outlets():
    a = ar.source_signature("https://a.com/x", {"outlet": "a.com", "title": "T1", "content_hash": "abc"})
    b = ar.source_signature("https://b.com/y", {"outlet": "b.com", "title": "T2", "content_hash": "abc"})
    indep, reason = ar.articles_independent(a, b)
    assert indep is False and reason == "same_wire"   # identical body = one wire copy


def test_articles_independent_cross_origin_is_true():
    a = ar.source_signature("https://cyprus-mail.com/x",
                            {"outlet": "cyprus-mail.com", "title": "16 wounded in strike", "content_hash": "h1"})
    b = ar.source_signature("https://xinhuanet.com/y",
                            {"outlet": "xinhuanet.com", "title": "Kyiv attack injures 13", "content_hash": "h2"})
    indep, reason = ar.articles_independent(a, b)
    assert indep is True and reason == "independent"


def _syndicated_readings_and_sources():
    readings = {
        "https://katherinetimes.com.au/x": {"claims": [{"text": "A1", "quote": "qa", "attribution": "asserted"}]},
        "https://blayneychronicle.com.au/y": {"claims": [{"text": "B1", "quote": "qb", "attribution": "asserted"}]},
    }
    sources = {
        "https://katherinetimes.com.au/x": {"outlet": "katherinetimes.com.au",
                                            "title": "Refinery resumes operations | Katherine Times"},
        "https://blayneychronicle.com.au/y": {"outlet": "blayneychronicle.com.au",
                                              "title": "Refinery resumes operations | Blayney Chronicle"},
    }
    return readings, sources


def test_validate_cross_downgrades_syndicated_corroboration():
    readings, sources = _syndicated_readings_and_sources()
    _, table = ar.build_cross_input(readings, sources)
    sigs = {u: ar.source_signature(u, sources[u]) for u in sources}
    parsed = {"findings": [{"kind": "corroboration", "a": "c1", "b": "c2", "note": "both agree"}]}
    out = ar.validate_cross(parsed, table, sigs)
    assert len(out) == 1
    assert out[0]["kind"] == "shared_source"                 # NOT corroboration
    assert out[0]["independence"]["independent"] is False
    assert out[0]["independence"]["reason"] == "same_wire"
    assert out[0]["independence"]["label"] == "2 outlets, 1 wire source"


def test_validate_cross_keeps_independent_corroboration():
    readings = {
        "https://cyprus-mail.com/x": {"claims": [{"text": "A1", "quote": "qa", "attribution": "asserted"}]},
        "https://xinhua.net/y": {"claims": [{"text": "B1", "quote": "qb", "attribution": "asserted"}]},
    }
    sources = {
        "https://cyprus-mail.com/x": {"outlet": "cyprus-mail.com", "title": "16 wounded"},
        "https://xinhua.net/y": {"outlet": "xinhua.net", "title": "13 injured in Kyiv"},
    }
    _, table = ar.build_cross_input(readings, sources)
    sigs = {u: ar.source_signature(u, sources[u]) for u in sources}
    parsed = {"findings": [{"kind": "corroboration", "a": "c1", "b": "c2", "note": "both report casualties"}]}
    out = ar.validate_cross(parsed, table, sigs)
    assert out[0]["kind"] == "corroboration"
    assert out[0]["independence"]["independent"] is True
    assert out[0]["independence"]["label"] == "2 independent sources"


async def test_cross_read_gates_syndication_end_to_end(monkeypatch):
    readings, sources = _syndicated_readings_and_sources()

    async def fake_read(urls):
        return readings

    async def fake_sources(urls):
        return sources

    async def fake_insight(*a, **k):
        return ('{"findings":[{"kind":"corroboration","a":"c1","b":"c2","note":"agree"}]}',
                "deepseek", None, {"model": "deepseek-chat"})
    monkeypatch.setattr(ar, "read_articles", fake_read)
    monkeypatch.setattr(ar, "article_sources", fake_sources)
    monkeypatch.setattr(ar, "generate_insight", fake_insight)
    ar._CROSS_CACHE.clear()
    out = await ar.cross_read(list(readings.keys()))
    assert out["independent_corroborations"] == 0
    assert out["shared_source_findings"] == 1
    assert out["findings"][0]["kind"] == "shared_source"


# ── attribution + quote overlap (corroborate-v2 R2, G-HAARETZ) ───────────────
# Byte-identity catches SYNDICATION. This catches DERIVATION: three rewrites of
# one Haaretz report have different bodies, headlines and mastheads — every
# existing check passes them — while their own quotes say "according to
# Haaretz". They are one voice, not "2 independent sources".

def test_attributed_outlet_detects_media_attribution():
    from app.services.article_read import attributed_outlet
    quotes = [
        "According to Haaretz, the meeting took place on Sunday.",
        "The plan was first drafted in May, according to Haaretz.",
    ]
    assert attributed_outlet(quotes) == "haaretz"


def test_attributed_outlet_ignores_non_media():
    from app.services.article_read import attributed_outlet
    assert attributed_outlet(["According to officials, the toll rose."]) is None
    assert attributed_outlet(["según las autoridades, hubo daños"]) is None
    assert attributed_outlet([]) is None


def test_attributed_outlet_spanish_and_german():
    from app.services.article_read import attributed_outlet
    assert attributed_outlet(["Según Haaretz, la reunión ocurrió el domingo."]) == "haaretz"
    assert attributed_outlet(["Wie Bild berichtete, begann der Einsatz früh."]) == "bild"


def test_g_haaretz_three_rewrites_one_primary_source():
    """G-HAARETZ (spec pre-registered): three rewrites of one Haaretz report,
    each attributing to Haaretz, are ONE voice — not '2 independent sources'."""
    from app.services.article_read import articles_independent
    a = {"outlet_root": "sitea.com", "wire_sig": "meeting plan drafted may",
         "content_hash": "h1", "derivative_of": "haaretz"}
    b = {"outlet_root": "siteb.net", "wire_sig": "secret plan meeting sunday",
         "content_hash": "h2", "derivative_of": "haaretz"}
    indep, reason = articles_independent(a, b)
    assert indep is False and reason == "same_primary_source"


def test_derivative_of_the_other_articles_masthead():
    from app.services.article_read import articles_independent
    a = {"outlet_root": "haaretz.com", "wire_sig": "x", "content_hash": "h1",
         "derivative_of": None}
    b = {"outlet_root": "siteb.net", "wire_sig": "y", "content_hash": "h2",
         "derivative_of": "haaretz"}
    indep, reason = articles_independent(a, b)
    assert indep is False and reason == "same_primary_source"


def test_quote_overlap_same_primary():
    from app.services.article_read import quote_overlap
    q1 = ["The strike was carried out at dawn near the northern crossing point",
          "We had no warning whatsoever before the explosions began that morning"]
    q2 = ["Officials said the strike was carried out at dawn near the northern crossing point",
          "A resident said: We had no warning whatsoever before the explosions began that morning"]
    assert quote_overlap(q1, q2) >= 0.6


def test_quote_overlap_distinct_reporting():
    from app.services.article_read import quote_overlap
    q1 = ["The strike was carried out at dawn near the northern crossing point"]
    q2 = ["Hospitals reported forty arrivals within the first hour of the incident"]
    assert quote_overlap(q1, q2) == 0.0


def _haaretz_rewrites():
    """Two derivative rewrites: distinct outlets, distinct headlines, distinct
    bodies — only their own quotes name the primary source."""
    readings = {
        "https://sitea.com/x": {"claims": [
            {"text": "The meeting happened on Sunday.",
             "quote": "The meeting took place on Sunday, according to Haaretz.",
             "attribution": "attributed"}]},
        "https://siteb.net/y": {"claims": [
            {"text": "The plan was drafted in May.",
             "quote": "The plan was first drafted in May, according to Haaretz.",
             "attribution": "attributed"}]},
    }
    sources = {
        "https://sitea.com/x": {"outlet": "sitea.com", "title": "Sunday meeting revealed",
                                "content_hash": "h1"},
        "https://siteb.net/y": {"outlet": "siteb.net", "title": "Secret plan drafted in May",
                                "content_hash": "h2"},
    }
    return readings, sources


def test_validate_cross_downgrades_attributed_rewrites():
    """The gate reads the claims' own quotes off the cross-read table, so every
    caller of validate_cross gets the attribution check without new plumbing."""
    readings, sources = _haaretz_rewrites()
    _, table = ar.build_cross_input(readings, sources)
    sigs = {u: ar.source_signature(u, sources[u]) for u in sources}
    parsed = {"findings": [{"kind": "corroboration", "a": "c1", "b": "c2", "note": "both agree"}]}
    out = ar.validate_cross(parsed, table, sigs)
    assert len(out) == 1
    assert out[0]["kind"] == "shared_source"                  # NOT corroboration
    assert out[0]["independence"]["independent"] is False
    assert out[0]["independence"]["reason"] == "same_primary_source"
    assert out[0]["independence"]["label"] == "2 outlets, 1 primary source (attributed)"


async def test_cross_read_gates_attributed_rewrites_end_to_end(monkeypatch):
    readings, sources = _haaretz_rewrites()

    async def fake_read(urls):
        return readings

    async def fake_sources(urls):
        return sources

    async def fake_insight(*a, **k):
        return ('{"findings":[{"kind":"corroboration","a":"c1","b":"c2","note":"agree"}]}',
                "deepseek", None, {"model": "deepseek-chat"})
    monkeypatch.setattr(ar, "read_articles", fake_read)
    monkeypatch.setattr(ar, "article_sources", fake_sources)
    monkeypatch.setattr(ar, "generate_insight", fake_insight)
    ar._CROSS_CACHE.clear()
    out = await ar.cross_read(list(readings.keys()))
    assert out["independent_corroborations"] == 0
    assert out["shared_source_findings"] == 1
    assert out["findings"][0]["independence"]["reason"] == "same_primary_source"


# ── leads: entity gates ──────────────────────────────────────────────────────

def test_gather_entities_gates_states_and_invalid_persons():
    readings = {
        "https://x.com/a": {"claims": [], "actors": [
            {"name": "Irán", "kind": "state", "role": "país"},
            {"name": "el niño", "kind": "person", "role": "weather, not a person"},
            {"name": "Carlos Restrepo", "kind": "person", "role": "financier"},
        ]},
    }
    ents = rl.gather_entities(readings)
    names = {e["name"] for e in ents}
    assert "Carlos Restrepo" in names
    assert "Irán" not in names and "el niño" not in names


def test_gather_entities_df_suppresses_investigation_subject():
    actor = {"name": "Repeated Actor", "kind": "org", "role": "r"}
    readings = {f"https://x.com/{i}": {"claims": [], "actors": [dict(actor)]} for i in range(3)}
    ents = rl.gather_entities(readings)
    assert ents[0]["suppressed"] == "investigation_subject"


def test_gather_entities_attaches_claim_quote_context():
    readings = {"https://x.com/a": {
        "claims": [{"text": "t", "quote": "El financista Carlos Restrepo movió los fondos"}],
        "actors": [{"name": "Carlos Restrepo", "kind": "person", "role": "financier"}],
    }}
    ents = rl.gather_entities(readings)
    assert "Carlos Restrepo" in (ents[0]["quote"] or "")


def test_name_matches_diacritics_and_transliteration():
    assert rl._name_matches("Nicușor Dan", "nicusor dan")
    assert rl._name_matches("Volodimir Zelenski", "volodymyr zelenskyy")
    assert not rl._name_matches("Maria Garcia", "Pedro Ramirez")
    assert not rl._name_matches("Li Wei", "Liu Weimin")     # short tokens never glue
    assert not rl._name_matches("Rare Actor", "Common Actor")  # shared word ≠ shared name


# ── leads: lookup ────────────────────────────────────────────────────────────

def _thread(tid, label, entities, n):
    return {"thread_id": tid, "label": label, "top_entities": entities, "signal_count": n}


async def test_find_leads_matches_excludes_and_sorts(monkeypatch):
    async def fake_read(urls):
        return {"https://x.com/a": {"claims": [], "actors": [
            {"name": "Rare Actor", "kind": "person", "role": "fixer"},
            {"name": "Common Actor", "kind": "person", "role": "president"},
        ]}}
    pool = (
        [_thread("dynamic-topic-1", "Pinned thread", ["rare actor"], 50)]
        + [_thread("dynamic-topic-2", "New lead", ["rare actor"], 30)]
        + [_thread(f"dynamic-topic-{i}", f"T{i}", ["common actor"], 10) for i in range(10, 23)]
    )

    async def fake_pool(**kwargs):
        return pool
    monkeypatch.setattr(rl, "read_articles", fake_read)
    monkeypatch.setattr(rl, "fetch_threads", fake_pool)
    monkeypatch.setattr(rl, "_pool_conn", lambda: None)
    out = await rl.find_leads(["https://x.com/a"], pinned_ids=["dynamic-topic-1"])
    leads = out["leads"]
    assert len(leads) == 1 and leads[0]["entity"] == "Rare Actor"
    assert leads[0]["threads"][0]["thread_id"] == "dynamic-topic-2"   # pinned excluded
    reasons = {s["reason"] for s in out["suppressed"]}
    assert any(r.startswith("ubiquitous_") for r in reasons)          # Common Actor suppressed


async def test_find_leads_no_entities_is_honest_empty(monkeypatch):
    async def fake_read(urls):
        return {}
    monkeypatch.setattr(rl, "read_articles", fake_read)
    out = await rl.find_leads(["https://x.com/a"])
    assert out["leads"] == [] and out["articles_read"] == 0
