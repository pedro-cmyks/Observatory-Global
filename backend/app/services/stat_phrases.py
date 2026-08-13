"""Plain-language companions for the stats the Brief serves as PROSE.

X4, 2026-08-13 — C5 of the blind college
(`docs/research/ux-council/2026-08-13-colegio-ciego.md`): four of eight
personas, the entire non-analyst range, could not parse the grading system.
The witnesses included this module's own former output — "surprise 2.6σ over
its own baseline, velocity +0.59 (log-volume per 6 h)". The retired teacher:
*"I taught school for forty years and cannot parse that."*

Why a module and not a copy edit: the panel's structural note is that a reader
who cannot parse the grading system takes the honesty ON FAITH. Jargon does not
merely obscure the receipts — it disables the trust mechanism the receipts exist
to provide, which is the whole product.

THE RULE, both halves load-bearing:

1. **The number stays.** The analyst and news-junkie personas named the numbers
   as the differentiator. This is translation, not simplification: the plain
   clause LEADS and the measured clause follows it in the same sentence.
2. **The phrase never out-claims the number.** Every band restates what was
   measured and nothing else — no cause, no forecast, no comparison the
   statistic did not make. `surprise` is a magnitude against a story's OWN
   Kalman baseline, so its phrase talks about that story and never the field.

Frontend mirror: `frontend-v2/src/lib/statPhrases.ts` (kept in lockstep; both
sides are test-pinned to the same words).

Deliberately does NOT restate the ingest base — that is X1's job
(`ingest_basis.py`), and `gap_prose` already opens with it.
"""
from __future__ import annotations

import math
from typing import Any

# Small whole counts read better as words — newspaper style, not code style.
_COUNT_WORDS = (
    "", "", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten", "eleven", "twelve",
)


def _num(value: Any) -> float | None:
    """A finite float, or None. A stat that was not measured has no phrase."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


# ── the acceleration pair (LO QUE SUBE) ────────────────────────────────────

def surprise_phrase(surprise: Any) -> str | None:
    """`surprise` in words — standard deviations against the story's OWN
    Kalman baseline, so every band compares the story to itself.

    The section's bar is 2.5, so the middle band is the one readers meet.
    """
    sigma = _num(surprise)
    if sigma is None:
        return None
    if sigma >= 4:
        return "far beyond anything this story normally does"
    if sigma >= 2.5:
        return "rising much faster than its own normal pace"
    if sigma >= 1.5:
        return "rising faster than its own normal pace"
    # A surprise is a MAGNITUDE: a small or negative reading means "nothing
    # unusual", never "falling". Direction is `velocity`'s to report.
    return "close to its own normal pace"


def velocity_phrase(velocity: Any) -> str | None:
    """`velocity` in words — the smoothed slope.

    The unit (change in log-volume per 6 h step) is meaningless to a lay reader
    and actively misleading if guessed at as a per-hour rate, so the phrase
    carries only the sign, which is the part that is plainly true.
    """
    slope = _num(velocity)
    if slope is None:
        return None
    if slope > 0:
        return "still speeding up"
    if slope < 0:
        return "already slowing down"
    return "holding steady"


def rising_plain(*, surprise: Any, velocity: Any) -> str | None:
    """The plain clause the why-now LEADS with, before the numbers.

    Sentence-cased because it opens the sentence. Either half may be missing —
    an older seal, or a lane that answered on one field — and the clause
    degrades to whichever was measured rather than inventing the other.
    """
    rising = surprise_phrase(surprise)
    slope = velocity_phrase(velocity)
    if rising and slope:
        head = rising[len("rising "):] if rising.startswith("rising ") else rising
        lead = "Rising " + head if rising.startswith("rising ") else head[:1].upper() + head[1:]
        return f"{lead}, and {slope}"
    if rising:
        return rising[:1].upper() + rising[1:]
    if slope:
        return slope[:1].upper() + slope[1:]
    return None


# ── the × multiplier (EL VACÍO) ────────────────────────────────────────────

def times_phrase(multiplier: Any, *, of: str = "its usual coverage") -> str | None:
    """A ratio in words: `12` becomes "twelve times its usual coverage".

    Rounding is allowed only where it cannot change the claim — within 0.25 of
    a whole number. Anything else keeps its decimal behind an explicit "about",
    so 1.4x never reads as "once", i.e. as "nothing is happening".
    """
    value = _num(multiplier)
    if value is None or value <= 0:
        return None
    rounded = round(value)
    clean = abs(value - rounded) < 0.25

    if clean and rounded <= 1:
        return f"about {of}"
    if clean and rounded == 2:
        return f"twice {of}"
    if clean and rounded <= 12:
        return f"{_COUNT_WORDS[rounded]} times {of}"
    if clean:
        return f"{rounded} times {of}"
    return f"about {value:.1f} times {of}"
