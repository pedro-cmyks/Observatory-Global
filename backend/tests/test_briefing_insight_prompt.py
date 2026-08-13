"""The Editor's Analysis prompt is a glass box — frozen (C3, blind judge §5).

The judge's single sharpest trust cost was this paragraph: the only editorial
voice on a page that promises "measured from coverage, not editorialized",
asserting "Western outlets are driving a narrative of instability or crisis"
from tone averages, and citing figures that appeared to contradict the tone
table four inches below it.

Both defects are structural, so both are frozen structurally:

* the prompt must NAME the population and scale it is actually given (the five
  most-covered countries, tone on the normalized ±1 scale) — the surface prints
  the same basis deterministically, and these two must not drift apart;
* the prompt must forbid causal / motive / bloc claims, which coverage tone
  cannot support at all.

Read against the source rather than a live call: an LLM's obedience is not a
test, but what we ask of it is.
"""

from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[1] / "app" / "routers" / "briefing.py").read_text()

# The prompt strings live inside get_briefing_insight; slice it so an unrelated
# prompt elsewhere in the router can never satisfy these assertions by accident.
_START = SOURCE.index("async def get_briefing_insight")
_END = SOURCE.index("# TRUST INDICATORS API", _START)
INSIGHT_SECTION = SOURCE[_START:_END]


def test_prompt_states_the_population_it_was_given():
    """It sees the top-N most-covered countries, not the whole world."""
    assert "MOST-COVERED countries only" in INSIGHT_SECTION
    assert "top_n = len(top_countries)" in INSIGHT_SECTION


def test_prompt_states_the_scale_its_figures_are_on():
    """±1 — the tone columns the reader sees below are raw -10..+10."""
    assert INSIGHT_SECTION.count("-1..+1") >= 2


def test_prompt_forbids_superlatives_it_cannot_support():
    """'The most negative country' is unknowable from five rows."""
    assert "never call a figure the highest or lowest overall" in INSIGHT_SECTION
    assert "No superlatives beyond the rows you were given" in INSIGHT_SECTION


@pytest.mark.parametrize(
    "forbidden",
    ["driving", "framing", "intent", "motive", "bloc language", "Western media"],
)
def test_prompt_bars_causal_and_geopolitical_claims(forbidden):
    """Tone measures wording. It cannot reach who is driving what, or why."""
    assert forbidden in INSIGHT_SECTION, (
        f"the prompt no longer bars {forbidden!r} — the judge's exact charge "
        "('Western outlets are driving a narrative of instability') is back in scope"
    )


def test_every_claim_must_carry_a_number():
    """The existing glass-box discipline, kept explicit rather than implied."""
    assert "Every claim must be supported by a number" in INSIGHT_SECTION


def test_the_surface_disclosure_and_the_prompt_agree():
    """The page prints the basis deterministically; the prompt must not deny it.

    frontend-v2/src/lib/editorAnalysis.ts prints "the five most-covered
    countries, tone on the normalized ±1 scale". That sentence is only true
    while this endpoint keeps feeding exactly that.
    """
    assert "LIMIT 5" in INSIGHT_SECTION, (
        "the insight's country population changed — update ANALYSIS_BASIS in "
        "frontend-v2/src/lib/editorAnalysis.ts in the same commit"
    )
    assert "float(r['avg_s'] or 0) / 10" in INSIGHT_SECTION, (
        "the insight's tone scale changed — update ANALYSIS_BASIS in "
        "frontend-v2/src/lib/editorAnalysis.ts in the same commit"
    )
