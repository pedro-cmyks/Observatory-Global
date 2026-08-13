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


# --- re-judge 2026-08-13 §4a: the three defects in one 90-word paragraph ----


def test_no_raw_taxonomy_code_can_reach_the_prompt():
    """`_clean_theme_label` (strip a prefix, .title()) wrote the witness.

    "Ungp Forests Rivers Oceans, Crisislexrec" — the mechanical cleaner is out
    of the prompt entirely; naming goes through the guarded resolver, which
    returns None (= omit) for anything it cannot name.
    """
    assert "_clean_theme_label(" not in INSIGHT_SECTION, (
        "the mechanical title-caser is back in the Analysis prompt — it is the "
        "code path that printed 'Crisislexrec' as English"
    )
    assert "taxonomy_line(" in INSIGHT_SECTION


def test_the_analysis_reads_the_same_category_lane_as_the_chart():
    """One taxonomy per screen: the paragraph and the chart share ONE query."""
    assert "_CATEGORY_COUNTS_SQL" in INSIGHT_SECTION, (
        "the Analysis stopped reading the category lane the chart under it "
        "serves — the judge's 'contradicts its own category chart' is back"
    )
    # ... and the briefing payload's own chart must read that same constant.
    payload_start = SOURCE.index("async def get_briefing")
    payload = SOURCE[payload_start:SOURCE.index("async def get_briefing_insight")]
    assert "_CATEGORY_COUNTS_SQL" in payload


def test_the_scale_bounds_are_declared_fixed():
    """"−0.48 on the −0.48…−0.48 scale" — the bounds are constants, and say so."""
    assert "fixed bounds" in INSIGHT_SECTION
    assert "a measured tone is never one of them" in INSIGHT_SECTION


def test_the_served_paragraph_is_checked_against_the_real_bounds():
    """Prompt wording is the belt; the post-generation repair is the brace."""
    assert "repair_scale_claims(" in INSIGHT_SECTION
    assert INSIGHT_SECTION.count("repair_scale_claims(") >= 2, (
        "a paragraph cached before the fix must not outlive it — the cached "
        "read path needs the same repair as the fresh one"
    )


def test_the_prompt_forbids_renaming_the_taxonomy_it_was_given():
    assert "Name the taxonomy exactly as the data line labels it" in INSIGHT_SECTION


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
