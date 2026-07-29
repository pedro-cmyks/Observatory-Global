from app.core.search_normalization import (
    build_query_variants,
    normalize_search_text,
    should_offer_fuzzy_suggestion,
)


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


def test_build_query_variants_keeps_compound_form_for_two_tokens():
    variants = build_query_variants("bird flu")

    assert "bird flu" in variants
    assert "birdflu" in variants


def test_build_query_variants_never_concatenates_long_queries():
    # Gold-external eval EQ-01: 'Bolivia fuel dollar shortage subsidy' surfaced
    # 'boliviafueldollarshortagesubsidy' in the Related-phrasings banner — a
    # 3+-token concatenation is never a real compound word.
    variants = build_query_variants("bolivia fuel dollar shortage subsidy")

    assert "bolivia fuel dollar shortage subsidy" in variants
    assert "boliviafueldollarshortagesubsidy" not in variants

    variants = build_query_variants("rare earth export controls")
    assert "rareearthexportcontrols" not in variants


def test_should_offer_fuzzy_suggestion_uses_confidence_and_distinct_values():
    assert should_offer_fuzzy_suggestion("donlad trump", "donald trump", 0.72) is True
    assert should_offer_fuzzy_suggestion("donlad trunp", "donald trump", 0.3) is True
    assert should_offer_fuzzy_suggestion("donald trump", "donald trump", 0.95) is False
    assert should_offer_fuzzy_suggestion("war", "water", 0.41) is False
