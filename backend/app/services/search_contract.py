from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def _has_supported_theme(themes: Sequence[dict[str, Any]]) -> bool:
    return any(int(theme.get("total_signals") or 0) > 0 for theme in themes)


def _has_supported_person(persons: Sequence[dict[str, Any]]) -> bool:
    return any(int(person.get("total_signals") or 0) > 0 for person in persons)


def should_show_concept_suggestions(
    *,
    concept_hits: Sequence[dict[str, Any]],
    merged_themes: Sequence[dict[str, Any]],
    persons: Sequence[dict[str, Any]],
    countries: Sequence[dict[str, Any]],
    public_attention: Sequence[dict[str, Any]],
    signal_matches: Sequence[dict[str, Any]],
) -> bool:
    """Only show fuzzy editorial concept suggestions for truly empty searches.

    Concept suggestions are weak "did you mean" hints. If the query already has
    direct evidence, such as a headline match for a person, showing unrelated
    investigative concepts reads like Atlas is forcing taxonomy onto the query.
    """

    if concept_hits:
        return False

    return not (
        _has_supported_theme(merged_themes)
        or _has_supported_person(persons)
        or bool(countries)
        or bool(public_attention)
        or bool(signal_matches)
    )
