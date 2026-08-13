"""A raw taxonomy code must never reach prose (re-judge 2026-08-13 §4a).

Witness, verbatim from the Editor's Analysis:

    "the most-covered themes being Ungp Forests Rivers Oceans, Crisislexrec,
     Public Sector Management, Historic, and General Health."

Two of those five are database codes (UNGP_FORESTS_RIVERS_OCEANS,
CRISISLEXREC) title-cased into English that means nothing, and one
("Historic") is a bare taxonomy fragment. The front end has carried
`getThemeLabel` (frontend-v2/src/lib/themeLabels.tsx) for exactly this reason
since the beginning — the INSIGHT PROMPT's inputs never got that treatment,
because `_clean_theme_label` only strips a prefix and calls `.title()`.

The prose rule is stricter than the chip rule: a chip can afford a mangled
label because the reader sees it IS a taxonomy chip; a sentence cannot. So a
code with no confident human name is OMITTED from the sentence. Honest absence
beats gibberish.
"""

import pytest

from app.services.theme_labels import human_theme_label, humanize_category


# --- the witness codes ------------------------------------------------------

def test_the_witness_codes_are_never_title_cased_into_prose():
    """Neither of the judge's two raw codes may survive as its own mangling."""
    assert human_theme_label("UNGP_FORESTS_RIVERS_OCEANS") != "Ungp Forests Rivers Oceans"
    assert human_theme_label("CRISISLEXREC") != "Crisislexrec"


def test_the_mapped_witness_gets_its_human_name():
    assert human_theme_label("UNGP_FORESTS_RIVERS_OCEANS") == "Forests, Rivers and Oceans"


@pytest.mark.parametrize("opaque", ["CRISISLEXREC", "HISTORIC", "REC", "TAX_FNCACT", "WB_2024"])
def test_codes_with_no_human_name_are_omitted(opaque):
    """None = "leave it out of the sentence", the only honest option."""
    assert human_theme_label(opaque) is None


@pytest.mark.parametrize(
    "code,label",
    [
        # World Bank topic codes ARE real English once the numeric prefix goes.
        ("WB_696_PUBLIC_SECTOR_MANAGEMENT", "Public Sector Management"),
        ("WB_621_GENERAL_HEALTH", "General Health"),
        # Plain multi-word GDELT roots need no map entry.
        ("GENERAL_HEALTH", "General Health"),
        # Explicit map wins over any mechanical rule.
        ("KILL", "Violence & Killings"),
        ("ARMEDCONFLICT", "Armed Conflict"),
        ("CRISISLEX_C07_SAFETY_AND_SECURITY", "Safety and Security"),
    ],
)
def test_known_shapes_resolve_to_english(code, label):
    assert human_theme_label(code) == label


def test_a_lone_word_is_omitted_unless_it_is_mapped_by_hand():
    """The deliberate trade: "Historic" and "Safety" are indistinguishable.

    Nothing mechanical separates a real one-word theme from a taxonomy
    fragment, so one-word codes are omitted unless someone named them in
    THEME_LABELS. Omission costs a list item; the alternative cost the
    paragraph its credibility.
    """
    assert human_theme_label("CRISISLEX_C07_SAFETY") is None
    assert human_theme_label("TERROR") == "Terrorism"  # mapped by hand


def test_case_and_blank_input():
    assert human_theme_label("wb_696_public_sector_management") == "Public Sector Management"
    assert human_theme_label("") is None
    assert human_theme_label(None) is None


def test_no_returned_label_ever_contains_an_underscore_or_digit():
    """The shape test: whatever survives reads as words, not as a record key."""
    codes = [
        "UNGP_FORESTS_RIVERS_OCEANS", "WB_696_PUBLIC_SECTOR_MANAGEMENT",
        "GENERAL_HEALTH", "CRISISLEX_C07_SAFETY", "KILL", "EPU_POLICY_TAX",
        "TAX_FNCACT_PRESIDENT", "SOC_POINTSOFINTEREST", "CRISISLEXREC",
    ]
    for code in codes:
        label = human_theme_label(code)
        if label is None:
            continue
        assert "_" not in label, code
        assert not any(ch.isdigit() for ch in label), code


# --- categories (the R3 lane the Analysis now describes) --------------------

def test_a_human_category_passes_through_untouched():
    """The chart prints `category` verbatim; the prose must print the same term."""
    assert humanize_category("Armed conflict escalation") == "Armed conflict escalation"
    assert humanize_category("Crime & Justice") == "Crime & Justice"


def test_a_slug_shaped_category_is_read_as_words():
    """Some R3 categories are auto-grown slugs — a slug in prose is the same bug."""
    assert humanize_category("crime-and-accidents") == "Crime and Accidents"
    assert humanize_category("financial_market_movements") == "Financial Market Movements"


def test_blank_category():
    assert humanize_category(None) is None
    assert humanize_category("   ") is None
