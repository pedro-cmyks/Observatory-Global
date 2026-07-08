"""#238 subject-geography core — GDELT primary-location selection.

GDELT's geocoder mis-locates non-English content: a stray place token in a
Spanish/Portuguese article (e.g. "Belén" -> Bethlehem) gets tagged, and the
old "first location with lat/lon wins" pick then stamped a Peruvian farándula
story onto the West Bank (FIPS WE -> PS). These tests pin the two levers in
``_select_primary_country``:

* PROMINENCE — the most-mentioned country wins, not the first-mentioned. A
  single spurious mention loses to the repeatedly-named real subject.
* NON-ENGLISH OUTLET-ORIGIN OVERRIDE — for the translation feed
  (source_lang='xx') with only single-mention scatter (no dominant subject)
  that conflicts with the outlet home country, trust the outlet and flag low
  confidence. Genuine foreign coverage (subject named >= 2x) is untouched.
* English content is never overridden (GDELT geo is strongest there).
* The kill-switch ATLAS_GEO_SUBJECT_GATE=off restores first-pick.

GKG V2ENHANCEDLOCATIONS block: Type#FullName#CountryCode#ADM1#Lat#Long#FeatureID#Offset
"""
from __future__ import annotations

import importlib

import pytest

from app.services import ingest_v2


def sel(locations, source_lang="xx", origin=None):
    return ingest_v2._select_primary_country(locations, source_lang, origin)


# --- prominence: most-mentioned country wins over first-mentioned -----------

def test_most_mentioned_country_wins_over_first():
    # A spurious West Bank mention (offset 5) appears FIRST, but Peru (PE) is
    # named twice -> PE is the subject. FIPS PE == ISO PE.
    loc = (
        "4#Bethlehem#WE#WE00#31.7#35.2#00#5;"
        "4#Lima, Peru#PE#PE00#-12.0#-77.0#00#40;"
        "1#Peru#PE##-10.0#-76.0#00#120"
    )
    out = sel(loc, source_lang="xx", origin="PE")
    assert out is not None
    iso, lat, lon, conf, method = out
    assert iso == "PE"
    assert method == "gdelt_geo_prominence"
    assert conf == 0.85


def test_single_dominant_subject_kept_even_when_foreign():
    # Genuine foreign coverage: DW (DE outlet) on Palestine, PS named 3x.
    # max_count >= 2 -> NOT overridden to DE.
    loc = (
        "1#Palestinian Territory#WE##31.9#35.2#00#10;"
        "4#Gaza#WE#WE01#31.5#34.4#00#55;"
        "4#Ramallah#WE#WE02#31.9#35.2#00#90"
    )
    out = sel(loc, source_lang="xx", origin="DE")
    assert out[0] == "PS"  # WE -> PS via fips_to_iso (worktree map may vary)
    assert out[4] == "gdelt_geo_prominence"


# --- non-English outlet-origin override (the noise class) -------------------

def test_spanish_stray_mention_overridden_to_outlet():
    # radioagricultura.cl (CL) Peruvian-entertainment story. One stray West
    # Bank token, nothing named twice -> distrust GDELT, fall back to CL.
    loc = "4#Belen#WE#WE00#31.7#35.2#00#8"
    out = sel(loc, source_lang="xx", origin="CL")
    assert out is not None
    iso, lat, lon, conf, method = out
    assert iso == "CL"
    assert method == "outlet_origin_override"
    assert conf == ingest_v2._GEO_OVERRIDE_CONFIDENCE
    assert lat is None and lon is None


def test_scatter_of_single_mentions_overridden():
    # Several foreign countries each mentioned once, none dominant, from a
    # known outlet -> outlet wins.
    loc = (
        "4#Belen#WE#WE00#31.7#35.2#00#8;"
        "1#France#FR##46.0#2.0#00#40;"
        "1#Italy#IT##42.0#12.0#00#80"
    )
    out = sel(loc, source_lang="xx", origin="ES")
    assert out[0] == "ES"
    assert out[4] == "outlet_origin_override"


def test_no_override_without_known_outlet():
    # elpopular.pe had no resolved origin in prod. Without a fallback we keep
    # GDELT's best guess rather than dropping the row.
    loc = "4#Belen#WE#WE00#31.7#35.2#00#8"
    out = sel(loc, source_lang="xx", origin=None)
    assert out is not None
    assert out[4] == "gdelt_geo_prominence"


def test_english_never_overridden():
    # English feed: GDELT geo trusted even on a single mention conflicting with
    # the outlet (e.g. a US outlet reporting one line on the West Bank).
    loc = "1#West Bank#WE##31.9#35.2#00#8"
    out = sel(loc, source_lang="en", origin="US")
    assert out[0] == "PS"
    assert out[4] == "gdelt_geo_prominence"


def test_override_needs_conflict():
    # Winner already equals the outlet country -> nothing to override.
    loc = "4#Santiago#CI#CI00#-33.4#-70.6#00#8"  # FIPS CI -> ISO CL (Chile)
    out = sel(loc, source_lang="xx", origin="CL")
    assert out[0] == "CL"
    assert out[4] == "gdelt_geo_prominence"


# --- degenerate inputs ------------------------------------------------------

def test_empty_locations_returns_none():
    assert sel("", origin="CL") is None
    assert sel(None, origin="CL") is None


def test_ungeocodable_blocks_return_none():
    # Blocks with no country code geocode to nothing.
    assert sel("4#Somewhere###0#0#00#1", origin="CL") is None


# --- kill-switch ------------------------------------------------------------

def test_kill_switch_restores_first_pick(monkeypatch):
    monkeypatch.setenv("ATLAS_GEO_SUBJECT_GATE", "off")
    mod = importlib.reload(ingest_v2)
    try:
        # First block (West Bank) wins by earliest offset, no override.
        loc = (
            "4#Belen#WE#WE00#31.7#35.2#00#8;"
            "1#Peru#PE##-10.0#-76.0#00#40;"
            "1#Peru#PE##-10.0#-76.0#00#120"
        )
        out = mod._select_primary_country(loc, "xx", "CL")
        assert out[0] == "PS"
        assert out[4] == "gdelt_geo_first"
    finally:
        monkeypatch.delenv("ATLAS_GEO_SUBJECT_GATE", raising=False)
        importlib.reload(ingest_v2)


# ===========================================================================
# #238 ambiguous-geo demotion (measured 2026-07-08). "Belén"/"Belém"/
# "Bethlehem, PA" -> Bethlehem, West Bank (FIPS WE -> ISO PS). Prominence winner
# is PS but the article never corroborates Palestine -> reassign to the real
# non-PS subject in the same article. Genuine, corroborated Palestine untouched.
# ===========================================================================


def selc(locations, source_lang="xx", origin=None, text=""):
    return ingest_v2._select_primary_country(locations, source_lang, origin, text)


def test_demote_ps_to_repeated_subject_brazil_belem():
    # Portuguese city-hall story about Belém (Pará, Brazil). GDELT tags
    # Bethlehem(WE)->PS twice AND Brazil twice; no Palestine token in the text.
    loc = (
        "4#Bethlehem#WE#WE00#31.7#35.2#00#5;"
        "4#Bethlehem#WE#WE00#31.7#35.2#00#60;"
        "4#Belem, Para, Brazil#BR#BR30#-1.45#-48.5#00#20;"
        "1#Brazil#BR##-10.0#-55.0#00#90"
    )
    out = selc(loc, source_lang="xx", origin="BR",
               text="Preco do pescado cai em Belem e estimula consumidores")
    assert out[0] == "BR"
    assert out[4] == "ambiguous_geo_demote"
    assert out[3] == 0.6


def test_demote_ps_to_repeated_subject_peru_farandula():
    # Peruvian entertainment story; "Belén" once, Lima/Peru named twice.
    loc = (
        "4#Bethlehem#WE#WE00#31.7#35.2#00#5;"
        "4#Lima, Peru#PE#PE00#-12.0#-77.0#00#40;"
        "1#Peru#PE##-10.0#-76.0#00#120"
    )
    out = selc(loc, source_lang="xx", origin=None,
               text="Austin Palao protagoniza fuerte pelea con Raimundo")
    # Winner is PE by prominence already (count 2 > 1); demotion not even needed.
    assert out[0] == "PE"


def test_demote_ps_single_alt_english_bethlehem_pa():
    # English "Bethlehem, PA" story: WE once, US once, no outlet resolves, no
    # Palestine corroboration -> take the US alternative at damped confidence.
    loc = (
        "4#Bethlehem#WE#WE00#31.7#35.2#00#8;"
        "3#Pennsylvania, United States#US#USPA#40.8#-75.4#00#30"
    )
    out = selc(loc, source_lang="en", origin=None,
               text="Bethlehem councilmember says rowhomes need space")
    assert out[0] == "US"
    assert out[4] == "ambiguous_geo_demote_weak"
    assert out[3] == 0.4


def test_genuine_gaza_corroborated_kept():
    # Real Gaza coverage: WE tagged twice, headline names Gaza/Hamas -> PS kept.
    loc = (
        "4#Gaza#WE#WE01#31.5#34.4#00#10;"
        "4#Gaza#WE#WE01#31.5#34.4#00#60;"
        "1#Egypt#EG##26.0#30.0#00#90"
    )
    out = selc(loc, source_lang="es", origin="EG",
               text="Hamas disuelve su gobierno en la Franja de Gaza")
    assert out[0] == "PS"
    assert out[4] == "gdelt_geo_prominence"


def test_genuine_palestine_corroborated_via_themes_kept():
    # No Palestine token in the headline but GDELT themes carry it.
    loc = "1#West Bank#WE##31.9#35.2#00#8;1#United States#US##38.0#-97.0#00#40"
    out = selc(loc, source_lang="en", origin="US",
               text="Aid convoy blocked at crossing WB_2733_PALESTINIAN_STATE")
    assert out[0] == "PS"
    assert out[4] == "gdelt_geo_prominence"


def test_ps_only_no_alternative_kept():
    # PS is the only geocoded country and no corroboration -> can't disambiguate,
    # leave it (damp-not-break: no over-correction without evidence).
    loc = "4#Bethlehem#WE#WE00#31.7#35.2#00#8"
    out = selc(loc, source_lang="en", origin=None, text="Belen a beautiful name")
    assert out[0] == "PS"
    assert out[4] == "gdelt_geo_prominence"


def test_ambiguous_demote_kill_switch(monkeypatch):
    monkeypatch.setenv("ATLAS_GEO_AMBIGUOUS_DEMOTE", "off")
    mod = importlib.reload(ingest_v2)
    try:
        loc = (
            "4#Bethlehem#WE#WE00#31.7#35.2#00#5;"
            "4#Bethlehem#WE#WE00#31.7#35.2#00#60;"
            "4#Belem#BR#BR30#-1.45#-48.5#00#20;"
            "1#Brazil#BR##-10.0#-55.0#00#90"
        )
        out = mod._select_primary_country(loc, "xx", "BR", "Belem noticias")
        assert out[0] == "PS"
        assert out[4] == "gdelt_geo_prominence"
    finally:
        monkeypatch.delenv("ATLAS_GEO_AMBIGUOUS_DEMOTE", raising=False)
        importlib.reload(ingest_v2)
