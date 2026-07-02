"""#176 — entity drilldown hygiene: the person gate.

Pedro's #228 review found the People panel is the weakest leaf: "El Niño"
(a climate pattern), "bafana bafana" (a football team), "dar una patada"
("to kick"), and "america latina" all surfaced as *people*. They slip through
``_is_valid_person`` because it only checked word-count, length, and an
English geo blocklist — so any 2+ word non-English non-person phrase passed.

These tests pin the hardened gate: it must keep real people (in any casing,
including multi-part and non-English names) while rejecting articles-led
phrases, repeated-token team chants, climate patterns, and the multilingual
geo forms the English blocklist missed.
"""
from __future__ import annotations

import pytest

from app.utils import _is_valid_person


# Real people — must be ACCEPTED (various casings, lengths, languages).
VALID_PEOPLE = [
    "Lionel Messi",
    "Donald Trump",
    "Gustavo Petro",
    "Dina Boluarte",
    "Volodymyr Zelensky",
    "Kim Jong Un",                       # 3 tokens
    "Recep Tayyip Erdogan",
    "Luiz Inácio Lula da Silva",         # long, internal particle
    "lionel messi",                      # lower-cased source
    "Cristina Fernández de Kirchner",
    "Narendra Modi",
]

# Non-people — must be REJECTED.
INVALID_NON_PEOPLE = [
    # climate / nature patterns
    "El Niño",
    "La Niña",
    "el nino",
    # sports team chants / nicknames (repeated token)
    "bafana bafana",
    # verb / article-led phrases
    "dar una patada",
    "el presidente",
    "la casa",
    "the guardian",
    # multilingual geo the English blocklist missed
    "america latina",
    "estados unidos",
    "reino unido",
    "naciones unidas",
    "union europea",
    "oriente medio",
    "corea del norte",
    "arabia saudita",
    # English geo blocklist (regression — must still reject)
    "saudi arabia",
    "north korea",
    "new york",
    "latin america",
    # structural rejects
    "Trump",                             # single token
    "X" * 61,                            # > 60 chars
]


@pytest.mark.parametrize("name", VALID_PEOPLE)
def test_real_people_are_accepted(name):
    assert _is_valid_person(name) is True, f"{name!r} should be a valid person"


@pytest.mark.parametrize("name", INVALID_NON_PEOPLE)
def test_non_people_are_rejected(name):
    assert _is_valid_person(name) is False, f"{name!r} should be rejected"


def test_gate_is_perfect_over_fixture():
    """Excellence bar: zero leaks and zero false rejects over the fixture."""
    leaks = [n for n in INVALID_NON_PEOPLE if _is_valid_person(n)]
    drops = [n for n in VALID_PEOPLE if not _is_valid_person(n)]
    assert not leaks, f"non-people leaked through: {leaks}"
    assert not drops, f"real people wrongly dropped: {drops}"


class TestBylineScrape:
    """#248: 'By ' credit glued onto the name — 'bysarah falson' (44 live signals)."""

    def test_rejects_byline_scrapes(self):
        from app.utils import _is_valid_person
        assert not _is_valid_person("bysarah falson")
        assert not _is_valid_person("bykristie kellahan")
        assert not _is_valid_person("bycatherine marshall")

    def test_keeps_real_by_names(self):
        from app.utils import _is_valid_person
        # Byron = real given name ('ron' is 3 letters, under the floor);
        # Byungjae → 'ungjae' is not a name.
        assert _is_valid_person("byron buxton")
        assert _is_valid_person("byron donalds")
        assert _is_valid_person("byungjae kim")
