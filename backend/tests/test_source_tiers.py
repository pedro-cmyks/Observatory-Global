"""#217 v1 — tier map with provenance; the claim-verification forcing case."""
from app.services.source_tiers import classify_source_tier, tier_payload


def test_forcing_case_conspiracy_below_met_agency():
    """Spec capability G acceptance: conspiracy amplifier labeled LOWER tier
    than the national met agency contradicting it."""
    agency = classify_source_tier("https://www.noaa.gov/forecast")
    conspiracist = classify_source_tier("globalresearch.ca")
    assert agency.tier < conspiracist.tier
    assert agency.label == "reference"
    assert conspiracist.label == "flagged"


def test_provenance_always_populated():
    for src in ("noaa.gov", "reuters.com", "globalresearch.ca",
                "random-blog.example", None):
        t = classify_source_tier(src)
        assert t.provenance and len(t.provenance) > 10


def test_state_media_is_perspective_label():
    t = classify_source_tier("rt.com", is_state_media=True)
    assert t.tier == 5 and t.label == "state"


def test_flagged_beats_state():
    t = classify_source_tier("globalresearch.ca", is_state_media=True)
    assert t.label == "flagged"


def test_unknown_is_honest_default():
    t = classify_source_tier("diario-regional-xyz.pe")
    assert t.tier == 4 and t.label == "unknown"


def test_subdomain_matches_root():
    assert classify_source_tier("nhc.noaa.gov").tier == 1
    assert classify_source_tier("es.globalresearch.ca").tier == 6


def test_family_fallbacks():
    assert classify_source_tier("x.org", source_family="ngo").tier == 1
    assert classify_source_tier("x.org", source_family="wire").tier == 2
    assert classify_source_tier("x.org", source_family="independent").tier == 3


def test_payload_shape():
    p = tier_payload("reuters.com")
    assert set(p) == {"tier", "label", "provenance"} and p["tier"] == 2


def test_ownership_group_state_outlets_share_group():
    from app.services.source_tiers import ownership_group
    assert ownership_group("ria.ru") == "state:ru"
    assert ownership_group("tass.com") == "state:ru"
    assert ownership_group("https://www.rt.com/news/x") == "state:ru"
    assert ownership_group("xinhuanet.com") == "state:cn"
    assert ownership_group("presstv.ir") == "state:ir"


def test_ownership_group_none_for_independent_press():
    from app.services.source_tiers import ownership_group
    assert ownership_group("cnn.com") is None
    assert ownership_group("reuters.com") is None
    assert ownership_group(None) is None


def test_state_groups_cover_exactly_the_state_dict():
    from app.services.source_tiers import STATE, STATE_GROUPS
    assert set(STATE_GROUPS) == set(STATE)
