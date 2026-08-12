"""Which table a served count was actually counted over -- and how to say so.

Cold-user probe 2026-08-12 §7: *"A product whose entire pitch is 'measured'
cannot afford two answers to 'how many signals did Germany have.'"* Measured
that day on prod, `/api/v2/nodes` answered it twice from two tables:

    ?hours=24                          -> country_hourly_v2   DE 3,836
    ?focus_type=country&focus_value=DE -> signals_v2 (raw)    DE 5,238

This module is the single place that decides -- and names -- the base. The rule
is the council's N19 lesson: unify where it is one quantity, and where two
bases genuinely cannot be merged, label them so a reader can reconcile instead
of concluding the product cannot count.
"""
from __future__ import annotations

from typing import Dict

#: Base served straight off the pre-aggregated country rollup that also drives
#: the map, the heat layer and the signal-density list.
BASIS_HOURLY_ROLLUP = "hourly_rollup"
#: Base served by scanning raw ``signals_v2`` rows under a focus predicate.
BASIS_SIGNALS_FOCUS = "signals_v2_focus"
#: Base served from the compact processed-history aggregates (long windows).
BASIS_HISTORICAL = "historical_topic_country_daily"

COUNT_BASIS_LABELS: Dict[str, str] = {
    BASIS_HOURLY_ROLLUP: "hourly rollup",
    BASIS_SIGNALS_FOCUS: "raw scan",
    BASIS_HISTORICAL: "processed history",
}

COUNT_BASIS_NOTES: Dict[str, str] = {
    BASIS_HOURLY_ROLLUP: (
        "Counted over the hourly country rollup that also draws the map and the "
        "signal-density list. The rollup is refreshed on a cadence, so the newest "
        "hour can be missing and this can read below the raw signal count."
    ),
    BASIS_SIGNALS_FOCUS: (
        "Counted by scanning raw signal rows under this focus. The country rollup "
        "carries no theme, person or source dimension, so this focus cannot be "
        "served from it -- expect it to sit above rollup-based country totals."
    ),
    BASIS_HISTORICAL: (
        "Counted over the processed historical daily aggregates, not raw rows or "
        "the live hourly rollup, because the requested window predates hot retention."
    ),
}

#: Focus types the country rollup can serve without losing a dimension.
_ROLLUP_SERVABLE_FOCUS = {"", "country"}


def nodes_count_basis(focus_type: str | None) -> str:
    """Return the base ``/api/v2/nodes`` counts over for a given focus.

    A country focus is servable from the rollup -- and MUST be, so the country
    card and the density list on the same screen stop printing two answers to
    one question. Every other focus needs a dimension the rollup does not have.
    """
    normalized = (focus_type or "").strip().lower()
    if normalized in _ROLLUP_SERVABLE_FOCUS:
        return BASIS_HOURLY_ROLLUP
    return BASIS_SIGNALS_FOCUS


def describe_count_basis(basis: str) -> Dict[str, str]:
    """Serialize a base so the surface can label the number it prints.

    An unrecognized base degrades to an honest "unknown" rather than borrowing
    another base's label -- printing a confident wrong basis is the exact
    failure this module exists to end.
    """
    if basis not in COUNT_BASIS_LABELS:
        return {
            "basis": basis,
            "label": "unknown basis",
            "note": (
                "This count's base is not declared, so it cannot be reconciled "
                "with counts elsewhere in the product."
            ),
        }
    return {
        "basis": basis,
        "label": COUNT_BASIS_LABELS[basis],
        "note": COUNT_BASIS_NOTES[basis],
    }
