"""Track C2 — churn-vs-narrative classifier over the C1 edge-snapshot store.

Spec: docs/superpowers/specs/2026-07-21-time-axis-versioned-relationships.md
§4 (the two-layer anchor — `identity_key` + entities — is how narrative
change is told apart from substrate churn) and §7 (honesty: "never present a
re-founded/merged topic as a narrative change").

This module is the MATH — pure (stdlib only, deterministic, zero DB), so the
classification logic is unit-tested without a database. The router
(`app/routers/edges.py`, Track C3) does the I/O: it fetches two
`topic_edge_snapshots` rows (one near a `since` date, one at the latest
snapshot), the CURRENT `dynamic_topics.state` for every identity_key touched
(the lifecycle lookup), and the entity backbone, then calls the functions
here.

The load-bearing question (spec §4): when a kinship edge between two topics
disappears between snapshots, did the STORY relationship end (narrative
change), or did the SUBSTRATE just churn (one side got re-founded/retired —
`dynamic_topics` rows are ephemeral by lifecycle design)? Presenting churn as
narrative change is a coverage≠corroboration-class lie (spec §0). The
disambiguation is the `identity_key` anchor itself: both sides still
`state='active'` at the later snapshot → the edge really dissolved
(NARRATIVE_CHANGE); either side retired/deprecated/unresolved → the vanished
edge is a SUBSTRATE_CHURN artifact, labeled as such, never narrative.

Divergence between the two anchors (§4 "divergence = signal, not bug"): the
coarse entity backbone (`entity_backbone_edges`, rarity-gated per #234) can
show two actors still co-occurring while no CURRENT thread-edge binds any of
their topics — a latent/dormant relationship, named honestly rather than
hidden. `classify_dormant_relationships` answers that question given the
identity_keys each entity currently appears in (a join the pure backbone rows
do not carry themselves — the caller supplies it).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping, Optional, Sequence

# ---------------------------------------------------------------- change types
FORMED = "formed"
WEAKENED = "weakened"
NARRATIVE_CHANGE = "narrative_change"
SUBSTRATE_CHURN = "substrate_churn"
STABLE = "stable"

CHANGE_TYPES = (FORMED, WEAKENED, NARRATIVE_CHANGE, SUBSTRATE_CHURN, STABLE)

# A dynamic_topics.state value that counts as "still alive" for the narrative-
# change test (migration 048: candidate/active/deprecated/retired). Only
# 'active' counts — 'deprecated'/'retired'/unresolved (missing identity_key)
# are all substrate-churn signals: the topic is not currently a live story.
ACTIVE_STATE = "active"

# Material weight-drop threshold (spec §3 "hermano → weaker"): the whitened
# cosine (migration 089) is NOT clamped to [0,1] and swings ~[-1,1], so an
# absolute drop is the simplest honest measure. Calibratable v1 default —
# tune once real snapshot pairs exist (C1 has just landed).
DEFAULT_WEAKEN_DELTA = 0.10

# ------------------------------------------------------- snapshot cadence
# The C1 writer runs on one nightly cron pass
# (`infra/launchd/com.atlas.edge-snapshot.plist`, 03:15 local) -> one stored
# snapshot per 24h. This is the cadence a diff between CONSECUTIVE snapshots
# implicitly claims when it shows no interval at all.
DEFAULT_SNAPSHOT_INTERVAL_HOURS = 24.0
# Cron drift is seconds and a late/early pass is normal; one hour of slack
# absorbs that without calling an ordinary night a gap. Anything beyond it is
# a real deviation the reader has to be told about.
DEFAULT_INTERVAL_TOLERANCE_HOURS = 1.0


@dataclass(frozen=True)
class SnapshotInterval:
    """How far apart the two snapshots being compared actually are, and
    whether that is the standard one-pass step the reader assumes.

    WHY this exists (measured, 2026-07-25): a half-written snapshot for that
    day was deleted, so the store holds 07-24 -> 07-26 as CONSECUTIVE passes
    48h apart. `classify_edge_changes` faithfully reports everything that
    changed across those 48h; presented with no interval, that reads as one
    day of narrative change. On prod the 48h step yields 9,789 formed edges
    against 6,934 / 6,304 for the adjacent 24h steps — a ~+50% phantom burst.
    Two days of change labeled as one day is the same class of lie as
    coverage-as-corroboration: the number is real, the frame is false.

    `missing_snapshot_passes` separates the two ways a step can be wide:
      - a GAP in the store (expected passes that produced nothing), vs
      - a deliberately WIDE window (`since` far in the past) that aggregates
        real intermediate passes.
    Both are non-standard; they mean different things and are named apart.
    """

    interval_hours: float
    expected_interval_hours: float
    intermediate_snapshots: int
    missing_snapshot_passes: int
    is_standard: bool
    note: str


def describe_snapshot_interval(
    t0: datetime,
    t1: datetime,
    *,
    intermediate_snapshots: int = 0,
    expected_interval_hours: float = DEFAULT_SNAPSHOT_INTERVAL_HOURS,
    tolerance_hours: float = DEFAULT_INTERVAL_TOLERANCE_HOURS,
) -> SnapshotInterval:
    """Describe the real distance between the two compared snapshot passes.

    `intermediate_snapshots` = stored passes strictly BETWEEN t0 and t1 (the
    caller counts them; this function is pure). With a healthy nightly store
    a consecutive pair has 0.

    Pure and total: any pair of timestamps yields a verdict plus a plain-language
    `note` (the receipt — same discipline as `EdgeChange.reason`), so a
    non-standard interval can never reach a surface unlabeled.
    """
    interval = round(abs((t1 - t0).total_seconds()) / 3600.0, 2)
    expected = float(expected_interval_hours)
    tol = abs(float(tolerance_hours))
    inter = max(0, int(intermediate_snapshots))

    # How many cadence passes this span covers, and how many of them left no
    # snapshot behind. Only meaningful once the span exceeds one pass.
    spanned_passes = int(round(interval / expected)) if expected > 0 else 0
    missing = max(0, spanned_passes - 1 - inter) if interval > expected + tol else 0

    standard = inter == 0 and interval > 0 and abs(interval - expected) <= tol

    if interval == 0:
        note = ("both ends of this diff are the same snapshot pass — there is no "
                "earlier pass to compare against, so no change can be reported")
    elif standard:
        note = f"one standard snapshot step ({interval:g}h, cadence {expected:g}h)"
    elif interval < expected - tol:
        note = (f"{interval:g}h apart — SHORTER than the standard {expected:g}h "
                "cadence, so this shows less than a full pass of change")
    elif missing > 0 and inter == 0:
        note = (f"{interval:g}h apart — {missing} snapshot "
                f"{'pass' if missing == 1 else 'passes'} missing from the store, "
                f"so this covers {interval / expected:.0f} days of change, not the "
                f"usual {expected:g}h")
    elif missing > 0:
        note = (f"{interval:g}h apart, aggregating {inter} intermediate "
                f"{'pass' if inter == 1 else 'passes'} with {missing} more missing "
                f"from the store — not a single {expected:g}h step")
    elif inter > 0:
        note = (f"{interval:g}h apart, aggregating {inter} intermediate snapshot "
                f"{'pass' if inter == 1 else 'passes'} — not a single "
                f"{expected:g}h step")
    else:
        note = (f"{interval:g}h apart — off the standard {expected:g}h cadence")

    return SnapshotInterval(
        interval_hours=interval,
        expected_interval_hours=expected,
        intermediate_snapshots=inter,
        missing_snapshot_passes=missing,
        is_standard=standard,
        note=note,
    )


def snapshot_interval_out(iv: SnapshotInterval) -> dict:
    """Serialize for the API payloads (`app/routers/edges.py`). One shared
    shape so the replay scrubber and the focus diff describe cadence
    identically."""
    return {
        "hours": iv.interval_hours,
        "expected_hours": iv.expected_interval_hours,
        "intermediate_snapshots": iv.intermediate_snapshots,
        "missing_snapshot_passes": iv.missing_snapshot_passes,
        "is_standard": iv.is_standard,
        "note": iv.note,
    }


def strip_focus_suffix(raw: str) -> str:
    """A focus ref may carry a served `slug--cc` country scope (the same
    convention `dossier._base_topic_id` / `threads.get_topic_relationship`
    strip) — return the bare topic/identity ref, keeping the raw id belongs
    to the caller (frontend maps results back to what it asked for)."""
    s = (raw or "").strip()
    if "--" in s:
        return s.split("--", 1)[0]
    return s


_DYNAMIC_TOPIC_ID_RE = re.compile(r"^dynamic-topic-(\d+)$")


def parse_dynamic_topic_id(base: str) -> Optional[int]:
    """`dynamic-topic-<n>` -> `<n>` as int, else None (an identity_key or an
    atlas slug — the caller resolves those differently)."""
    m = _DYNAMIC_TOPIC_ID_RE.match((base or "").strip())
    return int(m.group(1)) if m else None


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def _canonical_edge_map(rows: Iterable[Mapping[str, Any]]) -> dict[tuple[str, str], dict]:
    """Canonicalize a sequence of edge rows (each carrying identity_key_a/b,
    weight, basis — the exact shape `topic_edge_snapshots` rows / C1's
    `EdgeRow` have) into a pair-keyed map. Defensive re-canonicalization (sort
    a<=b) even though C1 already writes rows canonicalized, so this function
    tolerates any caller that hands rows in either order."""
    out: dict[tuple[str, str], dict] = {}
    for r in rows:
        a = str(r["identity_key_a"])
        b = str(r["identity_key_b"])
        key = _pair_key(a, b)
        weight = r.get("weight") if hasattr(r, "get") else r["weight"]
        basis = r.get("basis") if hasattr(r, "get") else r["basis"]
        out[key] = {
            "weight": None if weight is None else float(weight),
            "basis": basis,
        }
    return out


@dataclass(frozen=True)
class EdgeChange:
    """One classified change between two edge-snapshot passes.

    `reason` is the receipt (spec: "each labeled change carries its receipt
    — which anchor decided it") — always states in plain language WHY this
    change got its label, so a narrative_change/substrate_churn verdict is
    never a silent flag.
    """

    identity_key_a: str
    identity_key_b: str
    change_type: str
    weight_t0: Optional[float]
    weight_t1: Optional[float]
    delta: Optional[float]
    reason: str
    basis: Optional[str] = None


def classify_edge_changes(
    edges_t0: Sequence[Mapping[str, Any]],
    edges_t1: Sequence[Mapping[str, Any]],
    lifecycle: Mapping[str, str],
    *,
    weaken_delta: float = DEFAULT_WEAKEN_DELTA,
    include_stable: bool = False,
) -> list[EdgeChange]:
    """Classify every edge that appears in either snapshot.

    `edges_t0`/`edges_t1` are the identity_key-keyed rows at the earlier and
    later pass (any mapping/Record with `identity_key_a`, `identity_key_b`,
    `weight`, `basis` — an asyncpg Record or a plain dict both work).
    `lifecycle` maps identity_key -> its CURRENT `dynamic_topics.state`
    ('active' | 'candidate' | 'deprecated' | 'retired'); an identity_key
    absent from this map is treated as unresolved (the topic no longer
    exists at all under that key — a merge/deletion, still churn, never
    fabricated as narrative).

    Rules (spec §4, verbatim mapping):
      - present T0, absent T1, BOTH keys 'active' at T1        -> NARRATIVE_CHANGE
      - present T0, absent T1, one/both retired/deprecated/gone -> SUBSTRATE_CHURN
      - absent T0, present T1                                   -> FORMED
      - present both, weight dropped >= `weaken_delta`          -> WEAKENED
      - present both, no material change                        -> STABLE
        (only emitted when `include_stable=True` — the diff endpoint's
        default view is changes only; STABLE exists for callers that want a
        reconciling full accounting).

    A weight that both DROPS materially could in principle also flip a
    still-live edge into effective irrelevance, but that is still WEAKENED,
    not a churn/narrative question — churn/narrative only applies to edges
    that fully DISAPPEAR from the snapshot.
    """
    m0 = _canonical_edge_map(edges_t0)
    m1 = _canonical_edge_map(edges_t1)
    keys = set(m0) | set(m1)
    out: list[EdgeChange] = []
    for key in sorted(keys):
        a, b = key
        r0 = m0.get(key)
        r1 = m1.get(key)
        if r0 is None and r1 is not None:
            out.append(EdgeChange(
                identity_key_a=a, identity_key_b=b, change_type=FORMED,
                weight_t0=None, weight_t1=r1["weight"], delta=None,
                reason="edge absent at the earlier snapshot, present at the "
                       "later one — a new relationship formed",
                basis=r1["basis"],
            ))
            continue
        if r0 is not None and r1 is None:
            state_a = lifecycle.get(a)
            state_b = lifecycle.get(b)
            both_active = state_a == ACTIVE_STATE and state_b == ACTIVE_STATE
            if both_active:
                out.append(EdgeChange(
                    identity_key_a=a, identity_key_b=b, change_type=NARRATIVE_CHANGE,
                    weight_t0=r0["weight"], weight_t1=None, delta=None,
                    reason=(f"both {a} and {b} are still active topics with no "
                            "current edge between them — the connection dissolved"),
                    basis=r0["basis"],
                ))
            else:
                gone = []
                if state_a != ACTIVE_STATE:
                    gone.append(f"{a} is {state_a or 'unresolved (no longer found)'}")
                if state_b != ACTIVE_STATE:
                    gone.append(f"{b} is {state_b or 'unresolved (no longer found)'}")
                out.append(EdgeChange(
                    identity_key_a=a, identity_key_b=b, change_type=SUBSTRATE_CHURN,
                    weight_t0=r0["weight"], weight_t1=None, delta=None,
                    reason="substrate churn, not a narrative change: " + "; ".join(gone),
                    basis=r0["basis"],
                ))
            continue
        # present in both
        w0 = r0["weight"]
        w1 = r1["weight"]
        delta = None if (w0 is None or w1 is None) else round(w1 - w0, 6)
        basis = r1["basis"] or r0["basis"]
        if delta is not None and delta <= -abs(weaken_delta):
            out.append(EdgeChange(
                identity_key_a=a, identity_key_b=b, change_type=WEAKENED,
                weight_t0=w0, weight_t1=w1, delta=delta,
                reason=(f"weight dropped {abs(delta):.3f} "
                        f"(>= the material threshold {weaken_delta})"),
                basis=basis,
            ))
        elif include_stable:
            out.append(EdgeChange(
                identity_key_a=a, identity_key_b=b, change_type=STABLE,
                weight_t0=w0, weight_t1=w1, delta=delta,
                reason="present at both snapshots, no material change",
                basis=basis,
            ))
    return out


@dataclass(frozen=True)
class DormantRelationship:
    """A backbone entity pair that is ALIVE (co-occurring, rarity-gated) but
    has no CURRENT thread-edge binding any of the topics its two entities
    currently appear in — spec §4's "divergence between layers = signal":
    the actors still co-appear, no live story connects them right now, a
    bridge that was and may return. Explicitly co-occurrence, never an
    asserted relationship (spec §7)."""

    entity_a: str
    entity_b: str
    cooccur_count: int
    rarity_weight: float
    reason: str


def classify_dormant_relationships(
    backbone_rows: Sequence[Mapping[str, Any]],
    entity_active_identity_keys: Mapping[str, Sequence[str]],
    edges_t1: Sequence[Mapping[str, Any]],
) -> list[DormantRelationship]:
    """For each backbone pair (entity_a, entity_b), check whether ANY of the
    identity_keys entity_a currently appears in has a live edge (in
    `edges_t1`) to ANY identity_key entity_b currently appears in. No such
    edge -> DORMANT (co-occur, not currently bound by a live story).

    `entity_active_identity_keys` maps an entity name -> the identity_keys of
    topics it CURRENTLY (at T1) appears in — the join the pure backbone rows
    do not carry themselves; the caller (router) builds it from a bounded
    topic_members/signals_v2 scan restricted to active topics. An entity
    missing from this map has no currently-active topic at all; it is still
    eligible for DORMANT (the honest extreme case: the actors are not even
    in the same live story population right now) since an empty identity-key
    set can never be "bridged".

    Pure; never fabricates a bridge it cannot find — an entity pair with
    insufficient join data degrades to DORMANT rather than silently omitted,
    because "no data to prove a live connection" and "no live connection"
    both honestly mean the same thing for this signal (spec §7: co-occurrence
    is a fact regardless of whether we can currently trace its thread-edge).
    """
    edge_pairs = {
        _pair_key(str(r["identity_key_a"]), str(r["identity_key_b"]))
        for r in edges_t1
    }
    out: list[DormantRelationship] = []
    for r in backbone_rows:
        ea = str(r["entity_a"])
        eb = str(r["entity_b"])
        keys_a = entity_active_identity_keys.get(ea, ())
        keys_b = entity_active_identity_keys.get(eb, ())
        bridged = any(
            _pair_key(ka, kb) in edge_pairs
            for ka in keys_a for kb in keys_b if ka != kb
        )
        if bridged:
            continue
        out.append(DormantRelationship(
            entity_a=ea, entity_b=eb,
            cooccur_count=int(r["cooccur_count"]),
            rarity_weight=float(r["rarity_weight"]),
            reason=(
                f"{ea} and {eb} still co-occur in the entity backbone "
                f"({r['cooccur_count']}x) but no current thread-edge binds "
                "their topics — a latent relationship, not an asserted one"
            ),
        ))
    return out
