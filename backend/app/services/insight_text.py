"""Post-generation guards for LLM prose that quotes a measured scale.

Re-judge 2026-08-13 §4a, verbatim:

    "The overall average tone was −0.48 on the −0.48…−0.48 scale."

The judge called it a template bug. It is not: no template on either side of
the wire prints that sentence. The prompt states "on a normalized -1..+1
scale" and the model pattern-filled a range with the only number in front of
it. Wording can make that slip less likely (and the prompt now does), but a
generative slip cannot be closed by asking more nicely.

The bounds are CONSTANTS. So they are checked after generation: a range
claimed as a "scale" that is not the real scale is rewritten to the real
scale. The measured value is never touched — only the frame around it.

Pure module: no I/O, no DB, no model.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from app.services.theme_labels import human_theme_label, humanize_category

# The scale every tone figure in the Editor's Analysis is on (the prompt
# divides raw GDELT tone by 10 before showing it). Kept here so the prompt,
# the repair and the tests read one pair of numbers.
TONE_SCALE_LOW = -1.0
TONE_SCALE_HIGH = 1.0
# U+2212 MINUS, matching the typography of the served page ("−10…+10").
TONE_SCALE_PHRASE = "−1 to +1"

_NUM = r"[+\-−]?\d+(?:\.\d+)?"
# Range separators a model actually emits. A bare hyphen is deliberately NOT
# one: it is ambiguous with the minus sign of the next bound.
_SEP = r"(?:…|\.\.\.|\.\.|–|—|to|and)"

# "on the −0.48…−0.48 scale" / "on a -10 to +10 scale"
_ON_SCALE = re.compile(
    rf"(?P<lead>\b(?:on|along)\s+(?:the|a|an)\s+)"
    rf"(?P<a>{_NUM})\s*{_SEP}\s*(?P<b>{_NUM})"
    rf"(?P<tail>\s+scale\b)",
    re.IGNORECASE,
)
# "the scale of −0.48 to −0.48" / "a scale from -3 to 3"
_SCALE_OF = re.compile(
    rf"(?P<lead>\bscale\s+(?:of|from)\s+)"
    rf"(?P<a>{_NUM})\s*{_SEP}\s*(?P<b>{_NUM})",
    re.IGNORECASE,
)


def _as_float(raw: str) -> float | None:
    try:
        return float(raw.replace("−", "-").replace("+", ""))
    except ValueError:
        return None


def _bounds_are_true(a: str, b: str, low: float, high: float) -> bool:
    fa, fb = _as_float(a), _as_float(b)
    if fa is None or fb is None:
        return False
    return sorted((fa, fb)) == sorted((low, high))


def repair_scale_claims(
    text: str | None,
    low: float = TONE_SCALE_LOW,
    high: float = TONE_SCALE_HIGH,
    phrase: str = TONE_SCALE_PHRASE,
) -> str | None:
    """Rewrite any range asserted as *the scale* to the real bounds.

    A correct statement (`-1..+1`, `−1 to +1`, `±1`) is returned byte-identical,
    so this is a no-op on healthy prose and idempotent on repaired prose.
    Ranges that are not scales (volumes, counts) are never touched.
    """
    if not text:
        return text

    def _fix_on_scale(m: re.Match[str]) -> str:
        if _bounds_are_true(m.group("a"), m.group("b"), low, high):
            return m.group(0)
        return f"{m.group('lead')}{phrase}{m.group('tail')}"

    def _fix_scale_of(m: re.Match[str]) -> str:
        if _bounds_are_true(m.group("a"), m.group("b"), low, high):
            return m.group(0)
        return f"{m.group('lead')}{phrase}"

    out = _ON_SCALE.sub(_fix_on_scale, text)
    out = _SCALE_OF.sub(_fix_scale_of, out)
    return out


# --- the taxonomy the paragraph is allowed to describe ----------------------
#
# Re-judge §4a, third charge: the Analysis named GDELT theme codes while the
# chart directly below it named Atlas R3 categories, "with no reconciliation".
# The page settled that question in #249 — the category index is the
# user-facing lens and "By Theme" is only its fallback. This builds the prompt
# line from the SAME lane, in the SAME order, and NAMES it, so the two blocks
# on one screen cannot describe two different populations.

_CATEGORY_LANE = "Atlas categories"
_THEME_LANE = "GDELT themes"
_CHART_POINTER = "the same index charted below this paragraph"


def _row_get(row, key: str):
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return None


def taxonomy_line(
    categories: Sequence[Mapping] | None,
    themes: Sequence[Mapping] | None,
    limit: int = 5,
) -> str | None:
    """The prompt's "most-covered X" bullet, or ``None`` when nothing is nameable.

    Categories first (the served lens), themes only as the fallback the chart
    itself uses, and every theme code passes `human_theme_label` — a code with
    no human name is dropped, never title-cased into the sentence.
    """
    names: list[str] = []
    for row in categories or []:
        name = humanize_category(_row_get(row, "category"))
        if name:
            names.append(name)
        if len(names) >= limit:
            break
    if names:
        lane = _CATEGORY_LANE
    else:
        for row in themes or []:
            name = human_theme_label(_row_get(row, "theme"))
            if name:
                names.append(name)
            if len(names) >= limit:
                break
        lane = _THEME_LANE

    if not names:
        return None
    return f"- Most-covered {lane} ({_CHART_POINTER}): {', '.join(names)}"
