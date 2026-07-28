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


# ---------------------------------------------------------------------------
# FIPS/ISO divergence completion (2026-07-28)
#
# The gold UI eval traced a Lesotho brief rendering Lebanese conflict signals
# to FIPS 'LE' (Lebanon) being mapped to ISO 'LS' (Lesotho). Auditing the whole
# table against FIPS 10-4 found FIVE wrong entries and ~90 missing divergent
# ones that passed through as a plausible-but-wrong ISO code.
# ---------------------------------------------------------------------------

# The five entries that were WRONG in the map and silently mis-filed news.
CORRECTED = {
    "LE": "LB",  # Lebanon   (was LS = Lesotho)
    "PO": "PT",  # Portugal  (was PL = Poland)
    "PA": "PY",  # Paraguay  (was PA = Panama)
    "ZA": "ZM",  # Zambia    (was ZA = South Africa)
    "GA": "GM",  # Gambia    (was GA = Gabon)
}


def test_corrected_mappings():
    for fips, iso in CORRECTED.items():
        assert fips_to_iso(fips) == iso, f"{fips} must map to {iso}"


def test_lebanon_is_not_lesotho():
    """The headline regression: FIPS LE is Lebanon, Lesotho is FIPS LT."""
    assert fips_to_iso("LE") == "LB"  # Lebanon
    assert fips_to_iso("LT") == "LS"  # Lesotho
    assert fips_to_iso("LS") == "LI"  # Liechtenstein


# Pairs where BOTH letters are live codes in both standards but mean different
# countries. Each pair must round-trip to two DIFFERENT ISO codes -- if either
# side goes missing the passthrough silently merges two countries.
COLLIDING_PAIRS = [
    ("LE", "LB", "LT", "LS"),  # Lebanon      / Lesotho
    ("LT", "LS", "LS", "LI"),  # Lesotho      / Liechtenstein
    ("MN", "MC", "MG", "MN"),  # Monaco       / Mongolia
    ("MG", "MN", "MA", "MG"),  # Mongolia     / Madagascar
    ("MA", "MG", "MO", "MA"),  # Madagascar   / Morocco
    ("MU", "OM", "MP", "MU"),  # Oman         / Mauritius
    ("CH", "CN", "SZ", "CH"),  # China        / Switzerland
    ("CN", "KM", "CH", "CN"),  # Comoros      / China
    ("GA", "GM", "GB", "GA"),  # Gambia       / Gabon
    ("GM", "DE", "GA", "GM"),  # Germany      / Gambia
    ("PA", "PY", "PM", "PA"),  # Paraguay     / Panama
    ("PO", "PT", "PL", "PL"),  # Portugal     / Poland
    ("ZA", "ZM", "SF", "ZA"),  # Zambia       / South Africa
    ("KR", "KI", "KS", "KR"),  # Kiribati     / South Korea
    ("TD", "TT", "CD", "TD"),  # Trinidad     / Chad
    ("TN", "TO", "TS", "TN"),  # Tonga        / Tunisia
    ("TT", "TL", "TD", "TT"),  # Timor-Leste  / Trinidad
    ("PS", "PW", "GZ", "PS"),  # Palau        / Palestine
    ("BA", "BH", "BK", "BA"),  # Bahrain      / Bosnia
    ("BF", "BS", "UV", "BF"),  # Bahamas      / Burkina Faso
    ("SC", "KN", "SE", "SC"),  # St Kitts     / Seychelles
    ("SV", "SJ", "ES", "SV"),  # Svalbard     / El Salvador
    ("NE", "NU", "NG", "NE"),  # Niue         / Niger
    ("VI", "VG", "VQ", "VI"),  # British VI   / US VI
    ("MC", "MO", "MN", "MC"),  # Macau        / Monaco
]


def test_colliding_codes_stay_distinct():
    for fips_a, iso_a, fips_b, iso_b in COLLIDING_PAIRS:
        assert fips_to_iso(fips_a) == iso_a, f"{fips_a} must map to {iso_a}"
        assert fips_to_iso(fips_b) == iso_b, f"{fips_b} must map to {iso_b}"
        assert iso_a != iso_b, f"{fips_a}/{fips_b} collapsed onto {iso_a}"


# Requested regression locks over mappings other surfaces depend on.
STABLE = {
    "UK": "GB",  # United Kingdom
    "JA": "JP",  # Japan
    "SP": "ES",  # Spain
    "SW": "SE",  # Sweden
    "SZ": "CH",  # Switzerland
    "CH": "CN",  # China
    "GM": "DE",  # Germany
    "RP": "PH",  # Philippines
    "MN": "MC",  # Monaco
    "LT": "LS",  # Lesotho
}


def test_stable_mappings():
    for fips, iso in STABLE.items():
        assert fips_to_iso(fips) == iso, f"regressed: {fips} -> {iso}"


def test_identical_codes_pass_through():
    """Codes meaning the same country in both standards are returned as-is."""
    for code in ("FR", "US", "IT", "BR", "IN", "KE"):
        assert fips_to_iso(code) == code


def test_serbia_and_kosovo():
    """GDELT still emits the pre-2008 GEC code RB for Serbia; KV is Kosovo."""
    assert fips_to_iso("RB") == "RS"  # legacy Serbia
    assert fips_to_iso("RI") == "RS"  # current Serbia
    assert fips_to_iso("RS") == "RU"  # FIPS RS is Russia
    assert fips_to_iso("KV") == "XK"  # Kosovo (ISO user-assigned)


def test_guernsey_uses_its_own_iso_code():
    """Guernsey got ISO GG in 2006; older FIPS->ISO tables still say GB."""
    assert fips_to_iso("GK") == "GG"
    assert fips_to_iso("JE") == "JE"  # Jersey: identical in both
    assert fips_to_iso("IM") == "IM"  # Isle of Man: identical in both


def test_no_iso_codes_are_not_in_the_map():
    """Territories with no ISO equivalent must not claim a real country."""
    from app.services.country_codes import FIPS_NO_ISO

    for code in FIPS_NO_ISO:
        assert code not in FIPS_TO_ISO, f"{code} has no ISO equivalent"


def test_every_value_is_a_well_formed_iso_code():
    for fips, iso in FIPS_TO_ISO.items():
        assert len(fips) == 2 and fips.isalpha() and fips.isupper(), fips
        assert len(iso) == 2 and iso.isalpha() and iso.isupper(), iso


def test_values_are_known_iso_countries():
    """Guards against a typo'd ISO value that no surface could ever render."""
    from app.core.iso_country_names import ISO_COUNTRY_NAMES

    # UM (US Minor Outlying Islands) and a few dependency codes are valid ISO
    # but carry no Atlas country name; they are legitimately absent.
    allowed_missing = {"UM", "GS", "TF", "SJ", "BV", "HM", "AQ", "IO", "PN", "CC", "CX", "NF", "TK", "WF", "EH"}
    for fips, iso in FIPS_TO_ISO.items():
        assert iso in ISO_COUNTRY_NAMES or iso in allowed_missing, (
            f"{fips} -> {iso} is not a country any surface can name"
        )
