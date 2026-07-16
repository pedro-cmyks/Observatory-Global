"""Place → country GAZETTEER (C-clean slice 2, #238).

`resolve_place_to_country` gains a GeoNames-derived gazetteer
(`backend/app/data/place_to_country.json`, built by
`scripts/build_place_gazetteer.py` from cities15000 + admin1CodesASCII —
CC-BY, attribution in the JSON `_meta`). Coverage is honest and bounded:

- name + asciiname only (NO alternatenames) → Latin/ASCII forms resolve;
  native scripts (Cyrillic Херсон, Arabic, CJK) do NOT, unless the existing
  country-pattern fallback happens to fire.
- names <4 chars dropped (precision), names mapping to >1 country dropped
  UNLESS one country holds >=10x the population of the runner-up.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from app.services.subject_geography import resolve_place_to_country

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "app" / "data" / "place_to_country.json"


# ── Artifact shape ────────────────────────────────────────────────────────────

def test_gazetteer_file_exists_with_attribution_meta():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    meta = doc["_meta"]
    assert "geonames" in meta["attribution"].casefold()
    assert "cc" in meta["license"].casefold()  # CC-BY
    assert len(doc["places"]) > 10_000
    # compact budget: < 1.5MB on disk
    assert DATA.stat().st_size < 1_500_000


# ── Resolution through the real gazetteer ────────────────────────────────────

@pytest.mark.parametrize("place,expected", [
    ("Roseburg", "US"),
    ("Rimini", "IT"),
    ("Kherson", "UA"),      # ascii truth — GeoNames `name` for the city
    ("Split", "HR"),        # legit city that is also an English word — KEPT
    ("roseburg", "US"),     # case-insensitive normalize
    ("  Rimini  ", "IT"),   # whitespace normalize
])
def test_city_resolves_to_iso2(place, expected):
    assert resolve_place_to_country(place) == expected


def test_cyrillic_coverage_is_the_native_pattern_lexicon_only():
    # We keep only name+asciiname (no alternatenames) → the GAZETTEER misses
    # Cyrillic city forms. The _NATIVE_COUNTRY_PATTERNS fallback carries a
    # hand-built lexicon that happens to include Херсон→UA — that keeps
    # working. A Cyrillic city outside that lexicon is honestly uncovered.
    assert resolve_place_to_country("Херсон") == "UA"       # fallback, not gazetteer
    assert resolve_place_to_country("Сыктывкар") is None    # Syktyvkar — miss


def test_country_name_passthrough_via_iso_reverse_map():
    assert resolve_place_to_country("France") == "FR"
    assert resolve_place_to_country("united states") == "US"
    assert resolve_place_to_country("Gaza") == "PS"  # project alias GZ→PS


def test_short_names_rejected_for_precision():
    # Ufa (RU) is a real 1M+ city but <4 chars — dropped by the length rule.
    assert resolve_place_to_country("Ufa") is None


def test_ambiguous_multi_country_name_dropped():
    # Hamilton: CA ~693k / NZ ~152k / US / BM — no >=10x dominant → dropped.
    assert resolve_place_to_country("Hamilton") is None


def test_dominant_name_kept_over_minor_homonyms():
    # London GB ~8.9M vs London CA ~380k → >=10x → resolves GB.
    assert resolve_place_to_country("London") == "GB"


def test_unknown_place_returns_none_never_guesses():
    assert resolve_place_to_country("Bondi Beach") is None
    assert resolve_place_to_country("") is None
    assert resolve_place_to_country(None) is None


# ── Builder rules (unit, synthetic rows — no network) ─────────────────────────

def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_place_gazetteer", BACKEND / "scripts" / "build_place_gazetteer.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_builder_dominance_and_length_rules():
    b = _load_builder()
    places = b.build_places(
        city_rows=[
            ("Testville", "Testville", "US", 1_000_000),
            ("Testville", "Testville", "CA", 50_000),      # 20x → US wins
            ("Evenville", "Evenville", "FR", 500_000),
            ("Evenville", "Evenville", "DE", 100_000),     # 5x → ambiguous, dropped
            ("Ubb", "Ubb", "RU", 2_000_000),               # <4 chars → dropped
            ("Along", "Along", "IN", 20_000),              # stoplist → dropped
        ],
        admin1_rows=[("Regionia", "Regionia", "BR")],
    )
    assert places["testville"] == "US"
    assert "evenville" not in places
    assert "ubb" not in places
    assert "along" not in places
    assert places["regionia"] == "BR"


def test_builder_city_population_beats_admin1_zero_population():
    # documented rule: admin-1 regions carry no population in the dump; a
    # 15k+ city with the same name in another country wins dominance over them.
    b = _load_builder()
    places = b.build_places(
        city_rows=[("Sharedname", "Sharedname", "IT", 40_000)],
        admin1_rows=[("Sharedname", "Sharedname", "ES")],
    )
    assert places["sharedname"] == "IT"
