"""Thread labels must not leak bare country codes (#204-lite).

Pedro caught "Disease outbreak in France and UG" — UG is Uganda's ISO code,
unresolved because COUNTRY_METADATA only has 31 countries while the diversity
program now surfaces 126. `resolve_country_name` expands any ISO alpha-2 code to
its name; `build_thread_label` runs every country through it so a label never
shows a raw code again.
"""
from __future__ import annotations

from app.core.iso_country_names import resolve_country_name
from app.services.country_codes import fips_to_iso
from app.services.thread_intelligence import build_thread_label


def test_resolves_iso_code_to_name():
    assert resolve_country_name("UG") == "Uganda"
    assert resolve_country_name("US") == "United States"
    assert resolve_country_name("FR") == "France"


def test_leaves_already_resolved_names_unchanged():
    assert resolve_country_name("United States") == "United States"
    assert resolve_country_name("Uganda") == "Uganda"


def test_unknown_or_empty_passthrough():
    assert resolve_country_name("ZZ") == "ZZ"   # not a real code → unchanged
    assert resolve_country_name("") == ""


def test_gdelt_fips_kuwait_and_brunei_are_normalized():
    assert fips_to_iso("KU") == "KW"
    assert fips_to_iso("BX") == "BN"


def test_gdelt_fips_senegal_singapore_collision_is_normalized_by_direction():
    # GDELT/FIPS SG means Senegal; GDELT/FIPS SN means Singapore. ISO uses the
    # opposite-looking pair, so this conversion must happen only at GDELT
    # boundaries rather than over already-normalized RSS/API rows.
    assert fips_to_iso("SG") == "SN"
    assert fips_to_iso("SN") == "SG"


def test_project_gaza_code():
    # Project convention: GZ = Gaza (not standard ISO, which folds it into PS).
    assert resolve_country_name("GZ") == "Gaza"


def test_build_thread_label_expands_leaked_code():
    label = build_thread_label(anchor_label="Disease outbreak", top_countries=["France", "UG"])
    assert label == "Disease outbreak in France and Uganda"
    assert "UG" not in label


def test_build_thread_label_unchanged_for_real_names():
    label = build_thread_label(anchor_label="Flood", top_countries=["United States", "India"])
    assert label == "Flood in United States and India"
