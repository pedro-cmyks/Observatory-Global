from app.core.gdelt_taxonomy import get_theme_label


def test_get_theme_label_formats_unknown_gdelt_codes_without_raw_prefixes():
    assert get_theme_label("WB_2024_ANTI_CORRUPTION") == "Anti-Corruption (World Bank)"
    assert get_theme_label("USPEC_POLICY_ECONOMIC2") == "US Economic Policy"
    assert get_theme_label("EPU_NONDEFENSE_SPENDING") == "Policy: Non-Defense Spending"
    assert get_theme_label("CRISISLEX_C07_SAFETY") == "Public Safety"
    assert get_theme_label("UNGP_FORESTS_RIVERS_OCEANS") == "Environment"


def test_classify_source_unknown_for_unmapped_domain():
    """D4 (dataviz audit): an unmapped domain is 'unknown', never a confident
    'independent' claim — the all-INDEPENDENT badge wall was zero information."""
    from app.core.gdelt_taxonomy import classify_source

    assert classify_source("totally-unmapped-outlet-xyz.example") == "unknown"
    # mapped families still classify confidently
    assert classify_source("state.gov") == "state"


def test_unknown_family_downstream_behavior_is_sane():
    """The two consumers of the family value stay honest for 'unknown':
    tiers → 4 (no credibility signal either way, NOT junk); the thread-packet
    voice lane keeps counting unknown news domains as media."""
    from app.services.source_tiers import classify_source_tier
    from app.services.thread_packet import _lane_for

    t = classify_source_tier("totally-unmapped-outlet-xyz.example", source_family="unknown")
    assert t.tier == 4

    assert _lane_for("totally-unmapped-outlet-xyz.example") == "media"
