"""Plain-language companions for the stats the Brief serves as PROSE.

X4 (2026-08-13) — C5 of the blind college: four of eight personas, the whole
non-analyst range, could not parse "surprise 2.6σ over its own baseline,
velocity +0.59 (log-volume per 6 h)". The retired teacher: "I taught school for
forty years and cannot parse that."

The structural finding is why this is a module and not a copy edit: a reader who
cannot parse the grading system takes the honesty ON FAITH, so the jargon
disables the very trust mechanism the receipts exist to provide.

Lockstep with `frontend-v2/src/lib/statPhrases.ts` — the same bands and the same
words on both sides, so a number templated by the backend and a number rendered
by a panel never read differently. A one-sided edit fails one of the two suites.
"""
import pytest

from app.services import stat_phrases

# No phrase this module produces may carry analyst vocabulary.
JARGON = (
    "σ", "sigma", "z-score", "log-volume", "log volume", "velocity",
    "surprise", "baseline", "gate", "kalman", "deviation", "multiplier",
)


def assert_plain(phrase: str | None) -> None:
    assert phrase is not None
    lowered = phrase.lower()
    for word in JARGON:
        assert word not in lowered, f"jargon {word!r} leaked into {phrase!r}"


def test_surprise_translates_the_witness_value_without_the_sigma():
    phrase = stat_phrases.surprise_phrase(2.6)
    assert_plain(phrase)
    assert phrase == "rising much faster than its own normal pace"


@pytest.mark.parametrize("sigma,expected", [
    (6.0, "far beyond anything this story normally does"),
    (2.5, "rising much faster than its own normal pace"),
    (2.0, "rising faster than its own normal pace"),
    (0.4, "close to its own normal pace"),
    # A surprise is a MAGNITUDE — a negative reading is "nothing unusual",
    # never "falling". Direction belongs to velocity alone.
    (-3.0, "close to its own normal pace"),
])
def test_surprise_bands(sigma, expected):
    assert stat_phrases.surprise_phrase(sigma) == expected


def test_surprise_refuses_what_was_not_measured():
    assert stat_phrases.surprise_phrase(None) is None


def test_velocity_translates_the_witness_value_without_the_units():
    phrase = stat_phrases.velocity_phrase(0.59)
    assert_plain(phrase)
    assert phrase == "still speeding up"


@pytest.mark.parametrize("velocity,expected", [
    (-0.4, "already slowing down"),
    (0.0, "holding steady"),
])
def test_velocity_bands(velocity, expected):
    assert stat_phrases.velocity_phrase(velocity) == expected


def test_velocity_refuses_what_was_not_measured():
    assert stat_phrases.velocity_phrase(None) is None


def test_rising_plain_is_the_clause_the_reader_leads_with():
    phrase = stat_phrases.rising_plain(surprise=2.6, velocity=0.59)
    assert_plain(phrase)
    # Lockstep with statPhrases.ts `risingPlain`.
    assert phrase == "Rising much faster than its own normal pace, and still speeding up"


@pytest.mark.parametrize("surprise,velocity,expected", [
    (2.6, None, "Rising much faster than its own normal pace"),
    (None, 0.59, "Still speeding up"),
    (None, None, None),
])
def test_rising_plain_degrades_to_the_half_it_measured(surprise, velocity, expected):
    assert stat_phrases.rising_plain(surprise=surprise, velocity=velocity) == expected


def test_times_phrase_translates_the_witness_badge():
    phrase = stat_phrases.times_phrase(12)
    assert_plain(phrase)
    assert phrase == "twelve times its usual coverage"


@pytest.mark.parametrize("value,expected", [
    (2, "twice its usual coverage"),
    (3.05, "three times its usual coverage"),
    (3.6, "about 3.6 times its usual coverage"),
    (41, "41 times its usual coverage"),
    # 1.4x must never round to "once" — that turns a measured surge into
    # "nothing is happening".
    (1.4, "about 1.4 times its usual coverage"),
    (1.0, "about its usual coverage"),
    (0, None),
    (None, None),
])
def test_times_phrase_bands(value, expected):
    assert stat_phrases.times_phrase(value) == expected


def test_times_phrase_takes_the_subject_it_compares_against():
    assert stat_phrases.times_phrase(11.2, of="its usual day") == "eleven times its usual day"
    assert stat_phrases.times_phrase(11.6, of="its usual day") == "about 11.6 times its usual day"
