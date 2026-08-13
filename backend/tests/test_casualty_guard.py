"""The casualty-term guard — the witness that made it necessary, frozen.

2026-08-13 veracity scorecard, claim 2, CONFIRMED as a real Atlas error:
a Romanian headline about the Colombia earthquake was served in English as
"224 dead and over 600 dead". The originals (Observator News, GdS, Curierul
National) all say "224 de morţi şi peste 600 de **răniţi**" — răniţi is
INJURED. Three blind testers caught it independently and one root-caused it.

In a receipts product a casualty figure that flips category in translation is
the worst possible failure: the reader is holding a number that the source
never said, under a link that appears to back it.

So: after every translation we extract (number, casualty-category) pairs from
BOTH sides and refuse to serve a translation whose numbers changed category.
The rules, in the order they are checked per translated casualty number:

  category_flip            the same number carries a different category on
                           each side (injured -> dead) — the witness
  uncorroborated_category  the number is in the original but carries no
                           casualty category anywhere near it there
  number_absent            the translation attaches a casualty category to a
                           number the original never printed

PRECISION IS THE POINT. A guard that cries wolf gets switched off, so it is
deliberately conservative and this suite pins the not-firing side just as
hard as the firing side: same-category rephrasing (dead -> killed), two
different facts in one headline (224 dead AND 600 injured), umbrella words
("casualties", "victime", "жертв") that legitimately cover both, an original
that is itself odd (the Ziua Veche typo that printed "600 de morţi"), and
long-distance phrasing where we simply cannot tell.
"""
from __future__ import annotations

import pytest

from app.services.casualty_guard import (
    CASUALTY_CATEGORIES,
    LEXICON,
    casualty_terms_in,
    check_translation,
    extract_casualty_numbers,
)

# --------------------------------------------------------------------------
# THE WITNESS (frozen). Observator News / GdS / Curierul National, 2026-08-12.
# --------------------------------------------------------------------------

WITNESS_RO = (
    "Cutremur în Columbia. Noul bilanţ e devastator: "
    "cel puţin 224 de morţi şi peste 600 de răniţi"
)
WITNESS_SERVED = (
    "Earthquake in Colombia. The new toll is devastating: "
    "at least 224 dead and over 600 dead"
)
WITNESS_FAITHFUL = (
    "Earthquake in Colombia. The new toll is devastating: "
    "at least 224 dead and over 600 injured"
)


def test_the_witness_fires():
    v = check_translation(WITNESS_RO, WITNESS_SERVED)

    assert v.fired is True
    assert v.reason == "category_flip"
    flip = [f for f in v.findings if f.number == "600"]
    assert flip, f"expected a finding on 600, got {v.findings}"
    assert set(flip[0].original_categories) == {"injured"}
    assert set(flip[0].translated_categories) == {"dead"}


def test_the_faithful_translation_of_the_witness_passes_untouched():
    v = check_translation(WITNESS_RO, WITNESS_FAITHFUL)

    assert v.fired is False, v.as_dict()


def test_witness_second_wording_also_fires():
    # GdS / Curierul headline shape ("bilanţul ... urcă la ...").
    ro = "Bilanţul cutremurului din Columbia urcă la 224 de morţi şi peste 600 de răniţi"
    assert check_translation(ro, "Colombia earthquake toll rises to 224 dead and over 600 dead").fired
    assert not check_translation(
        ro, "Colombia earthquake toll rises to 224 dead and over 600 injured"
    ).fired


def test_diacritic_variants_of_the_witness_are_the_same_words():
    # Romanian ships both comma-below (ț/ș) and legacy cedilla (ţ/ş) forms, and
    # some feeds strip them entirely. All three must read as răniţi = injured.
    for ro in (
        "224 de morți și peste 600 de răniți",
        "224 de morţi şi peste 600 de răniţi",
        "224 de morti si peste 600 de raniti",
    ):
        assert check_translation(ro, "224 dead and over 600 dead").fired, ro


# --------------------------------------------------------------------------
# PRECISION — the guard must stay silent on healthy translations
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "original,translated",
    [
        # same category, different word (the explicit no-fire requirement)
        ("24 de morţi într-un accident", "24 killed in a crash"),
        ("24 killed in a crash", "24 dead in a crash"),
        ("24 dead in a crash", "24 fatalities in a crash"),
        ("Cutremur: 24 de morţi", "Earthquake: 24 deaths"),
        # two different facts in one headline, correctly translated
        (
            "Cel puţin 132 de persoane au murit, iar peste 480 sunt rănite",
            "At least 132 people died and over 480 are injured",
        ),
        ("3 morţi şi 12 răniţi", "3 dead and 12 injured"),
        # the original is itself the odd one (Ziua Veche printed 600 de morţi):
        # a faithful translation of a wrong original is not our failure
        ("224 de morţi şi peste 600 de morţi", "224 dead and over 600 dead"),
        # numbers that are not casualties at all
        ("224 de morţi pe o rază de 600 km", "224 dead within a 600 km radius"),
        ("Deadline extended for 600 refugees", "Plazo ampliado para 600 refugiados"),
        # thousands separators differ between locales
        ("1.200 de morţi în urma seismului", "1,200 dead after the quake"),
        ("Peste 1 200 de răniţi", "More than 1,200 injured"),
        # umbrella words legitimately cover both categories
        ("600 de victime în urma cutremurului", "600 casualties after the earthquake"),
        ("Число жертв достигло 600", "Death toll reaches 600"),
        # order swapped, still faithful
        ("Peste 600 de răniţi şi 224 de morţi", "224 dead and more than 600 injured"),
    ],
)
def test_healthy_translations_do_not_fire(original, translated):
    v = check_translation(original, translated)
    assert v.fired is False, v.as_dict()


def test_measured_prod_pair_that_the_first_draft_wrongly_refused():
    """Regression from the only false positive in 409 real cached pairs.

    Arabic signal 17573672, translated faithfully. The first draft anchored
    BOTH numbers to `injured` in the original (مصرع, "the death of", was
    missing from the lexicon) and both to `dead` in the translation (`killed`
    sat 5 chars before 13 while the true anchor `injured` sat 8 after) — so a
    correct translation would have been refused. Fixed by adding مصرع and by
    letting a coordinating conjunction demote a candidate the way a comma
    does. Frozen here because this pair is the guard's whole precision story.
    """
    v = check_translation(
        "مصرع 4 سيدات وإصابة 13 آخرين في انقلاب ميكروباص بصحراوي المنيا",
        "4 women killed and 13 others injured in a microbus rollover in the Minya desert road",
    )
    assert v.fired is False, v.as_dict()

    # …and the same pair with 13 flipped to dead must still fire.
    flipped = check_translation(
        "مصرع 4 سيدات وإصابة 13 آخرين في انقلاب ميكروباص بصحراوي المنيا",
        "4 women killed and 13 others killed in a microbus rollover in the Minya desert road",
    )
    assert flipped.fired is True, flipped.as_dict()
    assert flipped.reason == "category_flip"
    assert any(f.number == "13" for f in flipped.findings)


def test_headline_without_digits_is_skipped():
    v = check_translation("Doi oameni răniţi uşor la Galaţi", "Two people lightly injured in Galati")
    assert v.fired is False
    assert v.skipped == "no_numbers_in_original"


def test_headline_without_casualty_vocabulary_is_skipped():
    # Claim 12 of the same scorecard: "995 senjata api" = 995 firearms. No
    # casualty word anywhere, so the guard has nothing to say and says nothing.
    v = check_translation(
        "995 senjata api ditemukan di sekolah swasta Jakarta Selatan",
        "995 firearms found at a private school in South Jakarta",
    )
    assert v.fired is False
    assert v.skipped == "no_casualty_terms_in_original"


def test_language_outside_the_lexicon_is_skipped_not_flagged():
    # Thai is not in the lexicon. Refusing every Thai translation would be a
    # louder lie than the one we are fixing.
    v = check_translation("แผ่นดินไหว มีผู้เสียชีวิต 224 คน", "224 dead in earthquake")
    assert v.fired is False
    assert v.skipped == "no_casualty_terms_in_original"


def test_long_distance_phrasing_suppresses_the_weaker_rules():
    # The original anchors "rănite" far from 600; we cannot tell, so we do not
    # accuse. (Precision beats recall: an unverifiable case is not a flip.)
    ro = "600 de persoane au fost transportate de urgenţă la spitalele din zonă, rănite"
    v = check_translation(ro, "600 people were injured")
    assert v.fired is False, v.as_dict()


def test_dates_and_clock_times_are_not_casualty_counts():
    # Measured on the live corpus: a trailing date stamp was the commonest
    # spurious anchor ("…погиб 13/08/2026 – Новости" read 13, 8 and 2026 as
    # dead), and a re-formatted date is exactly what would misfire the
    # number_absent rule.
    assert extract_casualty_numbers("В Татарстане рабочий погиб 13/08/2026 – Новости") == {}
    assert extract_casualty_numbers("Explosion at 14:30 kills 3") == {"3": {"dead"}}
    # A bare year is left alone — "2000 Todesfälle" is a real toll.
    assert extract_casualty_numbers("Mehr als 2000 Todesfälle in Kongo") == {"2000": {"dead"}}
    v = check_translation(
        "В Татарстане рабочий погиб 13/08/2026 – Новости",
        "A worker died in Tatarstan, 13 August 2026 – News",
    )
    assert v.fired is False, v.as_dict()


def test_korean_is_covered():
    assert check_translation("교통사고로 3명 사망, 12명 부상", "3 dead and 12 dead in a traffic accident").fired
    assert not check_translation("교통사고로 3명 사망, 12명 부상", "3 dead and 12 injured in a traffic accident").fired


def test_scale_words_suppress_the_absent_number_rule():
    # "12,5 mii" -> "12,500": the same fact written two ways. Not a fabrication.
    v = check_translation("Peste 12,5 mii de răniţi", "More than 12,500 injured")
    assert v.fired is False, v.as_dict()


# --------------------------------------------------------------------------
# RECALL — flips in every direction and every serviced language
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "lang,original,translated,number",
    [
        ("ro", "224 de morţi şi peste 600 de răniţi", "224 dead and over 600 dead", "600"),
        ("es", "3 muertos y 40 heridos en el accidente", "3 dead and 40 dead in the crash", "40"),
        ("pt", "5 mortos e 22 feridos", "5 dead and 22 killed", "22"),
        ("fr", "7 morts et 31 blessés", "7 dead and 31 dead", "31"),
        ("de", "2 Tote und 5 Verletzte", "2 dead and 5 dead", "5"),
        ("it", "4 morti e 18 feriti", "4 dead and 18 dead", "18"),
        ("ru", "Погибли 12 человек, ранены 30", "12 killed, 30 dead", "30"),
        ("uk", "Загинули 3 людини, поранено 17", "3 killed, 17 dead", "17"),
        ("tr", "3 ölü, 12 yaralı", "3 dead, 12 dead", "12"),
        ("id", "5 tewas dan 40 luka-luka", "5 dead and 40 dead", "40"),
        ("ar", "مقتل 224 شخصا وإصابة 600 آخرين", "224 dead and 600 dead", "600"),
        ("zh", "至少224人死亡，600人受伤", "At least 224 dead, 600 dead", "600"),
        ("ja", "224人が死亡、600人が負傷", "224 dead, 600 dead", "600"),
    ],
)
def test_injured_to_dead_flip_fires_in_every_serviced_language(lang, original, translated, number):
    v = check_translation(original, translated)
    assert v.fired is True, f"{lang}: {v.as_dict()}"
    assert v.reason == "category_flip", f"{lang}: {v.as_dict()}"
    assert any(f.number == number for f in v.findings), f"{lang}: {v.as_dict()}"


@pytest.mark.parametrize(
    "lang,original,translated",
    [
        ("ro", "224 de morţi şi peste 600 de răniţi", "224 dead and over 600 injured"),
        ("es", "3 muertos y 40 heridos en el accidente", "3 dead and 40 injured in the crash"),
        ("pt", "5 mortos e 22 feridos", "5 dead and 22 injured"),
        ("fr", "7 morts et 31 blessés", "7 dead and 31 wounded"),
        ("de", "2 Tote und 5 Verletzte", "2 dead and 5 injured"),
        ("it", "4 morti e 18 feriti", "4 dead and 18 injured"),
        ("ru", "Погибли 12 человек, ранены 30", "12 killed, 30 injured"),
        ("uk", "Загинули 3 людини, поранено 17", "3 killed, 17 wounded"),
        ("tr", "3 ölü, 12 yaralı", "3 dead, 12 injured"),
        ("id", "5 tewas dan 40 luka-luka", "5 dead and 40 injured"),
        ("ar", "مقتل 224 شخصا وإصابة 600 آخرين", "224 killed and 600 injured"),
        ("zh", "至少224人死亡，600人受伤", "At least 224 dead, 600 injured"),
        ("ja", "224人が死亡、600人が負傷", "224 dead, 600 injured"),
    ],
)
def test_faithful_translations_pass_in_every_serviced_language(lang, original, translated):
    v = check_translation(original, translated)
    assert v.fired is False, f"{lang}: {v.as_dict()}"


def test_dead_to_injured_flip_also_fires():
    # The inverse understates a disaster; equally a lie about the source.
    v = check_translation("40 muertos en el naufragio", "40 injured in the shipwreck")
    assert v.fired is True
    assert v.reason == "category_flip"


def test_missing_to_dead_flip_fires():
    v = check_translation("3 desaparecidos tras el derrumbe", "3 dead after the collapse")
    assert v.fired is True
    assert v.reason == "category_flip"


def test_casualty_number_absent_from_the_original_fires():
    v = check_translation("17 morţi în urma exploziei", "17 dead and 40 injured after the blast")
    assert v.fired is True
    assert v.reason == "number_absent"
    assert any(f.number == "40" for f in v.findings)


def test_casualty_category_with_no_counterpart_in_the_original_fires():
    # 600 is in the original (evacuated families) and nothing anywhere near it
    # says those 600 are casualties; the translation asserts they are dead.
    # Excerpt-length text — the /translate/text lane carries up to 600 chars.
    original = (
        "Autorităţile au anunţat 224 de morţi în urma cutremurului din Columbia. "
        "Ancheta continuă la faţa locului, iar echipele de salvare au evacuat "
        "600 de familii din zonele afectate."
    )
    translated = (
        "Authorities announced 224 dead after the earthquake in Colombia. "
        "The investigation continues on site, and rescue teams evacuated "
        "600 dead from the affected areas."
    )
    v = check_translation(original, translated)

    assert v.fired is True, v.as_dict()
    assert v.reason == "uncorroborated_category"
    assert any(f.number == "600" for f in v.findings)


def test_known_blind_spot_a_neighbouring_casualty_word_masks_the_flip():
    """Documented limit, pinned so it cannot change silently.

    "224 de morţi, 600 de clădiri" puts the word morţi two characters from
    600, so the original itself anchors 600 to `dead` and the sides agree.
    We could only break this tie by parsing what the 600 counts — and a guard
    that guesses is a guard that accuses the innocent. It stays silent here
    BY CHOICE; the category_flip rule (the witness class) is unaffected.
    """
    v = check_translation(
        "Cutremur în Columbia: 224 de morţi, 600 de clădiri prăbuşite",
        "Colombia earthquake: 224 dead, 600 dead",
    )
    assert v.fired is False


# --------------------------------------------------------------------------
# THE LEXICON ITSELF
# --------------------------------------------------------------------------

REQUIRED_LANGS = ("en", "ro", "ru", "uk", "es", "pt", "fr", "de", "ar", "id", "tr")


@pytest.mark.parametrize("lang", REQUIRED_LANGS)
def test_every_required_language_covers_every_category(lang):
    assert lang in LEXICON, f"{lang} missing from the lexicon"
    for category in ("dead", "injured", "missing"):
        assert LEXICON[lang].get(category), f"{lang} has no {category} terms"


def test_categories_are_the_declared_three_plus_the_umbrella():
    assert CASUALTY_CATEGORIES == ("dead", "injured", "missing")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("224 de morţi", {"224": {"dead"}}),
        ("peste 600 de răniţi", {"600": {"injured"}}),
        ("224 de morţi şi peste 600 de răniţi", {"224": {"dead"}, "600": {"injured"}}),
        ("224 dead and over 600 injured", {"224": {"dead"}, "600": {"injured"}}),
        ("3 desaparecidos", {"3": {"missing"}}),
        # a bare number with no casualty word nearby anchors nothing
        ("600 km de carretera", {}),
    ],
)
def test_extraction_pairs_numbers_with_the_nearest_category(text, expected):
    assert extract_casualty_numbers(text) == {k: set(v) for k, v in expected.items()}


def test_terms_are_matched_on_word_boundaries_not_substrings():
    # "deadline" is not a death, "Toten" is (German plural), "mortgage" is not.
    assert casualty_terms_in("Deadline for the report") == ()
    assert casualty_terms_in("Mortgage rates rise") == ()
    assert casualty_terms_in("Sanierung der Kosten") == ()
    assert casualty_terms_in("2 Tote nach Unfall")


def test_arabic_prefixes_do_not_hide_the_term_nor_invent_one():
    # والقتلى = "and the dead" — same word behind two clitics.
    assert casualty_terms_in("ارتفاع عدد القتلى إلى 224")
    # اقتلع ("uproot") merely contains the letters of قتل and must not match.
    assert casualty_terms_in("اقتلع الإعصار 600 شجرة") == ()


def test_verdict_serialises_for_the_ledger():
    v = check_translation(WITNESS_RO, WITNESS_SERVED)
    d = v.as_dict()

    assert d["fired"] is True
    assert d["reason"] == "category_flip"
    assert isinstance(d["findings"], list) and d["findings"]
    assert set(d["findings"][0]) >= {"number", "original_categories", "translated_categories"}
