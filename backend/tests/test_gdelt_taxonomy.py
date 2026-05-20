from app.core.gdelt_taxonomy import get_theme_label


def test_get_theme_label_formats_unknown_gdelt_codes_without_raw_prefixes():
    assert get_theme_label("WB_2024_ANTI_CORRUPTION") == "Anti-Corruption (World Bank)"
    assert get_theme_label("USPEC_POLICY_ECONOMIC2") == "US Economic Policy"
    assert get_theme_label("EPU_NONDEFENSE_SPENDING") == "Policy: Non-Defense Spending"
    assert get_theme_label("CRISISLEX_C07_SAFETY") == "Public Safety"
    assert get_theme_label("UNGP_FORESTS_RIVERS_OCEANS") == "Environment"
