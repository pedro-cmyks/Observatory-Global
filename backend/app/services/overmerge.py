"""Over-merge detector — pure membership-multimodality math + decision (M4).

The merge sprint (label court 47.9% -> 24.3% failure) collapsed hundreds of
duplicate identities, but left a residual: ~220 OVER-MERGE blob-topics whose
members are a FUSION of 2+ distinct stories. They evade every existing guard:

  - the LABEL COURT passes them — 26% of the sprint's relabels are vague umbrella
    labels ("Diverse Local Incidents Across Regions", "Mixed Local News: Floods,
    Drones, and Housing", "Multiple Deadly Incidents Across Peru and Ukraine"),
    and a vague label trivially entails a diverse member set;
  - the CONTENT-JUNK classifier passes them — each member is a real news item, not
    a listicle or feed-dump;
  - the M2 RADIAL FLOOR (audit_topic_blackholes) passes them — the centroid falls
    BETWEEN the sub-clusters, so few members read "below floor".

The signal that catches them is MEMBERSHIP MULTIMODALITY: run 2-means over the
topic's member embeddings; if they split into TWO WELL-SEPARATED sub-clusters of
SUBSTANTIAL size, the topic fuses distinct stories.

THE FALSE-POSITIVE RISK (critical). A legit MEGA-STORY (Ukraine War: frontline +
diplomacy + sanctions + refugees) has internal sub-aspects a naive 2-means splits
too — but it is ONE story and must NOT be demoted. Three signals separate "sub-
aspects of one event" (KEEP) from "distinct events fused" (DEMOTE):

  (a) SEPARATION MAGNITUDE vs INTRA-CLUSTER SPREAD — a real fusion has a WIDE gap.
      gap_ratio = separation / intra_spread (the silhouette-style ratio). Sub-
      aspects of one story blend (narrow gap); two events stand apart (wide gap).
  (b) SHARED ACTORS — one story's sub-clusters share entities/countries (UA/RU on
      both sides); a fusion does not (Peru on one side, Ukraine on the other).
      A high overlap VETOES the demote regardless of the gap.
  (c) BORDERLINE band -> an LLM judge ("one story or two?", precision-first).

Precision-first is the whole posture: when unsure, KEEP. A wrongly demoted topic
loses a real story from serving; a wrongly kept blob merely stays a known blob the
next nightly rebuild can still split. So every ambiguity resolves toward KEEP.

Everything here is PURE (numpy only, deterministic seed) so the multimodality math,
the keep/demote decision, and the judge parse are unit-tested with zero DB. The
script `scripts/detect_overmerge.py` does the I/O (member-embedding fetch mirrors
`audit_topic_blackholes.py`; reversible demote active->candidate mirrors
`flag_junk_topics.py`).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

import numpy as np

# ---------------------------------------------------------------- constants
DEFAULT_SEED = 42

# ENV-tunable thresholds. Defaults are DEFENSIBLE SEEDS re-tuned in Measure
# (Step 2) against the real gap_ratio distribution + the relabel-ledger vague-blob
# set. Rationale for the seeds:
#   TAU_SEP      a genuine two-event fusion's sub-centroid gap is several times its
#                intra-cluster spread; a single blob's 2-means split sits near ~1.
#   TAU_SEP_LOW  below this the split is indistinguishable from splitting one blob
#                -> clearly unimodal (the borderline band's lower edge).
#   TAU_BAL      both sub-clusters must be SUBSTANTIAL; below this the smaller side
#                is a sliver of strays (the M2-floor case, not a fusion).
#   TAU_OVERLAP  sub-clusters sharing this fraction of actors read as one story's
#                aspects -> veto the demote (the mega-story guard).
#   MIN_MEMBERS  a topic below this cannot be a fusion of two substantial stories.
TAU_SEP = 1.8
TAU_SEP_LOW = 1.3
TAU_BAL = 0.20
TAU_OVERLAP = 0.5
MIN_MEMBERS = 12

# verdicts
KEEP = "keep"
DEMOTE = "demote"
BORDERLINE = "borderline"

_EPS = 1e-9


@dataclass(frozen=True)
class OverMergeParams:
    """Detector knobs — env-tunable at the call site, measured defaults."""

    tau_sep: float = TAU_SEP
    tau_sep_low: float = TAU_SEP_LOW
    tau_bal: float = TAU_BAL
    tau_overlap: float = TAU_OVERLAP
    min_members: int = MIN_MEMBERS
    seed: int = DEFAULT_SEED

    @classmethod
    def from_env(cls) -> "OverMergeParams":
        """Read overrides from ATLAS_OVERMERGE_* env vars (defaults otherwise)."""
        g = os.environ.get
        return cls(
            tau_sep=float(g("ATLAS_OVERMERGE_TAU_SEP", str(TAU_SEP))),
            tau_sep_low=float(g("ATLAS_OVERMERGE_TAU_SEP_LOW", str(TAU_SEP_LOW))),
            tau_bal=float(g("ATLAS_OVERMERGE_TAU_BAL", str(TAU_BAL))),
            tau_overlap=float(g("ATLAS_OVERMERGE_TAU_OVERLAP", str(TAU_OVERLAP))),
            min_members=int(g("ATLAS_OVERMERGE_MIN_MEMBERS", str(MIN_MEMBERS))),
            seed=int(g("ATLAS_OVERMERGE_SEED", str(DEFAULT_SEED))),
        )


@dataclass(frozen=True)
class SplitStats:
    """Multimodality of one topic's member matrix under its best 2-means split.

    separation      1 - cos(sub-centroid A, sub-centroid B). Cosine gap between
                    the two poles. Wide = two events; narrow = one story's aspects.
    intra_spread    mean member cosine-distance to its OWN sub-centroid. How
                    diffuse each sub-cluster is.
    gap_ratio       separation / intra_spread (floored). The silhouette-style
                    ratio — the primary demote signal (wide gap dominates spread).
    mean_silhouette standard 2-partition mean silhouette (cosine distance), in
                    [-1, 1]. Auxiliary, bounded — reported for Measure/tuning.
    balance         min(size_a, size_b) / n, in [0, 0.5]. Both sub-clusters
                    substantial <=> balance high.
    """

    n: int
    size_a: int
    size_b: int
    separation: float
    intra_spread: float
    gap_ratio: float
    mean_silhouette: float
    balance: float


# ---------------------------------------------------------------- geometry
def _unit(v: np.ndarray) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), _EPS)


def _normalize_rows(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    return mat / np.maximum(norms, _EPS)


def normalize_rows(mat: np.ndarray) -> np.ndarray:
    """Public row-L2-normalize. The script reuses this so its representative-
    headline selection sits in the SAME normalized space `partition` clusters in."""
    return _normalize_rows(np.asarray(mat, dtype=np.float64))


def two_means(mat: np.ndarray, *, seed: int = DEFAULT_SEED,
              n_iter: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic k=2 Lloyd's clustering (k-means++ seeded init).

    Euclidean on the (row-normalized) matrix is monotone in cosine, so the
    partition is a cosine partition. Empty-cluster-safe: a cluster that empties
    keeps its centroid (the degenerate all-identical input yields one non-empty
    cluster, read as balance 0 by `split_stats`). Same seed -> same labels."""
    mat = np.asarray(mat, dtype=np.float64)
    n = mat.shape[0]
    if n < 2:
        raise ValueError("two_means needs >= 2 rows")
    rng = np.random.default_rng(seed)
    # k-means++ init for k=2
    i0 = int(rng.integers(n))
    d2 = ((mat - mat[i0]) ** 2).sum(axis=1)
    total = float(d2.sum())
    if total <= _EPS:
        i1 = (i0 + 1) % n  # all points coincide with i0: any distinct second
    else:
        i1 = int(rng.choice(n, p=d2 / total))
    cent = np.vstack([mat[i0].copy(), mat[i1].copy()])
    labels: Optional[np.ndarray] = None
    for _ in range(n_iter):
        # (n, 2) squared distances to the two centroids
        dist = ((mat[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2)
        new = dist.argmin(axis=1)  # argmin ties -> first centroid (deterministic)
        if labels is not None and np.array_equal(new, labels):
            break
        labels = new
        for k in (0, 1):
            m = labels == k
            if m.any():
                cent[k] = mat[m].mean(axis=0)
    return labels, cent


def _mean_silhouette(mat: np.ndarray, labels: np.ndarray) -> float:
    """Mean silhouette over the 2-cluster partition, cosine distance.

    s(i) = (b - a) / max(a, b), a = mean dist to same-cluster others, b = mean
    dist to the other cluster. n is small (tens..hundreds of members)."""
    n = mat.shape[0]
    if n < 2:
        return 0.0
    dmat = 1.0 - mat @ mat.T
    np.fill_diagonal(dmat, 0.0)
    sils: list[float] = []
    for i in range(n):
        same = labels == labels[i]
        same[i] = False
        other = ~(labels == labels[i])
        n_same = int(same.sum())
        n_other = int(other.sum())
        if n_same == 0 or n_other == 0:
            sils.append(0.0)
            continue
        a = float(dmat[i, same].mean())
        b = float(dmat[i, other].mean())
        denom = max(a, b)
        sils.append((b - a) / denom if denom > _EPS else 0.0)
    return float(np.mean(sils))


def _stats_from_labels(matn: np.ndarray, labels: np.ndarray) -> SplitStats:
    """SplitStats from an already-normalized matrix + its 2-means labels."""
    n = matn.shape[0]
    a = matn[labels == 0]
    b = matn[labels == 1]
    size_a, size_b = a.shape[0], b.shape[0]
    if size_a == 0 or size_b == 0:
        return SplitStats(n=n, size_a=size_a, size_b=size_b, separation=0.0,
                          intra_spread=0.0, gap_ratio=0.0,
                          mean_silhouette=0.0, balance=0.0)
    ca = _unit(a.mean(axis=0))
    cb = _unit(b.mean(axis=0))
    separation = float(1.0 - ca @ cb)
    intra = float(np.concatenate([1.0 - a @ ca, 1.0 - b @ cb]).mean())
    gap_ratio = separation / max(intra, _EPS)
    mean_sil = _mean_silhouette(matn, labels)
    balance = min(size_a, size_b) / n
    return SplitStats(n=n, size_a=size_a, size_b=size_b, separation=separation,
                      intra_spread=intra, gap_ratio=gap_ratio,
                      mean_silhouette=mean_sil, balance=balance)


def partition(mat: np.ndarray, *, seed: int = DEFAULT_SEED
              ) -> tuple[Optional[np.ndarray], Optional[SplitStats]]:
    """One deterministic 2-means over the row-normalized matrix.

    Returns (labels, stats) so a caller that also needs the sub-cluster membership
    (e.g. representative headlines per side for the loud log / judge) gets labels
    that EXACTLY match the reported stats — no risk of a second, subtly-different
    2-means run. (None, None) if fewer than 2 rows."""
    mat = np.asarray(mat, dtype=np.float64)
    if mat.shape[0] < 2:
        return None, None
    matn = _normalize_rows(mat)
    labels, _cent = two_means(matn, seed=seed)
    return labels, _stats_from_labels(matn, labels)


def split_stats(mat: np.ndarray, *, seed: int = DEFAULT_SEED) -> Optional[SplitStats]:
    """Best-2-means multimodality of a member matrix. None if < 2 rows.

    A degenerate split (one empty sub-cluster, e.g. all-identical rows) is
    reported with balance 0 (separation/gap 0) so the decision keeps it."""
    _labels, stats = partition(mat, seed=seed)
    return stats


# ---------------------------------------------------------------- decision
def is_over_merge(stats: Optional[SplitStats],
                  params: OverMergeParams = OverMergeParams()) -> bool:
    """The pure structural predicate: a BALANCED split with a WIDE gap.

    over_merge <=> gap_ratio >= tau_sep AND balance >= tau_bal (and enough
    members). This is the raw multimodality flag; `decide` layers the shared-
    actor veto + borderline band on top of it for the final keep/demote routing."""
    if stats is None or stats.n < params.min_members:
        return False
    return stats.gap_ratio >= params.tau_sep and stats.balance >= params.tau_bal


def set_overlap(a: Iterable, b: Iterable) -> float:
    """Jaccard overlap of two actor/country sets, in [0, 1]. Empty union -> 0.0
    (no evidence of sharing, honestly not 1.0)."""
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


def country_dominant_overlap(actors_a: Iterable[str],
                             actors_b: Iterable[str]) -> float:
    """Shared-actor overlap that the DEMOTE veto reads — country-dominant.

    Actors are prefixed tokens: 'c:<CC>' for the subject country, 'p:<name>' for
    an NER person (see the script's `_member_actors`). The naive Jaccard over the
    COMBINED set is PERSON-SWAMPED: two halves of a single-country story share the
    one country token, but each news item names DIFFERENT people, so the many
    distinct person tokens dilute the intersection below any veto threshold — the
    single-country story then reads "distinct actors" and is wrongly demoted. That
    was the measured false-positive mechanism (the FP demotes were ~all single-
    country, persons dense and disjoint).

    Fix: score the two signals SEPARATELY and take the MAX. Sub-clusters that share
    EITHER their countries OR their people are one story. Country is the reliable
    signal (a genuine fusion has DISTINCT countries — "Peru and Ukraine"; NER
    persons are sparse/noisy and syndication-repeated); the person Jaccard only
    rescues a rare cross-/no-country ONE story (a summit, or NULL country codes) the
    country Jaccard misses. A single common wire-service person (Trump in both a
    Gaza item and a trade item) keeps the person Jaccard low, so it never spuriously
    vetoes a real cross-country fusion.
    """
    ca = {x for x in actors_a if isinstance(x, str) and x.startswith("c:")}
    cb = {x for x in actors_b if isinstance(x, str) and x.startswith("c:")}
    pa = {x for x in actors_a if isinstance(x, str) and x.startswith("p:")}
    pb = {x for x in actors_b if isinstance(x, str) and x.startswith("p:")}
    return max(set_overlap(ca, cb), set_overlap(pa, pb))


def decide(stats: Optional[SplitStats], entity_overlap: Optional[float],
           params: OverMergeParams = OverMergeParams()) -> tuple[str, str]:
    """Final keep/demote/borderline verdict + human reason. Precision-first.

    entity_overlap: shared-actor fraction between the two sub-clusters (from
    `set_overlap` over entities/countries), or None when unknown. A high overlap
    VETOES the demote (one story's aspects share actors — the mega-story guard).

    Order (each earlier branch is a KEEP that short-circuits toward safety):
      < min_members            -> KEEP  (too small to be a two-story fusion)
      balance < tau_bal        -> KEEP  (second sub-cluster is a sliver of strays)
      gap_ratio < tau_sep_low  -> KEEP  (unimodal: no wide gap)
      overlap >= tau_overlap   -> KEEP  (shared actors: one story)
      gap_ratio < tau_sep      -> BORDERLINE (judge decides; unavailable => KEEP)
      else                     -> DEMOTE (wide gap, balanced, distinct actors)
    """
    if stats is None or stats.n < params.min_members:
        return KEEP, "below min_members (too small to fuse two substantial stories)"
    if stats.balance < params.tau_bal:
        return KEEP, (f"unbalanced split (smaller side {stats.balance:.2f} < "
                      f"{params.tau_bal:.2f}: a sliver of strays, not a fusion)")
    if stats.gap_ratio < params.tau_sep_low:
        return KEEP, (f"unimodal (gap_ratio {stats.gap_ratio:.2f} < "
                      f"{params.tau_sep_low:.2f}: no wide gap)")
    if entity_overlap is not None and entity_overlap >= params.tau_overlap:
        return KEEP, (f"shared actors (overlap {entity_overlap:.2f} >= "
                      f"{params.tau_overlap:.2f}: one story, distinct aspects)")
    if stats.gap_ratio < params.tau_sep:
        return BORDERLINE, (f"gap_ratio {stats.gap_ratio:.2f} in borderline band "
                            f"[{params.tau_sep_low:.2f}, {params.tau_sep:.2f}) "
                            f"-> judge")
    return DEMOTE, (f"wide gap {stats.gap_ratio:.2f} >= {params.tau_sep:.2f}, "
                    f"balanced {stats.balance:.2f}, distinct actors "
                    f"(overlap {entity_overlap if entity_overlap is not None else 'n/a'})")


# ---------------------------------------------------------------- split judge
# Borderline topics only (one cheap DeepSeek call), mirrors the M1 umbrella
# child-guard confirm judge. The question is deliberately the INVERSE framing of
# a demote: the judge is asked to CONFIRM "two stories" before we act, and any
# ambiguity (unparseable / unavailable) fails toward KEEP.
SPLIT_JUDGE_SYSTEM = """You are an event-clustering auditor for a news-intelligence system.
A narrative TOPIC should cover ONE real-world story or one tightly-coupled
situation (an ongoing war's frontline + diplomacy + sanctions is ONE story; an
earthquake's deaths + rescues + aid is ONE story). You are shown a single topic
whose members split into TWO groups by embedding. Representative headlines from
each group are given.

Decide: do the two groups report the SAME story/situation, or TWO DISTINCT
unrelated stories fused into one topic? Different countries, different incidents,
different disasters are DISTINCT even in the same broad domain (a flood in
Indonesia and a housing bill in Peru are two stories).

Precision over recall: if the two groups plausibly belong to ONE story, answer
one_story. Only answer two_stories when they are clearly unrelated.

Output STRICT JSON, nothing else:
{"verdict":"one_story"} or {"verdict":"two_stories"}"""


def split_judge_user(label: str, headlines_a: Sequence[str],
                     headlines_b: Sequence[str]) -> str:
    def _fmt(hs: Sequence[str]) -> str:
        return "\n".join(f"- {h}" for h in hs) if hs else "- (none)"
    return (
        f"Topic label: {label}\n\n"
        f"Group A headlines:\n{_fmt(headlines_a)}\n\n"
        f"Group B headlines:\n{_fmt(headlines_b)}"
    )


def _first_json_object(text: str) -> Optional[str]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start:end + 1]


def apply_judge_verdict(judge: Optional[bool]) -> tuple[str, str]:
    """Map a split-judge answer to the FINAL verdict for a flagged candidate.

    The structural+country stage produces a CANDIDATE set (borderline OR demote);
    the judge is the precision gate that confirms each as truly two stories before
    it becomes a real demote. Precision-first, identical for both bands:

      True  (one_story)             -> KEEP   (the judge vetoes the demote)
      False (two_stories)           -> DEMOTE (confirmed fusion)
      None  (unavailable/unparsed)  -> KEEP   (never demote a real story on the
                                               absence of a positive confirmation)

    This is why the cross-country-SAME-story residual (a single global story split
    by outlet-country/language — a celebrity death, one war strike reported across
    Europe — that the country veto misses because the outlet countries genuinely
    differ) is caught: the judge, shown the two sides' headlines, returns one_story.
    """
    if judge is True:
        return KEEP, "judge: one story"
    if judge is False:
        return DEMOTE, "judge: two stories"
    return KEEP, "judge unavailable, KEPT (precision-first)"


def parse_split_judge_response(raw: str) -> Optional[bool]:
    """Tolerant parse of the split judge.

    Returns:
      True  -> "one_story"  => KEEP  (the judge vetoes the demote)
      False -> "two_stories" => the demote is confirmed
      None  -> unavailable / unparseable / unrecognized verdict => KEEP
               (precision-first: infrastructure state never drives a demote)
    """
    if not raw or not raw.strip():
        return None
    for candidate in (raw, _first_json_object(raw)):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        verdict = data.get("verdict")
        if isinstance(verdict, str):
            v = verdict.strip().lower()
            if v == "one_story":
                return True
            if v == "two_stories":
                return False
        return None  # parseable but not a recognized verdict -> KEEP
    return None
