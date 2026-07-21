"""Schema-freeze for FIPS 10-4 -> ISO 3166-1 alpha-2 conversion (#235).

CountryBrief showed a false "0% domestic voice" for countries whose native
press IS ingested but whose GDELT FIPS subject code never got converted to ISO
(the origin==subject ownership match failed on the code mismatch). This freezes
the six unambiguous aliases added for that fix plus a regression guard over the
pre-existing mappings that other surfaces depend on.
"""
from __future__ import annotations

from app.services.country_codes import FIPS_TO_ISO, fips_to_iso

# The six aliases this slice adds. Each is a genuinely unambiguous FIPS 10-4 ->
# ISO code (verified against the FIPS 10-4 / GEC country list).
NEW_ALIASES = {
    "AJ": "AZ",  # Azerbaijan
    "RI": "RS",  # Serbia
    "BK": "BA",  # Bosnia and Herzegovina
    "MJ": "ME",  # Montenegro
    "IC": "IS",  # Iceland
    "YM": "YE",  # Yemen
}

# A slice of pre-existing mappings other surfaces rely on; must never regress.
EXISTING_ALIASES = {
    "UK": "GB",
    "GM": "DE",
    "RS": "RU",  # FIPS RS = Russia (NOT Serbia — Serbia is FIPS RI)
    "CH": "CN",  # CRITICAL: CH is Switzerland in ISO
    "SZ": "CH",
    "RP": "PH",
    "GZ": "PS",
    "IS": "IL",  # FIPS IS = Israel (distinct from the new IC = Iceland -> IS)
}


def test_new_fips_aliases_present_and_correct():
    for fips, iso in NEW_ALIASES.items():
        assert FIPS_TO_ISO.get(fips) == iso, f"{fips} should map to {iso}"
        assert fips_to_iso(fips) == iso


def test_iceland_and_israel_do_not_collide():
    # Iceland uses FIPS key IC -> ISO IS; Israel uses FIPS key IS -> ISO IL.
    # They share the ISO value IS/ IL only as distinct keys, never overwriting.
    assert fips_to_iso("IC") == "IS"
    assert fips_to_iso("IS") == "IL"


def test_serbia_and_russia_do_not_collide():
    # Serbia is FIPS RI; Russia is FIPS RS. Adding RI must not touch RS.
    assert fips_to_iso("RI") == "RS"
    assert fips_to_iso("RS") == "RU"


def test_existing_mappings_unchanged():
    for fips, iso in EXISTING_ALIASES.items():
        assert FIPS_TO_ISO.get(fips) == iso, f"regressed: {fips} -> {iso}"


def test_unknown_code_returns_itself():
    assert fips_to_iso("ZZ") == "ZZ"
    assert fips_to_iso(None) is None
