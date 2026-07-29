"""Story-lens sibling ranking — a single-seed view over the constellation walk.

Ranking-with-receipts, NEVER merging: the transitive-collapse failure that
killed these signals as merge gates (recall-229 record) cannot occur here
because nothing is written and no closure is taken. Every sibling carries
the measured WHY.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from app.services.constellation_walk import (
    KnnGraph,
    WalkParams,
    blob_connector_flags,
    build_knn_graph,
    dedup_reached,
    max_product_walk,
)

# 11 siblings + the anchor = 12 topic ids — exactly signals.py _TOPIC_FILTER_MAX;
# the lens stream scope must never silently drop a rendered sibling.
DEFAULT_CAP = 11


@dataclass(frozen=True)
class Sibling:
    topic_key: str
    label: str
    weight: float          # accumulated walk weight (rank key)
    degree: int            # hops from the anchor
    kinship: str           # 'hermano' (direct edge) | 'primo' (walked)
    through_blob: bool
    is_blob: bool = False               # this sibling ITSELF is a flagged blob connector
    via_parent_key: str | None = None   # the node this was reached THROUGH; None when
    via_parent_label: str | None = None  # the parent IS the seed (nothing to name)
    folded: tuple[str, ...] = ()        # same-event topic_keys folded under this rep
    reasons: tuple[dict[str, str], ...] = ()  # ({'basis': str, 'value': str}, ...)


def rank_siblings(
    seed: int,
    whitened: np.ndarray,
    keys: Sequence[str],
    labels: Sequence[str],
    categories: Sequence[Optional[str]],
    params: WalkParams = WalkParams(),
    cap: int = DEFAULT_CAP,
    *,
    graph: Optional[KnnGraph] = None,
    blob_flags: Optional[set[int]] = None,
) -> list[Sibling]:
    """Rank the measured neighborhood of one topic.

    whitened: unit-norm rows (apply_whitening output) aligned with keys/labels.

    `graph`/`blob_flags` may be pre-computed by the caller — mirrors
    `constellation_walk.walk_constellation`'s own caching hook. Both depend
    only on `whitened`+`categories`+`params`, never on `seed`, so a caller
    serving many seeds over the same matrix within a TTL window (the story
    lens auto-enters on every thread open) should build the O(N^2) kNN graph
    and the blob-entropy pass ONCE and pass them in here — per-request work
    then reduces to the walk + dedup below. Omit either (the default) to have
    this function compute them itself, unchanged behavior for every existing
    caller/test.

    Misaligned arrays or a non-unit-norm seed row are CALLER programming
    errors, not honest absence — they raise loudly rather than returning []
    (a silent [] there would read as "this story stands alone," which is
    exactly the dishonest-empty class this service exists to avoid).
    """
    n = len(keys)
    if whitened.shape[0] != n or len(labels) != n or len(categories) != n:
        raise ValueError("aligned arrays required")
    if n < 2 or seed < 0 or seed >= n:
        return []
    if abs(float(np.linalg.norm(whitened[seed])) - 1.0) > 1e-3:
        raise ValueError("whitened rows must be unit-norm (apply_whitening output)")
    graph = graph if graph is not None else build_knn_graph(whitened, k=params.k)
    blobs = blob_flags if blob_flags is not None else blob_connector_flags(graph, categories, params)
    reached = max_product_walk([seed], graph, params, blob_flags=blobs)
    # Rank purely by -acc_weight (not walk_constellation's (degree, -acc_weight)
    # dedup-priority order): measured to yield equivalent rep sets here, chosen
    # so the dedup fold order matches the display order 1:1.
    ranked = sorted(
        (idx for idx in reached if idx != seed),
        key=lambda idx: -reached[idx].acc_weight,
    )
    reps, fold_map = dedup_reached(ranked, whitened, tau=params.dedup_tau)
    out: list[Sibling] = []
    for idx in reps:
        if len(out) >= cap:
            break
        node = reached[idx]
        parent_idx = node.via_parent
        if parent_idx is not None and parent_idx != seed:
            via_parent_key = keys[parent_idx]
            via_parent_label = labels[parent_idx]
        else:
            via_parent_key = None
            via_parent_label = None
        if node.degree > 1 and via_parent_label is not None:
            receipt_value = f"{node.via_weight:.2f} via {via_parent_label}"
        else:
            receipt_value = f"{node.via_weight:.2f}"
        reasons = [
            {"basis": "whitened_cos", "value": receipt_value},
            {"basis": "kinship", "value": f"{node.kinship} · {node.degree}º"},
        ]
        out.append(
            Sibling(
                topic_key=keys[idx],
                label=labels[idx],
                weight=float(node.acc_weight),
                degree=int(node.degree),
                kinship=node.kinship,
                through_blob=bool(node.through_blob),
                is_blob=idx in blobs,
                via_parent_key=via_parent_key,
                via_parent_label=via_parent_label,
                folded=tuple(keys[j] for j in fold_map.get(idx, [])),
                reasons=tuple(reasons),
            )
        )
    return out
