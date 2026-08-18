"""Vagón 4 (panel ciego 2026-08-18 §5) — the "PAÍSES" tile must count
COUNTRIES, not the FIPS∪ISO union of codes.

The Brief tile serves ``stats.countries`` = COUNT(DISTINCT country_code) over
``country_hourly_v2``; the stored column mixes lanes (post-2026-07-28 GDELT
ingest converts FIPS→ISO, but historical rows / stray lanes can still carry
raw FIPS). A FIPS code that spells a country ISO already counts (HO beside HN,
EI beside IE, SW beside SE…) inflates the count silently.

What this freezes:

1. Every divergent FIPS code that is NOT itself a valid ISO code collapses to
   its audited ISO twin (source: country_codes.FIPS_TO_ISO, the table that
   survived the b7ab7def FIPS-disaster audit — no invented mappings here).
2. AMBIGUOUS codes — valid ISO codes that also exist as FIPS keys for a
   DIFFERENT country (CH, ES, GA, ZA, KN, …) — are NEVER remapped. Post-fix
   ingest writes ISO, so a stored 'CH' is Switzerland; remapping it to China
   would be the exact corruption class the module warns about.
3. Codes that are neither valid ISO nor mappable FIPS (placeholders and junk:
   XX, OS, OC, NT, YI — all measured live in the 24h window 2026-08-18) are
   not counted as countries.
4. GZ stays GZ: the project deliberately serves Gaza as its own code
   (ISO_COUNTRY_NAMES carries it), so it is never folded into PS.
"""
from __future__ import annotations

from app.core.iso_country_names import ISO_COUNTRY_NAMES
from app.services.country_codes import (
    FIPS_ONLY_TO_ISO,
    FIPS_TO_ISO,
    canonical_country_code,
    count_distinct_countries,
)


# ── the safe normalization set itself ────────────────────────────────────────

def test_fips_only_set_contains_no_valid_iso_keys():
    # The whole point of the split: a key that is a valid ISO code is
    # ambiguous and must not be in the auto-normalization set.
    for fips in FIPS_ONLY_TO_ISO:
        assert fips not in ISO_COUNTRY_NAMES, f"{fips} is a valid ISO code"


def test_fips_only_set_agrees_with_the_audited_table():
    # Derived strictly from FIPS_TO_ISO — never hand-invented mappings.
    for fips, iso in FIPS_ONLY_TO_ISO.items():
        assert FIPS_TO_ISO.get(fips) == iso


def test_every_fips_only_code_normalizes_away():
    # THE freeze the vagón asked for: no FIPS code with an ISO equivalent
    # survives normalization.
    for fips, iso in FIPS_ONLY_TO_ISO.items():
        got = canonical_country_code(fips)
        assert got == iso, f"{fips} -> {got}, expected {iso}"
        assert got != fips


# ── canonical_country_code ───────────────────────────────────────────────────

def test_panel_duplicate_pairs_collapse():
    # The pairs Marcus read out of the dropdown, as they exist in DATA terms.
    assert canonical_country_code("HO") == "HN"   # Honduras
    assert canonical_country_code("EI") == "IE"   # Ireland
    assert canonical_country_code("SW") == "SE"   # Sweden
    assert canonical_country_code("YM") == "YE"   # Yemen
    assert canonical_country_code("RQ") == "PR"   # Puerto Rico
    assert canonical_country_code("RB") == "RS"   # Serbia (pre-2008 GEC)
    assert canonical_country_code("KS") == "KR"   # South Korea
    # NOTE the two the panel MIS-read (frontend labels, not data dupes):
    # FIPS RI is Serbia per the audited table — the frontend's "RI: Indonesia"
    # label is the frontend's own bug, reported separately.
    assert canonical_country_code("RI") == "RS"
    # ISO KN is Saint Kitts and Nevis; the frontend's "KN: North Korea" label
    # is FIPS-reading a valid ISO code. Data-side, KN must stay untouched.
    assert canonical_country_code("KN") == "KN"


def test_ambiguous_iso_codes_are_never_remapped():
    # Valid ISO codes that are also FIPS keys for a different country.
    # Remapping any of these is the b7ab7def corruption class.
    for code in ("CH", "ES", "GA", "ZA", "GB", "GM", "AT", "AU", "BD",
                 "KR", "IS", "LS", "LT", "MP", "NE", "NG", "NI", "PA",
                 "RS", "SE", "SG", "SN", "TD", "TT"):
        assert canonical_country_code(code) == code, code


def test_gaza_project_code_is_preserved():
    # GZ is deliberately served as its own entity across Atlas; it must not
    # fold into PS even though FIPS GZ -> PS.
    assert canonical_country_code("GZ") == "GZ"
    assert canonical_country_code("PS") == "PS"


def test_junk_and_placeholders_yield_none():
    # All five measured live in country_hourly_v2's 24h window (2026-08-18),
    # plus the empty/None guards.
    for junk in ("XX", "OS", "OC", "NT", "YI", "", None, "X1", "1A", "USA"):
        assert canonical_country_code(junk) is None, junk


def test_case_and_whitespace_are_tolerated():
    assert canonical_country_code("ho ") == "HN"
    assert canonical_country_code(" de") == "DE"


# ── count_distinct_countries ─────────────────────────────────────────────────

def test_count_collapses_fips_iso_twins():
    codes = ["HN", "HO", "IE", "EI", "RS", "RB", "SE", "SW", "YE", "YM",
             "PR", "RQ"]
    # 12 raw codes -> 6 countries.
    assert count_distinct_countries(codes) == 6


def test_count_ignores_junk_but_keeps_real_countries():
    codes = ["US", "CO", "XX", "OS", "NT", "GZ", "PS", None, ""]
    # US, CO, GZ, PS = 4; XX/OS/NT/None/"" are not countries.
    assert count_distinct_countries(codes) == 4


def test_count_of_empty_input_is_zero():
    assert count_distinct_countries([]) == 0
    assert count_distinct_countries(None) == 0


def test_count_of_measured_24h_window_2026_08_18():
    """The live measurement this fix was calibrated against.

    228 distinct codes served as "228 COUNTRIES" on the Brief tile. Measured
    composition: 223 valid ISO codes (incl. territories + the GZ project code)
    + 5 junk codes (NT, OC, OS, XX, YI). Zero FIPS-only codes — the hot window
    is clean post-b7ab7def, so the honest tile value for that window is 223.
    """
    measured = [
        "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS",
        "AT", "AU", "AW", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH",
        "BI", "BJ", "BM", "BN", "BO", "BR", "BS", "BT", "BW", "BY", "BZ",
        "CA", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN", "CO",
        "CR", "CU", "CV", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ",
        "EC", "EE", "EG", "ER", "ES", "ET", "FI", "FJ", "FM", "FO", "FR",
        "GA", "GB", "GD", "GE", "GG", "GH", "GI", "GL", "GM", "GN", "GP",
        "GR", "GT", "GU", "GW", "GY", "GZ", "HK", "HN", "HR", "HT", "HU",
        "ID", "IE", "IL", "IN", "IQ", "IR", "IS", "IT", "JE", "JM", "JO",
        "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY",
        "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LT", "LU", "LV", "LY",
        "MA", "MC", "MD", "ME", "MG", "MH", "MK", "ML", "MM", "MN", "MO",
        "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA",
        "NC", "NE", "NG", "NI", "NL", "NO", "NP", "NR", "NT", "NZ", "OC",
        "OM", "OS", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PR", "PS",
        "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW", "SA", "SB",
        "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN",
        "SO", "SR", "SS", "ST", "SV", "SY", "TC", "TD", "TG", "TH", "TJ",
        "TK", "TL", "TM", "TN", "TO", "TR", "TT", "TW", "TZ", "UA", "UG",
        "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VI", "VN", "VU", "WS",
        "XK", "XX", "YE", "YI", "YT", "ZA", "ZM", "ZW",
    ]
    assert len(measured) == 228          # what the tile said
    assert count_distinct_countries(measured) == 223   # what it should say


def test_count_result_contains_no_fips_only_codes():
    # Feed EVERY FIPS-only code at once beside its ISO twin: the normalized
    # set must contain only the twins (i.e. adding the FIPS spellings changes
    # nothing).
    twins = sorted(set(FIPS_ONLY_TO_ISO.values()))
    mixed = twins + sorted(FIPS_ONLY_TO_ISO.keys())
    assert count_distinct_countries(mixed) == len(twins)
