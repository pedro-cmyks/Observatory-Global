"""#176 — syndication-resistant person ranking.

The #228 review caught Peru's top-persons list led by David Hockney: a
syndicated obituary republished by dozens of outlets ranked #1 by raw
COUNT(*), outranking the actual local actors. Ranking by the number of
DISTINCT stories a person appears in (not raw mention rows) fixes it, plus a
corroboration floor so a single mass-republished story can't lead the panel —
with a fallback so low-coverage countries still get a People panel.
"""
from __future__ import annotations

from app.utils import rank_key_people


def _p(name, *, headlines, outlets, signals, sentiment=0.0, countries=1):
    return {
        "person": name,
        "distinct_headlines": headlines,
        "distinct_outlets": outlets,
        "signal_count": signals,
        "avg_sentiment": sentiment,
        "country_count": countries,
    }


def test_syndicated_single_story_does_not_outrank_local_actors():
    # Hockney: one obituary, 50 republications, 1 headline. Local: 3 stories.
    hockney = _p("David Hockney", headlines=1, outlets=50, signals=50)
    local = _p("Dina Boluarte", headlines=3, outlets=3, signals=5)
    out = rank_key_people([hockney, local])
    assert [r["person"] for r in out] == ["Dina Boluarte"]


def test_ranks_by_distinct_headlines_then_outlets_then_signals():
    a = _p("Alfa Uno", headlines=5, outlets=5, signals=5)   # top headlines
    b = _p("Bravo Dos", headlines=3, outlets=9, signals=9)  # tie hl, more outlets
    c = _p("Charlie Tres", headlines=3, outlets=4, signals=20)  # tie hl, fewer outlets
    out = rank_key_people([c, b, a])
    assert [r["person"] for r in out] == ["Alfa Uno", "Bravo Dos", "Charlie Tres"]


def test_invalid_persons_filtered_even_with_high_counts():
    junk = _p("El Niño", headlines=40, outlets=40, signals=99)
    real = _p("Lionel Messi", headlines=2, outlets=2, signals=2)
    out = rank_key_people([junk, real])
    assert [r["person"] for r in out] == ["Lionel Messi"]


def test_fallback_when_nobody_clears_the_floor():
    # Low-coverage country: every person appears in a single story. Don't blank
    # the panel — return the best-effort ranking instead.
    rows = [
        _p("One Story", headlines=1, outlets=1, signals=1),
        _p("Other Story", headlines=1, outlets=4, signals=4),
    ]
    out = rank_key_people(rows)
    assert [r["person"] for r in out] == ["Other Story", "One Story"]


def test_limit_respected():
    rows = [_p(f"Name{i} Sur{i}", headlines=2, outlets=2, signals=i) for i in range(20)]
    assert len(rank_key_people(rows, limit=8)) == 8


def test_passthrough_fields_preserved():
    rows = [_p("Gustavo Petro", headlines=2, outlets=2, signals=7, sentiment=-0.3, countries=4)]
    out = rank_key_people(rows)
    assert out[0]["avg_sentiment"] == -0.3
    assert out[0]["country_count"] == 4
