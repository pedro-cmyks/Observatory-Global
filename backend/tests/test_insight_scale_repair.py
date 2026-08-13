"""The scale's bounds are constants — a measured value can never be one.

Witness, verbatim from the same 90-word Editor's Analysis (re-judge §4a):

    "The overall average tone was −0.48 on the −0.48…−0.48 scale."

The judge read it as a template that substituted the VALUE where the BOUNDS
belong. It is worse than that: no template on either side of the wire prints
that sentence — the prompt says "on a normalized -1..+1 scale" and the model
pattern-filled the range with the one number it had. Prompt wording alone
cannot fix a generative slip, so the bounds are enforced AFTER generation:
they are known constants, and any range claimed as a "scale" that is not
those constants is repaired to the truth (never invented, never left).
"""

import pytest

from app.services.insight_text import (
    TONE_SCALE_HIGH,
    TONE_SCALE_LOW,
    TONE_SCALE_PHRASE,
    repair_scale_claims,
)

WITNESS = "The overall average tone was −0.48 on the −0.48…−0.48 scale."
REPAIRED = f"The overall average tone was −0.48 on the {TONE_SCALE_PHRASE} scale."


def test_the_witness_sentence_is_repaired_to_the_real_bounds():
    assert repair_scale_claims(WITNESS) == REPAIRED


def test_the_value_itself_is_never_touched():
    """Repair fixes the bounds; the measurement stays exactly as measured."""
    assert "−0.48 on" in repair_scale_claims(WITNESS)


@pytest.mark.parametrize(
    "text",
    [
        "Average tone was -0.48 on the -1..+1 scale.",
        "tone on the same -1 to +1 scale",
        "tone on a -1.0 to 1.0 scale",
        "measured on the −1…+1 scale",
        "reported on the ±1 scale",
    ],
)
def test_a_correct_scale_statement_is_left_alone(text):
    assert repair_scale_claims(text) == text


@pytest.mark.parametrize(
    "broken",
    [
        "tone was -0.48 on the -0.48 to -0.48 scale",
        "tone on a -10…+10 scale",
        "tone on the 0..1 scale",
        "the scale of -0.48 to -0.48",
        "the scale from -3 to 3",
    ],
)
def test_a_wrong_range_claimed_as_a_scale_is_repaired(broken):
    out = repair_scale_claims(broken)
    assert TONE_SCALE_PHRASE in out, broken
    assert "-0.48 to -0.48" not in out
    assert "-10" not in out


def test_ranges_that_are_not_scales_are_untouched():
    """Volumes, counts and shares carry ranges too — only 'scale' is bounded."""
    text = "Coverage ran from 4,754 to 2,670 articles across the top categories."
    assert repair_scale_claims(text) == text


def test_repair_is_idempotent():
    once = repair_scale_claims(WITNESS)
    assert repair_scale_claims(once) == once


def test_empty_and_none():
    assert repair_scale_claims(None) is None
    assert repair_scale_claims("") == ""


def test_the_constants_are_the_ones_the_prompt_declares():
    assert (TONE_SCALE_LOW, TONE_SCALE_HIGH) == (-1.0, 1.0)
    assert "1" in TONE_SCALE_PHRASE
