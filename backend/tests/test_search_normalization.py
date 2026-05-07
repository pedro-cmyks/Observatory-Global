from app.core.search_normalization import build_query_variants, normalize_search_text


def test_normalize_search_text_removes_accents_punctuation_and_extra_spaces():
    assert normalize_search_text("  EE.UU.,  Perú / México  ") == "ee uu peru mexico"


def test_build_query_variants_adds_aliases_and_compound_forms():
    variants = build_query_variants("Orthohantavirus")

    assert "orthohantavirus" in variants
    assert "hantavirus" in variants
    assert "orthohantaviru" not in variants


def test_build_query_variants_adds_token_reordering_for_short_person_queries():
    variants = build_query_variants("Trump Donald")

    assert "trump donald" in variants
    assert "donald trump" in variants


def test_build_query_variants_adds_plural_fallbacks():
    variants = build_query_variants("Donald Trumps")

    assert "donald trumps" in variants
    assert "donald trump" in variants


def test_build_query_variants_normalizes_us_aliases():
    variants = build_query_variants("EE.UU.")

    assert "ee uu" in variants
    assert "us" in variants
    assert "united states" in variants
