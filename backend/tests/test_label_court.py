"""Label Court pure-logic: verdict parsing + neutral-label building."""
from scripts.label_court import parse_verdict, build_neutral_label, _dominant_geo


def test_parse_verdict_json():
    v, r = parse_verdict('{"verdict": "failed", "reason": "Greek traffic news, not a British teen"}')
    assert v == "failed"
    assert "Greek" in r


def test_parse_verdict_fenced_json():
    v, _ = parse_verdict('```json\n{"verdict": "entailed", "reason": "fits"}\n```')
    assert v == "entailed"


def test_parse_verdict_bare_word():
    assert parse_verdict("failed")[0] == "failed"
    assert parse_verdict("The verdict is PARTIAL here")[0] == "partial"


def test_parse_verdict_unknown_defaults_partial_never_entailed():
    # an unreadable judgment must NOT clear a label
    assert parse_verdict("")[0] == "partial"
    assert parse_verdict("¯\\_(ツ)_/¯")[0] == "partial"


def test_dominant_geo_ignores_xx_and_empty():
    assert _dominant_geo(["GR", "GR", "XX", "", "IR"]) == "GR"
    assert _dominant_geo(["XX", "", None]) == "Global"


def test_build_neutral_label_shape():
    receipts = [
        {"headline": "Family killed in Halkidiki tanker crash", "country_code": "GR"},
        {"headline": "Halkidiki road tragedy claims mother and baby", "country_code": "GR"},
        {"headline": "Two women die in Lesbos collision", "country_code": "GR"},
    ]
    lab = build_neutral_label(receipts)
    assert lab.startswith("GR:")
    assert "from 3 receipts" in lab
    # subject drawn from the receipts, never a fabricated narrative
    assert "Halkidiki" in lab or "Lesbos" in lab or "crash" in lab.lower()


def test_build_neutral_label_decodes_html_entities():
    # the Greek-blob class: receipts arrive HTML-entity-encoded; without
    # html.unescape the tokens come out as 'x3c4x3bf' escape fragments
    receipts = [
        {"headline": "&#x3A4;&#x3C1;&#x3B1;&#x3B3;&#x3C9;&#x3B4;&#x3AF;&#x3B1; Halkidiki crash", "country_code": "GR"},
        {"headline": "Covid cases surge in hospitals", "country_code": "GR"},
    ]
    lab = build_neutral_label(receipts)
    assert "x3c4" not in lab.lower() and "x3b1" not in lab.lower()
    assert "Halkidiki" in lab or "Covid" in lab or "cases" in lab


def test_build_neutral_label_drops_bare_numbers_and_dates():
    receipts = [
        {"headline": "2026 2026 World roundup 1500", "country_code": "US"},
        {"headline": "Election results tallied nationwide", "country_code": "US"},
    ]
    lab = build_neutral_label(receipts)
    assert "2026" not in lab and "1500" not in lab


def test_build_neutral_label_global_when_no_geo():
    receipts = [
        {"headline": "Markets mixed across regions today", "country_code": "XX"},
        {"headline": "Global roundup of financial reports", "country_code": None},
    ]
    assert build_neutral_label(receipts).startswith("Global:")


def test_fallback_sql_columns_match_live_schema():
    # 2026-07-18 general-review finding: the fallback SQL referenced
    # dtm.cluster_id (real column: emergent_cluster_id) — it crashed the court
    # on exactly the thin-substrate case it exists for, swallowed as non-fatal.
    # Freeze the column names against the migration files (no DB needed).
    from scripts.label_court import _RECEIPTS_FALLBACK_SQL
    assert "dtm.emergent_cluster_id" in _RECEIPTS_FALLBACK_SQL
    assert "dtm.cluster_id" not in _RECEIPTS_FALLBACK_SQL.replace("emergent_cluster_id", "")
