"""Disaster-event ingest + binding — pure-logic tests (no live key, no DB).

Covers the country resolver (the honest best-effort ISO2), the confidence blend,
and the type→category mapping that decides which disaster topic a hazard binds to.
"""
from app.services.ingest_disasters import _resolve_country, _GDACS_TYPE
from scripts.bind_disaster_movement import _confidence, _CATEGORY_FOR_TYPE


NAME_MAP = {  # stand-in for the countries_v2 lookup (+ the module aliases fold in)
    "tonga": "TO", "japan": "JP", "chile": "CL", "australia": "AU",
    "iran": "IR", "united states": "US",
}


def test_resolve_country_name_tail():
    # USGS place string: comma-tail is the country name
    assert _resolve_country("10km S of Pangai, Tonga", NAME_MAP) == "TO"
    assert _resolve_country("49 km E of Noda, Japan", NAME_MAP) == "JP"


def test_resolve_country_us_state_abbrev():
    # USGS labels US quakes with a STATE postal code, not a country
    assert _resolve_country("95 km W of Ferndale, CA", NAME_MAP) == "US"
    assert _resolve_country("30 km N of Anchorage, AK", NAME_MAP) == "US"


def test_resolve_country_bare_name_and_alias():
    # GDACS gives a bare country name; aliases (Iran/USA) resolve too
    assert _resolve_country("Japan", NAME_MAP) == "JP"
    assert _resolve_country("Iran", NAME_MAP) == "IR"  # from _NAME_ALIASES


def test_resolve_country_unmapped_is_none():
    # honest: unmapped -> None (never a false binding)
    assert _resolve_country("Some Unknown Place, Ruritania", NAME_MAP) is None
    assert _resolve_country(None, NAME_MAP) is None
    assert _resolve_country("", NAME_MAP) is None


def test_confidence_magnitude():
    assert _confidence(8.0, None) == 1.0          # M8 caps
    assert _confidence(4.0, None) == 0.5          # linear below
    assert _confidence(None, None) == 0.3         # floor when nothing present


def test_confidence_alert_and_max():
    assert _confidence(None, "Red") == 0.9
    assert _confidence(None, "Green") == 0.35
    # blend takes the STRONGER of the two available signals
    assert _confidence(4.0, "Red") == 0.9         # alert 0.9 > mag 0.5
    assert _confidence(7.2, "Green") == 0.9       # mag 0.9 > alert 0.35


def test_category_for_type_maps_hazards():
    assert _CATEGORY_FOR_TYPE["earthquake"] == "Earthquake or volcanic disaster"
    assert _CATEGORY_FOR_TYPE["volcano"] == "Earthquake or volcanic disaster"
    assert _CATEGORY_FOR_TYPE["flood"] == "Flood and Landslide Disaster"
    assert _CATEGORY_FOR_TYPE["wildfire"] == "Wildfire or severe-storm disaster"
    assert _CATEGORY_FOR_TYPE["cyclone"] == "Wildfire or severe-storm disaster"


def test_drought_intentionally_unbound():
    # slow-onset, no discrete disaster thread -> not in the binding map (honest gap)
    assert "drought" not in _CATEGORY_FOR_TYPE
    # but GDACS still INGESTS drought (it's a real hazard record, just not bound)
    assert _GDACS_TYPE["DR"] == "drought"


def test_gdacs_type_codes():
    assert _GDACS_TYPE["EQ"] == "earthquake"
    assert _GDACS_TYPE["TC"] == "cyclone"
    assert _GDACS_TYPE["FL"] == "flood"
    assert _GDACS_TYPE["WF"] == "wildfire"
