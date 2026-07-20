"""Umbrella child ENTAILMENT guard — pure floor/band math + bookkeeping (M1).

The llm-event judge groups event fragments into umbrella families but
over-merges (council evidence 2026-07-19: a Belgian Molenbeek shooting and
Chinese landslide children INSIDE the Venezuela earthquake umbrella). This
module decides, per child, whether it actually belongs to the family it was
grouped into. A child joins only if:

  (a) HARD FLOOR — its centroid cosine vs the family centroid clears a
      MEASURED per-family floor. Adaptive, never a fixed cutoff (2026-07-03
      adaptive-noise-floor precedent: thresholds VARY per centroid; fixed
      cutoffs always serve junk). The precedent's ``mean+2.5σ`` was measured
      on a BACKGROUND sample; measured on the family's OWN children sims the
      same idea inverts — the floor sits below the family's central tendency:

          floor = center − k·σ_eff

      Robustness: the very outlier we hunt contaminates mean/σ (it drags the
      mean toward itself and inflates σ, weakening its own rejection — a
      0.90 outlier in a 0.98 family survives mean−2.5σ). So center = median
      and spread = 1.4826·MAD (the σ-equivalent scaling), with
      σ_eff = max(spread, sigma_min) so an all-identical family still has a
      non-degenerate floor/band.

  (b) GRAY BAND — floor ≤ sim < floor + band·σ_eff is BORDERLINE: the cheap
      chunked judge confirms family membership (one call per umbrella,
      listing that umbrella's borderline children). Below the floor is out
      regardless of the judge (a AND b); at/above the band top is in with no
      LLM spend.

Small families (n < min_measure) cannot yield a stable measured floor →
every non-anchor child is BORDERLINE (measurement impossible is not
permission to hard-reject; the judge decides). The anchor (head) child is
exempt — it IS the umbrella's identity; a family reduced below 2 kept
children dissolves and everyone stays top-level.

Bookkeeping is total: every child gets exactly one verdict; judge outages
fail OPEN (child kept, loudly labeled ``kept_judge_unavailable``) — never a
silent rejection driven by infrastructure state. Rejected children stay
TOP-LEVEL active; nothing is ever dropped.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from statistics import median
from typing import Iterable, Mapping, Sequence

# MAD → σ-equivalent scale factor for a normal distribution.
_MAD_SIGMA = 1.4826

ACCEPT = "accept"
BORDERLINE = "borderline"
REJECT = "reject"


@dataclass(frozen=True)
class GuardParams:
    """Floor/band knobs — env-tunable at the call site, measured defaults.

    k:           floor distance in σ_eff units below the family center.
    band:        gray-band width in σ_eff units above the floor.
    min_measure: minimum children for a stable measured floor; below it the
                 family is judged, not floored.
    sigma_min:   σ_eff floor (raw-e5 same-event sims are compressed ~0.94+;
                 0.01 keeps the band meaningful when MAD collapses to 0).
    """

    k: float = 2.5
    band: float = 1.0
    min_measure: int = 4
    sigma_min: float = 0.01


@dataclass(frozen=True)
class FamilyFloor:
    center: float
    sigma_eff: float
    floor: float
    band_top: float


@dataclass(frozen=True)
class ChildVerdict:
    topic_id: int
    label: str
    sim: float
    zone: str   # accept | borderline | reject (floor zone; anchor exempt)
    final: str  # anchor | accepted | accepted_judge | rejected_floor |
    #             rejected_judge | kept_judge_unavailable
    kept: bool


@dataclass(frozen=True)
class FamilyGuardReport:
    head_label: str
    floor: FamilyFloor | None
    verdicts: list[ChildVerdict]

    @property
    def kept_ids(self) -> list[int]:
        return [v.topic_id for v in self.verdicts if v.kept]

    @property
    def rejected(self) -> list[ChildVerdict]:
        return [v for v in self.verdicts if not v.kept]

    @property
    def dissolved(self) -> bool:
        return len(self.kept_ids) < 2


def compute_family_floor(
    sims: Sequence[float], params: GuardParams = GuardParams()
) -> FamilyFloor | None:
    """Measured per-family floor over the family's own child↔centroid sims.

    Returns None when the family is too small to measure (n < min_measure) —
    the caller treats every child as borderline (judge decides)."""
    if len(sims) < params.min_measure:
        return None
    center = float(median(sims))
    mad = float(median(abs(s - center) for s in sims))
    sigma_eff = max(mad * _MAD_SIGMA, params.sigma_min)
    floor = center - params.k * sigma_eff
    return FamilyFloor(
        center=center,
        sigma_eff=sigma_eff,
        floor=floor,
        band_top=floor + params.band * sigma_eff,
    )


def classify_children(
    sims: Sequence[float], floor: FamilyFloor | None
) -> list[str]:
    """Zone per child: below floor = REJECT, inside the gray band =
    BORDERLINE, at/above band top = ACCEPT. No floor → all BORDERLINE."""
    if floor is None:
        return [BORDERLINE] * len(sims)
    zones: list[str] = []
    for s in sims:
        if s < floor.floor:
            zones.append(REJECT)
        elif s < floor.band_top:
            zones.append(BORDERLINE)
        else:
            zones.append(ACCEPT)
    return zones


def finalize_family(
    children: Sequence[tuple[int, str, float]],
    floor: FamilyFloor | None,
    judge: Mapping[int, bool] | None,
    *,
    anchor_id: int,
) -> list[ChildVerdict]:
    """Fold floor zones + judge verdicts into one bookkept verdict per child.

    children:  (topic_id, label, sim) triples.
    judge:     {topic_id: same_event} for the borderline children this
               family's confirm call resolved; None = judge unavailable.
               Missing ids fail OPEN per child (kept, loudly labeled).
    anchor_id: the head child — exempt (it anchors the entailment question).
    """
    zones = classify_children([s for _, _, s in children], floor)
    verdicts: list[ChildVerdict] = []
    for (topic_id, label, sim), zone in zip(children, zones):
        if topic_id == anchor_id:
            final, kept = "anchor", True
        elif zone == REJECT:
            final, kept = "rejected_floor", False  # (a) AND (b): judge can't save it
        elif zone == ACCEPT:
            final, kept = "accepted", True
        elif judge is None or topic_id not in judge:
            final, kept = "kept_judge_unavailable", True  # fail open, loudly
        elif judge[topic_id]:
            final, kept = "accepted_judge", True
        else:
            final, kept = "rejected_judge", False
        verdicts.append(ChildVerdict(topic_id, label, sim, zone, final, kept))
    return verdicts


# --- borderline confirm judge (one cheap call per umbrella) ----------------

CHILD_CONFIRM_SYSTEM = """You are an event-clustering auditor for a news-intelligence system.
An umbrella FAMILY groups narrative threads that report the SAME real-world
event or one tightly-coupled situation. You are given the family's anchor
event, a sample of its confirmed members, and CANDIDATE children whose
semantic similarity to the family is borderline.

For EACH candidate decide: does it report the SAME event/situation as the
family anchor? A different country, a different incident, a different
disaster is NOT the same event even in the same broad domain (an earthquake
in Venezuela and a landslide in China are DIFFERENT events).

Precision over recall: when unsure answer false — a wrongly absorbed child
corrupts the family; a wrongly separated child merely stays top-level.

Output STRICT JSON:
{"verdicts":[{"topic_id":<id>,"same_event":true|false}]}
Include EVERY candidate id exactly once. Nothing else."""


def child_confirm_user(
    family_label: str,
    core_labels: Sequence[str],
    candidates: Sequence[dict],
) -> str:
    core = (
        "\n".join(f"- {lab}" for lab in core_labels)
        if core_labels
        else "- (none — small family; judge each candidate against the anchor)"
    )
    cand = "\n".join(f'{c["id"]}\t{c.get("label") or ""}' for c in candidates)
    return (
        f"Family anchor: {family_label}\n"
        f"Confirmed members:\n{core}\n"
        f"Candidates (id, label):\n{cand}"
    )


def _first_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _coerce_id(tid: object) -> int | None:
    if isinstance(tid, bool):
        return None
    if isinstance(tid, int):
        return tid
    try:
        return int(str(tid).strip())
    except (TypeError, ValueError):
        return None


def _coerce_bool(v: object) -> bool | None:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        low = v.strip().lower()
        if low == "true":
            return True
        if low == "false":
            return False
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    return None


def parse_child_confirm_response(
    raw: str, candidate_ids: Iterable[int]
) -> dict[int, bool] | None:
    """Tolerant parse of the confirm judge's verdicts.

    None = PARSE FAILURE (judge unavailable → the caller fails open for the
    whole family). A parseable response yields {topic_id: same_event} for
    the candidate ids it resolves; hallucinated ids and non-boolean verdicts
    are dropped (those children fail open per child). {} is a valid
    parseable-but-empty verdict, distinct from None."""
    if not raw or not raw.strip():
        return None
    allowed = set(candidate_ids)
    for candidate in (raw, _first_json_object(raw)):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        verdicts = data.get("verdicts")
        if not isinstance(verdicts, list):
            continue
        out: dict[int, bool] = {}
        for entry in verdicts:
            if not isinstance(entry, dict):
                continue
            tid = _coerce_id(entry.get("topic_id"))
            same = _coerce_bool(entry.get("same_event"))
            if tid is None or same is None or tid not in allowed:
                continue
            out[tid] = same
        return out
    return None
