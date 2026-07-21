"""Edge-snapshot store — pure math (Track C1).

Spec: docs/superpowers/specs/2026-07-21-time-axis-versioned-relationships.md
§6 ("Edge-snapshot store | NEW — persist the derived edge set (identity_key
pair + degree + weight + basis) + the entity backbone per pass, so replay/
diff is cheap and churn-labelable. Small."). Sibling: the chains spec
`2026-07-21-multi-hop-transitive-chains.md` §2.1-2.4 (the walk/rarity
machinery reused here, not rebuilt).

This module computes the two derived, VERSIONED artifacts C1 persists once
per pass so a later replay/diff feature (C2/C3, not built here) can read them
cheaply instead of recomputing:

  1. topic_edge_snapshots rows (`compute_edge_rows`) — the CURRENT kinship
     graph (spec §5a): the same whitened kNN edges the walk
     (`constellation_walk.build_knn_graph`) already computes, canonicalized
     onto the CHURN-RESISTANT anchor `dynamic_topics.identity_key` (spec §4 —
     "a vanished edge is disambiguated: both keys alive + no edge = narrative
     change; a key retired/merged = substrate event"). C1 persists only the
     DIRECT graph (degree=1, "hermano" in the chains spec's kinship model);
     the multi-hop primo walk stays an on-demand from-pins computation
     (`/api/v2/dossier/walk`) and is not re-derived or stored here.

  2. entity_backbone_edges rows (`compute_backbone_rows`) — the coarse,
     long-arc entity co-occurrence spine (spec §4: "actors/places outlast
     threads... the months-long spine"), RARITY-GATED (spec §7: "else
     Trump-<anything> glues the whole backbone across all of time — #234,
     again") over a rolling window. Co-occurrence, never an asserted
     relationship (spec §7).

Everything below is PURE (stdlib + numpy only, deterministic, zero DB) so the
edge canonicalization, the null-identity skip accounting, and the rarity
formula are unit-tested without a database or the whitening asset.
`scripts/snapshot_topic_edges.py` does the I/O: it fetches the active topic
centroids + identity keys, applies the ONE global whitening
(`app/services/whitening.py` — the same commitment as the walk, chains spec
§2.2), and the topic_members-derived entity lists, then calls the functions
here and upserts the results.

Rarity-weight design note (reused, not copy-pasted): the dossier's
`actor_edge_weight` (constellation_walk.py) takes the MAX norm_rarity over a
SET of candidate shared actors — the right question there is "does ANY shared
actor give this pin-pair a strong receipt?", so the rarest available one wins.
The backbone asks a different question for a SPECIFIC pair: "how much does
THIS entity pair risk gluing unrelated topics together?" — answered by the
MORE UBIQUITOUS side (the one actually doing the gluing), so
`compute_backbone_rows` takes the MIN norm_rarity of the pair (equivalently,
the norm_rarity of whichever entity has the HIGHER document frequency). A
Trump-<anything> pair is thin because Trump is ubiquitous, regardless of how
rare the "anything" is — that is the spec §7 guarantee, and MAX would not
give it (a rare partner would make the pair read falsely strong).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import numpy as np

from app.services.constellation_walk import (
    ACTOR_WEIGHT_BASE,
    ACTOR_WEIGHT_SPAN,
    K_NEIGHBORS,
    build_knn_graph,
    norm_rarity,
)

# Entity backbone knobs (spec §7 open question 4: "entity-pair x time is
# large; rarity-gate + top-k keeps it sparse, but needs a measured cap").
DEFAULT_TOP_ENTITIES_PER_TOPIC = 8    # mirrors dossier's actors_by_base cap of 8
DEFAULT_MAX_BACKBONE_EDGES = 2000     # sparsity bound — measured cap, tune at build
DEFAULT_MIN_COOCCUR = 1


@dataclass(frozen=True)
class EdgeRow:
    """One row of `topic_edge_snapshots` — a direct (degree=1, "hermano")
    kinship edge, keyed on the churn-resistant identity_key pair
    (canonicalized identity_key_a <= identity_key_b so an unordered pair is
    stored once per snapshot, never as two directed rows)."""

    identity_key_a: str
    identity_key_b: str
    topic_id_a: str
    topic_id_b: str
    degree: int
    weight: float
    basis: str = "semantic"


@dataclass(frozen=True)
class BackboneRow:
    """One row of `entity_backbone_edges` — rarity-gated entity co-occurrence
    over a rolling window (canonicalized entity_a <= entity_b)."""

    entity_a: str
    entity_b: str
    cooccur_count: int
    rarity_weight: float


def compute_edge_rows(
    topic_ids: Sequence[str],
    identity_keys: Sequence[Optional[str]],
    whitened: np.ndarray,
    k: int = K_NEIGHBORS,
) -> tuple[list[EdgeRow], int]:
    """Build the whitened kNN graph (identical math to the walk — chains spec
    §2.2: the ONE global whitening, never a per-request refit or the raw
    universe graph) and canonicalize it into an undirected, identity_key-keyed
    edge set.

    Each UNORDERED index pair is visited once regardless of kNN asymmetry (a
    node's top-k neighbor list need not be mutual; the underlying whitened
    cosine IS symmetric since `S = W @ W.T`, so which direction supplied the
    weight never matters — a mutual pair would otherwise be double-counted).

    A pair is SKIPPED — never written with a fabricated key — when either
    side's `identity_key` is missing. The second return value is that honest
    skip count (spec instruction: "skip edges where identity_key is null with
    an honest count"), so the caller can log/report it rather than silently
    drop rows.

    Pure; `whitened` must already be the output of
    `app.services.whitening.apply_whitening` — this function does not whiten.
    """
    n = len(topic_ids)
    if len(identity_keys) != n:
        raise ValueError("topic_ids and identity_keys must be the same length")
    graph = build_knn_graph(np.asarray(whitened, dtype=np.float32), k=k)
    rows: list[EdgeRow] = []
    skipped = 0
    seen_pairs: set[frozenset] = set()
    for i in range(graph.n):
        for j, w in graph.nbrs.get(i, []):
            if i == j:
                continue
            pair_idx = frozenset((i, j))
            if pair_idx in seen_pairs:
                continue
            seen_pairs.add(pair_idx)
            ik_i, ik_j = identity_keys[i], identity_keys[j]
            if not ik_i or not ik_j:
                skipped += 1
                continue
            if ik_i == ik_j:
                continue  # defensive: two topic rows sharing one identity_key
            if ik_i <= ik_j:
                a_key, b_key, a_tid, b_tid = ik_i, ik_j, topic_ids[i], topic_ids[j]
            else:
                a_key, b_key, a_tid, b_tid = ik_j, ik_i, topic_ids[j], topic_ids[i]
            rows.append(EdgeRow(
                identity_key_a=a_key, identity_key_b=b_key,
                topic_id_a=str(a_tid), topic_id_b=str(b_tid),
                degree=1, weight=round(float(w), 6), basis="semantic",
            ))
    return rows, skipped


def compute_backbone_rows(
    topic_entities: Mapping[object, Sequence[str]],
    *,
    top_k_per_topic: int = DEFAULT_TOP_ENTITIES_PER_TOPIC,
    max_edges: int = DEFAULT_MAX_BACKBONE_EDGES,
    min_cooccur: int = DEFAULT_MIN_COOCCUR,
) -> tuple[list[BackboneRow], dict]:
    """Rarity-gated entity co-occurrence backbone (spec §4/§7).

    `topic_entities` maps a topic identifier -> its entity names in
    frequency order (most-mentioned first; already lowercased/hygiene-
    filtered by the caller — e.g. the person-subject-type gate). Only the
    top `top_k_per_topic` DISTINCT names per topic participate, bounding the
    O(k^2) pair fan-out per topic (mirrors the dossier's `actors_by_base` cap
    of 8 — same discipline, applied to a population backbone instead of a
    pin-to-pin comparison).

    Document frequency (`df`) is measured per entity across ALL topics
    passed in. Rarity weight reuses the #234 LOCKED formula
    (`0.30 + 0.68*norm_rarity`, `constellation_walk.norm_rarity` /
    `ACTOR_WEIGHT_BASE` / `ACTOR_WEIGHT_SPAN`) but driven by the MORE
    UBIQUITOUS side of the pair (min norm_rarity — see the module
    docstring): a ubiquitous entity thins every pair it is in, regardless of
    how rare its partner is that specific time — the spec §7 guarantee.

    Sparse by construction: edges are capped to the top `max_edges`, ranked
    by rarity_weight (distinctive relationships first — the backbone is a
    long-arc SPINE of notable co-occurrence, not merely a frequency count),
    then by `cooccur_count` as a tiebreaker. `cooccur_count` itself is never
    blended into the weight — the two columns are deliberately independent
    signals (raw frequency vs. measured distinctiveness).

    Returns (rows, meta): meta carries the pre-cap pair count, entity count,
    and df_max — honest provenance for the caller to log.
    """
    doc_freq: dict[str, set] = {}
    pair_counts: dict[tuple[str, str], int] = {}
    for topic_id, ents in topic_entities.items():
        uniq: list[str] = []
        seen: set[str] = set()
        for raw in ents:
            e = (raw or "").strip().lower()
            if not e or e in seen:
                continue
            seen.add(e)
            uniq.append(e)
            if len(uniq) >= top_k_per_topic:
                break
        for e in uniq:
            doc_freq.setdefault(e, set()).add(topic_id)
        for a, b in itertools.combinations(sorted(uniq), 2):
            pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1

    df_max = max((len(v) for v in doc_freq.values()), default=1)
    scored: list[BackboneRow] = []
    for (a, b), count in pair_counts.items():
        if count < min_cooccur:
            continue
        df_a = len(doc_freq.get(a, ()))
        df_b = len(doc_freq.get(b, ()))
        # MIN norm_rarity — the more-ubiquitous (higher-df) side governs the
        # weight; see module docstring for why this differs from the
        # dossier's MAX-over-candidates `actor_edge_weight`.
        r = min(norm_rarity(df_a, df_max), norm_rarity(df_b, df_max))
        weight = round(ACTOR_WEIGHT_BASE + ACTOR_WEIGHT_SPAN * r, 6)
        scored.append(BackboneRow(entity_a=a, entity_b=b,
                                  cooccur_count=count, rarity_weight=weight))
    scored.sort(key=lambda r: (-r.rarity_weight, -r.cooccur_count, r.entity_a, r.entity_b))
    kept = scored[:max_edges]
    meta = {
        "pairs_considered": len(scored),
        "pairs_kept": len(kept),
        "entities": len(doc_freq),
        "df_max": df_max,
    }
    return kept, meta
