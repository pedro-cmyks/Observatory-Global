"""#238: country-scoped /threads keyed on SUBJECT geography, not the coverage
dateline. Pure-helper tests for resolve_thread_country_keys / thread_matches_country.
"""

from app.services.thread_intelligence import (
    resolve_thread_country_keys,
    thread_matches_country,
)


def test_verified_subject_wins_over_coverage():
    # A domestic story carried by foreign wires: coverage says US, subject says VE.
    res = resolve_thread_country_keys(
        subject_countries=["VE"],
        subject_geography_status="verified",
        coverage_country_codes=["US", "GB"],
    )
    assert res["keying_basis"] == "subject"
    assert res["country_keys"] == ["VE"]
    # Keyed under its subject country, not its dateline.
    assert thread_matches_country("VE", ["VE"], "verified", ["US", "GB"]) is True
    assert thread_matches_country("US", ["VE"], "verified", ["US", "GB"]) is False


def test_partial_status_falls_back_to_coverage():
    # subject inference abstained -> honest fallback to the coverage countries.
    res = resolve_thread_country_keys(
        subject_countries=[],
        subject_geography_status="partial",
        coverage_country_codes=["CO"],
    )
    assert res["keying_basis"] == "coverage"
    assert res["country_keys"] == ["CO"]
    assert thread_matches_country("CO", [], "partial", ["CO"]) is True


def test_unavailable_status_falls_back_to_coverage():
    assert thread_matches_country("FR", None, "unavailable", ["FR", "DE"]) is True
    assert thread_matches_country("DE", None, "unavailable", ["FR", "DE"]) is True
    assert thread_matches_country("ES", None, "unavailable", ["FR", "DE"]) is False


def test_missing_status_falls_back_to_coverage():
    # Default status 'missing' (no subject field served) never drops the thread.
    res = resolve_thread_country_keys(
        subject_countries=None,
        subject_geography_status="missing",
        coverage_country_codes=["JP"],
    )
    assert res["keying_basis"] == "coverage"
    assert res["country_keys"] == ["JP"]


def test_verified_but_empty_subject_falls_back_to_coverage():
    # Guard: status verified yet no verified countries -> coverage, not empty.
    res = resolve_thread_country_keys(
        subject_countries=[],
        subject_geography_status="verified",
        coverage_country_codes=["IN"],
    )
    assert res["keying_basis"] == "coverage"
    assert res["country_keys"] == ["IN"]


def test_case_insensitive_matching():
    assert thread_matches_country("ve", ["VE"], "verified", []) is True
    assert thread_matches_country("VE", ["ve"], "verified", []) is True


def test_multi_country_verified_subject():
    # A genuinely multi-country subject (Israel-US-Iran); both key it.
    keys = resolve_thread_country_keys(
        subject_countries=["IL", "IR"],
        subject_geography_status="verified",
        coverage_country_codes=["US"],
    )["country_keys"]
    assert keys == ["IL", "IR"]
    assert thread_matches_country("IL", ["IL", "IR"], "verified", ["US"]) is True
    assert thread_matches_country("IR", ["IL", "IR"], "verified", ["US"]) is True
    assert thread_matches_country("US", ["IL", "IR"], "verified", ["US"]) is False


def test_empty_country_code_never_matches():
    assert thread_matches_country("", ["VE"], "verified", ["VE"]) is False


def test_no_coverage_and_abstain_yields_empty_keys():
    # Honest: nothing to key on -> empty (caller keeps prior behavior; never a crash).
    res = resolve_thread_country_keys(
        subject_countries=[],
        subject_geography_status="partial",
        coverage_country_codes=[],
    )
    assert res["country_keys"] == []
    assert res["keying_basis"] == "coverage"
