"""The walked constellation — multi-hop transitive kinship over the topic graph.

Spec: docs/superpowers/specs/2026-07-21-multi-hop-transitive-chains.md.

The reframe (spec §0): Atlas edges measure ASSOCIATION (semantic cosine, shared
country/actor) — never causation or direction. A chain drawn over association
edges and rendered as a chain silently imports the causation the math never had.
The resolution is KINSHIP + honest distance: the walk REACHES a far story from an
analyst's pin, but labels it *primo Nº, no direct line, only this trail* — the
analyst's mind supplies the causal reading, the app supplies only the measured
walk with receipts.

This module is the MATH — PURE (numpy only, deterministic), zero DB, so the walk,
the depth brake, the blob penalty, the dedup fold and the rarity formula are all
unit-tested with no I/O. The endpoint (routers/dossier.py `/walk`) does the I/O:
it fetches centroids, applies the ONE global whitening (services/whitening.py —
NOT the raw universe kNN graph, NOT the dossier per-request refit; spec §2.2), and
calls `walk_constellation` here.

Honesty model (spec §1):
  - v1 is UNDIRECTED — no causal arrow, ever. A link = kinship.
  - the chain is never asserted; the DEGREE label ("primo 3º") carries the
    honest distance by construction.
  - every hop carries a receipt: the measured whitened cosine (the per-hop
    weight) + the basis. Glass-box.

Locked numbers (two probe rounds, spec §2.3/§2.4/§2.6 — do NOT re-derive):
  REL_FLOOR 0.35 · HOP_CAP 3 (both required — the relative floor alone leaks 4º
  on tight seeds) · DEDUP_TAU 0.85 · actor weight 0.30 + 0.68·norm_rarity.
"""
from __future__ import annotations

import heapq
import os
import re
from collections import Counter
from dataclasses import dataclass
from math import log2
from typing import Optional, Sequence

import numpy as np

# ---------------------------------------------------------------- locked knobs
# Depth brake (spec §2.3, Phase-0b LOCKED over 5 seeds bfh 0.544→0.863). A fixed
# absolute floor is seed-sensitive (0.20 self-terminates on a diffuse seed but
# explodes to 5º+ on a tight one); the RELATIVE floor stabilizes depth but leaks
# 4º on tight seeds without the hard hop-cap — BOTH are load-bearing.
REL_FLOOR = 0.35          # expand while (acc / seed_best_first_hop) >= this
HOP_CAP = 3               # hard backstop — the relative floor leaks 4º without it
K_NEIGHBORS = 6           # top-k whitened neighbors per node (probe locked on 6)

# Display dedup (spec §2.6, Phase-0b): fold same-event fragments so the walk shows
# one "US Strikes on Iran," not twelve near-duplicate centroids. 0.85 folds
# genuine same-event variants (WC-final 0.86, US-Iran-strikes 0.87–0.91) while
# distinct stories survive; 0.70–0.80 over-merge distinct stories, 0.90 under-folds.
DEDUP_TAU = 0.85

# Blob-connector penalty (spec §2.4 edge-level). A vague grab-bag topic ("Global
# Political Shifts…") glues spurious cross-domain hops. Blob ≠ hub and cosine
# coherence does NOT separate them; the measured discriminator is 2-hop
# neighborhood category-ENTROPY (genuine event-hubs ent≈0.0–0.6; blobs ent≈2.0–2.9)
# gated on being an actual connector (in-degree). A hop OUT of a flagged blob is
# down-weighted so the glued cross-domain trail dies faster at the floor; genuine
# event-hubs (low entropy) pass untouched. The raw cosine still rides the receipt;
# only the accumulated thickness (and thus the brake) sees the penalty.
BLOB_PENALTY = 0.5        # onward-hop multiplier through a flagged blob connector
BLOB_ENTROPY_TAU = 1.5    # 2-hop category entropy above this = topically-spread
BLOB_INDEG_MIN = 3        # …and enough in-degree to be a connector, not a stray

# Actor-rarity edge weight base (spec §2.4 actor-level, S2 LOCKED on real df).
# The #234 gate-removal alone does NOT thin the link — the old formula
# `0.65 + 0.15·(1/df)` has a 0.65 BASE, so a ubiquitous actor (df=14) still scores
# 0.66, above every gate, and now propagates transitively (a worse regression).
# Rarity must scale the BASE: `0.30 + 0.68·norm_rarity`. Measured on dt-31's 229
# actors — "donald trump" (df=29) drops 0.655→0.300 (below the 0.50 gate, barely
# propagates); a rare df=2 actor stays 0.628; crossover at the gate ≈ df 3.
ACTOR_WEIGHT_BASE = 0.30
ACTOR_WEIGHT_SPAN = 0.68


@dataclass(frozen=True)
class WalkParams:
    """Walk knobs — env-tunable at the call site, LOCKED defaults."""

    rel_floor: float = REL_FLOOR
    hop_cap: int = HOP_CAP
    k: int = K_NEIGHBORS
    blob_penalty: float = BLOB_PENALTY
    blob_entropy_tau: float = BLOB_ENTROPY_TAU
    blob_indeg_min: int = BLOB_INDEG_MIN
    dedup_tau: float = DEDUP_TAU

    @classmethod
    def from_env(cls) -> "WalkParams":
        g = os.environ.get
        return cls(
            rel_floor=float(g("ATLAS_WALK_REL_FLOOR", str(REL_FLOOR))),
            hop_cap=int(g("ATLAS_WALK_HOP_CAP", str(HOP_CAP))),
            k=int(g("ATLAS_WALK_K", str(K_NEIGHBORS))),
            blob_penalty=float(g("ATLAS_WALK_BLOB_PENALTY", str(BLOB_PENALTY))),
            blob_entropy_tau=float(g("ATLAS_WALK_BLOB_ENTROPY_TAU", str(BLOB_ENTROPY_TAU))),
            blob_indeg_min=int(g("ATLAS_WALK_BLOB_INDEG_MIN", str(BLOB_INDEG_MIN))),
            dedup_tau=float(g("ATLAS_WALK_DEDUP_TAU", str(DEDUP_TAU))),
        )


@dataclass(frozen=True)
class KnnGraph:
    """Sparse top-k whitened-cosine neighbor graph over N topic centroids.

    nbrs[i] = [(j, whitened_cos), …] top-k, descending. bfh[i] = i's best (first)
    neighbor cosine — the seed's spanning tightness, the denominator of the
    relative floor. indeg[i] = how many nodes list i as a neighbor (connector-ness).
    """

    nbrs: dict[int, list[tuple[int, float]]]
    bfh: np.ndarray
    indeg: np.ndarray
    n: int


@dataclass(frozen=True)
class ReachedNode:
    """One topic reached by the walk (never a seed itself).

    degree      hop-count of the MAX-PRODUCT path from its origin seed (spec B1 —
                max-product can prefer a longer strong path over a shorter weak one,
                so degree is the strong-path length, stated explicitly).
    kinship     'hermano' iff a DIRECT measured edge to a seed exists (promotion
                §2.5); else 'primo'. Degree ≥ 2 primos are the transitive cousins.
    acc_weight  product of the (penalty-adjusted) hop weights — the trail strength,
                which IS the far-primo's line thickness (spec §1.5: one number,
                honesty + brake).
    via_parent  the node this was reached THROUGH (the previous hop), or None.
    via_weight  the RAW whitened cosine of that final hop — the receipt (never the
                penalty-adjusted value; the penalty is a walk-internal brake).
    origin_seed the seed the max-product path started from.
    through_blob whether the final hop passed OUT of a flagged blob connector
                (surfaced so the UI can mark the trail "via a grab-bag topic").
    """

    index: int
    degree: int
    kinship: str
    acc_weight: float
    via_parent: Optional[int]
    via_weight: float
    origin_seed: int
    through_blob: bool


# ---------------------------------------------------------------- graph build
def build_knn_graph(whitened: np.ndarray, k: int = K_NEIGHBORS) -> KnnGraph:
    """Top-k whitened-cosine neighbor graph. `whitened` rows are UNIT-NORM
    (services/whitening.apply_whitening output), so a dot product is the whitened
    cosine — commit to the ONE global space (spec §2.2), never the raw universe
    graph or a per-request refit.

    Pure and deterministic. O(N²) in memory for the sim matrix — fine for the
    ~1.6k active topics (cached); the endpoint is the only caller and it caches.
    """
    W = np.asarray(whitened, dtype=np.float32)
    n = W.shape[0]
    nbrs: dict[int, list[tuple[int, float]]] = {}
    bfh = np.zeros(n, dtype=np.float32)
    indeg = np.zeros(n, dtype=np.int32)
    if n == 0:
        return KnnGraph(nbrs={}, bfh=bfh, indeg=indeg, n=0)
    S = W @ W.T
    np.fill_diagonal(S, -1.0)
    kk = min(k, max(1, n - 1))
    for i in range(n):
        row = S[i]
        # argpartition top-kk then sort those descending (probe TASK 2)
        part = np.argpartition(row, -kk)[-kk:]
        order = part[np.argsort(-row[part])]
        lst = [(int(j), float(row[j])) for j in order]
        nbrs[i] = lst
        bfh[i] = lst[0][1] if lst else 0.0
        for j, _s in lst:
            indeg[j] += 1
    return KnnGraph(nbrs=nbrs, bfh=bfh, indeg=indeg, n=n)


# ---------------------------------------------------------------- blob flags
def category_entropy(nbrs: dict[int, list[tuple[int, float]]],
                     categories: Sequence[Optional[str]], i: int) -> float:
    """Shannon entropy (bits) of the CATEGORIES over node i's 2-hop kNN
    neighborhood. Genuine event-hubs concentrate in one category (low entropy);
    vague blobs fan across many (high). Pure; the cheap first-pass discriminator
    (spec §2.4). '?' stands in for a missing category so the count is stable."""
    cc: Counter = Counter()
    for j, _ in nbrs.get(i, []):
        cc[categories[j] or "?"] += 1
        for k2, _ in nbrs.get(j, []):
            cc[categories[k2] or "?"] += 1
    tot = sum(cc.values())
    if tot == 0:
        return 0.0
    return float(-sum((v / tot) * log2(v / tot) for v in cc.values()))


def blob_connector_flags(graph: KnnGraph, categories: Sequence[Optional[str]],
                         params: WalkParams = WalkParams()) -> set[int]:
    """The set of node indices that are vague-blob CONNECTORS: high 2-hop category
    entropy AND enough in-degree to actually glue trails. Both conditions matter —
    a genuine event-hub (US-Iran) has high in-degree but LOW entropy (its neighbors
    are one category) so it is NOT flagged; a topically-spread grab-bag many stories
    point to IS. Flagged UP FRONT (intrinsic), before dedup + the walk penalty
    (spec §2.4 pipeline order — the dedup is itself confounded by blobs)."""
    flags: set[int] = set()
    for i in range(graph.n):
        if int(graph.indeg[i]) < params.blob_indeg_min:
            continue
        if category_entropy(graph.nbrs, categories, i) >= params.blob_entropy_tau:
            flags.add(i)
    return flags


# ---------------------------------------------------------------- the walk
def max_product_walk(seeds: Sequence[int], graph: KnnGraph,
                     params: WalkParams = WalkParams(),
                     blob_flags: Optional[set[int]] = None) -> dict[int, ReachedNode]:
    """From-pins, multi-source, max-product walk with the LOCKED depth brake.

    Accumulated weight along a path = PRODUCT of the hop weights (spec §2.3). Depth
    follows the real strength of the trail: a node is EXPANDED only while its
    accumulated weight ≥ `rel_floor · bfh[origin_seed]` (relative to that seed's
    strongest available trail) AND its hop-count < `hop_cap` (the hard backstop).
    Both required — the relative floor alone leaks 4º on tight seeds.

    Multi-source: every pin starts at acc 1.0 in one priority queue; each node
    keeps its best product from ANY seed, and the floor is measured against THAT
    origin seed's bfh — a strong-seed trail reaches further, a weak-seed trail dies
    early, independently. Seeds are never returned (they are the pins, already shown).

    Blob penalty (spec §2.4): a hop OUT of a flagged blob connector contributes a
    penalized weight to the accumulated product (the brake), so glued cross-domain
    trails die faster; the receipt keeps the RAW hop cosine.
    """
    blob_flags = blob_flags or set()
    seed_set = set(seeds)
    acc: dict[int, float] = {}
    hop: dict[int, int] = {}
    origin: dict[int, int] = {}
    via: dict[int, tuple[Optional[int], float, bool]] = {}
    pq: list[tuple[float, int]] = []
    for s in seed_set:
        acc[s] = 1.0
        hop[s] = 0
        origin[s] = s
        via[s] = (None, 1.0, False)
        heapq.heappush(pq, (-1.0, s))

    while pq:
        na, u = heapq.heappop(pq)
        a = -na
        if a < acc.get(u, -1.0) - 1e-12:
            continue  # stale heap entry (a better path already settled u)
        floor_u = params.rel_floor * float(graph.bfh[origin[u]])
        if a < floor_u:
            continue  # reached but below its trail's floor — do NOT expand
        if hop[u] >= params.hop_cap:
            continue  # hard backstop
        u_is_blob = u in blob_flags and u not in seed_set
        for j, w in graph.nbrs.get(u, []):
            w_eff = w * params.blob_penalty if u_is_blob else w
            cand = a * w_eff
            floor_j = params.rel_floor * float(graph.bfh[origin[u]])
            if cand >= floor_j and cand > acc.get(j, 0.0):
                acc[j] = cand
                hop[j] = hop[u] + 1
                origin[j] = origin[u]
                via[j] = (u, float(w), u_is_blob)
                heapq.heappush(pq, (-cand, j))

    # Direct-edge kinship (spec §2.5): a reached node is a HERMANO iff it shares a
    # direct measured edge with any seed (either direction — v1 is undirected).
    direct: set[int] = set()
    for s in seed_set:
        for j, _ in graph.nbrs.get(s, []):
            direct.add(j)
    for i in range(graph.n):
        if i in seed_set:
            continue
        if any(s == j for j, _ in graph.nbrs.get(i, []) for s in seed_set):
            direct.add(i)

    reached: dict[int, ReachedNode] = {}
    for i, a in acc.items():
        if i in seed_set:
            continue
        floor_i = params.rel_floor * float(graph.bfh[origin[i]])
        if a < floor_i:
            continue  # reached-but-not-kept (below floor): honest omission
        parent, vw, thru = via[i]
        reached[i] = ReachedNode(
            index=i,
            degree=hop[i],
            kinship="hermano" if i in direct else "primo",
            acc_weight=round(a, 6),
            via_parent=parent,
            via_weight=round(vw, 6),
            origin_seed=origin[i],
            through_blob=thru,
        )
    return reached


# ---------------------------------------------------------------- dedup
def dedup_reached(order: Sequence[int], whitened: np.ndarray,
                  tau: float = DEDUP_TAU) -> tuple[list[int], dict[int, list[int]]]:
    """Greedy same-event fold of the reached set (spec §2.6). `order` is the reached
    indices in PRIORITY order (strongest/nearest first — kept as representatives).
    A node folds into the first representative it exceeds `tau` whitened cosine to.
    Returns (representatives, fold_map rep→[folded]). Pure; a display mask over the
    substrate's under-merge debt, run AFTER blob-flagging, BEFORE the walk penalty."""
    W = np.asarray(whitened, dtype=np.float32)
    reps: list[int] = []
    fold_map: dict[int, list[int]] = {}
    for i in order:
        hit = None
        for r in reps:
            if float(W[i] @ W[r]) >= tau:
                hit = r
                break
        if hit is None:
            reps.append(i)
            fold_map[i] = []
        else:
            fold_map[hit].append(i)
    return reps, fold_map


# ---------------------------------------------------------------- typed dest
def match_destination(label: str, category: Optional[str], terms: Sequence[str],
                      categories: Optional[set[str]] = None) -> Optional[str]:
    """Typed-destination match (spec §2.7): a WORD-BOUNDARY term hit in the label OR
    a category membership — NEVER a substring (the probe's "Ukraine political
    t**oil**" false positive). Returns the matched reason (category name or term) or
    None. Case-insensitive; terms are matched with `\\b` boundaries."""
    if category and categories and category.lower() in {c.lower() for c in categories}:
        return category
    low = (label or "").lower()
    for t in terms:
        t = t.strip().lower()
        if not t:
            continue
        if re.search(r"\b" + re.escape(t) + r"\b", low):
            return t
    return None


# ---------------------------------------------------------------- #234 rarity
def norm_rarity(df: int, df_max: int) -> float:
    """Min-max-normalized actor rarity in [0, 1] (spec §2.4 / #234). df = the
    actor's document-frequency in view; df_max = the max df in the actor set.
    df=1 → 1.0 (unique), df=df_max → 0.0 (ubiquitous). Guards df≤0 and df_max≤1."""
    df = max(1, int(df))
    df_max = max(1, int(df_max))
    if df_max <= 1:
        return 1.0 if df == 1 else 0.0
    r = 1.0 / df
    r_min = 1.0 / df_max
    r_max = 1.0
    denom = r_max - r_min
    if denom <= 0:
        return 0.0
    return float((r - r_min) / denom)


def actor_edge_weight(dfs: Sequence[int], df_max: int) -> float:
    """Shared-actor edge weight (spec §2.4 LOCKED `0.30 + 0.68·norm_rarity`), taken
    over the RAREST shared actor (max norm_rarity) so a single distinctive actor
    carries the link while a ubiquitous one cannot launder it. Softens the old hard
    exclude to a thin CONTINUOUS link: trump df=29 → 0.300 (below the 0.50 gate,
    barely propagates); a rare df=2 actor → 0.628. Empty → 0.0."""
    if not dfs:
        return 0.0
    best = max(norm_rarity(df, df_max) for df in dfs)
    return round(ACTOR_WEIGHT_BASE + ACTOR_WEIGHT_SPAN * best, 6)


# ---------------------------------------------------------------- orchestrator
@dataclass(frozen=True)
class WalkResult:
    """The full walk over one seed set — everything the endpoint needs to render.

    reached       every kept kin (deduped representatives + folded), degree/kinship/
                  acc/via, ordered strongest-first.
    reps          representative indices after same-event dedup (what to draw).
    fold_map      rep index → [folded near-duplicate indices] (the collapsed count).
    blob_flags    node indices flagged vague-blob connectors (penalized in the walk).
    graph         the kNN graph (so the endpoint can read bfh/indeg for receipts).
    """

    reached: dict[int, ReachedNode]
    reps: list[int]
    fold_map: dict[int, list[int]]
    blob_flags: set[int]
    graph: KnnGraph


def walk_constellation(whitened: np.ndarray, categories: Sequence[Optional[str]],
                       seeds: Sequence[int],
                       params: WalkParams = WalkParams()) -> WalkResult:
    """End-to-end pure walk: build the whitened kNN graph, flag blob connectors UP
    FRONT (spec §2.4 pipeline order), walk from the seeds with the locked brake +
    blob penalty, then fold same-event fragments (spec §2.6) — representatives kept
    strongest-first. Zero DB; the endpoint feeds real whitened centroids + metadata.

    An empty `reached` is the HONEST ORPHAN state (spec §8): a semantic-orphan pin
    has no measured kin — the caller renders "this story stands alone," never a
    fabricated primo."""
    graph = build_knn_graph(whitened, k=params.k)
    blob_flags = blob_connector_flags(graph, categories, params)
    reached = max_product_walk(seeds, graph, params, blob_flags=blob_flags)
    # Priority order for dedup: nearest ground first (lowest degree, then strongest
    # accumulated weight) so the representative kept is the most-grounded variant.
    order = sorted(reached, key=lambda i: (reached[i].degree, -reached[i].acc_weight))
    reps, fold_map = dedup_reached(order, whitened, tau=params.dedup_tau)
    return WalkResult(reached=reached, reps=reps, fold_map=fold_map,
                      blob_flags=blob_flags, graph=graph)
