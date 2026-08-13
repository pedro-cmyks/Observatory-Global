"""The base every coverage/voice SHAPE claim is actually measured over.

X1, 2026-08-13 — the systemic class from the veracity scorecard
(`docs/research/gold/2026-08-13-veracidad-scorecard.md`, claim 3 REFUTADO,
claims 8 and 9 DIVERGEN).

Atlas told a blind panel that Colombia had "0% own voices" on its own 7.4
earthquake while El Tiempo, Noticias Caracol and El Colombiano were covering it
massively, and that the US press had not picked up the Hormuz tanker arc while
CNN ran live coverage. Neither number was wrong about what it measured. Both
were catastrophically wrong about what they were PRESENTED as measuring: **the
shape of Atlas's ingest, served as the shape of the world.**

This is the July silent-risk lesson returning in production UI — 5/5 "uncovered"
candidates turned out to be covered by outlets Atlas does not ingest
(`docs/methodology/silent-risk-detection.md`). There the conclusion was that
press silence is UNVERIFIABLE from this corpus. The same conclusion binds every
surface here: absence in Atlas is evidence about Atlas's feed set, never about
the world's press.

So the cure is structural rather than editorial. Every claim of this class reads
its base from this module, and every payload that serves one carries
`basis_field()`. Copy and data are then the same string by construction and
cannot drift apart — which is precisely how "of the 53 signals whose outlet home
country is known" (true) came to be read on screen as "Colombia said nothing"
(false).

Frontend mirror: `frontend-v2/src/lib/ingestBasis.ts` (kept in lockstep; both
sides are test-pinned).
"""
from __future__ import annotations

# ~220 hand-verified RSS feeds (219 URL literals in `services/ingest_rss.py` at
# the 2026-06-23 diversity baseline, plus later waves) across 126 countries and
# 31 languages, PLUS the GDELT firehose. Deliberately approximate: an exact
# count would go stale on the next feed wave and a stale precise number is worse
# than an honest round one.
POPULATION = "~220 curated feeds plus the GDELT firehose"

# The leading clause. Written to be dropped in front of a measured sentence so
# the qualification arrives BEFORE the claim, not as a footnote after it:
# "In what Atlas ingests, Timor-Leste ran 11.2x its own daily baseline ...".
IN_INGEST = "In what Atlas ingests"

# The fuller version, for tooltips and payload meta.
NOTE = (
    "Measured over what Atlas ingests: ~220 curated feeds across 126 countries "
    "plus the GDELT firehose. A zero here means none of THOSE outlets carried "
    "it — not that nobody did."
)


def absence_caveat(country_name: str) -> str:
    """The closing clause for a ZERO — the refutation written into the copy.

    A zero domestic count is the exact shape that misled the panel, so the
    sentence that carries it also carries its own refusal.
    """
    return (
        f"That is a gap in Atlas's own feed set — {POPULATION} — "
        f"not proof that {country_name}'s press stayed silent."
    )


def share_caveat() -> str:
    """The closing clause for a non-zero SHARE.

    A share is not a silence claim, but its denominator is still the ingest, so
    it must not be read as a share of the world's press.
    """
    return (
        f"Those shares are of Atlas's own feed set — {POPULATION} — "
        "not of everything published."
    )


def basis_field() -> dict[str, str]:
    """The `basis` block for any payload serving a coverage-shape claim."""
    return {
        "measured_over": "atlas_ingest",
        "population": POPULATION,
        "note": NOTE,
    }
