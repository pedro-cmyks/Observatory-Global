from app.services.search_contract import should_show_concept_suggestions


def test_concept_suggestions_are_hidden_when_direct_signal_matches_exist():
    assert should_show_concept_suggestions(
        concept_hits=[],
        merged_themes=[],
        persons=[],
        countries=[],
        public_attention=[],
        signal_matches=[{"headline": "Colombia Election 2026: Ivan Cepeda..."}],
    ) is False


def test_concept_suggestions_are_hidden_when_taxonomy_theme_has_signal_support():
    assert should_show_concept_suggestions(
        concept_hits=[],
        merged_themes=[{"theme": "HUMAN_RIGHTS", "total_signals": 12}],
        persons=[],
        countries=[],
        public_attention=[],
        signal_matches=[],
    ) is False


def test_concept_suggestions_are_allowed_only_for_empty_searches():
    assert should_show_concept_suggestions(
        concept_hits=[],
        merged_themes=[{"theme": "HUMAN_RIGHTS", "total_signals": 0}],
        persons=[],
        countries=[],
        public_attention=[],
        signal_matches=[],
    ) is True
