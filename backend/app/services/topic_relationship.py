"""Unified Engine F0.4 — topic relationship classification (spec
2026-06-29-atlas-unified-engine §9.2).

The 5 #168 relationship types are COMPUTED from the typed `topic_members` role
counts — not a new pipeline, a projection of the one membership model. This
closes the serving half of #168 and re-homes #172's silent-risk on the
discussion/evidence RATIO (a relative imbalance) rather than the disproved
absolute-zero pageview metric.

Honesty invariant (carried from the engine spec §15): evidence is press/
institutional only; discussion/mood are forum/social (`verified=false`) and are
NEVER folded into the evidence count. The classifier reads the separated counts;
it does not mix them.

Pure + deterministic → unit-tested in `tests/test_topic_relationship.py`.
"""
from __future__ import annotations

from typing import Any

# ── Calibratable v1 thresholds (documented; tune from labelled topics later) ──
# Press is "negligible" below this share of total narrative members → the topic
# is public/social/silent rather than media-led. A RATIO reframe (#172), not
# absolute zero: a couple of stray press rows don't disqualify a silent risk.
SILENT_EVIDENCE_FRAC = 0.05
# With press meaningfully present, discussion at/above this multiple of evidence
# flips media-led → public-led (the public conversation outweighs the coverage).
PUBLIC_LED_RATIO = 1.0

RELATIONSHIP_TYPES = (
    "media-led",
    "public-led",
    "social-led",
    "silent-risk",
    "uncoupled-attention",
)


def classify_relationship(
    *,
    evidence: int,
    discussion: int,
    mood: int,
    movement: int = 0,
) -> dict[str, Any]:
    """Classify a topic's press-vs-public relationship from its role counts.

    - **media-led** — evidence present and outweighs discussion.
    - **public-led** — evidence present but discussion outweighs it (public
      conversation is ahead of the coverage).
    - **social-led** — discussion present, press negligible, no concern signal.
    - **silent-risk** — discussion/mood present, evidence ≈ 0 (the imbalance
      worth flagging — the public is concerned, the press is not covering it).
    - **uncoupled-attention** — no narrative binding at all (the honest gap).
    """
    ev = max(int(evidence or 0), 0)
    di = max(int(discussion or 0), 0)
    mo = max(int(mood or 0), 0)
    mv = max(int(movement or 0), 0)

    total = ev + di + mo
    public_ratio = round(di / ev, 3) if ev > 0 else None
    evidence_frac = round(ev / total, 3) if total > 0 else None

    if total == 0:
        rel = "uncoupled-attention"
        rationale = (
            "no evidence/discussion/mood members"
            + (f"; {mv} movement signal(s) only" if mv else "")
        )
    elif evidence_frac is not None and evidence_frac < SILENT_EVIDENCE_FRAC:
        # press negligible relative to public attention
        if mo > 0:
            rel = "silent-risk"
            rationale = (
                f"evidence≈0 ({evidence_frac:.0%} of members) with {mo} mood "
                f"+ {di} discussion — public concern, press absent"
            )
        else:
            rel = "social-led"
            rationale = (
                f"discussion {di} dominates, press negligible "
                f"({evidence_frac:.0%} of members)"
            )
    elif di == 0 and mo == 0:
        rel = "media-led"
        rationale = f"press-only: {ev} evidence, no discussion/mood"
    elif public_ratio is not None and public_ratio >= PUBLIC_LED_RATIO:
        rel = "public-led"
        rationale = (
            f"discussion {di} ≥ evidence {ev} (ratio {public_ratio}) — "
            f"public conversation ahead of coverage"
        )
    else:
        rel = "media-led"
        rationale = (
            f"evidence {ev} outweighs discussion {di} (ratio {public_ratio})"
        )

    return {
        "relationship": rel,
        "evidence_count": ev,
        "discussion_count": di,
        "mood_count": mo,
        "movement_count": mv,
        "public_ratio": public_ratio,
        "evidence_fraction": evidence_frac,
        "rationale": rationale,
        # honesty: discussion/mood are verified=false social; never evidence.
        "verified_evidence_only": True,
    }
